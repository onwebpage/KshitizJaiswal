import os
import logging
import traceback
from collections import deque
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import func, desc
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# In-memory error log — keeps last 100 errors for admin review
_error_log = deque(maxlen=100)

def log_app_error(error, context=''):
    """Store an error entry for admin error log viewing."""
    _error_log.appendleft({
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'type': type(error).__name__,
        'message': str(error),
        'traceback': traceback.format_exc(),
        'context': context,
    })

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('instance', exist_ok=True)

# Configure the database
# Prefer Replit's native PostgreSQL (PGHOST=helium) over any external DATABASE_URL
def _build_replit_pg_url():
    host = os.environ.get("PGHOST")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER")
    password = os.environ.get("PGPASSWORD")
    dbname = os.environ.get("PGDATABASE")
    if host and user and dbname:
        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        return f"postgresql://{user}@{host}:{port}/{dbname}"
    return None

database_url = _build_replit_pg_url() or os.environ.get("DATABASE_URL")

# Check if we should use PostgreSQL or SQLite
use_sqlite = False

if database_url:
    # Try to use PostgreSQL, but fall back to SQLite if connection fails
    try:
        import psycopg2
        # Quick connection test
        test_conn = psycopg2.connect(database_url)
        test_conn.close()
        logging.info("Using PostgreSQL database (Production)")
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
    except Exception as e:
        logging.warning(f"PostgreSQL connection failed ({e}), falling back to SQLite")
        use_sqlite = True
else:
    use_sqlite = True

if use_sqlite:
    # Development: Use SQLite
    logging.info("Using SQLite database (Development)")
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
        # Run column migrations for existing tables
        from sqlalchemy import text
        migrations = [
            "ALTER TABLE user_course_access ALTER COLUMN clerk_user_id DROP NOT NULL",
            "ALTER TABLE user_course_access ADD COLUMN IF NOT EXISTS guest_name VARCHAR(200)",
            "ALTER TABLE user_course_access ADD COLUMN IF NOT EXISTS guest_email VARCHAR(200)",
            "ALTER TABLE user_course_access ADD COLUMN IF NOT EXISTS guest_phone VARCHAR(20)",
            "ALTER TABLE module ADD COLUMN IF NOT EXISTS is_visible BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE module ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'published'",
            "ALTER TABLE lesson ADD COLUMN IF NOT EXISTS is_visible BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE lesson ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'published'",
            "ALTER TABLE user_activity ALTER COLUMN session_id TYPE TEXT",
            "ALTER TABLE course ADD COLUMN IF NOT EXISTS preview_video_url VARCHAR(500)",
            "ALTER TABLE subscription_tier ADD COLUMN IF NOT EXISTS razorpay_plan_id VARCHAR(100)",
        ]
        for sql in migrations:
            try:
                db.session.execute(text(sql))
                db.session.commit()
            except Exception:
                db.session.rollback()
    except Exception as e:
        logging.error(f"Failed to create database tables: {e}")
        logging.warning("App will continue but database operations may fail")

# Add context processor for Clerk publishable key and footer data
@app.context_processor
def inject_global_context():
    from models import Opinion, SocialLink, SiteContent
    from utils import slugify, is_column_visible
    from forms import NewsletterForm
    import json

    # Newsletter form for footer (available on every page)
    footer_newsletter_form = NewsletterForm()

    # WhatsApp support phone from DB settings
    whatsapp_support_phone = ''
    try:
        wa_rec = SiteContent.query.filter_by(content_key='whatsapp_settings').first()
        if wa_rec:
            wa_data = json.loads(wa_rec.content_data)
            whatsapp_support_phone = wa_data.get('support_phone', '')
    except Exception:
        pass

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
    except Exception as e:
        logging.debug(f"Database not available for footer archives: {e}")
        pass  # If DB not ready, just skip
    
    # Get social links
    social_links = []
    try:
        social_links = [link.to_dict() for link in SocialLink.get_active_links()]
    except Exception as e:
        logging.debug(f"Database not available for social links: {e}")
        pass  # If DB not ready, just skip
    
    return {
        'clerk_publishable_key': os.environ.get('CLERK_PUBLISHABLE_KEY', ''),
        'clerk_domain': 'your-domain.com',
        'footer_archives': footer_archives,
        'social_links': social_links,
        'is_column_visible': is_column_visible,
        'footer_newsletter_form': footer_newsletter_form,
        'whatsapp_support_phone': whatsapp_support_phone,
    }

# Import routes after app and db creation
from routes import *
