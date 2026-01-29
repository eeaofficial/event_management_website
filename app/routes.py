"""
General Routes
"""


import hashlib
import json

from flask import  render_template, flash, redirect, url_for, request, jsonify, send_from_directory, Blueprint
from flask_login import login_user, current_user, logout_user, login_required

from app.extensions import db, bcrypt
from app.forms import SignUpForm, LoginForm, ResetRequestForm, ResetPasswordForm, UpdateProfileForm
from app.models import Users, EventDetails, Passes, Purchases, EventOrganizers
from app.utils import is_code_applicable, save_image, get_upload_dir, random_string
from app.mail_utils import send_mail_http as send_mail
from app.utils_routes import check_user_event_eligibility, register_participants, \
    send_registration_mail, send_welcome_mail, send_reset_email, get_mit_code_pass, \
    get_event_results

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

        user = Users(
            name=form.name.data,
            email=form.email.data,
            reg_no=form.reg_no.data,
            dept = dept,
            college = clg,
            password=hashed_password,
            mobile=form.mobile.data,
        )
        db.session.add(user)
        db.session.commit()

        ret = send_welcome_mail(user)
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
        user = Users.query.filter_by(email=form.email.data, reg_no=form.reg_no.data).first()
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

@bp.route('/forgot-password', methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = ResetRequestForm()

    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data, reg_no=form.reg_no.data).first()
        ret = send_reset_email(user)
        if ret['status'] == 'success':
            flash('Please check your mail for reset !', 'info')
        else:
            flash('Could not send mail, contact admin', 'info')
        return redirect(url_for('login'))

    return render_template('forgot_password.html', title='Forgot Password', form=form)

