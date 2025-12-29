"""
Routes
"""


from datetime import datetime
import hashlib
import json
import random
import string
from io import BytesIO
import xlsxwriter

from flask import  render_template, flash, redirect, url_for, request, jsonify, send_file, send_from_directory
from flask_login import login_user, current_user, logout_user, login_required

from app import app, db, bcrypt, upload_dir, static_dir
from app.forms import *
from app.models import *
# from app.send_mail_smtp import send_mail
from app.send_mail_http import send_mail_http as send_mail
from app.utils import is_code_applicable, save_image

# hash_file = hashlib.sha256()

# modify the pass names as per the sympo
pass_name = {
    'p1' : 'Premium Pass (All Premium Events)',
    'p2' : 'Tech Pass (All Tech Events)',
    'p3' : 'Non Tech Pass (All Non-Tech Events)',
    'p4' : 'Diamond Pass (All Events)',
    'p51' : 'Platinum Pass (All Premium and Non-Tech Events)',
    'p52' : 'Platinum Pass (All Premium and Tech Events)',
    'p6' : 'Gold Pass (All Tech and Non-Tech Events)',
    'p7' : 'Combo Pass (All Events ; 3 Participants)',
    'workshop_hIvTL':'Empowering Chip Design Innovators: RISC-V Workshop with Skywater 130nm Chips',
    'workshop_TRawK':'Data analysis on different domain Model training and advancements',
    'workshop_mOXHL':'Deep Learning using Python',
    'workshop_gjhuR':'Different types of multiple access technologies and 5G usage scenarios with its key capabilities'
}

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """
    used primarily for serving uploaded files paths
    example
    <img src="{{ url_for('uploaded_file', filename='payment_screenshots/tx12345.png') }}"/>
    """
    base_dir = upload_dir.absolute()
    return send_from_directory(base_dir, filename, as_attachment=False)

@app.route('/')
def home():
    event_types = json.load(open('event_types.json'))
    return render_template('home.html', title='', event_types=event_types)

@app.route('/signup', methods=["GET", "POST"])
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
        ret = send_mail(to, subject, body, format='html')
        flash(f'Account has been created for { form.name.data } ! You can now log in', 'success')
        if 'success' not in ret:
            flash('Unable to send welcome Mail; Contact admin for details', 'danger')
        return redirect(url_for('login'))

    return render_template('signup.html', title='Register', form=form, active_page='signup')


@app.route('/login', methods=["GET", "POST"])
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

@app.route('/logout')
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
    if 'success' not in ret:
        flash('Unable to send mail; Contact admin', 'danger')
    return ret

@app.route('/forgot-password', methods=["GET", "POST"])
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

@app.route('/forgot-password/<token>', methods=["GET", "POST"])
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


@app.route('/dashboard')
@login_required
def dashboard():
    events = current_user.events.split(',')
    events_dict = {}
    for i in events:
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
@app.route('/verify-code-mit', methods=['POST'])
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

@app.route('/send-code-mit')
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
            format='html'
        )
        if 'success' not in ret:
            flash('Unable to send mail; Contact admin', 'danger')
        else:
            flash('Mail Sent','success')
        return redirect(url_for('dashboard'))

    flash('Invalid Request','danger')
    return redirect(url_for('dashboard'))

@app.route('/update-profile', methods=['GET', 'POST'])
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
@app.route('/buy-pass')
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

@app.route('/get-user', methods=['POST'])
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

@app.route('/payment', methods=['GET', 'POST'])
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

