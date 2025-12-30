"""
init
"""

from app.models import User
from app.extensions import db, bcrypt

# modify the pass names as per the sympo
pass_name = {
    'p1' : 'Premium Pass (All Premium Events)',
    'p2' : 'Tech Pass (All Tech Events)',
    'p3' : 'Non Tech Pass (All Non-Tech Events)',
    'p4' : 'Diamond Pass (All Events)',
    'p51' : 'Platinum Pass (All Premium and Non-Tech Events)',
    'p52' : 'Platinum Pass (All Premium and Tech Events)',
    'p6' : 'Gold Pass (All Tech and Non-Tech Events)',
    'p7' : 'Combo Pass (All Events ; 3 Participants)',
    'workshop_hIvTL':'Empowering Chip Design Innovators: RISC-V Workshop with Skywater 130nm Chips',
    'workshop_TRawK':'Data analysis on different domain Model training and advancements',
    'workshop_mOXHL':'Deep Learning using Python',
    'workshop_gjhuR':'Different types of multiple access technologies and 5G usage scenarios with its key capabilities'
}


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
