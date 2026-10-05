# Notification Channels: Email, SMS and Web Push

## Overview
- **Goal:** Let each person pick any mix of email, text message (SMS) and web push for circle activity notifications (new photos, comments, replies, likes), instead of one channel.
- **Scope:** Data model + migration from the single `channel` choice to three on/off switches, a verified phone number for SMS, push subscriptions per device, senders for every enabled channel, the profile notifications UI, and tests.
- **Out of scope:** The daily `email_digest` (stays email-only and unchanged), localized SMS/push text (emails are English-only today, so these match), quiet hours, batching several events into one text, native apps, reusing the 2FA phone (see below), and push for anything other than activity notifications.

## Current State (Baseline)
- `UserNotificationPreferences` has one `channel` field (`email` | `sms`) per row. The global row has `circle=None`; per-circle rows override it.
- `keeps/notifications.py::_deliver` looks up `CHANNEL_SENDERS[prefs.channel]` and calls one sender. `_send_sms` only logs.
- The preferences serializer rejects `channel=sms` unless `NOTIFICATIONS_SMS_ENABLED` is on.
- `mysite/messaging` has the SMS provider abstraction (console/Twilio) and the `send_sms_async` Celery task on the `sms` queue.
- The web app is installable (manifest + iOS tags in `index.html`) but has **no service worker**.

## Data Model
- `UserNotificationPreferences`: replace `channel` with `email_enabled` (default on), `sms_enabled` (default off) and `push_enabled` (default off). They live on every row, so a circle override can pick its own channels, exactly like the event flags. `enabled_channels()` returns the channels that are on.
- `NotificationChannel` stays as the list of channel names (`email`, `sms`, `push`), used as the sender keys.
- New `NotificationPhone` (one per user): `phone_number` (E.164), `verified_at`, and the pending code (`code_hash`, `code_expires_at`, `code_attempts`).
- New `PushSubscription` (one per browser/device): `user`, `endpoint` (unique), `p256dh`, `auth`, `user_agent`, `created_at`, `last_used_at`.

### Migration
One `users` migration:
1. Add the three switches.
2. Data step: `channel=email` → email on; `channel=sms` → SMS on, email off. Reverse: SMS on → `channel=sms`, else `email`.
3. Remove `channel`.
4. Create `NotificationPhone` and `PushSubscription`.

Rows that picked SMS keep SMS on, but nothing is texted until that person verifies a phone number. That matches today: SMS was never delivered.

## Phone Number Source and Verification
**Decision: a separate, notification-only phone with its own code check. Don't reuse the 2FA phone.**

- The 2FA phone (`TwoFactorSettings.phone_number` + `sms_verified`) only gets verified through 2FA setup, and finishing that setup turns 2FA on (`TwoFactorVerifySetupView` sets `is_enabled=True`). Reusing it would force everyone who wants texts (grandparents included) to turn on SMS two-factor login. It would also tie notifications to a security setting: removing SMS 2FA wipes the number.
- The new flow is small and reuses the existing messaging service:
  - `POST /api/users/me/notification-phone/ {phone_number}` saves the number as unverified and texts a 6-digit code through `send_sms_async`. The code is stored hashed (HMAC) and expires after 10 minutes.
  - `POST /api/users/me/notification-phone/verify/ {code}` checks it in constant time. After 5 wrong tries the code is dead.
  - `DELETE /api/users/me/notification-phone/` removes the number and turns `sms_enabled` off on every row.
  - Changing the number clears `verified_at`, so texts stop until the new number is verified.
- SMS goes **only** to a number with `verified_at` set. The sender checks this on every send, not just when the switch is turned on.
- Turning `sms_enabled` on is rejected unless SMS is enabled server-side and the user has a verified number.

## SMS Delivery
- `_send_sms` texts `Circles: <one-line summary> <post link>`, for example `Circles: Pat added 2 new photos to Smith Family https://…/keeps/<id>`. The summary is the event's email subject line, so any new event that has an email template gets SMS and push text for free. Comment text is never included, which keeps texts short (one segment where possible) and private.
- Sent through `send_sms_async` (queue `sms`) on the configured provider. Dev and tests use the console provider.