@app.route('/callback', methods=['POST'])
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
                err_msg += ret + '\n'
                try:
                    if 'workshop' in p.pass_type:
                        _, id = p.pass_type.split('_')
                        u = User.query.filter_by(reg_no=p.reg_no).first()
                        if u.events:
                            u.events += id+','
                        else:
                            u.events = id+','

                        evt = EventDetails.query.filter_by(event_id=id).first()
                        evt.n_registrations += 1

                        evt_reg = Events(
                        event_id=id,
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
                        ret = send_mail(to, subject, body, format='html')
                        err_msg += f'{ret}\n'

                    elif p.pass_type not in ['p1','p2','p3','p4','p51','p52','p6','p7']:
                        if 'workshop' in p.pass_type:
                            _, id = p.pass_type.split('_')
                            u = User.query.filter_by(reg_no=p.reg_no).first()
                            if u.events:
                                u.events += id+','
                            else:
                                u.events = id+','

                            evt = EventDetails.query.filter_by(event_id=id).first()
                            evt.n_registrations += 1

                            evt_reg = Events(
                            event_id=id,
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
                            ret = send_mail(to, subject, body, format='html')
                            err_msg = f'{ret}\n'
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
                err_msg += f'{ret}\n'
        msg = 'success (updated as NOT verified)\n'
        if err_msg:
            msg +=  f"Mailing Errors: {err_msg}\n"
        return jsonify({'success':msg})


@app.route('/verifier-verify')
@login_required
def verifier_verify():
    if not current_user.isVerifier:
        flash('Invalid Route !', 'danger')
        return redirect(url_for('organiser_dashboard'))

    p = []
    payments = Payments.query.filter_by(is_valid_payment=False).all()

    for i in payments:
        u = User.query.filter_by(reg_no=i.reg_no).first()
        p.append((i, u))

    return render_template('verifier_verify.html', payments=p)

@app.route('/verifier-verify-all')
@login_required
def verifier_verify_all():
    if not current_user.isVerifier:
        flash('Invalid Route !', 'danger')
        return redirect(url_for('organiser_dashboard'))

    p = []
    payments = Payments.query.all()
    for i in payments:
        u = User.query.filter_by(reg_no=i.reg_no).first()
        p.append((i, u))

    return render_template('verifier_verify.html', payments=p)

@app.route('/events')
def events():
    event_types = json.load(open('event_types.json'))
    return render_template('events.html', title='Events', active_page='events', event_types=event_types)

@app.route('/tech-events')
def tech_events():
    all_events = EventDetails.query.filter_by(category='tech', is_event_accepted=True).all()
    return render_template('events_list.html', title='Tech Events', active_page='events', events=all_events, header='Technical Events')

@app.route('/non-tech-events')
def non_tech_events():
    all_events = EventDetails.query.filter_by(category='non_tech', is_event_accepted=True).all()
    return render_template('events_list.html', title='Non Tech Events', active_page='events', events=all_events, header='Non Technical Events')

@app.route('/premium-events')
def premium_events():
    all_events = EventDetails.query.filter_by(category='premium', is_event_accepted=True).all()
    return render_template('events_list.html', title='Premium Events', active_page='events', events=all_events, header='Premium Events')

@app.route('/workshops')
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

@app.route('/event-details/<idx>')
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


@app.route('/register', methods=["POST"])
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
                ret = send_mail(to, subject, body, format='html')
            except Exception as e:
                print(e)
            msg = "registered!\n"
            if 'success' not in ret:
                msg += "Unable to send mail; contact admin\n"
        return jsonify({"success":msg})
    except Exception as e:
        return jsonify({"error":f'{e}'})

@app.route('/sympo/admin/see/data', methods=["GET", "POST"])
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

@app.route('/refresh', methods=["POST"])
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

@app.route('/organiser/dashboard')
@login_required
def organiser_dashboard():
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    events = EventDetails.query.filter_by(primary_organiser=current_user.reg_no)
    return render_template('organiser_dashboard.html', events=events)

@app.route('/organiser/create-event', methods=['GET', 'POST'])
@login_required
def organiser_create_event():
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        details = dict(request.form)
        # print(details)
        rounds = {}
        ids = []
        for i in details.keys():
            if 'rd_' == i[:3]:
                _, _, idx = i.split('_')
                ids.append(idx)

        for i in ids:
            rounds.update({i:{}})

        for i, _ in rounds.items():
            for j, _ in details.items():
                if 'rd_' == j[:3]:
                    _, t, idx = j.split('_')
                    if i == idx:
                        rounds[i].update({t:details['rd_'+t+'_'+idx]})

        n_rounds = len(rounds.keys())

        organisers = []
        for j, val in details.items():
            if 'org_' == j[:4]:
                organisers.append(val)

        num_organisers = 1 + len(organisers)

        event_id = ''.join(random.choice(string.ascii_letters) for _ in range(5))

        cost = 0
        if details['category'] == 'workshop':
            cost = details['cost']

        event_pic = 'default.jpg'
        if 'event_pic' in request.files:
            image = request.files['event_pic']
            _, _, new_path = save_image(
                image,
                filename=event_id,
                category='event_thumbnails'
            )
            event_pic = new_path or event_pic

        evt = EventDetails(
            event_id=event_id,
            name=details['name'],
            category=details['category'],
            description=details['description'],
            primary_organiser=current_user.reg_no,
            max_team_size=details['max_team_size'],
            num_rounds=n_rounds,
            rounds=rounds,
            other_organisers=','.join(organisers),
            num_organisers=num_organisers,
            thumbnail=event_pic,
            topic=details['topic'],
            event_cost=cost,
            on_register_mail_cnt = details['mail_cnt']
        )

        if current_user.org_events:
            current_user.org_events += event_id + ','
        else:
            current_user.org_events = event_id + ','

        for i in organisers:
            user = User.query.filter_by(reg_no=i).first()
            if not user:
                flash('Some organiser doesn\'t seem to have an account', 'warning')
            else:
                if user.org_events:
                    user.org_events += event_id + ','
                else:
                    user.org_events = event_id + ','
        db.session.add(evt)
        db.session.commit()

        flash('Event Created Successfully', 'success')
        return redirect(url_for('organiser_dashboard'))

    return render_template('organiser_create_event.html')


@app.route('/organiser/event/<idx>', methods=['GET', 'POST'])
@login_required
def organiser_event(idx):
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        evt = EventDetails.query.filter_by(event_id=idx).first()
        if not evt:
            flash('Unable to find event !', 'danger')
            return redirect(url_for('organiser_dashboard'))
        orgs = [evt.primary_organiser]
        orgs.extend(evt.other_organisers.split(','))
        for i in orgs:
            u = User.query.filter_by(reg_no=i).first()
            if u:
                if u.org_events:
                    u.org_events = u.org_events.replace(evt.event_id+',', '')
        db.session.commit()

        details = dict(request.form)
        # print(details)
        rounds = {}
        ids = []
        for i in details.keys():
            if 'rd_' == i[:3]:
                _, _, id_rd = i.split('_')
                ids.append(id_rd)

        for i in ids:
            rounds.update({i:{}})

        for i, _ in rounds.items():
            for j, _ in details.items():
                if 'rd_' == j[:3]:
                    _, t, id_rd = j.split('_')
                    if i == id_rd:
                        rounds[i].update({t:details['rd_'+t+'_'+id_rd]})

        n_rounds = len(rounds.keys())

        organisers = []
        for j, val in details.items():
            if 'org_' == j[:4]:
                organisers.append(val)
        organisers.append(evt.primary_organiser)
        num_organisers = len(organisers)

        event_pic = evt.thumbnail
        if 'event_pic' in request.files:
            image = request.files['event_pic']
            _, _, new_path = save_image(
                image,
                filename=idx,
                category='event_thumbnails'
            )
            event_pic = new_path or event_pic

        evt.name=details['name']
        evt.category=details['category']
        evt.description=details['description']
        evt.max_team_size=details['max_team_size']
        evt.num_rounds=n_rounds
        evt.rounds=rounds
        evt.other_organisers=','.join(organisers[:-1])
        evt.num_organisers=num_organisers
        evt.thumbnail=event_pic
        evt.topic=details['topic']
        evt.on_register_mail_cnt=details['mail_cnt']

        for i in organisers:
            user = User.query.filter_by(reg_no=i).first()
            if not user:
                flash('Some organiser doesn\'t seem to have an account', 'warning')
            else:
                if user.org_events:
                    user.org_events += idx + ','
                else:
                    user.org_events = idx + ','

        db.session.commit()

        flash('Event Updated Successfully', 'success')
        return redirect(url_for('organiser_dashboard'))

    evt = EventDetails.query.filter_by(event_idx=idx).first()

    if not evt:
        flash('No Such Event Exists', 'danger')
        return redirect(url_for('organiser_dashboard'))

    organiser_reg_nos = [evt.primary_organiser]
    organiser_reg_nos.extend(evt.other_organisers.split(','))

    if not current_user.isAdministrator:
        if current_user.reg_no not in organiser_reg_nos and not current_user.isOrganiser:
            flash(f'You are not the organiser of Event {evt.name}!', 'danger')
            return redirect(url_for('dashboard'))

    event_rounds = []

    for i in evt.rounds.values():
        event_rounds.append(i)

    event_organisers = evt.other_organisers.split(',')
    event_organisers.append(evt.primary_organiser)
    for i in event_organisers:
        if current_user.reg_no == i:
            pass
            #event_organisers.remove(i)

    evts = Events.query.filter_by(event_id=idx).all()
    data = []
    for event in evts:
        us = []
        e = EventDetails.query.filter_by(event_id=idx).first()
        for i in event.reg_no.split(','):
            if i:
                u = User.query.filter_by(reg_no=i).first()
                is_winner = False
                is_runner = False
                if e.winner:
                    if u.reg_no in e.winner.split(','):
                        is_winner = True
                if e.runner:
                    if u.reg_no in e.runner.split(','):
                        is_runner = True

                us.append((u.name, u.reg_no, u.mobile, u.email, u.id, is_winner, is_runner))
        data.append([us]+[event.event_attended, event.id])

    return render_template('organiser_event_details.html', event=evt,
        registered=data, event_rounds=event_rounds,
        event_organisers=event_organisers
    )


@app.route('/organiser/event/<idx>/download')
@login_required
def organiser_event_download(idx):
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    evt = EventDetails.query.filter_by(event_id=idx).first()

    if not evt:
        flash('No Such Event Exists', 'danger')
        return redirect(url_for('organiser_dashboard'))

    organiser_reg_nos = [evt.primary_organiser]
    organiser_reg_nos.extend(evt.other_organisers.split(','))
    if not current_user.isAdministrator:
        if current_user.reg_no not in organiser_reg_nos:
            flash(f'You are not the organiser of Event {evt.name}!', 'danger')
            return redirect(url_for('dashboard'))

    evts = Events.query.filter_by(event_id=idx).all()
    data = []
    n = 5
    start_row = []
    sno = 1
    for event in evts:
        start_row.append(n)
        for i in event.reg_no.split(','):
            if i:
                u = User.query.filter_by(reg_no=i).first()
                data.append([sno, u.name, u.reg_no, u.mobile, u.email, event.event_attended])
                n += 1
        sno += 1
    start_row.append(n)

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(f'{evt.name}')
    header_format = workbook.add_format({'bold': True})
    headers = ['S.No.', 'Name', 'Registration Number', 'Phone Number', 'Email', 'Attended Event']
    worksheet.write(0, 0, evt.name, header_format)
    worksheet.write(1, 0, 'Data as of', header_format)
    worksheet.write(1, 1, datetime.now().strftime('%Y-%m-%d %I:%M %p'),header_format)
    for i, header in enumerate(headers):
        worksheet.write(3, i, header, header_format)

    for row, row_data in enumerate(data, start=4):
        for col, cell_data in enumerate(row_data):
            worksheet.write(row, col, cell_data)

    # print(start_row)
    for n, i in enumerate(range(1, len(start_row)), start=1):
        if not start_row[i]-1 == start_row[i-1]:
            worksheet.merge_range(f'A{start_row[i-1]}:A{start_row[i]-1}', n)

    workbook.close()

    output.seek(0)
    name = evt.name.lower()
    valid = string.ascii_letters+string.digits
    replacement = '_'
    name = ''.join(c if c in valid else replacement for c in name)
    resp = send_file(output, mimetype='application/vnd.ms-excel')
    resp.headers["Content-Disposition"] = f"attachment; filename=sympo_name_participants_{name}.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return resp

@app.route('/send-sample-mail', methods=['POST'])
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
    ret = send_mail(to, subject, body, format='html')
    if 'success' not in ret:
        return jsonify({'message':'Unable to send Mail; Contact Admin'})
    return jsonify({'message':'Mail sent'})

@app.route('/organiser/preview-event/<idx>')
@login_required
def preview_event(idx):
    evt = EventDetails.query.filter_by(event_id=idx).first()
    orgs = [evt.primary_organiser]
    orgs.extend(evt.other_organisers.split(',')[:-1])

    if not current_user.isAdministrator:
        if current_user.reg_no not in orgs:
            flash('Invalid Route !', 'danger')

    organiser_details = []
    o1 = User.query.filter_by(reg_no=evt.primary_organiser).first()
    organiser_details.append(
        {
            'name' : o1.name,
            'mobile' : o1.mobile
        }
    )

    for reg_no in evt.other_organisers.split(','):
        i = User.query.filter_by(reg_no=reg_no).first()
        if i:
            organiser_details.append(
                {
                    'name' : i.name,
                    'mobile' : i.mobile
                }
            )

    page = '<h1>Preview<h1>'
    page += render_template('event_details.html', event=evt, id=idx, organiser_details=organiser_details)

    return page

@app.route('/organiser/update_user_status', methods=['POST'])
@login_required
def update_user_status():
    event_id = request.form['event_id']
    new_status = request.form['new_status'] == 'true'
    evt = Events.query.get(event_id)
    evt.event_attended = new_status
    evt.time = str(datetime.now())
    db.session.commit()
    return jsonify(success=True)

@app.route('/organiser/update_event_detail', methods=['POST'])
@login_required
def update_event_detail():
    event_id = request.form['event_id']
    new_status = request.form['newAcceptRegistrationStatus'] == 'true'
    evt = EventDetails.query.filter_by(event_id=event_id).first()
    evt.is_accepting_registration = new_status
    db.session.commit()
    return jsonify(success=True)

@app.route('/organiser/update_event_result', methods=['POST'])
@login_required
def organiser_update_event_result():
    data =dict(request.form)
    user_id = data['user_id']
    event_id = data['event_id']
    # print('user id',user_id)
    # print('event id', event_id)
    u = User.query.filter_by(id=user_id).first()
    evt = EventDetails.query.filter_by(event_id=event_id).first()
    if not u:
        return jsonify({'message':'No such Participant'})

    e = Events.query.filter_by(event_id=evt.event_id).all()
    for i in e:
        if u.reg_no in i.reg_no:
            break

    if not i.event_attended:
        return jsonify({'message':'Participant not attended event'})
    if not evt:
        return jsonify({'message':'No such Event'})


    if data['newWinnerStatus'] == 'true':
        if evt.winner:
            evt.winner += u.reg_no + ','
        else:
            evt.winner = u.reg_no + ','
    else:
        if evt.winner:
            evt.winner = evt.winner.replace(u.reg_no+',', '')

    if data['newRunnerStatus'] == 'true':
        if evt.runner:
            evt.runner += u.reg_no + ','
        else:
            evt.runner = u.reg_no + ','
    else:
        if evt.runner:
            evt.runner = evt.runner.replace(u.reg_no+',', '')

    db.session.commit()
    return jsonify(success=True)

@app.route('/organiser/event_result', methods=['POST'])
@login_required
def organiser_event_result():
    data = dict(request.form)
    evt = EventDetails.query.filter_by(event_id=data['event_id']).first()

    if not evt:
        return jsonify({'message':'no such event'})

    evt.is_result_submitted = True

    db.session.commit()

    return jsonify({'success':'success', 'winner':evt.winner, 'runner':evt.runner})


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.isAdministrator:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('organiser_dashboard'))

    all_events = EventDetails.query.all()

    return render_template('admin_dashboard.html', events=all_events)


@app.route('/admin/modify_user', methods=['GET', 'POST'])
@login_required
def admin_modify_user():
    if not current_user.isAdministrator:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('organiser_dashboard'))

    if request.method == "POST":
        pass

    return render_template('admin_modify_user.html')


