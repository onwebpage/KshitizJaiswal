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
# Priority: Replit native PG (PGHOST) → external DATABASE_URL → SQLite fallback
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

def _is_external_db(url):
    """Return True when the URL is NOT Replit's internal helium database."""
    if not url:
        return False
    return "helium" not in url and "PGHOST" not in url

replit_pg_url = _build_replit_pg_url()
external_db_url = os.environ.get("DATABASE_URL")
database_url = replit_pg_url or external_db_url

use_sqlite = False

if database_url:
    try:
        import psycopg2
        # Build connection kwargs — external providers (Railway, Aiven, Neon, Supabase)
        # require sslmode=require; Replit's internal helium does not.
        is_external = _is_external_db(database_url) and not replit_pg_url
        connect_kwargs = {}
        if is_external and "sslmode" not in database_url:
            connect_kwargs["sslmode"] = "require"

        test_conn = psycopg2.connect(database_url, **connect_kwargs)
        test_conn.close()

        engine_options = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        if is_external and "sslmode" not in database_url:
            engine_options["connect_args"] = {"sslmode": "require"}

        logging.info(f"Using PostgreSQL database ({'external' if is_external else 'Replit internal'})")
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    except Exception as e:
        logging.warning(f"PostgreSQL connection failed ({e}), falling back to SQLite")
        use_sqlite = True
else:
    use_sqlite = True

