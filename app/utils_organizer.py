"""
utils for organizer routes
"""

from typing import Union

from app.models import EventDetails, EventRegistrations, Teams

def get_registered_teams(event: Union[EventDetails, str]) -> list[Teams]:
    if not isinstance(event, EventDetails):
        event = EventDetails.query.filter_by(event_id=event).first()

    if not event:
        return []

    event_id = event.event_id

    registered_teams = (Teams.query
        .join(EventRegistrations)
        .join(EventDetails)
        .filter(EventDetails.event_id == event_id)
        .all()
    )

    return registered_teams
