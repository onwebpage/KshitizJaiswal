---
name: Thumbnail fallback pattern
description: How to handle broken/missing thumbnail images across all templates
---

## Pattern
All `<img>` tags for user-uploaded or external thumbnails use an `onerror` handler:
```html
onerror="this.onerror=null;this.src='{{ url_for('static', filename='img/reel-placeholder.svg') }}'"
```

## Placeholder files
- `static/img/reel-placeholder.svg` — dark background with play icon, "No Preview Available"
- `static/img/resource-placeholder.svg` — light background with document icon, "No Image Available"

## Where applied
- `templates/reels_library.html` — reel grid cards
- `templates/reel_detail.html` — main video placeholder and related reels sidebar
- `templates/resources.html` — resource cards

**Why:** Seed/dev data uses Pixabay URLs which get rate-limited (429). External image hosts can go down. Fallback SVGs prevent broken image icons.

**How to apply:** Always add onerror to any img tag that uses a dynamic URL (either uploaded path or external URL from DB).
