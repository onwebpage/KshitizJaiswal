---
name: Tracking scripts conditional loading
description: GTM, Clarity, and Meta Pixel must only load when real IDs are configured
---

## Problem
The base.html had hardcoded placeholder IDs (`GTM-XXXXXXX`, `YOUR_CLARITY_ID`, `YOUR_PIXEL_ID`). These caused 400 Bad Request errors on every page load.

## Fix
All three tracking scripts in `base.html` are now conditional Jinja2 blocks that only render if `site_settings` contains a real (non-placeholder) ID.

- GTM uses key: `google_analytics_id` (matches admin form field)
- Meta Pixel uses key: `facebook_pixel_id`
- Clarity uses key: `clarity_id` (added as new field)

**Why:** Blank/placeholder tracking IDs fire real HTTP requests to analytics servers which return 400. They must be gated.

**How to apply:** Admin can configure these at `/admin/site-settings`. The `site_settings` dict is injected via the context processor in `routes.py`.