@app.route('/admin/get_user', methods=['POST'])
@login_required
def admin_get_user():
    if not current_user.isAdministrator:
        return jsonify({'error':'not admin'})

    data = dict(request.form)
    # print(data)
    regno = data['regno']
    user = User.query.filter_by(reg_no=regno).first()
    if user:
        return jsonify({
                'userid':user.id,
                'name':user.name,
                'email':user.email,
                'reg_no':user.reg_no,
                'college':user.college,
                'dept':user.dept,
                'mobile':user.mobile,
                'events':user.events,
                'org_events':user.org_events,
                'isOrganiser':user.isOrganiser,
                'isParticipant':user.isParticipant,
                'isVerifier':user.isVerifier
            })
        # return jsonify(user.__dict__)
    else:
        return jsonify({'error':'No Such Participant!'})


@app.route('/admin/update_user', methods=['POST'])
@login_required
def admin_update_user():
    if not current_user.isAdministrator:
        return jsonify({'error':'not admin'})

    data = dict(request.form)
    # print(data)

    user = User.query.filter_by(reg_no=data['reg_no']).first()
    if not user:
        return jsonify({'error':'no such user'})
    if data.get('name'):
        user.name = data['name']
    if data.get('email'):
        user.email = data['email']
    if data.get('college'):
        user.college = data['college']
    if data.get('dept'):
        user.dept = data['dept']
    if data.get('mobile'):
        user.mobile = data['mobile']
    if data.get('events'):
        user.events = data['events']
    else:
        user.events = ''
    if data.get('org_events'):
        user.org_events = data['org_events']
    else:
        user.org_events = ''

    user.isOrganiser = data['isOrganiser'] == 'true'
    user.isParticipant = data['isParticipant'] == 'true'
    user.isVerifier = data['isVerifier'] == 'true'

    db.session.commit()

    return jsonify({'message':'success'})


