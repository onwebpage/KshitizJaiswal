import os
import secrets
import re
import unicodedata
from PIL import Image
from flask import current_app
from werkzeug.utils import secure_filename

def save_uploaded_file(form_file, folder_name):
    """
    Upload an image file and return a URL/path, or None on failure.

    - When Cloudinary is configured, uploads the image there and returns
      the full https:// Cloudinary URL.
    - Falls back to local disk storage (static/uploads/<folder_name>/)
      and returns a relative path when Cloudinary is not configured.
    """
    import logging
    if not form_file or not form_file.filename:
        return None

    _, file_ext = os.path.splitext(form_file.filename)
    file_ext = file_ext.lower()
    is_image = file_ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp')

    # ── Cloudinary path (images only) ────────────────────────────────────────
    if is_image:
        try:
            from cloudinary_utils import upload_image_to_cloudinary, _is_configured
            if _is_configured():
                url = upload_image_to_cloudinary(form_file, folder_name)
                if url:
                    return url
                logging.warning("Cloudinary upload returned None — falling back to local storage.")
        except Exception as exc:
            logging.error(f"Cloudinary upload exception ({folder_name}): {exc} — falling back to local storage.")

    # ── Local disk fallback ───────────────────────────────────────────────────
    random_hex = secrets.token_hex(8)
    folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_name)
    os.makedirs(folder_path, exist_ok=True)

    save_ext = '.jpg' if is_image else file_ext
    filename = random_hex + save_ext
    file_path = os.path.join(folder_path, filename)

    if is_image:
        try:
            form_file.seek(0)
            img = Image.open(form_file)
            # Convert any mode (RGBA, P, LA, …) → RGB so JPEG save never fails
            if img.mode not in ('RGB', 'L'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode in ('RGBA', 'LA'):
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img.convert('RGB'))
                img = bg
            # Resize to max 1920×1920 while keeping aspect ratio
            img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
            img.save(file_path, 'JPEG', optimize=True, quality=85)
        except Exception as exc:
            logging.error(f"save_uploaded_file PIL error ({folder_name}): {exc}")
            try:
                form_file.seek(0)
                form_file.save(file_path)
            except Exception as exc2:
                logging.error(f"save_uploaded_file fallback save also failed: {exc2}")
                return None
    else:
        try:
            form_file.save(file_path)
        except Exception as exc:
            logging.error(f"save_uploaded_file non-image save failed: {exc}")
            return None

    return f"uploads/{folder_name}/{filename}"

def save_video_file(form_file, folder_name, max_duration=15):
    """
    Save an uploaded video, validate duration via ffprobe,
    and extract a thumbnail via ffmpeg.
    Returns (video_rel_path, thumbnail_rel_path, error_msg).
    On error, error_msg is non-empty and paths are None.
    """
    import subprocess, tempfile
    allowed_ext = {'.mp4', '.mov', '.webm'}
    if not form_file or not form_file.filename:
        return None, None, 'No file provided.'
    _, file_ext = os.path.splitext(form_file.filename)
    if file_ext.lower() not in allowed_ext:
        return None, None, f'Only MP4, MOV, and WebM are allowed (got {file_ext}).'

    random_hex = secrets.token_hex(8)
    filename = random_hex + file_ext.lower()
    folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_name)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, filename)
    form_file.save(file_path)

    # Validate duration with ffprobe
    try:
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            capture_output=True, text=True, timeout=15
        )
        duration = float(probe.stdout.strip())
        if duration > max_duration:
            os.remove(file_path)
            return None, None, f'Video is {duration:.1f}s — maximum is {max_duration}s.'
    except Exception:
        pass  # if ffprobe fails, allow the upload

    # Extract thumbnail at 0.5s
    thumb_filename = random_hex + '_thumb.jpg'
    thumb_path = os.path.join(folder_path, thumb_filename)
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-ss', '0.5', '-i', file_path,
             '-vframes', '1', '-q:v', '2', thumb_path],
            capture_output=True, timeout=20
        )
    except Exception:
        thumb_path = None

    video_rel = f'uploads/{folder_name}/{filename}'
    thumb_rel = f'uploads/{folder_name}/{thumb_filename}' if thumb_path and os.path.exists(thumb_path) else None
    return video_rel, thumb_rel, None


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

def _get_resend_from():
    """Return (from_email, from_name) for Resend, checking DB then env vars."""
    import json, os
    from_email = ''
    from_name  = 'Kshitiz Jaiswal Courses'
    try:
        from models import SiteContent
        email_content = SiteContent.query.filter_by(content_key='email_settings').first()
        if email_content:
            settings = json.loads(email_content.content_data)
            from_email = settings.get('from_email', '').strip()
            from_name  = settings.get('from_name', from_name).strip() or from_name
    except Exception:
        pass
    if not from_email:
        from_email = os.environ.get('SMTP_FROM_EMAIL', '').strip()
    if not from_name:
        from_name = os.environ.get('SMTP_FROM_NAME', 'Kshitiz Jaiswal Courses').strip()
    return from_email, from_name


