"""
organizer routes
"""

import string
from io import BytesIO
from datetime import datetime, timezone, timedelta

from flask import redirect, render_template, flash, url_for, request, Blueprint, send_file, jsonify, abort
from flask_login import login_required, current_user
import xlsxwriter

from app.models import EventDetails, TeamMembers, Users, Passes, PassAccesses, EventOrganizers, EventResults
from app.utils import save_image, random_string
from app.extensions import db
from app.mail_utils import send_mail_http as send_mail
from app.utils_organizer import get_organizers_from_regno, get_organizer_regnos, get_registered_tm_entires

bp = Blueprint("organizer", __name__)

@bp.route('/dashboard')
@login_required
def organiser_dashboard():
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))
    events = current_user.get_organizing_events()

    return render_template('organiser_dashboard.html', events=events)

@bp.route('/create-event', methods=['GET', 'POST'])
@login_required
def organiser_create_event():
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        details = dict(request.form)
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

        organizers = [current_user]
        no_ac = []
        for j, val in details.items():
            if 'org_' == j[:4]:
                user = Users.query.filter_by(reg_no=val).first()
                if not user:
                    no_ac.append(val)
                else:
                    organizers.append(user)
        if no_ac:
            flash(f'Organizer doesn\'t seem to have an account - {", ".join(no_ac)}', 'warning')


        event_id = random_string(5)

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
            created_by=current_user,
            max_team_size=details['max_team_size'],
            num_rounds=n_rounds,
            rounds=rounds,
            thumbnail=event_pic,
            topic=details['topic'],
            participant_instructions=details['mail_cnt']
        )

        for organizer in organizers:
            eo = EventOrganizers(
                event=evt,
                organizer=organizer
            )
            db.session.add(eo)

        db.session.add(evt)
        db.session.commit()

        if details['category'] == 'workshop':
            pass_id = random_string(10)
            p = Passes(
                pass_id= pass_id,
                created_by=current_user,
                pass_type=details['category'],
                pass_name=details['name'],
                pass_description=f"Pass for workshop: {details['name']}",
                is_active=False
            )
            db.session.add(p)

            pa = PassAccesses(
                event_pass=p,
                event=evt
            )
            db.session.add(pa)
        db.session.commit()

        flash('Event Created Successfully', 'success')
        return redirect(url_for('organizer.organiser_dashboard'))

    return render_template('organiser_create_event.html')

@bp.route('/send-sample-mail', methods=['POST'])
@login_required
def send_sample_mail():
    data = dict(request.form)

    if not current_user.isOrganiser:
        return jsonify({'message':'Not an organiser'})

    idx = data['id']
    event = EventDetails.query.filter_by(event_id=idx).first()
    if not event:
        return jsonify({'message':'No such event'})

    organizers = event.get_organizers()
    if not current_user.isAdministrator:
        if current_user not in organizers:
            return jsonify({'message':f'You are not the organiser of Event {event.name}!'})

    subject = 'Registation Successful | <Symposium-Name> year <Sample ; for Organiser>'
    to = current_user.email
    body = f'''<br>
    Successfully Registered for {event.name} ! <br><br>
    Team Members : (team members' registration numbers will be displayed here) <br><br>
    '''
    body += event.participant_instructions

    ret = send_mail(to, subject, body, body_format='html')

    if ret['status'] != 'success':
        return jsonify({'status': 'error', 'details': f'Unable to send Mail - {ret["details"]}'})

    return jsonify({'status': 'success', 'message':'Mail sent'})


