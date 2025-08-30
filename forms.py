from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, PasswordField, FileField
from wtforms.validators import DataRequired, Email, NumberRange, Length
from flask_wtf.file import FileAllowed

class NewsletterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    place = StringField('Place', validators=[DataRequired(), Length(min=2, max=50)])
    age = IntegerField('Age', validators=[DataRequired(), NumberRange(min=13, max=120)])

class PollVoteForm(FlaskForm):
    opinion_id = IntegerField('Opinion ID', validators=[DataRequired()])
    option_index = IntegerField('Option Index', validators=[DataRequired()])

class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class ReelForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    thumbnail = FileField('Thumbnail', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    video_url = StringField('Video URL')
    behind_thought = TextAreaField('Behind the Thought', validators=[DataRequired()])
    sources = TextAreaField('Sources (one per line)')
    extra_context = TextAreaField('Extra Context')

class OpinionForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    position = StringField('Position', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    poll_question = StringField('Poll Question', validators=[DataRequired()])
    poll_option1 = StringField('Poll Option 1', validators=[DataRequired()])
    poll_option2 = StringField('Poll Option 2', validators=[DataRequired()])
    poll_option3 = StringField('Poll Option 3')
