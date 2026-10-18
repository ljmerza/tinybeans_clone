# Agent API and per-circle API tokens

Circle admins can create **API tokens** that let an agent (an MCP client such as `circles-mcp`,
Claude Code or a local Ollama setup) read one circle and, if allowed, propose posts for its
Milestones album. Tokens work only on `/api/agent/v1/`. Every other endpoint rejects them.

Code: `mysite/agent_api/`. Tests: `mysite/agent_api/tests/`. Design:
`_docs/features/ai-integration/plan.md` §3.

## Turning it on

| Setting | Default | Meaning |
| --- | --- | --- |
| `AGENT_API_ENABLED` | off | Kill switch. While it is off, every `/api/agent/v1/` request gets 404 before authentication runs, so it costs no database queries. Admins can still list, create and revoke tokens; the list reports `agent_api_enabled: false`. |
| `AGENT_API_READ_RATE` | `1200/hour` | Per-token limit on all agent requests |
| `AGENT_API_SUGGEST_RATE` | `200/day` | Per-token limit on milestone suggestions (counted on top of the read limit) |
| `AGENT_API_MAX_TOKENS_PER_CIRCLE` | `10` | Most active (not revoked, not expired) tokens per circle |
| `MILESTONE_MAX_PENDING` | `200` | Shared with the in-app AI. With review on, new suggestions are refused once a circle has this many pending. |

The settings are read on every request, so a restart is enough after changing env. The throttles
read these settings directly rather than `DEFAULT_THROTTLE_RATES`, because `local.py` empties that
dict.

**Network exposure.** The decision (2026-10-18) is LAN-only. This is enforced in the host nginx on
the TCP peer address, not in Django, because Django can't see a trustworthy client IP behind
Cloudflare and Docker. The nginx change is not in this repo; see plan §3.9.

## Tokens

- **Format.** `circ_` plus 43 url-safe characters (256 random bits), 48 characters in all. Clients
  can check it against `^circ_[A-Za-z0-9_-]{43}$`.
- **Storage.** Only `sha256(token)` is stored, with no key. The display prefix is the first
  12 characters (`circ_` + 7). The plaintext appears once, in the create response, and nowhere else:
  not in the list, logs, emails or Django admin.
- **Scope.** One circle. Tokens are read-only, plus `can_suggest`, which allows the one write
  (proposing a milestone). Name, `can_suggest` and expiry are fixed when the token is created.
- **Expiry.** Optional. If set, it must be at least an hour away. The admin UI defaults to 90 days.
- **Status.** Revoked, expired or active, in that order of priority.

### Who can manage them (JWT, real circle admins only)