@bp.route('/event/<idx>', methods=['GET', 'POST'])
@login_required
def organiser_event(idx):
    if not current_user.isOrganiser:
        flash('Invalid Route!', 'danger')
        return redirect(url_for('dashboard'))

    evt = EventDetails.query.filter_by(event_id=idx).first()
    if not evt:
        flash('No Such Event Exists', 'danger')
        return redirect(url_for('organizer.organiser_dashboard'))

    if request.method == 'POST':
        if current_user != evt.created_by:
            if evt in current_user.get_organizing_events():
                return jsonify({'status': 'error', 'message': 'You can ONLY edit events that are created by you!'})
            return jsonify({'status': 'error', 'message': 'Invalid Route!'})
        form = request.form
        details = dict(form)

        if evt.is_event_accepted:
            return jsonify({'status': 'error', 'message': 'event can\'t be edited once it is live!'})

        if evt.is_result_submitted:
            return jsonify({'status': 'error', 'message': 'results are already submitted, no more modification allowed!'})

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
        evt.num_rounds=n_rounds
        evt.rounds=rounds

        org_regnos = []
        for j, val in details.items():
            if 'org_' == j[:4]:
                org_regnos.append(val)

        organizers, no_ac = get_organizers_from_regno(org_regnos)
        organizers.append(evt.created_by)

        if no_ac:
            flash(f'Organizer doesn\'t seem to have an account - {", ".join(no_ac)}', 'warning')

        event_pic = evt.thumbnail
        if 'event_pic' in request.files:
            image = request.files['event_pic']
            _, _, new_path = save_image(
                image,
                filename=idx,
                category='event_thumbnails'
            )
            event_pic = new_path or event_pic
        evt.thumbnail=event_pic

        if 'name' in form:
            evt.name = details['name']
        if 'catagory' in form:
            evt.category = details['category']
        if 'description' in form:
            evt.description = details['description']
        if 'max_team_size' in form:
            evt.max_team_size = details['max_team_size']
        if 'topic' in form:
            evt.topic = details['topic']
        if 'participant_instructions' in form:
            evt.participant_instructions = details['mail_cnt']

        EventOrganizers.query.filter_by(event_key=evt.id).delete()
        db.session.commit()
        for organizer in organizers:
            eo = EventOrganizers(
                event=evt,
                organizer=organizer
            )
            db.session.add(eo)

        db.session.commit()

        flash('Event Updated Successfully', 'success')
        return redirect(url_for('organizer.organiser_dashboard'))

    # GET

    if not current_user.isOrganiser:
        flash("Invalid Route!", "danger")

    if not current_user.isAdministrator:
        if current_user not in evt.get_organizers():
            flash(f'You are not the organizer of Event {evt.name}!', 'danger')
            return redirect(url_for('dashboard'))

    event_rounds = []

    for i in evt.rounds.values():
        event_rounds.append(i)

    org_regnos = get_organizer_regnos(evt.get_organizers())

    data = get_registered_tm_entires(evt)

    return render_template('organiser_event_details.html', event=evt,
        registered=data, event_rounds=event_rounds,
        event_organisers=org_regnos
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

    if not current_user.isAdministrator:
        if current_user not in evt.get_organizers():
            flash(f'You are not the organiser of Event {evt.name}!', 'danger')
            return redirect(url_for('dashboard'))
    IST = timezone(timedelta(hours=5, minutes=30))
    teams = get_registered_tm_entires(evt)
    data = []
    n = 5
    start_row = []
    sno = 1
    for team in teams:
        start_row.append(n)
        for tm in team:
            u = tm.user
            attended_at = "NA"
            if tm.event_attended:
                # as because tm.attended_at is naive, when we do astimezone of IST, it assumes that time is already local
                # so we want to first .replace(tzinfo=timezone.utc) and then astimezone of IST
                attended_at = tm.attended_at.replace(tzinfo=timezone.utc).astimezone(IST).replace(tzinfo=None)
                print(attended_at)
            data.append([sno, u.name, u.reg_no, u.mobile, u.email, u.dept, u.college, tm.event_attended, attended_at])
            n += 1
        sno += 1
    start_row.append(n)
    dt_cols = [8]

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(f'{evt.name}')
    header_format = workbook.add_format({'bold': True})
    header_dt_format = workbook.add_format({'bold': True, 'num_format': 'dd mmm yyyy, hh:mm AM/PM'})
    dt_format = workbook.add_format({'num_format': 'dd mmm yyyy, hh:mm AM/PM'})

    headers = ['S.No.', 'Name', 'Registration Number', 'Phone Number', 'Email', 'Department', 'College', 'Has Attended Event?', 'Attended At']
    worksheet.write(0, 0, evt.name, header_format)
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

    for n, i in enumerate(range(1, len(start_row)), start=1):
        if not start_row[i]-1 == start_row[i-1]:
            worksheet.merge_range(f'A{start_row[i-1]}:A{start_row[i]-1}', n)

    row += 4
    worksheet.write(row, 0, "All date and time are in IST")

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

@bp.route('/preview-event/<idx>')
@login_required
def preview_event(idx):
    if not current_user.isOrganiser:
        flash('Invalid Route', 'danger')
        return redirect(url_for('dashboard'))

    evt = EventDetails.query.filter_by(event_id=idx).one_or_none()
    if not evt:
        flash('Not a valid event', 'danger')
        return redirect(url_for('dashboard'))

    organizers = evt.get_organizers()

    if not current_user.isAdministrator:
        if current_user not in organizers:
            flash(f'You are not the organizer of the event {evt.name}!', 'danger')
            return redirect(url_for('dashboard'))

    organiser_details = []
    for organizer in organizers:
        organiser_details.append(
            {
                'name' : organizer.name,
                'mobile' : organizer.mobile
            }
        )

    page = '<h1>Preview<h1>'
    page += render_template('event_details.html', event=evt,
        id=idx, organiser_details=organiser_details)

    return page

@bp.route('/update-participation-status', methods=['POST'])
@login_required
def update_participation_status():
    if not current_user.isOrganiser:
        return jsonify({'status': 'error', 'details': 'Invalid Route!'})

    data = dict(request.form)

    if 'event_id' not in data or 'tm_id' not in data or 'new_status' not in data:
        return jsonify({'status': 'error', 'details': 'Request not complete!'})

    evt = EventDetails.query.filter_by(event_id=data['event_id']).one_or_none()
    if not evt:
        return jsonify({'status': 'error', 'details': 'No such event!'})
    if not current_user.isAdministrator:
        if current_user not in evt.get_organizers():
            return jsonify({'status': 'error', 'details': f'You are not an organizer of the requested event {evt.name}({evt.event_id})!'})

    tm_entry = TeamMembers.query.get(data['tm_id'])
    if not tm_entry:
        return jsonify({'status': 'error', 'details': 'Unable to find Team Member Entry for event'})
    if tm_entry.team.event != evt:
        return jsonify({'status': 'error', 'details': 'data mismatch!'})

    tm_entry.event_attended = data['new_status'] == 'true'
    tm_entry.attended_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify({'status': 'success', 'details': 'ok', 'timestamp': tm_entry.attended_at.isoformat()})

@bp.route('/update-accept-participants', methods=['POST'])
@login_required
def update_accept_participants():
    if not current_user.isOrganiser:
        return jsonify({'status': 'error', 'details': 'Invalid Route!'})

    data = dict(request.form)

    if 'event_id' not in data or 'newAcceptRegistrationStatus' not in data:
        return jsonify({'status': 'error', 'details': 'Incomplete request!'})

    evt = EventDetails.query.filter_by(event_id=data['event_id']).one_or_none()
    if not evt:
        return jsonify({'status': 'error', 'details': 'No such event!'})
    if not current_user.isAdministrator:
        if current_user not in evt.get_organizers():
            return jsonify({'status': 'error', 'details': f'You are not an organizer of the requested event {evt.name}({evt.event_id})!'})
    if evt.is_result_submitted:
        return jsonify({'status': 'error', 'details': 'Results are already submitted, no more edits possible'})

    event_id = request.form['event_id']
    new_status = request.form['newAcceptRegistrationStatus'] == 'true'
    evt = EventDetails.query.filter_by(event_id=event_id).first()
    evt.is_accepting_registration = new_status
    db.session.commit()
    return jsonify({'status': 'success', 'details': 'ok'})

@bp.route('/update-event-result', methods=['POST'])
@login_required
def update_event_result():
    if not current_user.isOrganiser:
        return jsonify({'status': 'error', 'details': 'Invalid Route!'})

    data = dict(request.get_json())

    if 'event_id' not in data or 'tm_ids' not in data or 'position' not in data:
        return jsonify({'status': 'error', 'details': 'Incomplete request!'})

    if data['position'] not in ['winner', 'runner']:
        return jsonify({'status': 'error', 'details': 'Invalid position value!'})

    evt = EventDetails.query.filter_by(event_id=data['event_id']).one_or_none()
    if not evt:
        return jsonify({'status': 'error', 'details': 'No such event!'})
    if not current_user.isAdministrator:
        if current_user not in evt.get_organizers():
            return jsonify({'status': 'error', 'details': f'You are not an organizer of the requested event {evt.name}({evt.event_id})!'})
    if evt.is_result_submitted:
        return jsonify({'status': 'error', 'details': 'Results are already submitted, no more edits possible'})

    tm_entries = []
    for i in data['tm_ids']:
        tm_entry = TeamMembers.query.get(i)
        if not tm_entry:
            return jsonify({'status': 'error', 'details': f'Unable to find Team Member Entry for event - {i}'})
        if tm_entry.team.event != evt:
            return jsonify({'status': 'error', 'details': 'data mismatch!'})
        if not tm_entry.event_attended:
            return jsonify({'status': 'error', 'details': f'User not participated in event yet - {i}'})
        tm_entries.append(tm_entry)

    position = 1 if data['position'] == 'winner' else 2
    EventResults.query.filter_by(event_key=evt.id, position=position).delete()
    db.session.commit()
    for tme in tm_entries:
        er = EventResults(
            event=evt,
            tm=tme,
            position=position
        )
        db.session.add(er)
    db.session.commit()

    return jsonify({'status': 'success', 'details': 'ok'})

@bp.route('/get-results/<idx>')
def get_results(idx):
    if not current_user.is_authenticated or not current_user.isOrganiser:
        abort(404)

    evt = EventDetails.query.get(idx)

    if not evt:
        return jsonify({'status': 'error', 'details': 'Event not found'})
    if not current_user.isAdministrator:
        if current_user not in evt.get_organizers():
            return jsonify({'status': 'error', 'details': f'You are not an organizer of the requested event {evt.name}({evt.event_id})!'})

    winners = []
    runners = []

    wer = EventResults.query.filter_by(event=evt, position=1).all()
    rer = EventResults.query.filter_by(event=evt, position=2).all()

    for i in wer:
        winners.append(i.participant.to_dict())
    for j in rer:
        runners.append(j.participant.to_dict())

    return jsonify({
        'status': 'success',
        'details': 'ok',
        'winners': winners,
        'runners': runners
    })


@bp.route('/finalize-results', methods=['POST'])
@login_required
def finalize_results():
    if not current_user.isOrganiser:
        return jsonify({'status': 'error', 'details': 'Invalid Route!'})

    data = dict(request.form)

    if 'event_id' not in data:
        return jsonify({'status': 'error', 'details': 'Incomplete request!'})

    evt = EventDetails.query.filter_by(event_id=data['event_id']).one_or_none()
    if not evt:
        return jsonify({'status': 'error', 'details': 'No such event!'})
    if not current_user.isAdministrator:
        if current_user not in evt.get_organizers():
            return jsonify({'status': 'error', 'details': f'You are not an organizer of the requested event {evt.name}({evt.event_id})!'})
    if evt.is_result_submitted:
        return jsonify({'status': 'error', 'details': 'Results already submitted!'})

    evt.is_result_submitted = True
    evt.is_accepting_registration = False
    db.session.commit()

    return jsonify({'status': 'success', 'details': 'ok'})

