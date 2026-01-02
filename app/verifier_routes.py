"""
verifier routes
"""

from flask import flash, url_for, Blueprint, redirect, \
      render_template, request, jsonify
from flask_login import login_required, current_user

from app.models import EventRegistrations, Teams, TeamMembers, Purchases, PurchaseStatusLogs, Passes, PassAccesses
from app.mail_utils import send_mail_http as send_mail
from app.extensions import db
from app.utils_routes import register_participants, send_registration_mail

bp = Blueprint("verifier", __name__)

@bp.route('/callback', methods=['POST'])
def callback():
    if not current_user.is_authenticated or not current_user.isVerifier:
        return jsonify({'status' : 'error', 'message': 'invalid route'})

    data = dict(request.form)

    purchase_id = data['purchase_id']
    p = Purchases.query.filter_by(purchase_id=purchase_id).first()
    if not p:
        return jsonify({'message' : 'Not a valid payment'})

    new_status = data['new_status']
    reason=data['reason']
    plog = PurchaseStatusLogs(
        old_status=p.payment_status,
        new_status=new_status,
        reason=reason,
        changed_by=current_user,
        purchase=p
    )
    db.session.add(plog)
    p.payment_status = new_status

    db.session.commit()

    u = p.purchased_by
    event_pass = p.event_pass
    # register the user for workshop if purchase is accepted
    # register as (self) by user
    if event_pass.pass_type == 'workshop':
        # assumes only one event allowed per workshop pass
        allowed_events = event_pass.events
        if len(allowed_events) != 1:
            return jsonify({'status': 'error', 'message': 'multiple events allowed with this pass?'})
        event = allowed_events[0]
        if new_status == 'accepted':
            register_participants(event, u)
            send_registration_mail(u, event)
        else:
            registration_entry = (
                EventRegistrations.query
                .join(Teams)
                .join(TeamMembers)
                .filter(
                    EventRegistrations.event_key == event.id,
                    TeamMembers.user_key == u.id
                )
                .one_or_none()
            )
            if not registration_entry:
                return jsonify({'staatus': 'error', 'message': 'user was never registered'})

            db.session.delete(registration_entry)
            db.session.commit()

    if p.payment_status=='accepted':
        subject = 'Transaction found in Order | <Symposium-Name>'
        body = f'Your Payment with Transaction number {purchase_id} is found in order and is accepted'
    else:
        subject = 'Transaction Alert | <Symposium-Name> year'
        body = f"""
Your Payment with Transaction number {purchase_id} is put to verification.
Please feel free to contact the organisers in case of discrepencies
"""
        if event_pass.pass_type == 'workshop':
            body += "Note: Your registeration from workshop is also subject to verification"

    ret = send_mail(
        u.email,
        subject,
        body
    )
    err_msg = ret["details"]
    msg = f'success (updated as {new_status})\n'
    if err_msg != 'ok':
        msg +=  f"Mailing Errors: {err_msg}\n"
    return jsonify({
        'status': 'success',
        'newStatus': new_status,
        'message': msg
    })



@bp.route('/verifier-verify')
@login_required
def verifier_verify():
    if not current_user.isVerifier:
        flash('Invalid Route !', 'danger')
        return redirect(url_for('organizer.organiser_dashboard'))

    purchases = Purchases.query.filter_by(payment_status='submitted').all()

    return render_template('verifier_verify.html', purchases=purchases)

@bp.route('/verifier-verify-all')
@login_required
def verifier_verify_all():
    if not current_user.isVerifier:
        flash('Invalid Route !', 'danger')
        return redirect(url_for('organizer.organiser_dashboard'))

    purchases = Purchases.query.all()

    return render_template('verifier_verify.html', purchases=purchases)
