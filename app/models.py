"""
Models
"""

from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy.ext.associationproxy import association_proxy

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
    mobile = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(128), nullable=False)

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

    def event_passes(self):
        return (
            db.session.query(Passes)
            .join(Purchases)
            .filter(
                Purchases.purchased_by_key == self.id,
                Purchases.payment_status == 'accepted'
            )
            .distinct()
            .all()
        )

    def get_organizing_events(self):
        return (
            EventDetails.query
            .join(EventOrganizers)
            .filter(
                EventOrganizers.organizer_key == self.id,
            )
            .distinct()
            .all()
        )
    
    def to_dict(self):
        return {
            'name': self.name,
            'reg_no': self.reg_no,
            'college': self.college,
            'dept': self.dept,
            'email': self.email,
            'mobile': self.mobile
        }

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
    registration_by_key = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # sqlite's NOW is UTC time with
    # note timezone info not stored
    # ensure every write to timestamp is in UTC
    registration_at = db.Column(db.DateTime, nullable=False,
        server_default=db.func.now()
    )

    event = db.relationship('EventDetails', lazy=True)
    team = db.relationship('Teams', lazy=True)
    registration_by = db.relationship('Users', lazy=True)

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
    tms = db.relationship('TeamMembers', lazy=True)

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

    event_attended = db.Column(db.Boolean, default=False)
    # is valid only if event_attended is set
    # else this holds time when team created
    attended_at = db.Column(db.DateTime, nullable=False,
        server_default=db.func.now()
    )

    team = db.relationship('Teams', lazy=True)
    user = db.relationship('Users', lazy=True)

    def is_winner(self):
        return (
            EventResults.query
            .join(EventResults.tm)
            .filter(
                EventResults.tm_key == self.id,
                EventResults.event_key == self.team.event_key,
                TeamMembers.user_key == self.user_key,
                EventResults.position == 1
            ).first()
            is not None
        )

    def is_runner(self):
        return (
            EventResults.query
            .join(EventResults.tm)
            .filter(
                EventResults.tm_key == self.id,
                EventResults.event_key == self.team.event_key,
                TeamMembers.user_key == self.user_key,
                EventResults.position == 2
            ).first()
            is not None
        )

    def __repr__(self):
        return f"TeamMembers('{self.id}', 'Teams:{self.team_key}', 'Users:{self.user_key}')"

class EventDetails(db.Model):
    __tablename__ = 'event_details'

    id = db.Column(db.Integer, primary_key=True)
    created_by_key = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    event_id = db.Column(db.String(5), nullable=False, unique=True)
    name = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    max_team_size = db.Column(db.Integer, nullable=False)
    num_rounds = db.Column(db.Integer, nullable=False)
    rounds = db.Column(db.JSON, nullable=False) # json string with name, description, time, mode
    thumbnail = db.Column(db.String(20))
    topic = db.Column(db.String(40))
    # send via mail once registered
    participant_instructions = db.Column(db.String(1000), default='', nullable=False)

    #admin should accept to make things "on-line" at website for the public
    is_event_accepted = db.Column(db.Boolean, default=False, nullable=False)

    # control accepting participants into events
    is_accepting_registration = db.Column(db.Boolean, default=True, nullable=False)

    is_result_submitted = db.Column(db.Boolean, default=False, nullable=False)
    # if result accepted by admin; will be pushed "on-line"
    is_result_accepted = db.Column(db.Boolean, default=False, nullable=False)

    created_by = db.relationship('Users', lazy=True)

    def get_organizers(self):
        return ( Users.query
            .join(EventOrganizers)
            .filter(
                EventOrganizers.event_key == self.id,
                Users.id == EventOrganizers.organizer_key,
            )
            .all()
        )


class EventOrganizers(db.Model):
    __tablename__ = 'event_organizers'

    id = db.Column(db.Integer, primary_key=True)
    event_key = db.Column(db.Integer, db.ForeignKey('event_details.id'), nullable=False)
    organizer_key = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    event = db.relationship('EventDetails', lazy=True)
    organizer = db.relationship('Users', lazy=True)


class EventResults(db.Model):
    __tablename__ = 'event_results'
    id = db.Column(db.Integer, primary_key=True)
    event_key = db.Column(db.Integer, db.ForeignKey('event_details.id'), nullable=False)
    tm_key = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=False)

    position = db.Column(db.Integer, default=0)

    event = db.relationship('EventDetails', lazy=True)
    tm = db.relationship('TeamMembers', lazy=True)
    participant = association_proxy('tm', 'user')


# Passes and Passes accesses are not yet robust enough
# while creating events, admin must ensure to add all respective events to passes
# while displaying to users, currently, it says Pass for ALL Tech Events etc
class Passes(db.Model):
    __tablename__ = 'passes'

    id = db.Column(db.Integer, primary_key=True)
    created_by_key = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    pass_id = db.Column(db.String(20), unique=True)
    pass_type = db.Column(db.String(20)) # event or workshop
    pass_name = db.Column(db.String(20))
    pass_description = db.Column(db.String(100))
    price = db.Column(db.Integer, default=-1)
    created_at = db.Column(db.DateTime, nullable=False,
        server_default=db.func.now()
    )
    is_active = db.Column(db.Boolean, default=True)

    created_by = db.relationship('Users', lazy=True)

    events = db.relationship(
        'EventDetails',
        secondary='pass_accesses',
        lazy=True
    )


class PassAccesses(db.Model):
    __tablename__ = 'pass_accesses'

    id = db.Column(db.Integer, primary_key=True)
    event_key = db.Column(db.Integer, db.ForeignKey('event_details.id'), nullable=False)
    pass_key = db.Column(db.Integer, db.ForeignKey('passes.id'), nullable=False)

    event = db.relationship('EventDetails', lazy=True)
    event_pass = db.relationship('Passes', lazy=True)

class Purchases(db.Model):
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    pass_key = db.Column(db.Integer, db.ForeignKey('passes.id'), nullable=False)
    purchased_by_key = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    purchase_id = db.Column(db.String(40), nullable=False, unique=True)
    payment_proof = db.Column(db.String(40), nullable=False, unique=True) # screenshot file name
    transaction_id = db.Column(db.String(40)) # nullable
    purchased_at = db.Column(db.DateTime, nullable=False,
        server_default=db.func.now()
    )
    purchase_price = db.Column(db.Integer)
    payment_status = db.Column(db.String(20), default='submitted') # submitted, accepted, rejected, cancelled

    event_pass = db.relationship('Passes', lazy=True)
    purchased_by = db.relationship('Users', lazy=True)

class PurchaseStatusLogs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_key = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    changed_by_key = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # just record new tx id
    tx_id = db.Column(db.String(20))
    status =  db.Column(db.String(20))
    reason = db.Column(db.String(30))
    changed_at = db.Column(db.DateTime, nullable=False,
        server_default=db.func.now()
    )
    changed_fields = db.Column(db.String(40))

    changed_by = db.relationship('Users', lazy=True)
    purchase = db.relationship('Purchases', lazy=True)
