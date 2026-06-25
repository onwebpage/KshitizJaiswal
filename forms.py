from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange, Length, Optional
from flask_wtf.file import FileAllowed

class NewsletterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    place = StringField('Place', validators=[Length(max=50)])
    age = IntegerField('Age', validators=[Optional(), NumberRange(min=13, max=120)], default=None)

class PollVoteForm(FlaskForm):
    opinion_id = IntegerField('Opinion ID', validators=[DataRequired()])
    option_index = IntegerField('Option Index', validators=[NumberRange(min=0)])

class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class ReelForm(FlaskForm):
    title = StringField('Reel Title', validators=[DataRequired(), Length(max=200)])
    thumbnail = FileField('Thumbnail Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'])])
    thumbnail_url = StringField('Thumbnail URL', validators=[Optional(), Length(max=500)])
    video_url = StringField('Instagram Reel URL', validators=[Optional(), Length(max=500)])
    video_type = SelectField('Content Type', choices=[
        ('auto', 'Auto-detect'),
        ('youtube', 'YouTube Video'),
        ('instagram', 'Instagram Reel'),
    ], default='instagram')
    card_layout = SelectField('Card Layout', choices=[
        ('portrait', 'Portrait (9:16)'),
        ('standard', 'Standard (16:9)'),
        ('landscape', 'Landscape (21:9)'),
    ], default='portrait')
    sort_order = IntegerField('Display Order (lower = first)', validators=[NumberRange(min=0)], default=0)
    behind_thought = TextAreaField('Description', validators=[Optional()])
    sources = TextAreaField('Sources (one per line)', validators=[Optional()])
    extra_context = TextAreaField('Extra Context', validators=[Optional()])
    category_tag = SelectField('Category Tag', choices=[
        ('', 'No Tag'),
        ('trending', '🔥 Trending'),
        ('new', '🆕 New'),
        ('fan_favourite', '❤ Fan Favourite'),
        ('exclusive', '⭐ Exclusive'),
        ('must_watch', '👀 Must Watch'),
        ('behind_scenes', '🎬 Behind the Scenes')
    ])
    topic_tag = StringField('Topic Tag', validators=[Optional(), Length(max=100)],
                           render_kw={"placeholder": "e.g., Vote Chori Issue, Education Reform"})
    is_featured = SelectField('Show on Homepage?', choices=[('0', 'No'), ('1', 'Yes')], default='0')
    is_visible = SelectField('Visible on Site?', choices=[('1', 'Yes — Show'), ('0', 'No — Hide')], default='1')

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
    # Keep for backward compatibility
    banner_image = FileField('Hero Background Image (Legacy)', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])

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
    image = FileField('Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'])])
    submit = SubmitField('Save Resource')

class ShowForm(FlaskForm):
    title = StringField('Show Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(max=500)])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'])])
    coming_soon = SelectField('Status', choices=[('1', 'Coming Soon'), ('0', 'Available Now')], default='1')
    banner_type = SelectField('Banner Type', choices=[
        ('youtube', '📺 YouTube — 16:9 Landscape'),
        ('instagram', '📸 Instagram — 9:16 Portrait'),
    ], default='youtube')
    notify_link = StringField('Notification/Registration Link', validators=[Length(max=500)])
    submit = SubmitField('Save Show')

class CourseForm(FlaskForm):
    title = StringField('Course Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Course Description', validators=[DataRequired()])
    thumbnail = FileField('Course Thumbnail', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'])])
    thumbnail_url = StringField('Thumbnail URL', validators=[Optional(), Length(max=500)])
    preview_video_url = StringField('Preview Video URL (YouTube)', validators=[Optional(), Length(max=500)])
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

class TestimonialForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    role = StringField('Role / Location', validators=[DataRequired(), Length(max=100)])
    text = TextAreaField('Testimonial Text', validators=[Optional(), Length(max=500)])
    video_url = StringField('Video Review URL (YouTube — optional)', validators=[Optional(), Length(max=500)])
    rating = SelectField('Rating', choices=[('5','★★★★★  5 Stars'), ('4','★★★★  4 Stars'), ('3','★★★  3 Stars')], default='5')
    is_visible = SelectField('Visible on Site?', choices=[('1','Yes — Show'), ('0','No — Hide')], default='1')
    sort_order = IntegerField('Sort Order (lower = first)', validators=[NumberRange(min=0)], default=0)
    submit = SubmitField('Save Testimonial')

class AnnouncementForm(FlaskForm):
    is_active = SelectField('Status', choices=[('1','Active — Show Banner'), ('0','Inactive — Hide Banner')], default='0')
    text = StringField('Announcement Text', validators=[DataRequired(), Length(max=200)])
    link_url = StringField('Link URL (optional)', validators=[Length(max=500)])
    link_text = StringField('Link Button Text', validators=[Length(max=50)], default='Learn More')
    style = SelectField('Banner Style', choices=[
        ('info',    '🔵 Info (Blue)'),
        ('warning', '🟡 Warning (Yellow)'),
        ('danger',  '🔴 Alert (Red)'),
        ('success', '🟢 Success (Green)'),
        ('dark',    '⚫ Dark'),
    ], default='info')
    submit = SubmitField('Save Announcement')

class AdminAccountForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_username = StringField('New Username', validators=[DataRequired(), Length(min=3, max=50)])
    new_password = PasswordField('New Password (leave blank to keep current)', validators=[Length(min=0, max=100)])
    confirm_password = PasswordField('Confirm New Password')
    submit = SubmitField('Update Account')

class SocialLinkForm(FlaskForm):
    platform = StringField('Platform Name', validators=[DataRequired(), Length(max=50)])
    url = StringField('URL', validators=[Length(max=500)])
    icon_class = StringField('Icon Class (Font Awesome)', validators=[Length(max=100)], default='fab fa-link')
    is_active = SelectField('Active', choices=[('1', 'Yes'), ('0', 'No')], default='1')
    sort_order = IntegerField('Sort Order', validators=[NumberRange(min=0)], default=0)
    submit = SubmitField('Save Link')

class PageContentForm(FlaskForm):
    reels_section_title = StringField('Reels Section Title', validators=[DataRequired(), Length(max=200)])
    reels_section_subtitle = StringField('Reels Section Subtitle', validators=[Length(max=500)])
    support_section_title = StringField('Support Section Title', validators=[DataRequired(), Length(max=200)])
    support_section_subtitle = StringField('Support Section Subtitle', validators=[Length(max=500)])
    custom_support_button_text = StringField('Custom Support Button Text', validators=[Length(max=200)])
    custom_support_subtitle = StringField('Custom Support Subtitle', validators=[Length(max=500)])
    support_stats_count = IntegerField('Supporters Count', validators=[NumberRange(min=0)], default=0)
    support_stats_amount = IntegerField('Amount Raised This Month (₹)', validators=[NumberRange(min=0)], default=0)
    submit = SubmitField('Save Page Content')
