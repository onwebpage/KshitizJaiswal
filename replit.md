# Kshitiz Jaiswal Portfolio Platform

A Flask-based personal portfolio and content platform for Kshitiz Jaiswal — journalist/anchor. Features include reels, opinion polls, courses with Razorpay payments, subscriber management, Cloudinary image uploads, Clerk authentication, and an admin panel.

## Stack
- **Backend**: Python / Flask + SQLAlchemy
- **Database**: PostgreSQL (prod via DATABASE_URL) with SQLite fallback for dev
- **Auth**: Clerk (frontend) + custom admin login
- **Payments**: Razorpay
- **Media**: Cloudinary (images), local storage (videos)
- **Email**: Resend

## Run
```
python -m gunicorn --bind 0.0.0.0:5000 --reuse-port --reload --timeout 120 main:app
```

## Key files
- `app.py` — Flask app factory, DB config, context processors
- `routes.py` — All route handlers (~280KB)
- `models.py` — SQLAlchemy models
- `forms.py` — WTForms
- `utils.py` — Helpers (email, Cloudinary, etc.)
- `main.py` — Entry point

## Required secrets
| Secret | Purpose |
|---|---|
| `SESSION_SECRET` | Flask session signing |
| `DATABASE_URL` | PostgreSQL connection string |
| `CLERK_PUBLISHABLE_KEY` | Clerk frontend auth |
| `CLERK_SECRET_KEY` | Clerk backend verification |
| `CLOUDINARY_CLOUD_NAME` | Image hosting |
| `CLOUDINARY_API_KEY` | Cloudinary uploads |
| `CLOUDINARY_API_SECRET` | Cloudinary uploads |
| `RAZORPAY_KEY_ID` | Payments |
| `RAZORPAY_KEY_SECRET` | Payment verification |
| `RESEND_API_KEY` | Transactional email |
| `SMTP_USER` | SMTP email (fallback) |
| `SMTP_PASSWORD` | SMTP email (fallback) |

## Notes
- The `DATABASE_URL` currently points to a Railway PostgreSQL host. If that host is unreachable, the app automatically falls back to SQLite (development only). Update `DATABASE_URL` to a Replit PostgreSQL or other accessible host for persistent production data.
- Admin panel at `/admin`
- All admin POST forms use CSRF tokens via `{{ csrf_token() }}`

## User preferences
