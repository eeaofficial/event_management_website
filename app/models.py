from app import db, login_manager, app, bcrypt
from flask_login import UserMixin
import os
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    reg_no = db.Column(db.String(30), unique=True, nullable=False)
    college = db.Column(db.String(50), nullable=False)
    dept = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    mobile = db.Column(db.String(10), nullable=False)
    
    #comma seperated event ids
    events = db.Column(db.String(500))

    #for organisers
    org_events = db.Column(db.String(500))

    # same account can be used for both organising and participating
    isOrganiser = db.Column(db.Boolean, default=False, nullable=False) # subject to approval from an admin
    isParticipant  = db.Column(db.Boolean, default=True, nullable=False)

    isAdministrator = db.Column(db.Boolean, default=False, nullable=False) # not created as other accounts; hard coded in db

    isVerifier = db.Column(db.Boolean, default=False, nullable=False)

    def get_reset_token(self, expiry_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expiry_sec)
        return s.dumps( {'user_id': self.id} ).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.name}', '{self.email}', '{self.reg_no}', '{self.dept}', '{self.college}', '{self.mobile}', [{self.events}])"


class Events(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(5), nullable=False)
    reg_no = db.Column(db.String(10*30+4), nullable=False)
    time = db.Column(db.String(20), nullable=False) # "YYYY-MM-DD HH:MM:SS" (19 characters long)
    event_attended = db.Column(db.Boolean, default=False, nullable=False)
    # payment_order_id = db.Column(db.String(30), nullable=False)
    def __repr__(self):
        return f"Events('{self.event_id}', '[{self.reg_no}]', '{self.time}')"


class EventDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(5), nullable=False, unique=True)
    name = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    primary_organiser = db.Column(db.String(10), nullable=False)
    max_team_size = db.Column(db.Integer, nullable=False)
    num_rounds = db.Column(db.Integer, nullable=False)
    rounds = db.Column(db.JSON, nullable=False) # json string with name, description, time, mode
    other_organisers = db.Column(db.String(100), nullable=False) # other organisers reg no
    num_organisers = db.Column(db.Integer, nullable=False) # including primary organisers
    thumbnail = db.Column(db.String(20))
    topic = db.Column(db.String(20))
    event_cost = db.Column(db.Integer)

    winner = db.Column(db.String(10*30+9))
    runner = db.Column(db.String(10*10+9))

    # control accepting participants into events
    is_accepting_registration = db.Column(db.Boolean, default=True, nullable=False)

    #admin should accept to make things "on-line" at website for the public
    is_event_accepted = db.Column(db.Boolean, default=False, nullable=False)
    
    is_result_submitted = db.Column(db.Boolean, default=False, nullable=False)
    is_result_accepted = db.Column(db.Boolean, default=False, nullable=False) # if result accepted by admin; will be pushed "on-line"
    
    workshop_fee = db.Column(db.Integer, default=0, nullable=False)
    n_registrations = db.Column(db.Integer, default=0, nullable=False)
    on_register_mail_cnt = db.Column(db.String(1000), default='', nullable=False)
    
class Payments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reg_no = db.Column(db.String(200), nullable=False) # reg number of user
    pass_type = db.Column(db.String(20), nullable=False)
    # session_id = db.Column(db.String(200), nullable=False)
    # order_id = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, default=0, nullable=False)
    screenshot = db.Column(db.String(50), nullable=False)
    tx_no = db.Column(db.String(50), unique=True, nullable=False)
    is_valid_payment = db.Column(db.Boolean, default=False, nullable=False)
    

with app.app_context():
    if "database.db" not in os.listdir():
        db.create_all()

    # hard coded creation of SUPER ADMIN login
    email='super-admin@domain.com'
    user = User.query.filter_by(email=email).first()
    hashed_password = bcrypt.generate_password_hash('superPASS').decode('utf-8')
    if not user:
        admin = User(
                name='SuperAdmin',
                email=email,
                reg_no='1234567890',
                dept='',
                college='',
                events='',
                password=hashed_password,
                mobile=0,
                isOrganiser=True,
                isParticipant=True,
                isAdministrator=True,
                isVerifier=True
                )
        db.session.add(admin)
        db.session.commit()
