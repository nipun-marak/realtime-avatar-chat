from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Optional


class LoginForm(FlaskForm):
    """Form for user login/start session."""
    username = StringField('Username', 
                          validators=[DataRequired(), Length(min=1, max=50)],
                          render_kw={'placeholder': "What's your name?", 'maxlength': '50'})
    submit = SubmitField('Start Conversation')


class ChatForm(FlaskForm):
    """Form for chat message input."""
    message = TextAreaField('Message', 
                           validators=[DataRequired(), Length(min=1, max=1000)],
                           render_kw={'placeholder': 'Type or click the mic to speak...', 
                                    'rows': '1', 'maxlength': '1000'})
    submit = SubmitField('Send')


class VoiceToggleForm(FlaskForm):
    """Form for voice toggle functionality."""
    enabled = BooleanField('Voice Enabled', default=True)
    submit = SubmitField('Toggle Voice')


class FullscreenToggleForm(FlaskForm):
    """Form for fullscreen toggle functionality."""
    enabled = BooleanField('Fullscreen Enabled', default=False)
    submit = SubmitField('Toggle Fullscreen')


class AvatarStateForm(FlaskForm):
    """Form for avatar state management."""
    state = StringField('Avatar State', 
                       validators=[DataRequired()],
                       default='idle')
    submit = SubmitField('Set State')