def _send_via_resend(to_email, subject, html_body, plain_body, from_email, from_name):
    """Send an email via Resend API. Returns True on success, False on failure."""
    import logging, os
    try:
        import resend
    except ImportError:
        logging.error("resend package not installed — cannot send email.")
        return False
    api_key = os.environ.get('RESEND_API_KEY', '').strip()
    if not api_key:
        logging.warning("RESEND_API_KEY not set — skipping email delivery.")
        return False
    if not from_email:
        logging.warning("From email not configured — skipping email delivery.")
        return False
    resend.api_key = api_key
    try:
        import httpx
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{from_name} <{from_email}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_body,
                    "text": plain_body,
                },
            )
            resp.raise_for_status()
        logging.info(f"Resend: email sent to {to_email} — {subject}")
        return True
    except Exception as e:
        logging.error(f"Resend send error: {e}")
        return False


def send_email_credentials(email, name, login_id, password, login_url=None):
    """Send login credentials to user via Resend."""
    import logging
    login_url  = login_url or 'https://your-site.com/user/login'
    first_name = (name or 'Student').split()[0]
    from_email, from_name = _get_resend_from()

    plain_body = f"""Hello {first_name},

Your account has been created for Kshitiz Jaiswal Courses.

Here are your login details:

  Login ID : {login_id}
  Password : {password}

Login here: {login_url}

You can change your password after logging in.

-- 
Kshitiz Jaiswal | Unfiltered Commentator
{login_url}
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:24px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;max-width:560px;width:100%;">
      <tr>
        <td style="background:#1e1b4b;padding:28px 32px;text-align:center;">
          <p style="margin:0;color:#c7d2fe;font-size:13px;letter-spacing:1px;text-transform:uppercase;">Kshitiz Jaiswal Courses</p>
          <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;">Your Account is Ready</h1>
        </td>
      </tr>
      <tr>
        <td style="padding:32px;">
          <p style="margin:0 0 16px;color:#1e293b;font-size:16px;">Hello <strong>{first_name}</strong>,</p>
          <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.6;">
            Your account has been created. Use the details below to log in and access your course.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:24px;">
            <tr>
              <td style="padding:14px 20px;border-bottom:1px solid #e2e8f0;">
                <span style="color:#64748b;font-size:13px;display:block;margin-bottom:3px;">Login ID</span>
                <strong style="color:#1e293b;font-size:15px;">{login_id}</strong>
              </td>
            </tr>
            <tr>
              <td style="padding:14px 20px;">
                <span style="color:#64748b;font-size:13px;display:block;margin-bottom:3px;">Password</span>
                <strong style="color:#1e293b;font-size:15px;font-family:monospace;">{password}</strong>
              </td>
            </tr>
          </table>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td align="center" style="padding-bottom:24px;">
                <a href="{login_url}" style="display:inline-block;background:#4f46e5;color:#ffffff;text-decoration:none;padding:14px 36px;border-radius:6px;font-weight:600;font-size:15px;">
                  Log In to Your Course
                </a>
              </td>
            </tr>
          </table>
          <p style="margin:0;color:#94a3b8;font-size:13px;text-align:center;">
            You can change your password any time after logging in.
          </p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8fafc;padding:18px 32px;border-top:1px solid #e2e8f0;text-align:center;">
          <p style="margin:0;color:#94a3b8;font-size:12px;">
            Kshitiz Jaiswal | Unfiltered Commentator<br>
            <a href="{login_url}" style="color:#6366f1;text-decoration:none;">{login_url}</a>
          </p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""

    return _send_via_resend(email, "Your login details for Kshitiz Jaiswal Courses",
                            html_body, plain_body, from_email, from_name)


def send_course_purchase_confirmation(email, name, course_title, amount_paid, my_courses_url=None, login_url=None):
    """Send a purchase confirmation email after every successful course payment via Resend."""
    import logging
    from_email, from_name = _get_resend_from()
    my_courses_url = my_courses_url or login_url or 'https://your-site.com/my-courses'
    login_url      = login_url or 'https://your-site.com/user/login'
    first_name     = (name or 'Student').split()[0]
    amount_str     = f"₹{int(amount_paid):,}" if amount_paid else ''

    plain_body = f"""Hello {first_name},

Thank you for purchasing "{course_title}"!

{('Amount Paid: ' + amount_str + chr(10)) if amount_str else ''}Your course is now active and ready to access.

Access your course here: {my_courses_url}

