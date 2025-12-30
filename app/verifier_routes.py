"""
verifier routes
"""

from flask import flash, url_for, Blueprint, redirect, render_template
from flask_login import login_required, current_user

from app.models import Users, Payments

bp = Blueprint("verifier", __name__)

@bp.route('/verifier-verify')
@login_required
def verifier_verify():
    if not current_user.isVerifier:
        flash('Invalid Route !', 'danger')
        return redirect(url_for('organizer.organiser_dashboard'))

    p = []
    payments = Payments.query.filter_by(is_valid_payment=False).all()

    for i in payments:
        u = Users.query.filter_by(reg_no=i.reg_no).first()
        p.append((i, u))

    return render_template('verifier_verify.html', payments=p)

@bp.route('/verifier-verify-all')
@login_required
def verifier_verify_all():
    if not current_user.isVerifier:
        flash('Invalid Route !', 'danger')
        return redirect(url_for('organizer.organiser_dashboard'))

    p = []
    payments = Payments.query.all()
    for i in payments:
        u = Users.query.filter_by(reg_no=i.reg_no).first()
        p.append((i, u))

    return render_template('verifier_verify.html', payments=p)
