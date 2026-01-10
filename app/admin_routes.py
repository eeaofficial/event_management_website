"""
Admin Routes
"""

from io import BytesIO
from datetime import datetime, timezone, timedelta
import string
import json

from flask import Blueprint, render_template, request, jsonify, abort, send_file
from flask_login import current_user
import xlsxwriter

from app.models import EventDetails, Users, Purchases, Passes, PassAccesses
from app.extensions import db
from app.mail_utils import send_mail_http as send_mail
from app.utils import get_static_dir
from app.utils_admin import get_data

bp = Blueprint("admin", __name__)

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
        return jsonify({'error':'unknown page'})

    data = dict(request.form)
    # print(data)
    regno = data['regno']
    user = Users.query.filter_by(reg_no=regno).first()
    if user:
        x = user.registered_events()
        user_events = [i.event_id for i in x]
        y = user.get_organizing_events()
        user_org_events = [i.event_id for i in y]
        return jsonify({
                'userid':user.id,
                'name':user.name,
                'email':user.email,
                'reg_no':user.reg_no,
                'college':user.college,
                'dept':user.dept,
                'mobile':user.mobile,
                'events':user_events,
                'org_events':user_org_events,
                'isOrganiser':user.isOrganiser,
                'isParticipant':user.isParticipant,
                'isVerifier':user.isVerifier
            })
        # return jsonify(user.__dict__)
    else:
        return jsonify({'error':'No Such Participant!'})


@bp.route('/update-user', methods=['POST'])
def admin_update_user():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'error':'unknown page'})

    data = dict(request.form)
    print(data)

    user = Users.query.filter_by(reg_no=data['reg_no']).first()
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

    user.isOrganiser = data['isOrganiser'] == 'true'
    user.isParticipant = data['isParticipant'] == 'true'
    user.isVerifier = data['isVerifier'] == 'true'

    db.session.commit()

    return jsonify({'message':'success'})


@bp.route('/see/data', methods=["GET", "POST"])
def admin_see_data():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        if request.method == "POST":
            return jsonify({'error':'unknown page'})
        else:
            abort(404)

    if not current_user.isAdministrator:
        send_mail('super_admin@domain.com', 'Admin Login Detected', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

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

    event_passes_map = {}
    for event in all_events:
        passes = (
            Passes.query
            .join(PassAccesses)
            .filter(
                Passes.is_active == True,
                PassAccesses.event_key == event.id
            )
            .all()
        )
        event_passes_map[event.id] = passes
    return render_template('admin_manage_events.html', events=all_events,
        all_passes=all_passes, event_passes_map=event_passes_map)


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
        if event.category == 'workshop':
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

    if not current_user.isAdministrator:
        send_mail('super_admin@domain.com', 'All Payment Page Accessed', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    purchases = Purchases.query.order_by(Purchases.purchased_at.asc()).all()

    return render_template('all_payments.html', purchases=purchases)

@bp.route('/all-payments/download')
def all_payments_download():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    if not current_user.isAdministrator:
        send_mail('super_admin@domain.com', 'All Payment Page Accessed', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

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

    headers = ['S.No.', 'Purchase ID', 'Tranaction ID', 'Purchased At',
        'Registration Number', 'Name', 'Dept & College',
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
