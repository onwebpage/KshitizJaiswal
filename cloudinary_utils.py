"""
Cloudinary image upload helper.
Used exclusively for image storage — videos stay on local disk.
"""
import os
import logging
import io
from PIL import Image

def _is_configured():
    """Return True only if all three Cloudinary env vars are set."""
    return all([
        os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip(),
        os.environ.get('CLOUDINARY_API_KEY', '').strip(),
        os.environ.get('CLOUDINARY_API_SECRET', '').strip(),
    ])

def _get_cloudinary():
    """Import and configure the cloudinary module, or raise if not available."""
    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError:
        raise RuntimeError("cloudinary package is not installed.")

    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip(),
        api_key=os.environ.get('CLOUDINARY_API_KEY', '').strip(),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET', '').strip(),
        secure=True,
    )
    return cloudinary


def upload_image_to_cloudinary(file_obj, folder):
    """
    Upload an image file-like object to Cloudinary.

    - Converts the image to RGB JPEG (max 1920×1920) before uploading,
      matching the same processing that save_uploaded_file applies locally.
    - Returns the secure Cloudinary URL string on success, or None on failure.
    - Only for images — do NOT pass videos here.

    Args:
        file_obj: werkzeug FileStorage or any seekable file-like object.
        folder:   Cloudinary folder name (e.g. 'reels', 'hero', 'courses').
    """
    if not _is_configured():
        logging.warning("Cloudinary not configured — skipping cloud upload.")
        return None

    try:
        cld = _get_cloudinary()
    except RuntimeError as e:
        logging.error(f"Cloudinary import error: {e}")
        return None

    try:
        file_obj.seek(0)
        img = Image.open(file_obj)

        # Convert any mode → RGB so JPEG encoding never fails
        if img.mode not in ('RGB', 'L'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode in ('RGBA', 'LA'):
                bg.paste(img, mask=img.split()[-1])
            else:
                bg.paste(img.convert('RGB'))
            img = bg

        # Resize to max 1920×1920 keeping aspect ratio
        img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)

        # Encode to JPEG bytes in memory
        buf = io.BytesIO()
        img.save(buf, format='JPEG', optimize=True, quality=85)
        buf.seek(0)

        result = cld.uploader.upload(
            buf,
            folder=f"kshitiz/{folder}",
            resource_type="image",
        )

        url = result.get('secure_url')
        if url:
            logging.info(f"Cloudinary upload OK → {url}")
        else:
            logging.error(f"Cloudinary upload returned no secure_url: {result}")
        return url

    except Exception as exc:
        logging.error(f"Cloudinary upload error ({folder}): {exc}")
        return None
