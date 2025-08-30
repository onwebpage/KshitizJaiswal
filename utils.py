import os
import secrets
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
