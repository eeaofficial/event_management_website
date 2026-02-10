"""
Admin Routes
"""

from io import BytesIO
from datetime import datetime, timezone, timedelta
import random, string
import json

from flask import Blueprint, render_template, request, jsonify, abort, send_file, flash, current_app, redirect, url_for
from flask_login import current_user, login_required
import xlsxwriter

from werkzeug.utils import secure_filename
from pathlib import Path
from app.models import EventDetails, Users, Purchases, Passes, PassAccesses, PaymentSettings, Sponsor, EventOrganizers, MITPasscode, PasswordResetOTP
from app.extensions import db, bcrypt
from app.mail_utils import send_mail_http as send_mail
from app.utils import get_static_dir
from app.utils_admin import get_data

bp = Blueprint("admin", __name__)

import random
import string

def random_string(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


@bp.route('/dashboard')
def admin_dashboard():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    return render_template('admin_dashboard.html')

@bp.route('/modify-user')
def admin_modify_user():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    return render_template('admin_modify_user.html')

@bp.route('/get-user', methods=['POST'])
def admin_get_user():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'error': 'unknown page'})

    regno = request.form.get('regno')
    user = Users.query.filter_by(reg_no=regno).first()

    if not user:
        return jsonify({'error': 'No Such Participant!'})

    # 1. Fetch ALL events from DB
    all_events = EventDetails.query.with_entities(
        EventDetails.id,
        EventDetails.name,
        EventDetails.category
    ).all()

    # 2. Fetch events THIS USER organizes
    assigned_event = EventOrganizers.query.filter_by(
    organizer_key=user.id
).first()


    return jsonify({
    'userid': user.id,
    'name': user.name,
    'email': user.email,
    'reg_no': user.reg_no,
    'college': user.college,
    'dept': user.dept,
    'mobile': user.mobile,
    'isOrganiser': user.isOrganiser,
    'isParticipant': user.isParticipant,
    'isVerifier': user.isVerifier,


    'all_events': [
        {'id': e.id, 'name': e.name, 'category': e.category}
        for e in EventDetails.query.all()
    ],
    'assigned_event_id': assigned_event.event_key if assigned_event else None
})




# @bp.route('/update-user', methods=['POST'])
# def admin_update_user():
#     if not current_user.is_authenticated or not current_user.isAdministrator:
#         return jsonify({'error':'unknown page'})

#     data = dict(request.form)

#     user = Users.query.filter_by(reg_no=data['reg_no']).first()
#     if not user:
#         return jsonify({'error':'no such user'})
#     if data.get('name'):
#         user.name = data['name']
#     if data.get('email'):
#         user.email = data['email']
#     if data.get('college'):
#         user.college = data['college']
#     if data.get('dept'):
#         user.dept = data['dept']
#     if data.get('mobile'):
#         user.mobile = data['mobile']

#     user.isOrganiser = data['isOrganiser'] == 'true'
#     user.isParticipant = data['isParticipant'] == 'true'
#     user.isVerifier = data['isVerifier'] == 'true'

#     db.session.commit()

#     return jsonify({'message':'success'})

@bp.route('/update-user', methods=['POST'])
def admin_update_user():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'error':'unknown page'})

    data = dict(request.form)

    user = Users.query.filter_by(reg_no=data['reg_no']).first()
    if not user:
        return jsonify({'error':'no such user'})

    # --- BASIC USER UPDATE ---
    def to_bool(val):
        return str(val).lower() in ('true', '1', 'yes', 'on')

    user.name = data.get('name', user.name)
    user.email = data.get('email', user.email)
    user.college = data.get('college', user.college)
    user.dept = data.get('dept', user.dept)
    user.mobile = data.get('mobile', user.mobile)

    user.isOrganiser   = to_bool(data.get('isOrganiser'))
    user.isParticipant = to_bool(data.get('isParticipant'))
    user.isVerifier    = to_bool(data.get('isVerifier'))
    user.isSpectator   = to_bool(data.get('isSpectator'))

    db.session.commit()


    # --- ORGANIZER EVENT ASSIGNMENT ---
    # selected_event_ids = request.form.getlist('organizer_events[]')

    # if user.isOrganiser:
    #     # Remove old assignments
    #     EventOrganizers.query.filter_by(organizer_key=user.id).delete()

    # if user.isOrganiser:
    #     for event_id in selected_event_ids:
    #         eo = EventOrganizers(
    #             organizer_key=current_user.id,
    #             event_key=int(event_id)
    #     )
    #     db.session.add(eo)

    selected_event_id = request.form.get('organizing_event')