@bp.route('/forgot-password/<token>', methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    user = Users.verify_reset_token(token)
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
    code_possible = is_code_applicable()

    purchases = Purchases.query.filter_by(purchased_by_key=current_user.id).all()

    return render_template('dashboard.html', title=current_user.name,
        code_possible=code_possible, purchases=purchases
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
        purchase_id = random_string(40)
        screenshot = f'{purchase_id}_logo.png'
        event_pass = get_mit_code_pass()
        if not event_pass:
            if not code_possible:
                return jsonify({'message':'unable to get pass, contact admin'})
        p = Purchases(
            purchase_id=purchase_id,
            payment_proof=screenshot,
            purchase_price=0,
            event_pass=event_pass,
            purchased_by=current_user,
            payer_account=current_user.reg_no
            # purchase_status='accepted'
        )

        db.session.add(p)
        db.session.commit()

        return jsonify({'message':'Success ! You can attend all events'})

    return jsonify({'message':'Failed to get pass; invalid code or invaid user'})

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

        user = Users.query.filter_by(reg_no=current_user.reg_no).first()
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
    all_passes = Passes.query.order_by(Passes.id).all()
    user_passes = current_user.event_passes()

    return render_template('buy_pass.html', all_passes=all_passes, user_passes=user_passes)

@bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    if request.method == 'POST':
        data = dict(request.form)

        # take TX ID typing burden off participant
        # pa = Purchases.query.filter_by(tx_no=data['tx-id']).first()
        # if pa:
        #     flash('A proof with this transaction id is already submitted', 'danger')
        #     return redirect(url_for('dashboard'))

        if not 'screenshot' in request.files:
            flash('Invalid Proof or proof not uploaded !')
            return redirect(request.referrer or url_for('dashboard'))

        filename = f'{current_user.reg_no}_{random_string(10)}'

        image = request.files['screenshot']
        _, _, filename = save_image(
            image,
            filename=filename,
            category='payment_screenshots'
        )
        if not filename:
            flash('Error in uploading proof image !', 'danger')
            return redirect(request.referrer or url_for('dashboard'))

        purchase_id = random_string(40)
        pass_id = data['pass_id']
        event_pass = Passes.query.filter_by(pass_id=pass_id).one_or_none()
        if not event_pass.is_active:
            flash('No such pass exists!', 'danger')
            return redirect(request.referrer or url_for('dashboard'))

        payer_account = data['payer-account']
        if not payer_account:
            flash('Payer account is required', 'danger')
            return redirect(request.referrer or url_for('dashboard'))

        p = Purchases(
            purchase_id=purchase_id,
            payment_proof=filename,
            transaction_id=data['tx-id'],
            purchase_price=data['amount'],
            event_pass=event_pass,
            payer_account=payer_account,
            purchased_by=current_user
        )
        db.session.add(p)
        db.session.commit()

        flash('Payment Submitted; You\'ll be notified upon Verification', 'success')
        return redirect(url_for('dashboard'))

    pass_id = request.args.get('pass_id')
    pass_obj = Passes.query.filter_by(pass_id=pass_id).one_or_none()
    if not pass_obj:
        flash('Invalid Pass Requested', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    if pass_obj in current_user.event_passes():
        flash('You already have this pass', 'info')
        return redirect(url_for('dashboard'))
    if not pass_obj.is_active:
        flash('Not a valid active pass', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    amount = str(pass_obj.price)

    verifiers = Users.query.filter_by(isVerifier=True, isAdministrator=False).all()

    return render_template('payment.html', amount=amount, verifiers=verifiers, pass_obj=pass_obj)

@bp.route('/events')
def events():
    event_types = json.load(open('event_types.json'))
    return render_template('events.html', title='Events',
        active_page='events', event_types=event_types)

@bp.route('/tech-events')
def tech_events():
    all_events = EventDetails.query.filter_by(category='tech', is_event_accepted=True).all()
    return render_template('events_list.html', title='Tech Events',
        active_page='events', events=all_events, header='Technical Events')

@bp.route('/non-tech-events')
def non_tech_events():
    all_events = EventDetails.query.filter_by(category='non_tech', is_event_accepted=True).all()
    return render_template('events_list.html', title='Non Tech Events',
        active_page='events', events=all_events, header='Non Technical Events')

@bp.route('/premium-events')
def premium_events():
    all_events = EventDetails.query.filter_by(category='premium', is_event_accepted=True).all()
    return render_template('events_list.html', title='Premium Events',
        active_page='events', events=all_events, header='Premium Events')

@bp.route('/workshops')
def workshops():
    all_events = EventDetails.query.filter_by(category='workshop', is_event_accepted=True).all()
    return render_template('events_list.html', title='Workshops',
        active_page='events', events=all_events, header='Workshops')

@bp.route('/event-details/<idx>')
def event_details(idx):
    force_details = False
    event = EventDetails.query.filter_by(event_id=idx).first()

    if not event:
        flash('Event no longer exist, please contact support', 'danger')
        return redirect(url_for('events'))

    if not event.is_event_accepted:
        flash('Event no longer accepting participants, please contact support', 'danger')
        return redirect(url_for('events'))

    is_eligible = check_user_event_eligibility(current_user, event)

    organizer_details = []
    organizers = EventOrganizers.query.filter_by(event_key=event.id).all()
    for o in organizers:
        organizer = o.organizer
        organizer_details.append(
            {
                'name' : organizer.name,
                'mobile' : organizer.mobile
            }
        )
    registered_events = []

    if current_user.is_authenticated:
        registered_events = current_user.registered_events()
        
    reg_event_ids = [e.event_id for e in registered_events]

    # pass_id = ''
    # if event.category == 'workshop':
    #     passes_allowed = PassAccesses.query.filter_by(event_key=event.id).first()
    #     if not passes_allowed:
    #         pass
    #         # flash("No registration allowed", "danger")
    #         # return redirect(url_for('events'))
    #     if passes_allowed:
    #         pass_id = Passes.query.get(passes_allowed.pass_key).pass_id

    if force_details or not event.is_result_accepted:
        return render_template('event_details.html', event=event,
            organiser_details=organizer_details, is_eligible=is_eligible,
            reg_event_ids=reg_event_ids)

    winners = get_event_results(event, 1)
    runners = get_event_results(event, 2)

    return render_template('event_result.html', winners=winners, runners=runners, event=event)


@bp.route('/register', methods=["POST"])
@login_required
def register():
    data = dict(request.form)

    event = EventDetails.query.filter_by(event_id=data['id']).first()

    if not event:
        return jsonify({'status': 'error', 'details': 'No such events'})

    if not event.is_accepting_registration:
        return jsonify({'status': 'error', 'details': 'This event is no loonger accepting registrations'})
        # raise Exception("This event is no loonger accepting registrations")

    users = []
    for key, value in data.items():
        if 'reg' not in key:
            continue

        x = Users.query.filter_by(reg_no=value).first()
        if x:
            #user-event
            event_registered = x.registered_events()
            if event in event_registered:
                return jsonify({"error": f'{x.reg_no} Already registered!'})

            users.append(x)
        else:
            return jsonify({"error":f'{value} does not have an account !'})

    users = set(users)

    for user in users:
        if not check_user_event_eligibility(user, event):
            return jsonify({'error':'No pass!'})

    register_participants(event, current_user, users)

    for user in users:
        ret = send_registration_mail(user, event, team_members=users)
        msg = "registered!\n"
        if ret['status'] != 'success':
            msg += "Unable to send mail; contact admin\n"
    return jsonify({"success":msg})

# ******** remove after testing ***********
@bp.route('/beta/send_message/<msg>/to/<idx>')
def send(msg, idx):
    message = send_mail(idx, 'Hello(Beta)', msg)
    return message

# ****************************************
