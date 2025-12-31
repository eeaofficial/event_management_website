"""
utils for routes.py
"""

from datetime import datetime, timezone
from typing import Optional

from flask import url_for

from app.models import EventDetails, Users, Payments, Teams, TeamMembers, EventRegistrations
from app.extensions import db
from app.mail_utils import send_mail_http as send_mail
from app.utils import random_string


def send_welcome_mail(user: Users) -> dict[str, str]:
    if not isinstance(user, Users):
        return {'status': 'error', 'message': 'Not valid user'}

    subject = 'Welcome to <Symposium-Name> \'23'
    to = user.email
    body = f'''
    Reserve the dates ... for taking part in interesting events!!!
    Take a look at the events {url_for('events', _external=True)}<br><br>

    Don't forget <b> some event <b> is waiting for you !!!! <br><br>
    
    <a href="{url_for('events', _external=True)}">Register for events</a> <br><br><br>
    '''

    ret = send_mail(to, subject, body, body_format='html')
    return ret

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

    p = Payments.query.filter_by(reg_no=user.reg_no, is_valid_payment=True).all()
    types = [i.pass_type for i in p]

    allowed_catagories = []
    # any vaid user can register to workshop
    allowed_catagories.append('workshop')
    if 'p1' in types or 'Premium Pass (All Premium Events)' in types:
        allowed_catagories.extend(['premium'])
    if 'p2' in types or 'Tech Pass (All Tech Events)' in types:
        allowed_catagories.extend(['tech'])
    if 'p3' in types or 'Non Tech Pass (All Non-Tech Events)' in types:
        allowed_catagories.extend(['non_tech'])
    if 'p4' in types or 'Diamond Pass (All Events)' in types:
        allowed_catagories.extend(['tech','non_tech','premium'])
    if 'p51' in types or 'Platinum Pass (All Premium and Non-Tech Events)' in types:
        allowed_catagories.extend(['non_tech', 'premium'])
    if 'p52' in types or 'Platinum Pass (All Premium and Tech Events)' in types:
        allowed_catagories.extend(['tech','premium'])
    if 'p6' in types or 'Gold Pass (All Tech and Non-Tech Events)' in types:
        allowed_catagories.extend(['tech','non_tech'])
    if 'p7' in types or 'Combo Pass (All Events ; 3 Participants)' in types:
        allowed_catagories.extend(['tech','non_tech','premium'])

    return allowed_catagories

def check_user_event_eligibility(user: Users, event: EventDetails) -> bool:
    allowed_catagories = eligible_events(user)
    if event.catagory in allowed_catagories:
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

    users = list[registration_by]
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

def send_registration_mail(
        user: Users,
        event: EventDetails,
        team_members: Optional[list[Users]]=None
    ) -> dict[str, str]:
    subject = 'Registation Successful | <Symposium-Name> year'
    to = user.email
    body = f"<br>Successfully Registered for {event.name} ! <br><br>"
    if team_members:
        members_regno = [member.reg_no for member in team_members]
        body += f"Team Members : {', '.join(members_regno)} <br>"
    body += event.on_register_mail_cnt

    ret = send_mail(to, subject, body, body_format='html')

    return ret
