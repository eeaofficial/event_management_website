from flask_wtf import FlaskForm
from wtforms import *
from wtforms.fields import DateField, TimeField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from datetime import date

from app.models import User

from string import ascii_letters, digits

from datetime import datetime
# change ALL FORM and FORM ELEMENTS as per requirement
class SignUpForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    name = StringField('Name', validators=[DataRequired(), Length(min=5, max=20)])
    reg_no = StringField('Your Registration Number in your College', validators=[DataRequired()])
    dept = SelectField(
        'Department',
        choices=[
            ('Aero', 'Aeronautical'), 
            ('Auto', 'Automobile'), 
            ('CT', 'Computer Technology'),
            ('EC', 'Electronics and Communication'),
            ('IT', 'Information Technology'),
            ('EI', 'Electronics and Instrumentation'),
            ('RPT', 'Rubber and Plastic Technology'),
            ('PT', 'Production Technology'),
            ('Mech', 'Mechanical'),
            ('AIDS', 'Artificial Intelligence & Data Science'),
            ('RA', 'Robotics & Automation'),
            ('Other', 'Other')
        ],
        validators=[DataRequired()]
    )

    other_dept_name = StringField('Department')

    college = SelectField(
        'College',
        choices=[
            ('MIT', 'MIT'),
            ('Other', 'Other')
        ]
    )

    other_college_name = StringField('College Name')
    
    mobile = StringField('Phone', validators=[DataRequired(), Length(min=10, max=10)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', "Password doesn't match")])

    submit = SubmitField('Sign Up')

    # if email needs to be unique, uncomment below snippet of code
    # def validate_email(self, email):
    #     user = User.query.filter_by(email=email.data).first()
    #     if user:
    #         raise ValidationError('Account already exists')
    
    def validate_reg_no(self, reg_no):
        user = User.query.filter_by(reg_no=reg_no.data).first()
        if user:
            raise ValidationError('Account already exists')

    def validate_mobile(self, mobile):
        try:
            n = int(mobile.data)
        except:
            raise ValidationError('Invalid Mobile Number')

        
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    reg_no = StringField('College Registration Number', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    reg_no = StringField('College Registration Number', validators=[DataRequired()])
    submit = SubmitField('Get Reset Link')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('No such account exists')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', "Password doesn't match")])

    submit = SubmitField('Reset')

# class AdminForm(FlaskForm):
#     password = PasswordField('Password', validators=[DataRequired()])
#     submit = SubmitField('Login')

class UpdateProfileForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    name = StringField('Name', validators=[DataRequired(), Length(min=5, max=20)])
    dept = SelectField(
        'Department',
        choices=[
            ('Aero', 'Aeronautical'), 
            ('Auto', 'Automobile'), 
            ('CT', 'Computer Technology'),
            ('EC', 'Electronics and Communication'),
            ('IT', 'Information Technology'),
            ('EI', 'Electronics and Instrumentation'),
            ('RPT', 'Rubber and Plastic Technology'),
            ('PT', 'Production Technology'),
            ('Mech', 'Mechanical'),
            ('AIDS', 'Artificial Intelligence & Data Science'),
            ('RA', 'Robotics & Automation'),
            ('Other', 'Other')
        ],
        validators=[DataRequired()]
    )

    other_dept_name = StringField('Department')

    college = SelectField(
        'College',
        choices=[
            ('MIT', 'MIT'),
            ('Other', 'Other')
        ]
    )

    other_college_name = StringField('College Name')
    
    mobile = StringField('Phone', validators=[DataRequired(), Length(min=10, max=10)])

    submit = SubmitField('Update')

    def validate_reg_no(self, reg_no):
        try:
            print(reg_no)
            int(reg_no.data)
        except:
            raise ValidationError('Invalid Registration Number')
        user = User.query.filter_by(reg_no=reg_no.data).first()
        if user:
            raise ValidationError('Account already exists')

    def validate_mobile(self, mobile):
        try:
            n = int(mobile.data)
        except:
            raise ValidationError('Invalid Mobile Number')
