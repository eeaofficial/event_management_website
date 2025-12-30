"""
organizer routes
"""

import random
import string
from io import BytesIO
from datetime import datetime

from flask import redirect, render_template, flash, url_for, request, Blueprint, send_file, jsonify
from flask_login import login_required, current_user
import xlsxwriter

from app.models import EventDetails, User, Events
from app.utils import save_image
from app.extensions import db
from app.mail_utils import send_mail_http as send_mail

bp = Blueprint("organizer", __name__)

@bp.route('/dashboard')
@login_required
def organiser_dashboard():
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    events = EventDetails.query.filter_by(primary_organiser=current_user.reg_no)
    return render_template('organiser_dashboard.html', events=events)

@bp.route('/create-event', methods=['GET', 'POST'])
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
        return redirect(url_for('organizer.organiser_dashboard'))

    return render_template('organiser_create_event.html')

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


@bp.route('/event/<idx>', methods=['GET', 'POST'])
@login_required
def organiser_event(idx):
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        evt = EventDetails.query.filter_by(event_id=idx).first()
        if not evt:
            flash('Unable to find event !', 'danger')
            return redirect(url_for('organizer.organiser_dashboard'))
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
        return redirect(url_for('organizer.organiser_dashboard'))

    evt = EventDetails.query.filter_by(event_id=idx).first()

    if not evt:
        flash('No Such Event Exists', 'danger')
        return redirect(url_for('organizer.organiser_dashboard'))

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


@bp.route('/event/<idx>/download')
@login_required
def organiser_event_download(idx):
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    evt = EventDetails.query.filter_by(event_id=idx).first()

    if not evt:
        flash('No Such Event Exists', 'danger')
        return redirect(url_for('organizer.organiser_dashboard'))

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

@bp.route('/event_result', methods=['POST'])
@login_required
def organiser_event_result():
    data = dict(request.form)
    evt = EventDetails.query.filter_by(event_id=data['event_id']).first()

    if not evt:
        return jsonify({'message':'no such event'})

    evt.is_result_submitted = True

    db.session.commit()

    return jsonify({'success':'success', 'winner':evt.winner, 'runner':evt.runner})

@bp.route('/preview-event/<idx>')
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

@bp.route('/update_user_status', methods=['POST'])
@login_required
def update_user_status():
    event_id = request.form['event_id']
    new_status = request.form['new_status'] == 'true'
    evt = Events.query.get(event_id)
    evt.event_attended = new_status
    evt.time = str(datetime.now())
    db.session.commit()
    return jsonify(success=True)

@bp.route('/update_event_detail', methods=['POST'])
@login_required
def update_event_detail():
    event_id = request.form['event_id']
    new_status = request.form['newAcceptRegistrationStatus'] == 'true'
    evt = EventDetails.query.filter_by(event_id=event_id).first()
    evt.is_accepting_registration = new_status
    db.session.commit()
    return jsonify(success=True)

@bp.route('/update_event_result', methods=['POST'])
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
