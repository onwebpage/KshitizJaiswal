import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
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

# Configure the database, relative to the app instance folder
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    logging.error("DATABASE_URL environment variable is not set!")
    sqlite_path = os.path.join(os.getcwd(), 'instance', 'app.db')
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    database_url = f"sqlite:///{sqlite_path}"  # Fallback to SQLite for development
    logging.warning(f"Using fallback database: {database_url}")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    db.create_all()

# Add context processor for Clerk publishable key and footer data
@app.context_processor
def inject_global_context():
    from models import Opinion
    from utils import slugify
    
    # Get top 5 archives for footer
    footer_archives = []
    try:
        topics_query = db.session.query(
            Opinion.topic_tag,
            db.func.max(Opinion.created_at).label('latest_date')
        ).filter(
            Opinion.topic_tag.isnot(None),
            Opinion.topic_tag != ''
        ).group_by(Opinion.topic_tag).order_by(db.desc('latest_date')).limit(5).all()
        
        for topic, latest_date in topics_query:
            footer_archives.append({
                'title': topic,
                'slug': slugify(topic),
                'year': latest_date.year if latest_date else ''
            })
    except:
        pass  # If DB not ready, just skip
    
    return {
        'clerk_publishable_key': os.environ.get('CLERK_PUBLISHABLE_KEY', ''),
        'clerk_domain': 'your-domain.com',
        'footer_archives': footer_archives
    }

# Import routes after app and db creation
from routes import *
