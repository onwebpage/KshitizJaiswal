import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Database Models
class Reel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    thumbnail = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    behind_thought = db.Column(db.Text)
    sources = db.Column(db.Text)  # JSON string of sources list
    extra_context = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'thumbnail': self.thumbnail or '',
            'video_url': self.video_url or '',
            'behind_thought': self.behind_thought or '',
            'sources': json.loads(self.sources) if self.sources else [],
            'extra_context': self.extra_context or ''
        }

class Opinion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Text)
    description = db.Column(db.Text)
    poll_question = db.Column(db.String(500))
    poll_options = db.Column(db.Text)  # JSON string of options list
    votes = db.Column(db.Text)  # JSON string of votes list
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'position': self.position or '',
            'description': self.description or '',
            'poll_question': self.poll_question or '',
            'poll_options': json.loads(self.poll_options) if self.poll_options else [],
            'votes': json.loads(self.votes) if self.votes else []
        }

class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    place = db.Column(db.String(100))
    age = db.Column(db.String(20))
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'place': self.place or '',
            'age': self.age or '',
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else ''
        }

class SiteContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_key = db.Column(db.String(50), unique=True, nullable=False)
    content_data = db.Column(db.Text)  # JSON string
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)