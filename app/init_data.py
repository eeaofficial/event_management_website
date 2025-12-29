"""
init
"""

from app.models import User
from app.extensions import db, bcrypt

# hard coded creation of SUPER ADMIN login
def ensure_super_admin():
    super_email='super-admin@domain.com'
    super_user = User.query.filter_by(email=super_email).first()
    super_pass = bcrypt.generate_password_hash('superPASS').decode('utf-8')
    if not super_user:
        admin = User(
                name='SuperAdmin',
                email=super_email,
                reg_no='1234567890',
                dept='',
                college='',
                events='',
                password=super_pass,
                mobile=0,
                isOrganiser=True,
                isParticipant=True,
                isAdministrator=True,
                isVerifier=True
                )
        db.session.add(admin)
        db.session.commit()