if use_sqlite:
    logging.info("Using SQLite database (Development fallback)")
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

        # ── Safe column migrations ────────────────────────────────────────────
        # Uses inspect() to check existence first — compatible with both
        # PostgreSQL (supports IF NOT EXISTS) and SQLite (does not).
        from sqlalchemy import text, inspect as sa_inspect

        def _has_column(table, column):
            try:
                insp = sa_inspect(db.engine)
                return column in [c['name'] for c in insp.get_columns(table)]
            except Exception:
                return False  # unknown → skip the migration

        def _add_column(table, column, col_type):
            """ADD COLUMN only if missing; silently skips on any error."""
            if _has_column(table, column):
                return
            try:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                db.session.commit()
                logging.info(f"Migration: added {table}.{column}")
            except Exception as _e:
                db.session.rollback()
                logging.warning(f"Migration skipped {table}.{column}: {_e}")

        # Add missing columns (safe for both PostgreSQL and SQLite)
        _add_column("user_course_access", "guest_name",           "VARCHAR(200)")
        _add_column("user_course_access", "guest_email",          "VARCHAR(200)")
        _add_column("user_course_access", "guest_phone",          "VARCHAR(20)")
        _add_column("user_course_access", "order_id",             "VARCHAR(200)")
        _add_column("user_course_access", "payment_status",       "VARCHAR(50) DEFAULT 'success'")
        _add_column("user_course_access", "account_created",      "BOOLEAN DEFAULT FALSE")
        _add_column("user_course_access", "access_revoked",       "BOOLEAN DEFAULT FALSE")
        _add_column("module",             "is_visible",           "BOOLEAN NOT NULL DEFAULT TRUE")
        _add_column("module",             "status",               "VARCHAR(20) NOT NULL DEFAULT 'published'")
        _add_column("lesson",             "is_visible",           "BOOLEAN NOT NULL DEFAULT TRUE")
        _add_column("lesson",             "status",               "VARCHAR(20) NOT NULL DEFAULT 'published'")
        _add_column("course",             "preview_video_url",    "VARCHAR(500)")
        _add_column("subscription_tier",  "razorpay_plan_id",     "VARCHAR(100)")
        _add_column("subscriber",         "phone",                "VARCHAR(20)")
        _add_column("reel",               "video_type",           "VARCHAR(20) DEFAULT 'auto'")
        _add_column("reel",               "card_layout",          "VARCHAR(20) DEFAULT 'standard'")
        _add_column("course",             "created_at",           "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column("reel",               "created_at",           "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column("reel",               "sort_order",           "INTEGER DEFAULT 0")
        _add_column("reel",               "category_tag",         "VARCHAR(50)")
        _add_column("reel",               "topic_tag",            "VARCHAR(100)")
        _add_column("reel",               "view_count",           "INTEGER DEFAULT 0")
        _add_column("reel",               "is_featured",          "BOOLEAN DEFAULT FALSE")
        _add_column("opinion",            "topic_tag",            "VARCHAR(100)")
        _add_column("subscriber",         "place",                "VARCHAR(100)")
        _add_column("subscriber",         "age",                  "VARCHAR(20)")

        # PostgreSQL-only migrations (silently ignored on SQLite)
        pg_only = [
            "ALTER TABLE user_course_access ALTER COLUMN clerk_user_id DROP NOT NULL",
            "ALTER TABLE user_activity ALTER COLUMN session_id TYPE TEXT",
        ]
        for sql in pg_only:
            try:
                db.session.execute(text(sql))
                db.session.commit()
            except Exception:
                db.session.rollback()

        # ── Seed default data on fresh databases ─────────────────────────────
        try:
            from models import SocialLink, AdminUser as _AdminUser
            SocialLink.seed_missing_platforms()   # adds any missing platform rows
            _AdminUser.create_default_tiers()     # creates subscription tiers if none
            logging.info("Default data seeding complete")
        except Exception as _seed_err:
            logging.warning(f"Seeding skipped: {_seed_err}")

    except Exception as e:
        logging.error(f"Failed to create database tables: {e}")
        logging.warning("App will continue but database operations may fail")

# ── CSRF token available in all templates ────────────────────────────────────
@app.context_processor
def inject_csrf():
    from flask_wtf.csrf import generate_csrf
    def csrf_token():
        return generate_csrf()
    return dict(csrf_token=csrf_token)

# Add context processor for Clerk publishable key and footer data
@app.context_processor
def inject_global_context():
    from models import Opinion, SocialLink, SiteContent
    from utils import slugify, is_column_visible
    from forms import NewsletterForm
    import json

    # Newsletter form for footer (available on every page)
    footer_newsletter_form = NewsletterForm()

    from utils import load_whatsapp_settings
    _wa = load_whatsapp_settings()
    whatsapp_support_phone = _wa['phone_digits']
    whatsapp_link = _wa['whatsapp_link']
    whatsapp_web_link = _wa['whatsapp_web_link']

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

    # Get footer stats (top 2 active stats for the footer bar)
    footer_stats = []
    try:
        from models import Subscriber, Reel
        stats_rec = SiteContent.query.filter_by(content_key='statistics_data').first()
        if stats_rec:
            import json as _json
            _sd = _json.loads(stats_rec.content_data)
            _active = sorted(
                [s for s in _sd.get('stats', []) if s.get('is_active', True)],
                key=lambda s: s.get('sort_order', 999)
            )
            _sup_cache = None
            for s in _active:
                if s.get('auto') == 'subscriber_count':
                    s['resolved_value'] = str(Subscriber.query.count())
                elif s.get('auto') == 'reel_count':
                    s['resolved_value'] = str(Reel.query.filter_by(is_visible=True).count())
                elif s.get('auto') == 'support_total':
                    if _sup_cache is None:
                        try:
                            from models import UserSubscription as _US
                            _rows = db.session.query(_US.amount_paise, _US.paid_count).filter(_US.status == 'active').all()
                            _tp = sum((r.amount_paise or 0) * (r.paid_count or 0) for r in _rows)
                            _sup_cache = '₹{:,}'.format(_tp // 100)
                        except Exception:
                            _sup_cache = s.get('value', '₹0')
                    s['resolved_value'] = _sup_cache
                else:
                    s['resolved_value'] = s.get('value', '')
            footer_stats = _active[:2]
    except Exception as e:
        logging.debug(f"Could not load footer stats: {e}")

    return {
        'clerk_publishable_key': os.environ.get('CLERK_PUBLISHABLE_KEY', ''),
        'clerk_domain': 'your-domain.com',
        'footer_archives': footer_archives,
        'social_links': social_links,
        'is_column_visible': is_column_visible,
        'footer_newsletter_form': footer_newsletter_form,
        'whatsapp_support_phone': whatsapp_support_phone,
        'whatsapp_link': whatsapp_link,
        'whatsapp_web_link': whatsapp_web_link,
        'footer_stats': footer_stats,
    }

# Import routes after app and db creation
from routes import *
