---
name: Payment flows — Razorpay
description: How course vs support payments are handled and verified
---

## Course payments
- Initiate: `POST /course/<id>/purchase` — creates Razorpay order
- Verify: `POST /course/payment/verify` — verifies signature, creates UserCourseAccess

## Support/donation payments
- Initiate: `POST /create_payment` — creates Razorpay order
- Verify: `POST /support/payment/verify` — added during QA; verifies signature, logs to UserActivity

**Why:** Originally support payments had no server-side verification — only a frontend success toast. This allowed spoofing. Server-side HMAC signature verification via `razorpay_client.utility.verify_payment_signature` is mandatory.

**How to apply:** Any new Razorpay payment type needs a matching `/*/payment/verify` endpoint. Both course and support use the same Razorpay client (falls back to env vars if admin hasn't set keys in payment_settings).