# Remove old assignment ALWAYS (1 event per user)
    EventOrganizers.query.filter_by(organizer_key=current_user.id).delete()

    if user.isOrganiser and selected_event_id:
        eo = EventOrganizers(
            event_key=int(selected_event_id),
            organizer_key=user.id
        )
        db.session.add(eo)

    db.session.commit()

    return jsonify({'message': 'User updated successfully'})


@bp.route('/see/data', methods=["GET", "POST"])
def admin_see_data():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        if request.method == "POST":
            return jsonify({'error':'unknown page'})
        else:
            abort(404)

    # if not current_user.isAdministrator:
    #     send_mail('super_admin@domain.com', 'Admin Login Detected', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    data = get_data('all')

    all_events = EventDetails.query.with_entities(EventDetails.event_id, EventDetails.name).all()

    return render_template('data.html', data=data, events=all_events)


@bp.route('/refresh', methods=["POST"])
def refresh():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'error':'unknown page'})

    req = dict(request.form)
    if req['request'] == 'refresh':
        data = get_data(req['event_id'])
        return jsonify({
            "html": render_template('admin_data_content.html', data=data),
            "time": str(datetime.now())
        })
    return jsonify({"html":"error"})


@bp.route('/manage-events')
def manage_events():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    all_events = EventDetails.query.all()
    all_passes = Passes.query.filter_by(is_active=True).order_by(Passes.id).all()

    return render_template('admin_manage_events.html', events=all_events, all_passes=all_passes)


@bp.route('/modify-event', methods=["POST"])
def admin_modify_event():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'status': 'error', 'details': 'Invalid route'})

    idx = request.form['idx']
    event = EventDetails.query.get(idx)
    if not event:
        return jsonify({'status': 'error', 'details': 'no such event'})

    if 'new_accept_status' in request.form:
        new_accept_status = request.form['new_accept_status'] == 'true'

        if new_accept_status and event.category == 'workshop':
            # expected 1 but still let's assume multiple pas are there
            pas = PassAccesses.query.filter_by(event_key=event.id).all()

            active_passes_count = 0
            workshop_pass = None
            for pa in pas:
                if pa.event_pass.is_active:
                    active_passes_count += 1
                    workshop_pass = pa.event_pass
                    # and pa.event_pass.price <= 0:
                    # price_not_set.append(pa.event_pass)

            if active_passes_count != 1:
                return jsonify({'status': 'error', 'details': f'Workshop requires EXACTLY ONE active pass, but now has {active_passes_count}'})

            if not workshop_pass:
                return jsonify({'status': 'error', 'details': 'Could not find workshop pass'})

            if workshop_pass.price <= 0:
                return jsonify({'status': 'error', 'details': f'Pass price not set (or is invalid) - {workshop_pass.pass_id}'})

        # is_event_accepted primarily controls making event live
        # allow admin to retract event even after result getting live
        # so no constraint here
        event.is_event_accepted = new_accept_status

    if 'new_result_status' in request.form:
        new_result_status = request.form['new_result_status'] == 'true'
        if new_result_status and not event.is_result_submitted:
            return jsonify({'status': 'error', 'details': 'organizer has not submitted result yet'})

        event.is_result_accepted = request.form['new_result_status'] == 'true'

    if 'accepted_pass_ids' in request.form:
        if event.category != 'workshop':
            return jsonify({'status': 'error', 'details': 'workshop passes are not editable'})

        accepted_pass_ids = request.form['accepted_pass_ids'].split(',')

        PassAccesses.query.filter_by(event_key=event.id).delete()
        db.session.commit()
        for pass_id in accepted_pass_ids:
            pass_id = pass_id.strip()
            if pass_id:
                event_pass = Passes.query.filter_by(pass_id=pass_id).first()
                if event_pass:
                    pa = PassAccesses(
                        event=event,
                        event_pass=event_pass
                    )
                    db.session.add(pa)

    db.session.commit()

    return jsonify({'status': 'success', 'details': 'ok'})

