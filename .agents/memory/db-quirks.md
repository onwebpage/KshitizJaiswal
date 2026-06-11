---
name: DB quirks & migrations
description: Known DB column size issues and how migrations are applied at startup
---

## session_id column overflow
- `UserActivity.session_id` was `VARCHAR(100)` but Flask session cookies are JWT-like and can be 114+ chars.
- Fixed to `db.Column(db.Text)` in models.py.
- Migration added to app.py migrations list: `ALTER TABLE user_activity ALTER COLUMN session_id TYPE TEXT`

**Why:** Flask cookies encode CSRF token + session data as a signed string, routinely exceeding 100 chars.

**How to apply:** Migrations run at app startup in `app.py` in the `migrations` list. Always add `ALTER TABLE ... TYPE TEXT` migrations for any column that stores user-generated strings of unknown length.
