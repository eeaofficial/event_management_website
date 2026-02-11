"""
utils for routes.py
"""

from typing import Optional

from flask import url_for
from flask_login import current_user

from app.models import EventDetails, Users, Purchases, \
    Teams, TeamMembers, EventRegistrations, Passes, PassAccesses, \
    EventResults
from app.extensions import db
from app.mail_utils import send_mail_http as send_mail
from app.utils import random_string


# def send_welcome_mail(user: Users) -> dict[str, str]:
#     if not isinstance(user, Users):
#         return {'status': 'error', 'message': 'Not valid user'}

#     subject = 'Welcome to <Symposium-Name> \'23'
#     to = user.email
#     body = f'''
#     Reserve the dates ... for taking part in interesting events!!!
#     Take a look at the events {url_for('events', _external=True)}<br><br>

#     Don't forget <b> some event <b> is waiting for you !!!! <br><br>
    
#     <a href="{url_for('events', _external=True)}">Register for events</a> <br><br><br>
#     '''

#     ret = send_mail(to, subject, body, body_format='html')
#     return ret

def send_reset_email(user: Users) -> dict[str, str]:
    if not isinstance(user, Users):
        return {'status': 'error', 'message': 'Not valid user'}

    m = 5
    token = user.get_reset_token(m*60) #120 sec valid token
    subject = 'Password Reset Request | <Symposium-Name> year'
    to = user.email
    body = f'''
    To reset Password, Click on the following link (expires in {m} mins)
    {url_for('reset_password', token=token, _external=True)}
    '''
    ret = send_mail(to, subject, body)
    return ret


def eligible_events(user: Users) -> list[str]:
    if not isinstance(user, Users):
        return []

    p = Purchases.query.filter_by(purchased_by_key=user.id, payment_status='accepted').all()
    passes = [i.event_pass for i in p]
    print()
    allowed_events = []
    for i in passes:
        events = (EventDetails.query
            .join(PassAccesses, PassAccesses.event_key == EventDetails.id)
            .filter(PassAccesses.pass_key == i.id)
            .all()
        )
        for event in events:
            allowed_events.append(event.event_id)

    print(allowed_events)

    return allowed_events

def check_user_event_eligibility(user: Users, event: EventDetails) -> bool:
    allowed_events = eligible_events(user)
    if event.event_id in allowed_events:
        return True
    if current_user.is_authenticated and getattr(user, "is_mit", False):
        return True

    return False

def register_participants(
        event: EventDetails,
        registration_by: Users,
        team_members: Optional[list[Users]]=None
    ) -> None:
    team_id = random_string(20)
    team = Teams(
        team_id=team_id,
        event=event
    )
    db.session.add(team)

    users = [registration_by]
    if team_members:
        users += team_members
    users = set(users)

    for user in users:
        member = TeamMembers(
            user=user,
            team=team
        )
        db.session.add(member)

    registration_entry = EventRegistrations(
        event=event,
        team=team,
        registration_by=registration_by
    )
    db.session.add(registration_entry)

    db.session.commit()

# def send_registration_mail(
#         user: Users,
#         event: EventDetails,
#         team_members: Optional[list[Users]]=None
#     ) -> dict[str, str]:
#     subject = 'Registation Successful | <Symposium-Name> year'
#     to = user.email
#     body = f"<br>Successfully Registered for {event.name} ! <br><br>"
#     if team_members:
#         members_regno = [member.reg_no for member in team_members]
#         body += f"Team Members : {', '.join(members_regno)} <br>"
#     body += event.participant_instructions

#     ret = send_mail(to, subject, body, body_format='html')

#     return ret

def get_mit_code_pass():
    event_pass = Passes.query.filter_by(pass_id='nL4BFHtkh6').one_or_none()
    return event_pass

def get_event_results(event: EventDetails, position: int) -> list[Users]:
    if not isinstance(event, EventDetails):
        return []

    ers = EventResults.query.filter_by(event_key=event.id, position=position).all()
    candidates = []
    for er in ers:
        participant = er.participant
        if er.tm.event_attended:
            candidates.append(participant)
        else:
            print(f"[WARN] Ignore participant didn't attend - {participant}")

    return candidates
