# Project Memory — Kshitiz Jaiswal Portfolio Platform

- [Tracking scripts conditional loading](tracking-scripts.md) — GTM/Clarity/Meta Pixel must only load when IDs are configured via admin; placeholder IDs caused 400 errors on every page load.
- [UserActivity session_id overflow](db-quirks.md) — Flask session cookies exceed 100 chars; session_id must be TEXT not VARCHAR(100).
- [site_settings context processor](template-context.md) — site_settings must be injected via context processor to be available in base.html for tracking scripts and other global settings.
- [Support payment verification](payment-flows.md) — Support/donation payments need server-side Razorpay signature verification at /support/payment/verify (course payments already had this, support did not).
- [Thumbnail fallback pattern](thumbnail-fallback.md) — All img tags for user-uploaded/external thumbnails need onerror fallback to static/img/reel-placeholder.svg or resource-placeholder.svg.
- [Admin new features pattern](admin-new-features.md) — SEO, Testimonials, Announcement, Account Settings — each backed by SiteConfig/SiteContent; context processor injects announcement+seo_config globally; no Jinja2 md5 filter (use Python hash instead).
- [Admin panel CSRF pattern](admin-csrf.md) — All admin POST forms use {{ csrf_token() }} (not form.hidden_tag()). Templates that display data tables with action forms (revoke, cancel, delete) must include <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"> in each form.
- [Admin base template rule](admin-base-rule.md) — All admin pages must extend admin/admin_base.html and use {% block admin_content %}. Pages extending base.html with inline sidebars are broken (no full nav, inconsistent layout).
- [Cloudinary image integration](cloudinary-integration.md) — All user-uploaded images go to Cloudinary; videos stay local. Template pattern and edit-handler guard required.
