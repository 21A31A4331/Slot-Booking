from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, 
    TextAreaField, IntegerField, DecimalField, SelectField, DateField, TimeField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange
from datetime import date, time
from app.models import User

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[Length(max=20)])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError('Username is already taken. Please choose another.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError('Email is already registered. Please sign in or use another email.')


class ServiceForm(FlaskForm):
    name = StringField('Service Name', validators=[DataRequired(), Length(max=100)])
    category = StringField('Category', validators=[DataRequired(), Length(max=50)], default='Consultation')
    duration_minutes = IntegerField('Duration (Minutes)', validators=[
        DataRequired(), 
        NumberRange(min=5, max=480, message='Duration must be between 5 and 480 minutes.')
    ], default=30)
    price = DecimalField('Price ($)', validators=[
        NumberRange(min=0, message='Price must be non-negative.')
    ], default=0.00, places=2)
    description = TextAreaField('Description', validators=[Length(max=1000)])
    is_active = BooleanField('Active & Available for Booking', default=True)
    submit = SubmitField('Save Service')


class SlotGeneratorForm(FlaskForm):
    service_id = SelectField('Service', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()], default=date.today)
    end_date = DateField('End Date', validators=[DataRequired()], default=date.today)
    start_time = TimeField('Day Start Time', validators=[DataRequired()], default=time(9, 0))
    end_time = TimeField('Day End Time', validators=[DataRequired()], default=time(17, 0))
    slot_duration = IntegerField('Slot Duration (Minutes)', validators=[
        DataRequired(), 
        NumberRange(min=10, max=240, message='Slot duration must be between 10 and 240 minutes.')
    ], default=30)
    capacity = IntegerField('Capacity per Slot', validators=[
        DataRequired(),
        NumberRange(min=1, max=100, message='Capacity must be at least 1.')
    ], default=1)
    skip_weekends = BooleanField('Skip Weekends (Saturday & Sunday)', default=True)
    submit = SubmitField('Generate Slots')

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError('End date cannot be earlier than start date.')

    def validate_end_time(self, field):
        if field.data <= self.start_time.data:
            raise ValidationError('End time must be later than start time.')


class ManualSlotForm(FlaskForm):
    service_id = SelectField('Service', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    start_time = TimeField('Start Time', validators=[DataRequired()], default=time(9, 0))
    end_time = TimeField('End Time', validators=[DataRequired()], default=time(9, 30))
    capacity = IntegerField('Capacity', validators=[DataRequired(), NumberRange(min=1, max=100)], default=1)
    submit = SubmitField('Add Slot')

    def validate_end_time(self, field):
        if field.data <= self.start_time.data:
            raise ValidationError('End time must be later than start time.')


class BookingForm(FlaskForm):
    slot_id = IntegerField('Slot ID', validators=[DataRequired()])
    notes = TextAreaField('Special Notes or Requirements', validators=[Length(max=500)])
    submit = SubmitField('Confirm Booking')
