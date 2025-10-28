from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, PasswordField, FileField, SubmitField
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
    category_tag = SelectField('Category Tag', choices=[
        ('', 'No Tag'),
        ('trending', '🔥 Trending'),
        ('new', '🆕 New'),
        ('fan_favourite', '❤ Fan Favourite'),
        ('exclusive', '⭐ Exclusive'),
        ('must_watch', '👀 Must Watch'),
        ('behind_scenes', '🎬 Behind the Scenes')
    ])
    topic_tag = StringField('Topic Tag', validators=[Length(max=100)], 
                           render_kw={"placeholder": "e.g., Vote Chori Issue, Education Reform"})
    is_featured = SelectField('Show on Homepage?', choices=[('0', 'No'), ('1', 'Yes')], default='0')

class OpinionForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    position = StringField('Position', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    topic_tag = StringField('Topic Tag', validators=[Length(max=100)], 
                           render_kw={"placeholder": "e.g., Politics, Social Issues, Economics"})
    poll_question = StringField('Poll Question', validators=[DataRequired()])
    poll_option1 = StringField('Poll Option 1', validators=[DataRequired()])
    poll_option2 = StringField('Poll Option 2', validators=[DataRequired()])
    poll_option3 = StringField('Poll Option 3')

class HeroContentForm(FlaskForm):
    name = StringField('Hero Title', validators=[DataRequired(), Length(max=100)])
    tagline = TextAreaField('Hero Tagline', validators=[DataRequired(), Length(max=500)])
    desktop_image = FileField('Desktop Hero Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    mobile_image = FileField('Mobile Hero Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    desktop_url = StringField('Or Desktop Image URL', validators=[Length(max=500)])
    mobile_url = StringField('Or Mobile Image URL', validators=[Length(max=500)])
    # Keep for backward compatibility
    banner_image = FileField('Hero Background Image (Legacy)', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    banner_url = StringField('Or Banner URL (Legacy)', validators=[Length(max=500)])

class PaymentSettingsForm(FlaskForm):
    razorpay_key_id = StringField('Razorpay Key ID', validators=[DataRequired(), Length(max=100)])
    razorpay_key_secret = StringField('Razorpay Key Secret', validators=[DataRequired(), Length(max=100)])

class SubscriptionTierForm(FlaskForm):
    name = StringField('Tier Name', validators=[DataRequired(), Length(max=100)])
    price = IntegerField('Price (₹)', validators=[DataRequired(), NumberRange(min=1)])
    period = SelectField('Period', choices=[('week', 'Week'), ('month', 'Month'), ('year', 'Year')], default='week')
    description = TextAreaField('Description', validators=[DataRequired(), Length(max=500)])
    icon = StringField('Icon Class (Font Awesome)', validators=[Length(max=50)], default='fas fa-heart')
    benefit1 = StringField('Benefit 1', validators=[DataRequired(), Length(max=100)])
    benefit2 = StringField('Benefit 2', validators=[Length(max=100)])
    benefit3 = StringField('Benefit 3', validators=[Length(max=100)])
    benefit4 = StringField('Benefit 4', validators=[Length(max=100)])
    is_popular = SelectField('Mark as Popular?', choices=[('0', 'No'), ('1', 'Yes')], default='0')
    sort_order = IntegerField('Sort Order', validators=[NumberRange(min=0)], default=0)
    submit = SubmitField('Save Tier')

class ResourceForm(FlaskForm):
    title = StringField('Resource Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(max=500)])
    price = StringField('Price', validators=[Length(max=50)], default='Free')
    link = StringField('Link/URL', validators=[DataRequired(), Length(max=500)])
    image = StringField('Image URL', validators=[Length(max=500)])
    submit = SubmitField('Save Resource')

class ShowForm(FlaskForm):
    title = StringField('Show Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(max=500)])
    image = StringField('Image URL', validators=[Length(max=500)])
    coming_soon = SelectField('Status', choices=[('1', 'Coming Soon'), ('0', 'Available Now')], default='1')
    notify_link = StringField('Notification/Registration Link', validators=[Length(max=500)])
    submit = SubmitField('Save Show')

class CourseForm(FlaskForm):
    title = StringField('Course Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Course Description', validators=[DataRequired()])
    thumbnail = FileField('Course Thumbnail', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    thumbnail_url = StringField('Or Thumbnail URL', validators=[Length(max=500)])
    price = IntegerField('Price (₹)', validators=[DataRequired(), NumberRange(min=0)])
    is_active = SelectField('Active', choices=[('1', 'Yes'), ('0', 'No')], default='1')
    sort_order = IntegerField('Sort Order', validators=[NumberRange(min=0)], default=0)
    submit = SubmitField('Save Course')

class ModuleForm(FlaskForm):
    title = StringField('Module Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Module Description')
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    sort_order = IntegerField('Sort Order', validators=[NumberRange(min=0)], default=0)
    submit = SubmitField('Save Module')

class LessonForm(FlaskForm):
    title = StringField('Lesson Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Lesson Description')
    module_id = SelectField('Module', coerce=int, validators=[DataRequired()])
    video_url = StringField('YouTube Video URL', validators=[DataRequired(), Length(max=500)])
    notes = TextAreaField('Lesson Notes/Resources')
    duration = StringField('Duration (e.g., 15:30)', validators=[Length(max=20)])
    sort_order = IntegerField('Sort Order', validators=[NumberRange(min=0)], default=0)
    submit = SubmitField('Save Lesson')