### Cost and Abuse Guards
- `NOTIFICATIONS_SMS_ENABLED` (default off) gates everything: the switch, the phone endpoints and the sender.
- Only verified numbers get texts. Starting verification requires a verified email (same permission as the preferences API).
- Verification codes are rate-limited per user (`NOTIFICATION_PHONE_CODE_RATELIMIT`, default `3/15m`), and a code dies after 5 wrong tries.
- `NOTIFICATIONS_SMS_ALLOWED_PREFIXES` (default `+1`) limits which countries numbers can be in. This blocks SMS-pumping/toll-fraud to premium international ranges. Set it to an empty value to allow every country.
- `NOTIFICATIONS_SMS_DAILY_LIMIT` (default 20) caps activity texts per user per day. Anything over the cap is dropped and logged.
- Event switches apply to every channel on that row. There is no per-channel event matrix (for example "likes by push only"); that's out of scope.

## Web Push Design
- **Keys:** VAPID keys come from env: `VAPID_PUBLIC_KEY` (base64url, uncompressed P-256 point, which the browser uses as `applicationServerKey`), `VAPID_PRIVATE_KEY` (base64url raw 32-byte key, or DER), and `VAPID_SUBJECT` (`mailto:you@example.com` or an `https:` URL). Push is **off** unless all three are set (`NOTIFICATIONS_PUSH_ENABLED` is derived from them).
- **Library:** `pywebpush`, imported lazily inside the push sender. An image built before this change doesn't have it, so a missing import is logged and skipped instead of crashing the task.
- **Subscriptions:** `POST /api/users/me/push-subscriptions/` takes the browser's `PushSubscription.toJSON()` (`endpoint`, `keys.p256dh`, `keys.auth`) and upserts by endpoint. If someone else logs in on the same browser, the subscription moves to them. `DELETE` with `{endpoint}` removes it. Endpoints must be `https` on a known push service host (`PUSH_ALLOWED_ENDPOINT_HOSTS`: FCM, Mozilla, Apple, Windows). Without this, the server would POST to any URL a user supplied (SSRF).
- **Sending:** `_send_push` queues `send_push_async(user_id, payload)` on the `email` queue, next to `send_activity_notifications` (no new queue, so no worker or metrics changes). That task sends to each of the user's subscriptions with a 10-second timeout and a 12-hour TTL. The payload is JSON: `{title, body, url, tag}`. The title is the one-line summary, the body is the comment text or post summary, and the tag (the post URL) collapses repeat notices about the same post.
- **Cleanup:** a `404` or `410` from the push service means the subscription is gone, so the row is deleted. Other errors are logged and the row is kept.
- **Service worker:** `web/public/sw.js` (scope `/`) handles only `push` (show the notification) and `notificationclick` (focus an open tab or open the post URL, same-origin only). There's no fetch/caching handler, so it can't serve stale app code. It's registered only when someone enables push, not on every page load. The manifest and install tags are unchanged.
- **Status:** `GET /api/users/me/notification-channels/` returns `{sms_available, phone_number, phone_verified, phone_verification_pending, push_available, vapid_public_key, push_device_count}` for the UI.

### iOS and Browser Limitations
- On iPhone/iPad, web push works only for the app **added to the home screen**, on **iOS/iPadOS 16.4 or newer**. In Safari tabs `PushManager` isn't available. The UI detects this (`navigator.standalone` / `display-mode: standalone`) and asks the person to add Circles to the home screen first. I'm reasonably confident of the 16.4 cut-off and the home-screen requirement. I haven't verified on a device how reliably iOS delivers in the background, or whether it caps notifications from apps that are rarely opened.
- Push needs a secure context: HTTPS, or `localhost` in dev. Opening the dev server by LAN IP over plain HTTP shows "This browser can't receive push notifications."
- If permission is denied, the browser won't ask again. The UI explains how to re-allow it in browser/site settings.