-- 
Kshitiz Jaiswal | Unfiltered Commentator
{login_url}
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:24px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;max-width:560px;width:100%;">
      <tr>
        <td style="background:#7f1d1d;padding:28px 32px;text-align:center;">
          <p style="margin:0;color:#fca5a5;font-size:13px;letter-spacing:1px;text-transform:uppercase;">Payment Confirmed</p>
          <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;">Thank You for Your Purchase!</h1>
        </td>
      </tr>
      <tr>
        <td style="padding:32px;">
          <p style="margin:0 0 16px;color:#1e293b;font-size:16px;">Hello <strong>{first_name}</strong>,</p>
          <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.6;">
            Your payment was successful. You now have full access to:
          </p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;margin-bottom:24px;">
            <tr>
              <td style="padding:18px 20px;">
                <span style="color:#7f1d1d;font-size:13px;display:block;margin-bottom:4px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;">Course</span>
                <strong style="color:#1e293b;font-size:17px;">{course_title}</strong>
                {f'<br><span style="color:#dc2626;font-size:14px;margin-top:6px;display:block;">Amount Paid: {amount_str}</span>' if amount_str else ''}
              </td>
            </tr>
          </table>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td align="center" style="padding-bottom:24px;">
                <a href="{my_courses_url}" style="display:inline-block;background:#dc2626;color:#ffffff;text-decoration:none;padding:14px 36px;border-radius:6px;font-weight:600;font-size:15px;">
                  Go to My Courses
                </a>
              </td>
            </tr>
          </table>
          <p style="margin:0;color:#94a3b8;font-size:13px;text-align:center;">
            If you have any questions, reply to this email.
          </p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8fafc;padding:18px 32px;border-top:1px solid #e2e8f0;text-align:center;">
          <p style="margin:0;color:#94a3b8;font-size:12px;">
            Kshitiz Jaiswal | Unfiltered Commentator<br>
            <a href="{login_url}" style="color:#dc2626;text-decoration:none;">{login_url}</a>
          </p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""

    return _send_via_resend(email, f"Purchase Confirmed: {course_title}",
                            html_body, plain_body, from_email, from_name)