@bp.route('/assign-organizer-events', methods=['POST'])
def assign_organizer_events():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'status': 'error', 'details': 'Unauthorized'})

    user_id = request.form.get('user_id')
    event_ids = request.form.getlist('event_ids[]')

    user = Users.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'details': 'User not found'})

    # 🔥 Clear old assignments
    EventOrganizers.query.filter_by(organizer_key=current_user.id).delete()

    # 🔥 Add new assignments
    for event_id in event_ids:
        eo = EventOrganizers(
            organizer_key=current_user.id,
            event_key=int(event_id)
        )
        db.session.add(eo)

    db.session.commit()

    return jsonify({'status': 'success'})


@bp.route('/all-users')
def admin_all_users():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    users = Users.query.all()
    return render_template('all_user.html', users=users)

@bp.route('/all-payments')
def admin_all_payments():
    # allow certain user to see data like "current_user.id == 66", when you don't want to give them admin access
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    # if not current_user.isAdministrator:
    #     send_mail('super_admin@domain.com', 'All Payment Page Accessed', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    purchases = Purchases.query.order_by(Purchases.purchased_at.asc()).all()

    return render_template('all_payments.html', purchases=purchases)

@bp.route('/all-payments/download')
def all_payments_download():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    # if not current_user.isAdministrator:
    #     send_mail('super_admin@domain.com', 'All Payment Page Accessed', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    IST = timezone(timedelta(hours=5, minutes=30))
    dt_cols = [3]
    payments = Purchases.query.order_by(Purchases.purchased_at.asc()).all()
    data = []
    sno = 1
    for i in payments:
        u = i.purchased_by
        p = i.event_pass
        data.append([
            sno,
            i.purchase_id,
            i.transaction_id,
            i.payer_account,
            i.purchased_at,
            u.reg_no,
            u.name,
            f'{u.dept}, {u.college}',
            i.purchase_price,
            i.payment_status,
            p.pass_name,
        ])
        sno += 1

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('All Purchases')
    header_format = workbook.add_format({'bold': True})
    header_dt_format = workbook.add_format({'bold': True, 'num_format': 'dd mmm yyyy, hh:mm AM/PM'})
    dt_format = workbook.add_format({'num_format': 'dd mmm yyyy, hh:mm AM/PM'})

    headers = ['S.No.', 'Purchase ID', 'Tranaction ID', 'Payer Account' 
        'Purchased At', 'Registration Number', 'Name', 'Dept & College',
        'Amount Paid', 'Payment Status', 'Pass Name'
    ]
    worksheet.write(0, 0, 'All Purchases', header_format)
    worksheet.write(1, 0, 'Data as of', header_format)
    worksheet.write(1, 1, datetime.now().astimezone(IST).replace(tzinfo=None), header_dt_format)

    for i, header in enumerate(headers):
        worksheet.write(3, i, header, header_format)

    row = 4
    for row, row_data in enumerate(data, start=4):
        for col, cell_data in enumerate(row_data):
            if col in dt_cols:
                worksheet.write(row, col, cell_data, dt_format)
            else:
                worksheet.write(row, col, cell_data)

    row += 4
    worksheet.write(row, 0, "All date and time are in IST")

    workbook.close()

    output.seek(0)
    name = 'All Purchases'
    valid = string.ascii_letters+string.digits
    replacement = '_'
    name = ''.join(c if c in valid else replacement for c in name)
    resp = send_file(output, mimetype='application/vnd.ms-excel')
    resp.headers["Content-Disposition"] = f"attachment; filename=sympo_name_year_{name}.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return resp


