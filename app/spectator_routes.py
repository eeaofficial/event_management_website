from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

spectator_bp = Blueprint('spectator', __name__, url_prefix='/spectator')


def spectator_required():
    if not current_user.is_authenticated:
        abort(403)
    if not (current_user.isSpectator or current_user.isAdministrator):
        abort(403)


@spectator_bp.route('/dashboard')
@login_required
def spectator_dashboard():
    spectator_required()
    return render_template('spectator_dashboard.html')


@spectator_bp.route('/mit-passcodes')
@login_required
def spectator_mit_passcodes():
    spectator_required()
    # reuse existing admin logic
    return render_template('spectator/mit_passcodes.html')


@spectator_bp.route('/password-resets')
@login_required
def spectator_password_resets():
    spectator_required()
    # reuse existing admin logic
    return render_template('spectator/password_resets.html')
