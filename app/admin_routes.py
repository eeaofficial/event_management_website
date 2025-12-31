"""
Admin Routes
"""

from io import BytesIO
from datetime import datetime
import string
import json

from flask import Blueprint, render_template, request, jsonify, abort, send_file
from flask_login import current_user
import xlsxwriter

from app.models import EventDetails, Users, Payments, EventRegistrations
from app.extensions import db
from app.mail_utils import send_mail_http as send_mail
from app.init_data import pass_name
from app.utils import get_static_dir

bp = Blueprint("admin", __name__)

# ******************* Utils ******************
def get_data(event_id):
    data = []
    if event_id == 'all':
        entries = EventRegistrations.query.join(EventDetails).order_by(EventDetails.event_id).all()
    else:
        entries = (
            EventRegistrations.query
            .join(EventDetails)
            .filter(EventDetails.event_id==event_id)
            .all()
        )

    for i in entries:
        name = i.event.name
        us = []
        for participant in i.team.members:
            us.append((
                participant.name,
                participant.reg_no,
                participant.mobile,
                participant.email
            ))
        data.append((name, us))

    return data
# ******************* End Utils ******************

@bp.route('/dashboard')
def admin_dashboard():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    all_events = EventDetails.query.all()

    return render_template('admin_dashboard.html', events=all_events)


@bp.route('/modify_user', methods=['GET', 'POST'])
def admin_modify_user():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    if request.method == "POST":
        pass

    return render_template('admin_modify_user.html')


@bp.route('/get_user', methods=['POST'])
def admin_get_user():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'error':'unknown page'})

    data = dict(request.form)
    # print(data)
    regno = data['regno']
    user = Users.query.filter_by(reg_no=regno).first()
    if user:
        return jsonify({
                'userid':user.id,
                'name':user.name,
                'email':user.email,
                'reg_no':user.reg_no,
                'college':user.college,
                'dept':user.dept,
                'mobile':user.mobile,
                'events':user.registered_events(),
                'org_events':user.organizing_events(),
                'isOrganiser':user.isOrganiser,
                'isParticipant':user.isParticipant,
                'isVerifier':user.isVerifier
            })
        # return jsonify(user.__dict__)
    else:
        return jsonify({'error':'No Such Participant!'})


@bp.route('/update_user', methods=['POST'])
def admin_update_user():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'error':'unknown page'})

    data = dict(request.form)
    # print(data)

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

@bp.route('/modify_event', methods=["POST"])
def admin_modify_event():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        return jsonify({'error':'unknown page'})

    event_id = request.form['event_id']
    new_accept_status = request.form['new_accept_status'] == 'true'
    new_result_status = request.form['new_result_status'] == 'true'
    evt = EventDetails.query.get(event_id)
    evt.is_event_accepted = new_accept_status
    evt.is_result_accepted = new_result_status
    db.session.commit()

    return jsonify(success=True)

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

    payments = Payments.query.order_by(Payments.pass_type.asc()).all()
    data = []
    for i in payments:
        u = Users.query.filter_by(reg_no=i.reg_no).first()
        data.append([i, u])
    return render_template('all_payments.html', payments=data, pass_name=pass_name)

@bp.route('/all-payments/download')
def all_payments_download():
    if not current_user.is_authenticated or not current_user.isAdministrator:
        abort(404)

    if not current_user.isAdministrator:
        send_mail('super_admin@domain.com', 'All Payment Page Accessed', f'Admin Page Accessed! --- {current_user.name, current_user.mobile, current_user.email}')

    payments = Payments.query.order_by(Payments.pass_type.asc()).all()
    data = []
    sno = 1
    for i in payments:
        u = Users.query.filter_by(reg_no=i.reg_no).first()
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
