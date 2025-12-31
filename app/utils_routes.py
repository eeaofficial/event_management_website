"""
utils for routes.py
"""
from datetime import datetime, timezone
from typing import Optional

from app.models import EventDetails, Users, Events, Payments
from app.extensions import db
from app.mail_utils import send_mail_http as send_mail

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

def check_user_event_eligibility(user: Users, event: Events) -> bool:
    allowed_catagories = eligible_events(user)
    if event.catagory in allowed_catagories:
        return True

    return False

def register_participants(users: list[Users], event: EventDetails) -> None:
    event.n_registrations += 1
    regnos = [user.reg_no for user in users]
    evt_reg = Events(
        event_id=event.event_id,
        reg_no = ','.join(regnos),
        time=str(datetime.now(timezone.utc)),
    )
    db.session.add(evt_reg)
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