## API Summary
| Method | Path | Purpose |
| --- | --- | --- |
| GET/PATCH/DELETE | `/api/users/me/email-preferences/[?circle_id=]` | Existing. Now returns/accepts `email_enabled`, `sms_enabled`, `push_enabled` instead of `channel`. |
| GET | `/api/users/me/notification-channels/` | Channel availability, phone status, VAPID public key, device count. |
| POST / DELETE | `/api/users/me/notification-phone/` | Start verification for a number / remove it. |
| POST | `/api/users/me/notification-phone/verify/` | Confirm the 6-digit code. |
| POST / DELETE | `/api/users/me/push-subscriptions/` | Save / remove this device's push subscription. |

## Frontend Plan
- The profile notifications card replaces the "Send notifications by" dropdown with three switches (Email, Text message, Push). They're per scope, so a circle override can pick different channels.
- **Text message:** shown only when the server says SMS is available. In the default scope, a phone form sends a code, takes the code, and then shows the verified number with a "Remove" option. The SMS switch stays disabled until the number is verified.
- **Push:** shown only when the server says push is available. In the default scope, "Enable push on this device" registers `/sw.js`, asks for permission, subscribes with the VAPID key and posts the subscription. The UI covers four states: unsupported browser, iOS not installed, permission denied, and already on for this device (with "Turn off on this device").
- New strings live in `en`/`es`/`it` locale files.

## Settings and Environment Variables
| Variable | Default | Purpose |
| --- | --- | --- |
| `NOTIFICATIONS_SMS_ENABLED` | off | Existing flag. Turns on the SMS switch, phone verification and SMS sending. |
| `SMS_PROVIDER` | `twilio` | Existing. Use `console` in dev. |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` | empty | Existing Twilio credentials. |
| `NOTIFICATIONS_SMS_DAILY_LIMIT` | `20` | Activity texts per user per day. |
| `NOTIFICATIONS_SMS_ALLOWED_PREFIXES` | `+1` | Comma-separated E.164 prefixes allowed for notification phones. Empty allows all. |
| `NOTIFICATION_PHONE_CODE_RATELIMIT` | `3/15m` | Verification codes a user can request. |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | empty | Web push keys. Push is off unless all three are set. |
| `PUSH_ALLOWED_ENDPOINT_HOSTS` | FCM, Mozilla, Apple, Windows push hosts | Comma-separated host suffixes accepted for subscription endpoints. |

Generate VAPID keys locally (no network) with the `cryptography` package already in the image:

```bash
python -c "import base64; from cryptography.hazmat.primitives import serialization; from cryptography.hazmat.primitives.asymmetric import ec; k = ec.generate_private_key(ec.SECP256R1()); b = lambda x: base64.urlsafe_b64encode(x).rstrip(b'=').decode(); print('VAPID_PRIVATE_KEY=' + b(k.private_numbers().private_value.to_bytes(32, 'big'))); print('VAPID_PUBLIC_KEY=' + b(k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)))"
```

Changing the keys makes every existing subscription stop working. Browsers have to subscribe again.

## Deployment Notes
- The image must be rebuilt for `pywebpush` (added to `pyproject.toml`/`uv.lock`). Until then, push sends are logged and skipped.
- Run the `users` migration.
- `sw.js` is served from `web/dist` by the existing nginx `location /`.

## Tests
- Migration: email → email on; sms → SMS on/email off; reverse mapping.
- Dispatch: every enabled channel gets the event. Per-circle overrides change channels. SMS goes only to verified numbers, only with the flag on, and only under the daily cap.
- Phone verification: send code (console provider), wrong/expired/used codes, country allowlist, rate limit.
- Push: subscribe (upsert, endpoint host allowlist), unsubscribe, sending with `pywebpush` mocked, and deleting the row on 404/410 while keeping it on other errors.
- Frontend (vitest): channel switches, SMS hidden when unavailable, phone flow, push enable plus unsupported/denied states.