All three endpoints need a signed-in user who is a `CIRCLE_ADMIN` of the circle. Superusers get no
bypass and act through Django admin only.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/users/circles/<circle_id>/api-tokens/` | `{agent_api_enabled, tokens: [{id, name, display_prefix, can_suggest, status, created_by: {id, display_name}, created_at, expires_at, last_used_at, last_used_ip, revoked_at, revoked_reason}]}`, newest first, revoked and expired tokens included |
| POST | same | `{name (1-100), can_suggest, expires_at: null \| ISO, code}` → `201 {token, plaintext}` with `Cache-Control: no-store` |
| DELETE | `/api/users/circles/<circle_id>/api-tokens/<token_id>/` | 204. Any admin can revoke any of the circle's tokens. Revoking twice is a no-op. No re-auth needed. |

**Creating** a token checks these in order:

1. Rate limits: 5 per 15 minutes per user and 20 per 15 minutes per IP (429).
2. That the user is an admin (403).
3. The fields (400).
4. The token cap (400, `errors.api_token_limit`).
5. The re-auth code (400, `errors.reauth_invalid_code` on field `code`).

The code comes from `POST /api/auth/reauth/code/`, which emails a one-time code to the account
address. Authenticator and SMS codes are never accepted. The fields and the cap are checked
before the code, so a typo doesn't use up the code. Once the token is committed, every admin of
the circle gets an "API token created" email (template `api_token.created`). The email never
includes the token.

### Automatic revocation

Each request re-checks the token's creator. If the creator is inactive, has an unverified email
(when `EMAIL_VERIFICATION_ENFORCED` is on) or is no longer a `CIRCLE_ADMIN` of the circle, the token
is revoked for good (`revoked_reason` = `creator_inactive`, `creator_unverified` or
`creator_not_admin`). Promoting the creator again doesn't bring the token back. Tokens are also
revoked:

- When a membership save demotes the creator (`creator_not_admin`) or a delete removes them from
  the circle (`creator_removed`). Deleting the whole circle deletes its tokens instead.
- When the creator changes or resets their password (`password_changed`), in every circle.
- By hand (`manual`), from the app or with Django admin's "Revoke selected API tokens" action.

The membership signals are only a backstop: queryset `.update()` skips them. The per-request check
is the one that counts.

## The agent API (`/api/agent/v1/`)

**Auth.** Send `Authorization: Bearer circ_…`; the scheme is case-insensitive. Tokens in the query
string are ignored. These all get the same 401, with `WWW-Authenticate: Bearer realm="circles-agent"`
and the body `{"detail": "Invalid, expired or revoked API token."}`:

- no token
- a JWT
- an unknown, malformed, revoked or expired token
- a token whose creator fails the check above

**The circle comes only from the token.** No endpoint takes a circle id. Posts, children and
suggestions from any other circle are 404s. Responses are plain JSON with `Cache-Control: no-store`.
They never contain URLs, media ids, storage keys, filenames, emails, user ids, author names or
birthdates.

**Untrusted text.** Everything family-written (titles, captions, tags, media captions, comments)
sits under an `untrusted` key. It may contain instructions aimed at the model reading it, so
clients must treat it as data. Before it is sent:

- Control characters (other than newline and tab), bidi marks and overrides, and invisible
  characters (zero-width spaces and joiners, BOM, variation selectors, the Unicode tag block)
  are stripped.
- Lengths are capped: title 300, caption 2000, media caption 300, comment 300, tag 100.
  `truncated: true` says a cap was applied.

People and child names (`people[].name`, `children[].name`), the circle name and the token name
sit outside `untrusted` but are family-written too. They get the same stripping, and their
lengths are bounded (150 characters for people and child names). Clients should treat the whole
response as data, not just the `untrusted` key.

### `GET whoami/`

```json
{"circle": {"name": "Example Family"},
 "token": {"name": "Laptop", "prefix": "circ_AbCdEfG", "expires_at": null, "can_suggest": true},
 "children": [{"id": "uuid", "name": "Sophia", "age_today": {"years": 1, "months": 4, "days": 26}}],
 "milestones_album": {"exists": true, "post_count": 43},
 "counts": {"posts": 1234, "pending_suggestions": 0},
 "server_date": "2026-10-18"}
```

`age_today` is null when the birthdate isn't set. Raw birthdates are never returned. Counts only
include posts the feed would show.

### `GET posts/`

Lists posts the feed would show: text posts, and posts with a photo or a processed video.

| Param | Meaning |
| --- | --- |
| `from`, `to` | `YYYY-MM-DD`, inclusive UTC days. Errors are keyed by the parameter name. |
| `q` | Up to 200 characters and up to 10 comma-separated terms, OR-ed together. Each term is matched case-insensitively against the title, caption, tags and media captions. |
| `child` | A child id from `whoami`. Another circle's child (or an unknown id) is a 404. |
| `milestone` | `any` (default), `unreviewed` (not in the album, and never suggested or only judged `not_milestone` by the in-app AI), `in_album`, or `pending` (waiting for review, not in the album) |
| `order` | `oldest` (default) or `newest` |
| `page_size` | 1-50, default 25. Larger values are capped at 50. |
| `cursor` | The `next_cursor` from the previous page. An invalid cursor is a 400. |

The response is `{"posts": [...], "next_cursor": "…" | null}`. Each post looks like this:

```json
{"id": "uuid", "date": "2025-03-14",
 "people": [{"name": "Sophia", "kind": "child", "age_at_post": {"years": 1, "months": 4, "days": 26}}],
 "media": {"photos": 2, "videos": 0}, "comment_count": 3,
 "mentions_birthday": false, "in_milestones_album": false, "suggestion_status": null,
 "untrusted": {"title": "…", "caption": "…", "tags": ["walking"], "media_captions": ["…"]},
 "truncated": false}
