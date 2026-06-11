# Project Memory — Kshitiz Jaiswal Portfolio Platform

- [Tracking scripts conditional loading](tracking-scripts.md) — GTM/Clarity/Meta Pixel must only load when IDs are configured via admin; placeholder IDs caused 400 errors on every page load.
- [UserActivity session_id overflow](db-quirks.md) — Flask session cookies exceed 100 chars; session_id must be TEXT not VARCHAR(100).
- [site_settings context processor](template-context.md) — site_settings must be injected via context processor to be available in base.html for tracking scripts and other global settings.
- [Support payment verification](payment-flows.md) — Support/donation payments need server-side Razorpay signature verification at /support/payment/verify (course payments already had this, support did not).
- [Thumbnail fallback pattern](thumbnail-fallback.md) — All img tags for user-uploaded/external thumbnails need onerror fallback to static/img/reel-placeholder.svg or resource-placeholder.svg.
