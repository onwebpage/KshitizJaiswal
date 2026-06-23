import os
import secrets
import re
import unicodedata
from PIL import Image
from flask import current_app
from werkzeug.utils import secure_filename

def save_uploaded_file(form_file, folder_name):
    """Save uploaded file and return filename"""
    if form_file and form_file.filename:
        # Generate random filename
        random_hex = secrets.token_hex(8)
        _, file_ext = os.path.splitext(form_file.filename)
        filename = random_hex + file_ext
        
        # Create folder if it doesn't exist
        folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, filename)
        
        # Resize image if it's an image file
        if file_ext.lower() in ['.jpg', '.jpeg', '.png']:
            img = Image.open(form_file)
            # Resize to max 800x600 while maintaining aspect ratio
            img.thumbnail((800, 600), Image.Resampling.LANCZOS)
            img.save(file_path, optimize=True, quality=85)
        else:
            form_file.save(file_path)
        
        return f"uploads/{folder_name}/{filename}"
    
    return None

def format_number(num):
    """Format number with K, M suffixes"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def calculate_poll_percentages(votes):
    """Calculate poll percentages"""
    total = sum(votes)
    if total == 0:
        return [0] * len(votes)
    return [round((vote / total) * 100, 1) for vote in votes]

def slugify(text):
    """Convert text to URL-safe slug"""
    if not text:
        return ''
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Convert to lowercase and replace spaces/special chars with hyphens
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    text = text.strip('-')
    
    return text

def get_video_info(url, video_type='auto'):
    """Detect video source and return embed URL, original URL, and type.
    
    Returns a dict:
      embed_url    — iframe-safe URL (YouTube embed or Instagram embed)
      original_url — the canonical link to open on the platform
      video_type   — 'youtube' | 'youtube_short' | 'instagram' | 'unknown'
      video_id     — the extracted ID string
    """
    if not url:
        return {'embed_url': None, 'original_url': url or '', 'video_type': 'unknown', 'video_id': None}

    # ── Instagram ────────────────────────────────────────────────
    # Matches both formats:
    #   instagram.com/reel/ID
    #   instagram.com/username/reel/ID  (with profile slug)
    #   instagram.com/p/ID
    instagram_pattern = r'(?:https?://)?(?:www\.)?instagram\.com/(?:[^/]+/)?(?:p|reel)/([A-Za-z0-9_-]+)'
    instagram_match = re.search(instagram_pattern, url)

    if instagram_match or video_type == 'instagram':
        if instagram_match:
            reel_id = instagram_match.group(1)
        else:
            # Forced type — best-effort ID extraction
            reel_id = re.sub(r'/+$', '', url).split('/')[-1]
        return {
            'embed_url': f'https://www.instagram.com/reel/{reel_id}/embed/',
            'original_url': f'https://www.instagram.com/reel/{reel_id}/',
            'video_type': 'instagram',
            'video_id': reel_id,
        }

    # ── YouTube ───────────────────────────────────────────────────
    yt_patterns = [
        (r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]+)', True),
        (r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]+)', False),
        (r'(?:https?://)?youtu\.be/([A-Za-z0-9_-]+)', False),
        (r'(?:https?://)?(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]+)', False),
    ]
    for pattern, is_short in yt_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1).split('?')[0]  # strip any trailing query params
            embed_params = 'controls=1&rel=0&modestbranding=1&iv_load_policy=3&playsinline=1'
            return {
                'embed_url': f'https://www.youtube.com/embed/{video_id}?{embed_params}',
                'original_url': f'https://youtu.be/{video_id}',
                'video_type': 'youtube_short' if is_short else 'youtube',
                'video_id': video_id,
            }

    # ── Forced YouTube with no recognisable pattern ───────────────
    if video_type == 'youtube':
        return {
            'embed_url': None,
            'original_url': url,
            'video_type': 'youtube',
            'video_id': None,
        }

    return {'embed_url': None, 'original_url': url, 'video_type': 'unknown', 'video_id': None}


def get_youtube_embed_url(url):
    """Backward-compatible wrapper — returns just the embed URL string."""
    info = get_video_info(url)
    return info['embed_url']

def is_column_visible(table_name, column_name):
    """Check if a column should be visible in the admin panel"""
    from models import ColumnVisibility
    # Normalize table name to handle legacy plural names
    normalized_table = normalize_table_name(table_name)
    return ColumnVisibility.is_column_visible(normalized_table, column_name)

def get_all_database_tables():
    """Get all tables from the database"""
    from app import db
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    # Filter out internal/system tables
    excluded_tables = ['alembic_version', 'sqlite_sequence']
    tables = [t for t in tables if t not in excluded_tables]
    
    return sorted(tables)

def get_table_columns(table_name):
    """Get all available columns for a table dynamically from the database"""
    from app import db
    from sqlalchemy import inspect
    
    # Manual column mappings for display names (optional, for better readability)
    column_display_names = {
        'id': 'ID',
        'clerk_user_id': 'User ID',
        'course_id': 'Course ID',
        'module_id': 'Module ID',
        'created_at': 'Created At',
        'updated_at': 'Updated At',
        'subscribed_at': 'Subscribed At',
        'granted_at': 'Granted At',
        'expires_at': 'Expires At',
        'is_active': 'Is Active',
        'is_featured': 'Is Featured',
        'is_popular': 'Is Popular',
        'video_url': 'Video URL',
        'thumbnail': 'Thumbnail',
        'view_count': 'View Count',
        'sort_order': 'Sort Order',
        'poll_question': 'Poll Question',
        'poll_options': 'Poll Options',
        'topic_tag': 'Topic Tag',
        'category_tag': 'Category Tag',
        'behind_thought': 'Behind Thought',
        'extra_context': 'Extra Context',
        'password_hash': 'Password Hash',
        'content_key': 'Content Key',
        'content_data': 'Content Data',
        'hidden_columns': 'Hidden Columns',
        'payment_id': 'Payment ID',
        'amount_paid': 'Amount Paid',
        'icon_class': 'Icon Class'
    }
    
    try:
        inspector = inspect(db.engine)
        columns = inspector.get_columns(table_name)
        
        # Convert column names to display names
        display_columns = []
        for col in columns:
            col_name = col['name']
            # Use custom display name if available, otherwise convert snake_case to Title Case
            display_name = column_display_names.get(col_name)
            if not display_name:
                display_name = col_name.replace('_', ' ').title()
            display_columns.append(display_name)
        
        return display_columns
    except Exception as e:
        # Fallback to empty list if table doesn't exist
        return []

def get_column_actual_name(display_name):
    """Convert display name back to actual column name"""
    return display_name.lower().replace(' ', '_')

def get_legacy_table_name_mapping():
    """Map legacy plural table names to actual database table names for backward compatibility"""
    return {
        'subscribers': 'subscriber',
        'reels': 'reel',
        'opinions': 'opinion',
        'courses': 'course',
        'modules': 'module',
        'lessons': 'lesson',
        'enrollments': 'user_course_access',
        'subscription_tiers': 'subscription_tier',
        'social_links': 'social_link'
    }

def normalize_table_name(table_name):
    """Normalize table name to actual database table name (handles legacy names)"""
    legacy_mapping = get_legacy_table_name_mapping()
    return legacy_mapping.get(table_name, table_name)

def send_email_credentials(email, name, login_id, password, login_url=None):
    """Send login credentials to user via email (SMTP). Reads settings from DB."""
    import logging
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    try:
        from models import SiteContent
        import json

        email_content = SiteContent.query.filter_by(content_key='email_settings').first()
        if not email_content:
            logging.info("Email settings not configured — skipping email delivery.")
            return False

        settings = json.loads(email_content.content_data)
        if not settings.get('enabled'):
            logging.info("Email delivery disabled — skipping.")
            return False

        smtp_host = settings.get('smtp_host', '').strip()
        smtp_port = int(settings.get('smtp_port', 587))
        smtp_user = settings.get('smtp_user', '').strip()
        smtp_password = settings.get('smtp_password', '').strip()
        from_email = settings.get('from_email', smtp_user).strip()
        from_name = settings.get('from_name', 'Kshitiz Jaiswal Courses').strip()

        if not smtp_host or not smtp_user or not smtp_password:
            logging.warning("Email SMTP credentials missing.")
            return False

        login_url = login_url or 'https://your-site.com/user/login'
        first_name = (name or 'Student').split()[0]

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#f8fafc;padding:32px 16px;">
          <div style="background:linear-gradient(135deg,#7c3aed,#4f46e5);border-radius:16px 16px 0 0;padding:32px;text-align:center;">
            <div style="font-size:48px;margin-bottom:12px;">🎓</div>
            <h1 style="color:#fff;margin:0;font-size:24px;">Welcome to Your Course!</h1>
            <p style="color:rgba(255,255,255,0.8);margin:8px 0 0;">Kshitiz Jaiswal — Unfiltered Commentator</p>
          </div>
          <div style="background:#fff;border-radius:0 0 16px 16px;padding:32px;box-shadow:0 4px 16px rgba(0,0,0,0.08);">
            <p style="color:#334155;font-size:16px;">Hello <strong>{first_name}</strong>,</p>
            <p style="color:#64748b;">Your account has been created after your course purchase. Use the credentials below to log in:</p>
            <div style="background:#f1f5f9;border-radius:12px;padding:20px;margin:20px 0;">
              <p style="margin:0 0 8px;color:#64748b;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Your Login Details</p>
              <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:8px 0;color:#64748b;width:110px;">Login ID</td><td style="padding:8px 0;color:#1e293b;font-weight:700;">{login_id}</td></tr>
                <tr><td style="padding:8px 0;color:#64748b;">Password</td><td style="padding:8px 0;color:#1e293b;font-weight:700;">{password}</td></tr>
              </table>
            </div>
            <div style="text-align:center;margin:24px 0;">
              <a href="{login_url}" style="background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff;text-decoration:none;padding:14px 32px;border-radius:10px;font-weight:700;font-size:16px;display:inline-block;">
                👉 Login to Your Dashboard
              </a>
            </div>
            <p style="color:#94a3b8;font-size:13px;text-align:center;">You can change your password after logging in for the first time.</p>
            <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0;">
            <p style="color:#94a3b8;font-size:12px;text-align:center;">
              Kshitiz Jaiswal | Unfiltered Commentator<br>
              <a href="{login_url}" style="color:#7c3aed;">{login_url}</a>
            </p>
          </div>
        </div>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎓 Your Course Login Credentials — Kshitiz Jaiswal"
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [email], msg.as_string())

        logging.info(f"Email credentials sent to {email}")
        return True

    except Exception as e:
        logging.error(f"send_email_credentials error: {e}")
        return False


def send_whatsapp_credentials(phone, name, login_id, password, login_url=None):
    """Send login credentials to user via WhatsApp (Meta Cloud API)."""
    import logging
    import requests as req_lib
    try:
        from models import SiteContent
        import json

        wa_content = SiteContent.query.filter_by(content_key='whatsapp_settings').first()
        if not wa_content:
            logging.info("WhatsApp not configured — skipping credential delivery.")
            return False

        settings = json.loads(wa_content.content_data)
        if not settings.get('enabled'):
            logging.info("WhatsApp disabled in settings — skipping.")
            return False

        phone_number_id = settings.get('phone_number_id', '').strip()
        access_token = settings.get('access_token', '').strip()

        if not phone_number_id or not access_token:
            logging.warning("WhatsApp phone_number_id or access_token missing.")
            return False

        clean_phone = re.sub(r'[^0-9]', '', phone or '')
        if len(clean_phone) == 10:
            clean_phone = '91' + clean_phone
        if not clean_phone:
            logging.warning("No valid phone number to send WhatsApp.")
            return False

        login_url = login_url or 'https://your-site.com/user/login'
        first_name = (name or 'Student').split()[0]

        message = (
            f"🎓 *Welcome to Kshitiz Jaiswal's Courses!*\n\n"
            f"Hello {first_name},\n\n"
            f"Your account has been created successfully after your purchase.\n\n"
            f"📧 *Login ID:* {login_id}\n"
            f"🔑 *Password:* {password}\n\n"
            f"👉 *Login here:* {login_url}\n\n"
            f"_You can change your password after logging in._\n\n"
            f"*Kshitiz Jaiswal — Unfiltered Commentator* 🎙️"
        )

        url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "text",
            "text": {"body": message, "preview_url": False},
        }

        resp = req_lib.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            logging.info(f"WhatsApp credentials sent to {clean_phone}")
            return True
        else:
            logging.warning(f"WhatsApp API returned {resp.status_code}: {resp.text}")
            return False

    except Exception as e:
        logging.error(f"send_whatsapp_credentials error: {e}")
        return False


def get_readable_table_name(table_name):
    """Convert table name to readable format"""
    # Handle special cases
    special_names = {
        'user_course_access': 'Course Enrollments',
        'site_content': 'Site Content',
        'column_visibility': 'Column Visibility Settings',
        'subscription_tier': 'Subscription Tiers',
        'social_link': 'Social Links'
    }
    
    if table_name in special_names:
        return special_names[table_name]
    
    # Default conversion: replace underscores with spaces and title case
    return table_name.replace('_', ' ').title()