@app.route('/admin/modify_event', methods=["POST"])
def admin_modify_event():
    event_id = request.form['event_id']
    new_accept_status = request.form['new_accept_status'] == 'true'
    new_result_status = request.form['new_result_status'] == 'true'
    evt = EventDetails.query.get(event_id)
    evt.is_event_accepted = new_accept_status
    evt.is_result_accepted = new_result_status
    db.session.commit()
    return jsonify(success=True)


@app.route('/admin/all-users')
@login_required
def admin_all_users():
    if not current_user.isAdministrator:
        flash('Invalid Route', 'danger')
        return redirect(url_for('dashboard'))

    users = User.query.all()
    return render_template('all_user.html', users=users)

@app.route('/bg/certificate')
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


@app.route('/certificate-content', methods=['POST'])
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

@app.route('/admin/all-payments')
@login_required
def admin_all_payments():
    if not current_user.isAdministrator:
        # to monitor admin logins - super admin
        send_mail('super_admin@domain.com', 'All Payment Page Accessed', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    payments = Payments.query.order_by(Payments.pass_type.asc()).all()
    data = []
    for i in payments:
        u = User.query.filter_by(reg_no=i.reg_no).first()
        data.append([i, u])
    return render_template('all_payments.html', payments=data, pass_name=pass_name)

@app.route('/admin/all-payments/download')
@login_required
def all_payments_download():
    # allow certain user to see data like "current_user.id == 66", when you don't want to give them admin access
    if not (current_user.isAdministrator or current_user.id == 66):
        flash('Invalid Route', 'danger')
        return redirect(url_for('dashboard'))

    if not current_user.isAdministrator:
        # to monitor admin logins - super admin
        send_mail('super_admin@domain.com', 'All Payment Page Accessed', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    payments = Payments.query.order_by(Payments.pass_type.asc()).all()
    data = []
    sno = 1
    for i in payments:
        u = User.query.filter_by(reg_no=i.reg_no).first()
        try:
            p = pass_name[i.pass_type]
        except Exception as e:
            print("Error in pass type name:", e)
            p = i.pass_type
        data.append([
            sno,
            i.reg_no,
            u.name,
            f'{u.dept}, {u.college}',
            p,
            i.amount,
            i.tx_no,
            i.is_valid_payment
        ])
        sno += 1

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('All Payments')
    header_format = workbook.add_format({'bold': True})
    headers = ['S.No.', 'Registration Number', 'Name',
        'Dept & College', 'Pass Type', 'Amount',
        'Transaction Number', 'Is Valid Payment'
    ]
    worksheet.write(0, 0, 'All Payments', header_format)
    worksheet.write(1, 0, 'Data as of', header_format)
    worksheet.write(1, 1, datetime.now().strftime('%Y-%m-%d %I:%M %p'),header_format)
    for i, header in enumerate(headers):
        worksheet.write(3, i, header, header_format)

    for row, row_data in enumerate(data, start=4):
        for col, cell_data in enumerate(row_data):
            worksheet.write(row, col, cell_data)

    workbook.close()

    output.seek(0)
    name = 'All Payments'
    valid = string.ascii_letters+string.digits
    replacement = '_'
    name = ''.join(c if c in valid else replacement for c in name)
    resp = send_file(output, mimetype='application/vnd.ms-excel')
    resp.headers["Content-Disposition"] = f"attachment; filename=sympo_name_year_{name}.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return resp


# **************** Unsent Mail Management ****************

@app.route('/admin/unsent-mails')
@login_required
def view_unsent_mails():
    if not current_user.isAdministrator:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    unsent_mails_dir = static_dir / 'unsent_mails'
    unsent_mails = []

    if unsent_mails_dir.exists():
        for filename in unsent_mails_dir.glob('*.json'):
            filepath = unsent_mails_dir / filename
            try:
                with open(filepath, 'r') as file:
                    mail_data = json.load(file)
                    data_to = mail_data.get('to', 'N/A')
                    data_subject = mail_data.get('subject', 'N/A')
                    data_body = mail_data.get('body', '')
                    if len(data_body) > 100:
                        data_body = data_body[:100] + '...'

                    unsent_mails.append({
                        'filename': filename,
                        'to': data_to,
                        'subject': data_subject,
                        'body': data_body,
                        'full_data': mail_data
                    })
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    return render_template('unsent_mails.html', unsent_mails=unsent_mails)


@app.route('/admin/resend-mail/<filename>', methods=['POST'])
@login_required
def resend_unsent_mail(filename):
    if not current_user.isAdministrator:
        return jsonify({'message': 'error', 'details': 'Not authorized'})

    unsent_mails_dir = static_dir / 'unsent_mails'
    filepath = unsent_mails_dir / filename

    # Security check: ensure file is in unsent_mails directory
    if not filepath.is_relative_to(unsent_mails_dir):
        return jsonify({'message': 'error', 'details': 'Invalid file path'})

    if not filepath.exists():
        return jsonify({'message': 'error', 'details': 'File not found'})

    try:
        with open(filepath, 'r') as f:
            mail_data = json.load(f)

        # Resend the mail
        result = send_mail(
            mail_data.get('to'),
            mail_data.get('subject'),
            mail_data.get('body'),
            format=mail_data.get('format', 'plain'),
            attachments=mail_data.get('attchments', [])
        )

        if result == 'success':
            filepath.unlink() # Delete the file after successful resend
            return jsonify({'message': 'success', 'details': 'Mail resent successfully and record deleted'})
        else:
            return jsonify({'message': 'error', 'details': 'Failed to resend mail'})

    except Exception as e:
        return jsonify({'message': 'error', 'details': str(e)})


@app.route('/admin/delete-unsent-mail/<filename>', methods=['POST'])
@login_required
def delete_unsent_mail(filename):
    if not current_user.isAdministrator:
        return jsonify({'message': 'error', 'details': 'Not authorized'})

    unsent_mails_dir = static_dir / 'unsent_mails'
    filepath = unsent_mails_dir / filename

    # Security check: ensure file is in unsent_mails directory
    if not filepath.is_relative_to(unsent_mails_dir):
        return jsonify({'message': 'error', 'details': 'Invalid file path'})

    try:
        if filepath.exists():
            filepath.unlink()
            return jsonify({'message': 'success', 'details': 'Mail record deleted'})
        else:
            return jsonify({'message': 'error', 'details': 'File not found'})
    except Exception as e:
        return jsonify({'message': 'error', 'details': str(e)})

# ***********************************************


# **************** Error Pages ****************

@app.errorhandler(404)
def page_not_found(e):
    return render_template('page_not_found.html')
@app.errorhandler(405)
def method_not_allowed(e):
    return render_template('method_not_allowed.html')

# ***********************************************

# ******** remove after testing ***********
@app.route('/beta/send_message/<msg>/to/<idx>')
def send(msg, idx):
    message = send_mail(idx, 'Hello(Beta)', msg)
    return message

# ****************************************
