import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import func, desc
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "kshitiz-jaiswal-website-2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('instance', exist_ok=True)

# Configure the database
database_url = os.environ.get("DATABASE_URL")

# For now, use SQLite for reliable local development
logging.info(f"Using SQLite database")
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    try:
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Failed to create database tables: {e}")
        logging.warning("App will continue but database operations may fail")

# Add context processor for Clerk publishable key and footer data
@app.context_processor
def inject_global_context():
    from models import Opinion, SocialLink
    from utils import slugify, is_column_visible
    
    # Get top 5 archives for footer
    footer_archives = []
    try:
        topics_query = db.session.query(
            Opinion.topic_tag,
            func.max(Opinion.created_at).label('latest_date')
        ).filter(
            Opinion.topic_tag.isnot(None),
            Opinion.topic_tag != ''
        ).group_by(Opinion.topic_tag).order_by(desc('latest_date')).limit(5).all()
        
        for topic, latest_date in topics_query:
            footer_archives.append({
                'title': topic,
                'slug': slugify(topic),
                'year': latest_date.year if latest_date else ''
            })
    except:
        pass  # If DB not ready, just skip
    
    # Get social links
    social_links = []
    try:
        social_links = [link.to_dict() for link in SocialLink.get_active_links()]
    except:
        pass  # If DB not ready, just skip
    
    return {
        'clerk_publishable_key': os.environ.get('CLERK_PUBLISHABLE_KEY', ''),
        'clerk_domain': 'your-domain.com',
        'footer_archives': footer_archives,
        'social_links': social_links,
        'is_column_visible': is_column_visible
    }

# Import routes after app and db creation
from routes import *
