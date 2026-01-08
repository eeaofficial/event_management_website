"""
utils for organizer routes
"""

from typing import Union

from app.models import EventDetails, EventRegistrations, Teams, Users

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


def get_organizers_from_regno(regnos: list[str]) -> tuple[list[Users], list[str]]:
    """
        Returns users and no account regnos
    """

    organizers = []
    no_ac = []
    for regno in regnos:
        user = Users.query.filter_by(reg_no=regno).first()
        if user:
            organizers.append(user)
        else:
            no_ac.append(regno)

    return (organizers, no_ac)


def get_organizer_regnos(organizers: list[Users]) -> list[str]:
    regnos = []
    for organizer in organizers:
        if not isinstance(organizer, Users):
            continue
        regnos.append(organizer.reg_no)

    return regnos
