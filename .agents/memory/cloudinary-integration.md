---
name: Cloudinary image integration
description: How images are uploaded and served — Cloudinary for all user-uploaded images, local disk fallback.
---

# Cloudinary Image Integration

## Rule
All user-uploaded images go to Cloudinary. Videos stay on local disk. Never use Cloudinary for non-image assets.

**Why:** User explicitly requested Cloudinary for images only.

## How it works
- `cloudinary_utils.py` — `upload_image_to_cloudinary(file_obj, folder)` handles PIL conversion/resize then uploads; returns `secure_url` or `None`.
- `utils.py` — `save_uploaded_file()` tries Cloudinary first (if env vars set), falls back to `static/uploads/<folder>/` on any failure.
- Cloudinary URLs are full `https://res.cloudinary.com/...` strings; local paths are relative `uploads/<folder>/<file>.jpg`.

## Template pattern
All `<img src>` and `style="background-image:url(...)"` for user-uploaded images must use:
```
X if X.startswith('http') else url_for('static', filename=X)
```
This is already applied everywhere. Never add a raw `url_for('static', filename=user_image_field)` without the http check.

## Edit-handler guard
When overwriting an image field on edit, always guard against None:
```python
obj.thumbnail = save_uploaded_file(...) or obj.thumbnail
```
Prevents accidental field-clearing if Cloudinary upload fails transiently.

## Cloudinary folder structure
Images are uploaded to `kshitiz/<folder_name>` (e.g. `kshitiz/reels`, `kshitiz/hero`, `kshitiz/courses`).

## Credentials
Read from env vars: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`. Never hardcoded.
