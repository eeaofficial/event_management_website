"""
Models
"""

from datetime import datetime, timezone

from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from app.extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

class Users(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    reg_no = db.Column(db.String(30), unique=True, nullable=False)
    college = db.Column(db.String(50), nullable=False)
    dept = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    mobile = db.Column(db.String(10), nullable=False)

    # same account can be used for both organising and participating
    isOrganiser = db.Column(db.Boolean, default=False, nullable=False) # subject to approval from an admin
    isParticipant  = db.Column(db.Boolean, default=True, nullable=False)

    # not created as other accounts; hard coded in db
    isAdministrator = db.Column(db.Boolean, default=False, nullable=False)

    isVerifier = db.Column(db.Boolean, default=False, nullable=False)

    # while join, sqlalchemy will figure out the FK column, if not InvalidRequestError is raised
    # we can join by giving any column as we need
    def registered_events(self):
        return (
            db.session.query(EventDetails)
            .join(EventRegistrations)
            .outerjoin(Teams)
            .outerjoin(TeamMembers)
            .filter(
                TeamMembers.user_key == self.id
            )
            .distinct()
            .all()
        )

    def organizing_events(self):
        return []

    def get_reset_token(self, expiry_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expiry_sec)
        return s.dumps( {'user_id': self.id} ).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except Exception as e:
            return None

        return Users.query.get(user_id)

    def __repr__(self):
        return f"Users('{self.name}', '{self.email}', '{self.reg_no}', '{self.dept}', '{self.college}', '{self.mobile}')"


class EventRegistrations(db.Model):
    __tablename__ = 'event_registrations'
    __table_args__ = (
        db.UniqueConstraint('event_key', 'team_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_key = db.Column(db.Integer, db.ForeignKey('event_details.id'), nullable=False)
    team_key = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    registered_by_key = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # sqlite's NOW is UTC time with
    # note timezone info not stored
    # ensure every write to timestamp is in UTC
    timestamp = db.Column(db.DateTime, nullable=False,
        server_default=db.func.now()
    )

    event = db.relationship('EventDetails', lazy=True)
    team = db.relationship('Teams', lazy=True)
    registered_by = db.relationship('Users', lazy=True)

    def __repr__(self):
        return f"EventRegistrations('{self.event_key}', '{self.registered_by_key}', '{self.team_key}', '{self.timestamp}')"


class Teams(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    event_key = db.Column(db.Integer, db.ForeignKey('event_details.id'), nullable=False)

    team_id = db.Column(db.String(30), nullable=False, unique=True)
    # some dummy name
    team_name = db.Column(db.String(30), default='')

    event = db.relationship('EventDetails', lazy=True)

    members = db.relationship(
        'Users',
        secondary='team_members',
        lazy=True
    )

    def __repr__(self):
        return f"Teams('{self.team_id}', '{self.event_key}', '{self.team_name}')"

class TeamMembers(db.Model):
    __tablename__ = 'team_members'
    __table_args__ = (
        db.UniqueConstraint('team_key', 'user_key'), # user team pair should be unique
    )

    id = db.Column(db.Integer, primary_key=True)
    team_key = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_key = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    team = db.relationship('Teams', lazy=True)
    user = db.relationship('Users', lazy=True)

    def __repr__(self):
        return f"TeamMembers('{self.team_key}', '{self.user_key}')"

class EventDetails(db.Model):
    __tablename__ = 'event_details'
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
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    reg_no = db.Column(db.String(200), nullable=False) # reg number of user
    pass_type = db.Column(db.String(20), nullable=False)
    # session_id = db.Column(db.String(200), nullable=False)
    # order_id = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, default=0, nullable=False)
    screenshot = db.Column(db.String(50), nullable=False)
    tx_no = db.Column(db.String(50), unique=True, nullable=False)
    is_valid_payment = db.Column(db.Boolean, default=False, nullable=False)
