"""
admin utils
"""

from app.models import EventRegistrations, EventDetails

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
