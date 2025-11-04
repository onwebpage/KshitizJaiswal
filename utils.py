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

def get_youtube_embed_url(url):
    """Convert YouTube or Instagram URL to embeddable format with security parameters"""
    if not url:
        return None
    
    import re
    
    # Check if it's an Instagram URL
    instagram_pattern = r'(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel)/([a-zA-Z0-9_-]+)'
    instagram_match = re.search(instagram_pattern, url)
    if instagram_match:
        reel_id = instagram_match.group(1)
        return f"https://www.instagram.com/reel/{reel_id}/embed"
    
    # Handle different YouTube URL formats
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # Add parameters for better embedding
            # controls=1: Show player controls for playback
            # rel=0: Don't show related videos from other channels
            # modestbranding=1: Use modest YouTube branding
            # iv_load_policy=3: Disable video annotations
            # playsinline=1: Play inline without full-screen on mobile
            return f"https://www.youtube.com/embed/{video_id}?controls=1&rel=0&modestbranding=1&iv_load_policy=3&playsinline=1"
    
    return None

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
