---
name: Template context processor
description: What global variables are injected into all templates
---

The context processor `inject_section_visibility()` in `routes.py` injects:
- `section_vis` — dict of booleans controlling homepage section visibility
- `site_settings` — dict from SiteContent key `site_settings` (JSON), used for tracking IDs, site title, social links, etc.

**Why:** base.html needs `site_settings` for conditional tracking scripts (GTM, Clarity, Pixel). Without this injection, templates would get a NameError or silently skip the conditional blocks.

**How to apply:** Any new global template variable must be added to this context processor. Do not pass it page-by-page.