```

- `kind` is `child`, `member`, `pet` or `other`. `age_at_post` is null unless the person is a child
  with a birthdate.
- `suggestion_status` is the post's milestone suggestion row, if it has one: `pending`, `approved`,
  `dismissed`, `not_milestone` or `auto_added`.
- `mentions_birthday` uses the same check that makes suggestions refuse birthday posts.

### `GET posts/<id>/`

Returns the same item, plus `untrusted.comments`: `[{date, text}]`. These are the latest
10 comments, oldest first, with no authors. Every `@Name` or `@email` of a circle member, or of
anyone who wrote or is mentioned in those comments (former members too), is replaced with
`@member`.

### `POST milestone-suggestions/`

Needs a token created with `can_suggest` (otherwise 403). Body: `{post_id, label (1-80),
reason (1-500)}`. The label and reason are untrusted text. They are shown to admins as plain
text and stored with the token's display prefix.

| Case | Status | Body |
| --- | --- | --- |
| Suggested now | 201 | `{"status": "pending" \| "auto_added", "created": true}` |
| Already has a row | 200 | `{"status": <its status>, "created": false}` (dismissed and approved rows are never reopened) |
| Already in the Milestones album | 200 | `{"status": "in_album", "created": false}` |
| Birthday post (any kind, "1 month birthday" included) | 422 | `{"code": "birthday"}` |
| Pending cap reached (review on) | 429 | `{"code": "pending_cap"}` |
| Post not in the circle, or hidden | 404 | |

With the circle's "review AI picks first" setting off (the default), a suggestion goes into the
Milestones album at once (`auto_added`). With it on, the suggestion waits for an admin (`pending`).
A token's suggestion can overrule the in-app AI's `not_milestone`. See `mysite/albums/milestones.py`.

### Throttling

Requests are throttled per token, not per IP. Every request counts against
`AGENT_API_READ_RATE`. Suggestions also count against `AGENT_API_SUGGEST_RATE`. A throttled request
gets 429 with `Retry-After`. Failed authentication isn't throttled here, because guessing a 256-bit
token isn't feasible. The host nginx limits each IP.

## Logs and audit events

| Event | Logger | Notes |
| --- | --- | --- |
| `api_token.create`, `api_token.revoke` | `mysite.audit` | circle id and prefix |
| `api_token.auto_revoke` | `mysite.audit` (security) | reason, circle id, prefix |
| `api_token.auth_failed` | `mysite.audit` (security) | reason, prefix, IP, path; never the token |
| `agent_api.access` | `mysite.agent_api` (INFO) | token id, circle id, view, status, one line per authenticated request |

`mysite.audit` doesn't propagate, so log-assertion tests must set `propagate = True` for the
test (see `mysite/agent_api/tests/helpers.py::captured_logs`).

## Django admin

**Agent API → Circle api tokens** is a read-only list (no add, change or delete, and the hash is
never shown). Its "Revoke selected API tokens" action is for emergencies.

## Code map

| File | What |
| --- | --- |
| `models.py` | `CircleApiToken`, `RevokeReason`, derived `status` |
| `tokens.py` | Generating, hashing and checking the token format |
| `authentication.py` | `CircleApiTokenAuthentication`, used only by the agent views |
| `principal.py` | `ApiTokenPrincipal`, the `request.user` for token requests; its `pk` and `id` raise so user-scoped code fails closed |
| `permissions.py`, `throttling.py` | `IsApiToken`, `CanSuggest`; per-token throttles |
| `services.py` | Create (cap, notice email), revoke, automatic revoke |
| `signals.py` | Membership demotion and removal |
| `queries.py`, `hygiene.py`, `pagination.py` | Post queryset and shapes, text cleaning and `@member` masking, cursor pagination |
| `views/base.py` | `AgentAPIView`: kill switch, identical 401s, `no-store`, access log |
| `views/agent.py`, `views/manage.py` | Agent endpoints; token management |

`tests/test_default_deny.py` walks the URL resolver and fails if any view outside the four agent
views lists `CircleApiTokenAuthentication`.
