"""
verifier routes utils
"""

from flask import url_for

from app.models import Users, Purchases, EventDetails
from app.mail_utils import send_mail_http as send_mail

def send_purchase_update_mail(
        to: Users,
        purchase: Purchases,
        event: EventDetails,
        prev_status: str,
        reason: str,
    ) -> dict[str, str]:

    subject = f'Transaction Update for {purchase.purchase_id} | <Symposium-Name>'
    body = f'''
Update for {event.name}
<br>
with Purchase ID: {purchase.purchase_id}
<br>
Payment Status: <b>{purchase.payment_status}</b>
<br>
Reason: <b>{reason}</b>
'''
    if purchase.payment_status != 'accepted' and prev_status != purchase.payment_status:
        if event.category == 'workshop':
            body += f'<b>Note: Your registeration for the workshop: <a href="{url_for('event_details', idx=event.event_id, _external=True)}">{event.name}</a> is also subject to verification</b>'
        else:
            body += f"<b>Note: The events you registered with the pass ({purchase.event_pass.pass_name}) are subject to verification</b>"

    if purchase.payment_status != 'accepted':
        body += "<br>Please feel free to contact the organisers in case of discrepencies.<br>"

    ret = send_mail(to, subject, body, body_format='html')
    return ret