@bp.route('/manage-passes')
def manage_passes():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    # if not current_user.isAdministrator:
    #     send_mail('super_admin@domain.com', 'All Payment Page Accessed', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    passes = Passes.query.all()
    return render_template('admin_manage_passes.html', passes=passes)

@bp.route('/manage-passes', methods=['POST'])
def update_pass_status():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'status': 'error', 'details': 'Invalid route'})

    data = dict(request.form)

    if 'pass_id' not in data or 'new_status' not in data:
        return jsonify({'status': 'error', 'details': 'Request not complete'})

    p = Passes.query.get(data['pass_id'])
    if not p:
        return jsonify({'status': 'error', 'details': f'Pass not found - {data["pass_id"]}'})

    new_status = data['new_status'] == 'true'
    if new_status:
        if p.price <= 0:
            return jsonify({'status': 'error', 'details': 'Pass has invalid cost, cannot make it active'})

    p.is_active = new_status
    db.session.commit()


    return jsonify({'status': 'success', 'details': 'ok'})

@bp.route('/upadte-pass-price', methods=['POST'])
def update_pass_price():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'status': 'error', 'details': 'Invalid route'})

    data = dict(request.form)

    if 'pass_id' not in data or 'new_price' not in data:
        return jsonify({'status': 'error', 'details': 'Request not complete'})

    p = Passes.query.get(data['pass_id'])
    if not p:
        return jsonify({'status': 'error', 'details': 'Pass not found'})

    new_price = -1
    try:
        new_price = int(data['new_price'])
    except:
        pass

    if new_price <= 0:
        return jsonify({'status': 'error', 'details': 'Pass price invalid, should be > 0'})

    # workshop passes are only the passes that are less than zero by default
    if p.is_active:
        return jsonify({
        'status': 'error',
        'details': 'Cannot change price once pass is active'
    })

    p.price = new_price
    db.session.commit()

    return jsonify({'status': 'success', 'details': 'ok'})

# **************** Unsent Mail Management ****************

@bp.route('/unsent-mails')
def view_unsent_mails():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    unsent_mails_dir = get_static_dir() / 'unsent_mails'
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


@bp.route('/resend-mail/<filename>', methods=['POST'])
def resend_unsent_mail(filename):
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'message': 'error', 'details': 'unknown page'})

    unsent_mails_dir = get_static_dir() / 'unsent_mails'
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
            body_format=mail_data.get('format', 'plain'),
            attachments=mail_data.get('attchments', [])
        )

        if result['status'] == 'success':
            filepath.unlink() # Delete the file after successful resend
            return jsonify({
                'message': 'success',
                'details': 'Mail resent successfully and record deleted'
            })
        else:
            return jsonify({
                'message': 'error',
                'details': 'Failed to resend mail'
            })
    except Exception as e:
        return jsonify({'message': 'error', 'details': str(e)})


@bp.route('/delete-unsent-mail/<filename>', methods=['POST'])
def delete_unsent_mail(filename):
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'message': 'error', 'details': 'unknown page'})

    unsent_mails_dir = get_static_dir() / 'unsent_mails'
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

@bp.route('/create-pass', methods=['POST'])
def create_pass():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'status': 'error', 'details': 'Unauthorized'})

    data = dict(request.form)

    pass_name = data.get('pass_name')
    pass_type = data.get('pass_type')  # event / workshop
    description = data.get('description')
    price = int(data.get('price', -1))

    new_pass = Passes(
        pass_id=random_string(10),
        created_by=current_user,
        pass_type=pass_type,
        pass_name=pass_name,
        pass_description=description,
        price=price,
        is_active=False
    )

    db.session.add(new_pass)
    db.session.commit()

    return jsonify({'status': 'success', 'details': 'Pass created'})


