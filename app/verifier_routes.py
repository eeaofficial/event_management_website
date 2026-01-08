"""
verifier routes
"""

from flask import flash, url_for, Blueprint, redirect, \
      render_template, request, jsonify
from flask_login import login_required, current_user

from app.models import EventRegistrations, Teams, TeamMembers, Purchases, PurchaseStatusLogs
from app.extensions import db
from app.utils_routes import register_participants, send_registration_mail
from app.init_data import VALID_PAYMENT_STATUSES
from app.utils_verifier import send_purchase_update_mail

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

    reason = data.get('reason', None)
    if isinstance(reason, str):
        reason = reason.strip()
    if not reason:
        return jsonify({'message' : 'Change reason is required'})

    new_status = data.get('new_status', None)
    if new_status not in VALID_PAYMENT_STATUSES:
        return jsonify({'message': 'Not a valid payment status'})

    new_txid = data.get('new_txid', None)

    if not (new_status or new_txid):
        return jsonify({'message': 'Nothing to update'})

    changed_fields = []
    old_status = p.payment_status
    if new_status and p.payment_status != new_status:
        changed_fields.append('status')
    if new_txid and p.transaction_id != new_txid:
        changed_fields.append('txid')

    plog = PurchaseStatusLogs(
        status=new_status or p.payment_status,
        tx_id=new_txid or p.transaction_id,
        reason=reason,
        changed_by=current_user,
        purchase=p,
        changed_fields=','.join(changed_fields)
    )
    db.session.add(plog)

    if 'status' in changed_fields:
        p.payment_status = new_status
    if 'txid' in changed_fields:
        p.transaction_id = new_txid

    db.session.commit()

    msg = ''
    u = p.purchased_by
    event_pass = p.event_pass
    # register the user for workshop if purchase is accepted
    # register as (self) by user
    if event_pass.pass_type == 'workshop':
        # assumes only one event allowed per workshop pass
        allowed_events = event_pass.events
        if len(allowed_events) != 1:
            msg += f'{len(allowed_events)} number of events allowed with this pass? should be ONE, contact admin, user needs to be registered for the event with WORKSHOP PASS\n'

        event = allowed_events[0]
        if new_status == 'accepted':
            register_participants(event, u)
            send_registration_mail(u, event)
        else:
            # de register if already registered
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
            # if not registration_entry:
            #     return jsonify({'status': 'error', 'message': 'user was never registered'})
            if registration_entry:
                db.session.delete(registration_entry)
                db.session.commit()
            else:
                msg += 'user was never registered\n'

        if 'status' in changed_fields and old_status != p.payment_status:
            ret = send_purchase_update_mail(current_user.email, p.payment_status, event_pass.pass_type, old_status, reason)
            err_msg = ret["details"]
            if err_msg != 'ok':
                msg +=  f"Mailing Errors: {err_msg}\n"

    msg = f'success (updated as {new_status})\n {msg}'

    return jsonify({
        'status': 'success',
        'newStatus': new_status,
        'message': msg
    })



@bp.route('/verifier-verify/')
@bp.route('/verifier-verify/<category>')
@login_required
def verifier_verify(category=None):
    if not current_user.isVerifier:
        flash('Invalid Route !', 'danger')
        return redirect(url_for('organizer.organiser_dashboard'))

    if category == 'all':
        purchases = Purchases.query.all()
    else:
        if not category:
            category = "submitted"
        if category not in VALID_PAYMENT_STATUSES:
            flash("Invalid category requested, showing 'submitted' entries", 'warning')
            category = "submitted"
        purchases = Purchases.query.filter_by(payment_status=category).all()

    return render_template('verifier_verify.html', purchases=purchases)
