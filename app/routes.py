"""
General Routes
"""


from datetime import datetime
import hashlib
import json

from flask import  render_template, flash, redirect, url_for, request, jsonify, send_from_directory, Blueprint
from flask_login import login_user, current_user, logout_user, login_required

from app.extensions import db, bcrypt
from app.forms import SignUpForm, LoginForm, ResetRequestForm, ResetPasswordForm, UpdateProfileForm
from app.models import User, EventDetails, Payments, Events
from app.utils import is_code_applicable, save_image, get_upload_dir
from app.init_data import pass_name
from app.mail_utils import send_mail_http as send_mail

bp = Blueprint("", __name__)

@bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """
    used primarily for serving uploaded files paths
    example
    <img src="{{ url_for('uploaded_file', filename='payment_screenshots/tx12345.png') }}"/>
    """
    base_dir = get_upload_dir()
    return send_from_directory(base_dir, filename, as_attachment=False)

@bp.route('/')
def home():
    event_types = json.load(open('event_types.json'))
    return render_template('home.html', title='', event_types=event_types)

@bp.route('/signup', methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        flash('Already Logged In. Please Log Out to Register', 'info')
        return redirect(url_for('dashboard'))

    form = SignUpForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        if form.dept.data == 'Other':
            dept = form.other_dept_name.data
        else:
            dept = form.dept.data

        if form.college.data == 'Other':
            clg = form.other_college_name.data
        else:
            clg = form.college.data

        user = User(
            name=form.name.data,
            email=form.email.data,
            reg_no=form.reg_no.data,
            dept = dept,
            college = clg,
            events='',
            password=hashed_password,
            mobile=form.mobile.data,
            )
        db.session.add(user)
        db.session.commit()

        subject = 'Welcome to <Symposium-Name> \'23'
        to = user.email
        # sample body template while; mail sent when a user creates an account in the website
        body = f'''
        Reserve the dates ... for taking part in interesting events!!!
        Take a look at the events {url_for('events', _external=True)}<br><br>

        Don't forget <b> some event <b> is waiting for you !!!! <br><br>
        
        <a href="{url_for('events', _external=True)}">Register for events</a> <br><br><br>
        '''
        ret = send_mail(to, subject, body, body_format='html')
        flash(f'Account has been created for { form.name.data } ! You can now log in', 'success')
        if ret['status'] != 'success':
            flash('Unable to send welcome Mail; Contact admin for details', 'danger')
        return redirect(url_for('login'))

    return render_template('signup.html', title='Register', form=form, active_page='signup')


@bp.route('/login', methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash('Already Logged In.', 'info')
        return redirect(url_for('dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data, reg_no=form.reg_no.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('Logged In!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html', title='Login', form=form, active_page='login')

@bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash('Successfully Logged Out!', 'success')

    return redirect(url_for('home'))

def send_reset_email(user):
    m = 5
    token = user.get_reset_token(m*60) #120 sec valid token
    subject = 'Password Reset Request | <Symposium-Name> year'
    to = user.email
    body = f'''
    To reset Password, Click on the following link (expires in {m} mins)
    {url_for('reset_password', token=token, _external=True)}
    '''
    ret = send_mail(to, subject, body)
    if ret['status'] != 'success':
        flash('Unable to send mail; Contact admin', 'danger')
    return ret

@bp.route('/forgot-password', methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = ResetRequestForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data, reg_no=form.reg_no.data).first()
        ret = send_reset_email(user)
        if 'success' in ret:
            flash('Please check your mail for reset !', 'info')
        return redirect(url_for('login'))

    return render_template('forgot_password.html', title='Forgot Password', form=form)

@bp.route('/forgot-password/<token>', methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid request or Expired token !!!', 'warning')
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been reset! ', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', title='Reset Password',form=form)


@bp.route('/dashboard')
@login_required
def dashboard():
    user_events = current_user.events.split(',')
    events_dict = {}
    for i in user_events:
        events_dict[i] = EventDetails.query.filter_by(event_id=i).first()

    p = Payments.query.filter_by(reg_no=current_user.reg_no, is_valid_payment=True).all()
    types = [i.pass_type for i in p]
    passes = []
    for i in types:
        try:
            passes.append(pass_name[i])
        except Exception as e:
            print("Error in pass name fetching: ", e)
            passes.append(i)

    code_possible = is_code_applicable()

    return render_template('dashboard.html', title=current_user.name,
        events_dict=events_dict, passes=passes, code_possible=code_possible
    )

# based on institution previlegde
@bp.route('/verify-code-mit', methods=['POST'])
@login_required
def verify_code_mit():
    data = dict(request.form)
    code_ori = hashlib.sha256(current_user.reg_no.encode('utf-8')).hexdigest()[20:50]
    code_possible = is_code_applicable()
    if not code_possible:
        return jsonify({'message':'error code only for MIT'})

    if data['code'] == code_ori:
        p = Payments(
            reg_no=current_user.reg_no,
            pass_type='p4',
            screenshot='logo.png',
            tx_no='Via_Code_'+current_user.reg_no,
            is_valid_payment = True
        )

        db.session.add(p)
        db.session.commit()

        return jsonify({'message':'Success ! You can attend all events'})

    return jsonify({'message':'Failed to get pass ; invalid code or invaid user'})

# based on institution previlegde

@bp.route('/send-code-mit')
@login_required
def send_code_mit():
    code_possible = is_code_applicable()

    if code_possible:
        code = hashlib.sha256(current_user.reg_no.encode('utf-8')).hexdigest()[20:50]
        msg = f"""
Your Code : {code}
<br><br>
THIS PASS IS SUBJECT TO VERIFICATION AT REGISTRATION DESK !!!
<br><br>
"""
        ret = send_mail(current_user.email,
            'Code for Getting access to All events | <Symposium-Name> year',
            msg,
            body_format='html'
        )
        if ret['status'] != 'success':
            flash('Unable to send mail; Contact admin', 'danger')
        else:
            flash('Mail Sent','success')
        return redirect(url_for('dashboard'))

    flash('Invalid Request','danger')
    return redirect(url_for('dashboard'))

@bp.route('/update-profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    form = UpdateProfileForm()

    if form.validate_on_submit():
        if form.dept.data == 'Other':
            dept = form.other_dept_name.data
        else:
            dept = form.dept.data

        if form.college.data == 'Other':
            clg = form.other_college_name.data
        else:
            clg = form.college.data

        user = User.query.filter_by(reg_no=current_user.reg_no).first()
        user.email = form.email.data
        user.name = form.name.data
        user.college = clg
        user.dept = dept
        user.mobile = form.mobile.data

        db.session.commit()
        flash('Profile Updated !', 'success')
        return redirect(url_for('dashboard'))

    return render_template('update_profile.html', form=form)

# based on pass idea you have for your sympo
@bp.route('/buy-pass')
@login_required
def buy_pass():
    not_eligible = []
    is_eligible = eligible_events()
    if 'premium ' in is_eligible:
        not_eligible.extend(['p1','p4','p51','p52','p7'])
    if 'non_tech' in is_eligible:
        not_eligible.extend(['p3','p4','p51','p7'])
    if 'tech' in is_eligible:
        not_eligible.extend(['p2','p4','p52','p7'])
    # print(eligible_events())
    return render_template('buy_pass.html', not_eligible=not_eligible)

@bp.route('/get-user', methods=['POST'])
@login_required
def get_user():
    data = dict(request.form)

    r = {}
    regno1 = data['regno1']
    regno2 = data['regno2']

    msg = ''

    f1 = False
    f2 = False
    u1 = User.query.filter_by(reg_no=regno1).first()
    if u1:
        u1passes = Payments.query.filter_by(reg_no=u1.reg_no).all()
        if u1passes:
            u1ptyes = [p.pass_type for p in u1passes]
            if 'p4' in u1ptyes:
                return jsonify({'msg':f'Registration Number :{regno1} has already the pass'})
        else:
            f1 = True
            r['u1'] = {'name':u1.name,'college':u1.college,'mobile':u1.mobile}
    else:
        msg += f'Registration Number ({regno1}) seems not existing'

    u2 = User.query.filter_by(reg_no=regno2).first()
    if u2:
        u2passes = Payments.query.filter_by(reg_no=u2.reg_no).all()
        if u2passes:
            u2ptyes = [p.pass_type for p in u2passes]
            if 'p4' in u2ptyes:
                return jsonify({'msg':f'Registration Number :{regno2} has already the pass'})
        else:
            f2 = True
            r['u2'] = {'name':u2.name,'college':u2.college,'mobile':u2.mobile}
    else:
        msg += f'<br><br>Registration Number ({regno2}) seems not existing'
    # print(u1passes)

    if u1 and u2 and f1 and f2:
        if u1.reg_no == u2.reg_no:
            return jsonify({'msg':'Same User repeated'})
        r.update({'msg':'Passes for these users can be obtained', 'success':'success'})
        return jsonify(r)

    return jsonify({'msg':msg})

@bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    if request.method == 'POST':
        data = dict(request.form)

        pa = Payments.query.filter_by(tx_no=data['tx-id']).first()
        if pa:
            flash('A proof with this is already submitted', 'danger')
            return redirect(url_for('dashboard'))

        if not 'screenshot' in request.files:
            flash('Invalid Proof or proof not uploaded !')
            return redirect(url_for('dashboard'))

        image = request.files['screenshot']
        _, _, filename = save_image(
            image,
            filename=data['tx-id'].strip(),
            category='payment_screenshots'
        )
        if not filename:
            flash('Error in uploading proof image !', 'danger')
            return redirect(url_for('dashboard'))

        p = Payments(
            reg_no=data['reg_no'],
            pass_type=data['pass_type'],
            tx_no=data['tx-id'].strip(),
            screenshot=filename,
            amount=data['amount'],
            is_valid_payment=False
        )
        db.session.add(p)
        db.session.commit()

        flash('Payment Submitted; You\'ll be notified upon Verification', 'success')
        return redirect(url_for('dashboard'))

    amount = request.args.get('amount')
    reg_no = request.args.get('reg_no')
    pass_type = request.args.get('pass_type')
    workshop_name = ''
    if pass_type and 'workshop' in pass_type:
        workshop_name = EventDetails.query.filter_by(event_id=pass_type[-5:]).first().name

    verifiers = User.query.filter_by(isVerifier=True, isAdministrator=False).all()

    return render_template('payment.html', amount=amount,
        reg_no=reg_no, pass_type=pass_type, pass_name=pass_name,
        workshop_name=workshop_name, verifiers=verifiers
    )

@bp.route('/callback', methods=['POST'])
@login_required
def callback():
    data = dict(request.form)
    tx_no = data['tx_no']
    p = Payments.query.filter_by(tx_no=tx_no).first()
    if not p:
        return jsonify({'message' : 'Not a valid payment'})

    p.is_valid_payment = data['new_status'] == 'true'
    db.session.commit()
    err_msg = ''
    if p.is_valid_payment:
        for i in p.reg_no.split(','):
            if i:
                u = User.query.filter_by(reg_no=i).first()
                ret = send_mail(u.email, 'Transaction found in Order | <Symposium-Name>', f'Your Payment with Transaction number {tx_no} is found in order and is accepted')
                err_msg += ret['details'] + '\n'
                try:
                    if 'workshop' in p.pass_type:
                        _, idx = p.pass_type.split('_')
                        u = User.query.filter_by(reg_no=p.reg_no).first()
                        if u.events:
                            u.events += idx+','
                        else:
                            u.events = idx+','

                        evt = EventDetails.query.filter_by(event_id=idx).first()
                        evt.n_registrations += 1

                        evt_reg = Events(
                        event_id=idx,
                        reg_no = p.reg_no,
                        time=str(datetime.now()),
                        )
                        db.session.add(evt_reg)

                        subject = 'Registation Successful | <Symposium-Name> year'
                        to = u.email
                        body = f'''<br>
                        Successfully Registered for {evt.name} ! <br><br>
                        '''
                        body += evt.on_register_mail_cnt
                        ret = send_mail(to, subject, body, body_format='html')
                        err_msg += f'{ret["details"]}\n'

                    elif p.pass_type not in ['p1','p2','p3','p4','p51','p52','p6','p7']:
                        if 'workshop' in p.pass_type:
                            _, idx = p.pass_type.split('_')
                            u = User.query.filter_by(reg_no=p.reg_no).first()
                            if u.events:
                                u.events += idx+','
                            else:
                                u.events = idx+','

                            evt = EventDetails.query.filter_by(event_id=idx).first()
                            evt.n_registrations += 1

                            evt_reg = Events(
                            event_id=idx,
                            reg_no = p.reg_no,
                            time=str(datetime.now()),
                            )
                            db.session.add(evt_reg)

                            subject = 'Registation Successful | <Symposium-Name> year'
                            to = u.email
                            body = f'''<br>
                            Successfully Registered for {evt.name} ! <br><br>
                            '''
                            body += evt.on_register_mail_cnt
                            ret = send_mail(to, subject, body, body_format='html')
                            err_msg = f'{ret["details"]}\n'
                    db.session.commit()
                    msg = 'success (updated as verified) \n'
                    if err_msg:
                        msg +=  f"Mailing Errors: {err_msg}\n"
                    return jsonify({'success':msg})
                except Exception as e:
                    return jsonify({'message':str(e)})
    else:
        err_msg = ""
        for i in p.reg_no.split(','):
            if i:
                u = User.query.filter_by(reg_no=i).first()
                msg = f"""
Your Payment with Transaction number {tx_no} is put to verification.
Please feel free to contact the organisers in case of discrepencies
"""
                ret = send_mail(
                    u.email,
                    'Transaction Alert | <Symposium-Name> year',
                    msg
                )
                err_msg += f'{ret["details"]}\n'
        msg = 'success (updated as NOT verified)\n'
        if err_msg:
            msg +=  f"Mailing Errors: {err_msg}\n"
        return jsonify({'success':msg})


@bp.route('/events')
def events():
    event_types = json.load(open('event_types.json'))
    return render_template('events.html', title='Events', active_page='events', event_types=event_types)

@bp.route('/tech-events')
def tech_events():
    all_events = EventDetails.query.filter_by(category='tech', is_event_accepted=True).all()
    return render_template('events_list.html', title='Tech Events', active_page='events', events=all_events, header='Technical Events')

@bp.route('/non-tech-events')
def non_tech_events():
    all_events = EventDetails.query.filter_by(category='non_tech', is_event_accepted=True).all()
    return render_template('events_list.html', title='Non Tech Events', active_page='events', events=all_events, header='Non Technical Events')

@bp.route('/premium-events')
def premium_events():
    all_events = EventDetails.query.filter_by(category='premium', is_event_accepted=True).all()
    return render_template('events_list.html', title='Premium Events', active_page='events', events=all_events, header='Premium Events')

@bp.route('/workshops')
def workshops():
    all_events = EventDetails.query.filter_by(category='workshop', is_event_accepted=True).all()
    return render_template('events_list.html', title='Workshops', active_page='events', events=all_events, header='Workshops')

# define your own eligibility criteria
def eligible_events():
    p = Payments.query.filter_by(reg_no=current_user.reg_no, is_valid_payment=True).all()
    types = [i.pass_type for i in p]
    is_eligible = []
    if 'p1' in types or 'Premium Pass (All Premium Events)' in types:
        is_eligible.extend(['premium'])
    if 'p2' in types or 'Tech Pass (All Tech Events)' in types:
        is_eligible.extend(['tech'])
    if 'p3' in types or 'Non Tech Pass (All Non-Tech Events)' in types:
        is_eligible.extend(['non_tech'])
    if 'p4' in types or 'Diamond Pass (All Events)' in types:
        is_eligible.extend(['tech','non_tech','premium'])
    if 'p51' in types or 'Platinum Pass (All Premium and Non-Tech Events)' in types:
        is_eligible.extend(['non_tech', 'premium'])
    if 'p52' in types or 'Platinum Pass (All Premium and Tech Events)' in types:
        is_eligible.extend(['tech','premium'])
    if 'p6' in types or 'Gold Pass (All Tech and Non-Tech Events)' in types:
        is_eligible.extend(['tech','non_tech'])
    if 'p7' in types or 'Combo Pass (All Events ; 3 Participants)' in types:
        is_eligible.extend(['tech','non_tech','premium'])

    return is_eligible

@bp.route('/event-details/<idx>')
def event_details(idx):
    event = EventDetails.query.filter_by(event_id=idx).first()

    if not event:
        flash('Seems like event no longer exist please contact the support team', 'danger')
        return redirect(url_for('home'))

    if not event.is_event_accepted:
        flash('Seems like event no longer exist please contact the support team', 'danger')
        return redirect(url_for('home'))

    code_possible = is_code_applicable()

    if idx in ['Xlwac', 'bhDMT'] and (not code_possible):
        flash('This event is only for MIT Students', 'danger')
        return redirect(url_for('home'))

    is_eligible = []
    if current_user.is_authenticated:
        is_eligible.append('workshop')
        is_eligible.extend(eligible_events())

    organiser_details = []
    o1 = User.query.filter_by(reg_no=event.primary_organiser).first()
    organiser_details.append(
        {
            'name' : o1.name,
            'mobile' : o1.mobile
        }
    )

    for reg_no in event.other_organisers.split(','):
        i = User.query.filter_by(reg_no=reg_no).first()
        if i:
            organiser_details.append({
                    'name' : i.name,
                    'mobile' : i.mobile
            })

    if not event.is_result_accepted:
        return render_template('event_details.html', event=event, id=idx,
            organiser_details=organiser_details, is_eligible=is_eligible)

    winners = []
    runners = []
    if event.winner:
        for i in event.winner.split(','):
            winners.append(User.query.filter_by(reg_no=i).first())

    if event.runner:
        for i in event.runner.split(','):
            runners.append(User.query.filter_by(reg_no=i).first())

    return render_template('event_result.html', winners=winners, runners=runners, event=event)


@bp.route('/register', methods=["POST"])
@login_required
def register():
    data = dict(request.form)
    users = []
    try:
        for key, value in data.items():
            if 'reg' not in key:
                continue
            try:
                x = User.query.filter_by(reg_no=value).first()
                if x:
                    if data['id'] in x.events.split(','):
                        return jsonify({"error": f'{x.reg_no} Already registered!'})

                    users.append(x)
                else:
                    return jsonify({"error":f'{value} does not have an account !'})

            except Exception as e:
                return jsonify({"error":str(e)})

        r = ''
        users = set(users)

        for i in users:
            p = Payments.query.filter_by(reg_no=i.reg_no).all()
            if not p:
                return jsonify({'error':'No pass!'})

            evt = EventDetails.query.filter_by(event_id=data['id']).first()
            is_eligible = eligible_events()
            if evt.category not in is_eligible:
                return jsonify({'error':'No pass!'})

        for i in users:
            r+=(str(i.reg_no)+',')
            i.events += data['id']+','

        evt = EventDetails.query.filter_by(event_id=data['id']).first()

        if not evt.is_accepting_registration:
            raise Exception("This event is no loonger accepting registrations")
            # return jsonify({"error":"This event is no loonger accepting registrations"})

        evt_reg = Events(
            event_id=data['id'],
            reg_no = r[:-1],
            time=str(datetime.now()),
            )

        evt.n_registrations += 1

        db.session.add(evt_reg)
        db.session.commit()

        people = evt_reg.reg_no.split(',')
        for i in users:
            subject = 'Registation Successful | <Symposium-Name> year'
            to = i.email
            body = f'''<br>
            Successfully Registered for {EventDetails.query.filter_by(event_id=data['id']).first().name} ! <br><br>
            Team Members : {', '.join(people)} <br>
            '''
            body += evt.on_register_mail_cnt
            try:
                ret = send_mail(to, subject, body, body_format='html')
            except Exception as e:
                print(e)
            msg = "registered!\n"
            if ret['status'] != 'success':
                msg += "Unable to send mail; contact admin\n"
        return jsonify({"success":msg})
    except Exception as e:
        return jsonify({"error":f'{e}'})

@bp.route('/sympo/admin/see/data', methods=["GET", "POST"])
@login_required
def admin_login():
    # allow certain user to see data like "current_user.id == 66"
    # when you don't want to give them admin access
    # if not (current_user.isAdministrator or current_user.id == 66):
    #     flash('Invalid Route','danger')
    #     return redirect(url_for('dashboard'))

    if not current_user.isAdministrator:
        # to monitor admin logins - super admin
        send_mail('super_admin@domain.com', 'Admin Login Detected', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    data = []
    evts = Events.query.order_by(Events.event_id).all()

    all_events = EventDetails.query.with_entities(EventDetails.event_id, EventDetails.name).all()

    for i in evts:
        name = EventDetails.query.filter_by(event_id=i.event_id).first().name
        us = []
        for i in i.reg_no.split(','):
            if i:
                u = User.query.filter_by(reg_no=i).first()
                us.append((u.name, u.reg_no, u.mobile, u.email))
        data.append((name, us))
    return render_template('data.html', data=data, events=all_events)

def get_data(event_id):
    data = []
    if event_id == 'all':
        evts = Events.query.order_by(Events.event_id).all()
    else:
        evts = Events.query.filter_by(event_id=event_id).all()

    for i in evts:
        name = EventDetails.query.filter_by(event_id=i.event_id).first().name
        us = []
        for i in i.reg_no.split(','):
            if i:
                u = User.query.filter_by(reg_no=i).first()
                us.append((u.name, u.reg_no, u.mobile, u.email))
        data.append((name, us))

    return data

@bp.route('/refresh', methods=["POST"])
@login_required
def refresh():
    if not current_user.isAdministrator:
        return jsonify({'html':'error'})

    req = dict(request.form)
    # print(data)
    if req['request'] == 'refresh':
        data = get_data(req['event_id'])
        return jsonify({"html":render_template('admin_data_content.html', data=data), "time":str(datetime.now())})
    return jsonify({"html":"error"})

@bp.route('/send-sample-mail', methods=['POST'])
@login_required
def send_sample_mail():
    data = dict(request.form)
    idx = data['id']
    if not current_user.isOrganiser:
        return jsonify({'message':'Not an organiser'})
    e = EventDetails.query.filter_by(event_id=idx).first()
    if not e:
        return jsonify({'message':'No such event'})
    organiser_reg_nos = [e.primary_organiser]
    organiser_reg_nos.extend(e.other_organisers.split(','))
    if not current_user.isAdministrator:
        if current_user.reg_no not in organiser_reg_nos and not current_user.isOrganiser:
            return jsonify({'message':f'You are not the organiser of Event {e.name}!'})

    subject = 'Registation Successful | <Symposium-Name> year <Sample ; for Organiser>'
    to = current_user.email
    body = f'''<br>
    Successfully Registered for {e.name} ! <br><br>
    Team Members : (team members registration numbers will be displayed here) <br><br>
    '''
    body += e.on_register_mail_cnt
    ret = send_mail(to, subject, body, body_format='html')
    if ret['status'] != 'success':
        return jsonify({'message':'Unable to send Mail; Contact Admin'})
    return jsonify({'message':'Mail sent'})

@bp.route('/bg/certificate')
@login_required
def certificate():
    return 'contact admin' # CHANGE: remove when required
    try:
        if not current_user.isAdministrator:
            # to monitor admin logins - super admin
            send_mail('super_admin@domain.com', 'Certificate Writing Login Detected | <Symposium-Name> year', f'Certificate Login by : {current_user.name}, {current_user.reg_no}, {current_user.mobile}')
    except:
        pass
    return render_template('certificate_data.html')


@bp.route('/certificate-content', methods=['POST'])
@login_required
def certificate_content():
    return jsonify({'html':'contact admin'})
    data = []
    evts = Events.query.filter_by(event_attended=True).order_by(Events.time.asc()).all()
    for i in evts:
        e = EventDetails.query.filter_by(event_id=i.event_id).first()
        for i in i.reg_no.split(','):
            if i:
                u = User.query.filter_by(reg_no=i).first()
                data.append([e, u])

    return jsonify({"html":render_template('certificate_content.html', data=data), "time":str(datetime.now())})

# ******** remove after testing ***********
@bp.route('/beta/send_message/<msg>/to/<idx>')
def send(msg, idx):
    message = send_mail(idx, 'Hello(Beta)', msg)
    return message

# ****************************************