@bp.route('/payment-settings', methods=['GET', 'POST'])
def payment_settings():
    settings = PaymentSettings.query.first()

    if not settings:
        settings = PaymentSettings(
            upi_id='default@upi',
            qr_image='payment_qr/Payment_QR.jpeg'
        )
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.upi_id = request.form['upi_id']

        file = request.files.get('qr_code')
        if file and file.filename:
            filename = 'Payment_QR.jpeg'   # 🔒 FIXED NAME
            save_path = Path(current_app.static_folder) / 'payment_qr'
            save_path.mkdir(parents=True, exist_ok=True)
            file.save(save_path / filename)

            # IMPORTANT
            settings.qr_image = f'payment_qr/{filename}'

        db.session.commit()
        flash('Payment details updated successfully', 'success')

    return render_template(
        'admin_payment_settings.html',
        settings=settings
    )

@bp.route('/sponsors', methods=['GET', 'POST'])
def manage_sponsors():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    if request.method == 'POST':
        name = request.form.get('name')
        website = request.form.get('website')
        file = request.files.get('logo')

        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = Path(current_app.static_folder) / 'sponsor_logos'
            save_path.mkdir(exist_ok=True)
            file.save(save_path / filename)

            sponsor = Sponsor(
                name=name,
                website=website,
                logo=f'sponsor_logos/{filename}'
            )
            db.session.add(sponsor)
            db.session.commit()

    sponsors = Sponsor.query.order_by(Sponsor.created_at.desc()).all()
    return render_template('admin_sponsors.html', sponsors=sponsors)

@bp.route('/sponsors/delete/<int:sponsor_id>', methods=['POST'])
def delete_sponsor(sponsor_id):
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    sponsor = Sponsor.query.get_or_404(sponsor_id)

    # Optional: delete logo file from static folder
    logo_path = Path(current_app.static_folder) / sponsor.logo
    if logo_path.exists():
        logo_path.unlink()

    db.session.delete(sponsor)
    db.session.commit()

    flash('Sponsor deleted successfully', 'success')
    return redirect(url_for('admin.manage_sponsors'))

@bp.route('/mit-passcodes')
@login_required
def mit_passcodes():

    requests = MITPasscode.query.order_by(
        MITPasscode.created_at.desc()
    ).all()

    return render_template(
        'mit_passcodes.html',
        requests=requests,
        timedelta = timedelta
    )

@bp.route('/mit-passcodes/generate/<int:req_id>', methods=['POST'])
@login_required
def generate_mit_passcode(req_id):

    req = MITPasscode.query.get_or_404(req_id)

    if req.status != 'PENDING':
        flash("Passcode already generated or invalid.", "warning")
        return redirect(url_for('admin.mit_passcodes'))

    code = "MIT-" + ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=10)
    )

    req.passcode = code
    req.status = 'GENERATED'
    req.expires_at = datetime.utcnow() + timedelta(minutes=30)

    db.session.commit()

    flash(f"Passcode generated: {code} (valid 30 mins)", "success")
    return redirect(url_for('admin.mit_passcodes'))

@bp.route('/password-resets')
@login_required
def password_resets():

    requests = PasswordResetOTP.query.order_by(
        PasswordResetOTP.created_at.desc()
    ).all()

    return render_template(
        'password_resets.html',
        requests=requests
    )

@bp.route('/password-resets/generate/<int:req_id>', methods=['POST'])
@login_required
def generate_password_reset_otp(req_id):

    req = PasswordResetOTP.query.get_or_404(req_id)

    if req.status != 'PENDING':
        flash("OTP already generated or request invalid.", "warning")
        return redirect(url_for('admin.password_resets'))

    # 🔢 Generate 6-digit numeric OTP
    otp = ''.join(random.choices('0123456789', k=6))

    req.otp_plain = otp   # 👈 store temporarily
    req.otp_hash = bcrypt.generate_password_hash(otp).decode('utf-8')
    req.status = 'GENERATED'
    req.expires_at = datetime.utcnow() + timedelta(minutes=30)

    db.session.commit()

    flash(
        f"OTP generated: {otp} (valid for 30 minutes)",
        "success"
    )
    return redirect(url_for('admin.password_resets'))
