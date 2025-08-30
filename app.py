import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "kshitiz-jaiswal-website-2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
database_url = os.environ.get("DATABASE_URL")
if not database_url or database_url.strip() == "":
    # Use a default SQLite database for development if DATABASE_URL is empty
    database_url = "sqlite:///./data/app.db"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# Import and initialize database
from database import db
db.init_app(app)

with app.app_context():
    # Create all database tables
    db.create_all()

# Import routes after app and db creation
from routes import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
