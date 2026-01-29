"""
init
"""

from app.models import Users, Passes
from app.extensions import db, bcrypt
from app.utils import random_string

# modify the pass names as per the sympo
pass_name = {
    'p1' : 'Premium Pass (All Premium Events)',
    'p2' : 'Tech Pass (All Tech Events)',
    'p3' : 'Non Tech Pass (All Non-Tech Events)',
    'p4' : 'Diamond Pass (All Events)',
    'p51' : 'Platinum Pass (All Premium and Non-Tech Events)',
    'p52' : 'Platinum Pass (All Premium and Tech Events)',
    'p6' : 'Gold Pass (All Tech and Non-Tech Events)',
}

VALID_PAYMENT_STATUSES = ['submitted', 'accepted', 'rejected', 'cancelled']

# hard coded creation of SUPER ADMIN login
def ensure_super_admin():
    super_email='eea2526official@gmail.com'
    super_user = Users.query.filter_by(email=super_email).first()
    super_pass = bcrypt.generate_password_hash('AdminAccess').decode('utf-8')
    if not super_user:
        admin = Users(
                name='SuperAdmin',
                email=super_email,
                reg_no='2022504019',
                dept='ECE',
                college='MIT',
                password=super_pass,
                mobile=7092554888,
                isOrganiser=True,
                isParticipant=True,
                isAdministrator=True,
                isVerifier=True
                )
        db.session.add(admin)

    # users for testing
    if not Users.query.filter_by(reg_no='1234567899').first():
        pass_new = bcrypt.generate_password_hash('1').decode('utf-8')
        u1 = Users(
            name='abcde',
            email='a@b.c',
            reg_no='1234567899',
            dept='',
            college='',
            password=pass_new,
            mobile=0
        )
        db.session.add(u1)
    if not Users.query.filter_by(reg_no='0123456789').first():
        pass_new = bcrypt.generate_password_hash('1').decode('utf-8')
        u2 = Users(
            name='xyzwx',
            email='x@y.z',
            reg_no='0123456789',
            dept='',
            college='',
            password=pass_new,
            mobile=0
        )
        db.session.add(u2)

    db.session.commit()


def create_passes():
    exists = db.session.query(Passes.id).first() is not None
    if not exists:
        admin = Users.query.get(1)
        all_pass = []
        for i, j in pass_name.items():
            pass_id = random_string(10)
            pass_type = 'workshop' if 'workshop' in i else 'event'
            name, desc, *_ = j.split('(') + [j, j]
            each = Passes(
                pass_id= pass_id,
                created_by=admin,
                pass_type=pass_type,
                pass_name=name,
                pass_description=desc[:-1],
                price=200,
            )
            all_pass.append(each)
        db.session.add_all(all_pass)
        db.session.commit()