def send_subscription_welcome_email(email, name):
    """Send a thank you / welcome email to a new newsletter subscriber."""
    import logging
    from_email, from_name = _get_resend_from()

    plain_body = f"""Hi {name},

Thank you for subscribing to Kshitiz Jaiswal's newsletter!

You're now part of the Inner Circle — you'll get unfiltered commentary and exclusive updates straight to your inbox.

Stay tuned. Sach aaega! 🎙️

– Kshitiz Jaiswal
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
      <tr>
        <td style="background:#9b1c1c;padding:30px;text-align:center;">
          <h1 style="color:#ffffff;margin:0;font-size:24px;letter-spacing:1px;">🎙️ Kshitiz Jaiswal</h1>
          <p style="color:#fca5a5;margin:6px 0 0;font-size:14px;">Unfiltered Commentator</p>
        </td>
      </tr>
      <tr>
        <td style="padding:36px 40px;">
          <h2 style="color:#1e293b;margin:0 0 12px;">Welcome to the Inner Circle, {name}! 🙌</h2>
          <p style="color:#475569;font-size:15px;line-height:1.7;margin:0 0 16px;">
            Thank you for subscribing. You're now part of a community that believes in unfiltered truth and real commentary.
          </p>
          <p style="color:#475569;font-size:15px;line-height:1.7;margin:0 0 24px;">
            Expect exclusive updates, behind-the-reel insights, and commentary that you won't find anywhere else — straight to your inbox.
          </p>
          <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:16px 20px;border-radius:4px;margin-bottom:28px;">
            <p style="color:#9b1c1c;font-style:italic;margin:0;font-size:15px;">"Reel to sirf ek hissa tha, kahani bahut badi hai."</p>
          </div>
          <p style="color:#64748b;font-size:14px;margin:0;">– Kshitiz Jaiswal</p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8fafc;padding:20px 40px;text-align:center;border-top:1px solid #e2e8f0;">
          <p style="color:#94a3b8;font-size:12px;margin:0;">You received this email because you subscribed at kshitizjaiswal.in</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""

    return _send_via_resend(email, "Welcome to the Inner Circle! 🎙️", html_body, plain_body, from_email, from_name)


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


def normalize_phone_digits(phone):
    """Strip a phone value to E.164 digits (defaults 10-digit Indian numbers to 91 prefix)."""
    digits = re.sub(r'[^0-9]', '', phone or '')
    if len(digits) == 10:
        digits = '91' + digits
    return digits


def _normalize_whatsapp_link(link):
    """Convert any WhatsApp URL to a mobile-compatible https://wa.me/ universal deep link.

    wa.me links open the WhatsApp app directly on Android/iOS and fall back to
    WhatsApp Web on desktop — unlike api.whatsapp.com/send which causes
    'Couldn't Open Link' errors on many mobile browsers.
    """
    link = (link or '').strip()
    if not link:
        return ''

    if link.startswith('http://'):
        link = 'https://' + link[7:]

    lower = link.lower()

    # whatsapp:// deep-link scheme → convert to wa.me
    if lower.startswith('whatsapp://'):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(link.replace('whatsapp://', 'https://', 1))
        qs = parse_qs(parsed.query)
        phone = normalize_phone_digits((qs.get('phone') or [''])[0])
        text = (qs.get('text') or [''])[0]
        if phone:
            base = f'https://wa.me/{phone}'
            return f'{base}?text={text}' if text else base
        return link

    # Group invite links — pass through unchanged
    if 'chat.whatsapp.com' in lower:
        return link

    # /message/ business links → keep as wa.me/message/CODE (universal)
    msg_match = re.match(r'https?://(?:wa\.me|api\.whatsapp\.com)/message/([A-Za-z0-9]+)', link, re.I)
    if msg_match:
        return f'https://wa.me/message/{msg_match.group(1)}'

    # wa.me phone link — normalise digits and rebuild cleanly
    phone_match = re.match(r'https?://wa\.me/(\+?\d[\d\s\-]*)(\?.*)?$', link, re.I)
    if phone_match:
        digits = normalize_phone_digits(phone_match.group(1))
        suffix = phone_match.group(2) or ''
        if digits:
            return f'https://wa.me/{digits}{suffix}'

    # api.whatsapp.com/send?phone= or web.whatsapp.com/send?phone= → wa.me
    send_match = re.search(r'[?&]phone=(\d+)', link, re.I)
    if send_match:
        digits = send_match.group(1)
        text_match = re.search(r'[?&]text=([^&]*)', link, re.I)
        base = f'https://wa.me/{digits}'
        return f'{base}?text={text_match.group(1)}' if text_match else base

    # Already a clean wa.me link
    if lower.startswith('https://wa.me/'):
        return link

    return link


def _whatsapp_web_fallback(primary_url, phone_digits=''):
    """Build an explicit web.whatsapp.com URL for desktop browsers.

    On desktop the JS handler opens this fallback in a new tab so users
    without the desktop app can still reach WhatsApp Web.
    """
    # Business message links work the same everywhere
    if 'wa.me/message/' in primary_url.lower() or 'api.whatsapp.com/message/' in primary_url.lower():
        return primary_url

    # Extract phone from wa.me/PHONE or ?phone=PHONE
    wame_match = re.match(r'https?://wa\.me/(\d+)', primary_url, re.I)
    if wame_match:
        return f'https://web.whatsapp.com/send?phone={wame_match.group(1)}'

    phone_match = re.search(r'[?&]phone=(\d+)', primary_url)
    if phone_match:
        return f'https://web.whatsapp.com/send?phone={phone_match.group(1)}'

    if phone_digits:
        return f'https://web.whatsapp.com/send?phone={phone_digits}'

    return primary_url


def build_whatsapp_urls(custom_link='', support_phone=''):
    """Return normalized WhatsApp chat URLs for mobile (wa.me) and desktop fallback."""
    custom_link = (custom_link or '').strip()
    phone_digits = normalize_phone_digits(support_phone)

    url = ''
    if custom_link:
        url = _normalize_whatsapp_link(custom_link)
    elif phone_digits:
        url = f'https://wa.me/{phone_digits}'

    web_url = _whatsapp_web_fallback(url, phone_digits) if url else ''
    return {'url': url, 'web_url': web_url, 'phone_digits': phone_digits}


_DEFAULT_WA_MESSAGE_CODE = 'TYMT7KS4JVF7F1'


def load_whatsapp_settings():
    """Load WhatsApp support settings from DB with mobile-safe URL normalization."""
    default_url = f'https://wa.me/message/{_DEFAULT_WA_MESSAGE_CODE}'
    result = {
        'support_phone': '',
        'phone_digits': '',
        'whatsapp_link': default_url,
        'whatsapp_web_link': default_url,
    }
    try:
        from models import SiteContent
        import json

        wa_rec = SiteContent.query.filter_by(content_key='whatsapp_settings').first()
        if wa_rec:
            wa_data = json.loads(wa_rec.content_data)
            raw_phone = wa_data.get('support_phone', '')
            raw_link = wa_data.get('whatsapp_link', '').strip()
            result['support_phone'] = raw_phone
            urls = build_whatsapp_urls(raw_link, raw_phone)
            if urls['url']:
                result['whatsapp_link'] = urls['url']
                result['whatsapp_web_link'] = urls['web_url']
                result['phone_digits'] = urls['phone_digits']
    except Exception:
        pass
    return result
