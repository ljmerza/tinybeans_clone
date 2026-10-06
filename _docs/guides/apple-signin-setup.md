# Sign in with Apple setup

The Apple button is hidden until the server has Apple credentials.
`GET /api/auth/providers/` reports `apple: true` only once every variable below is
set, so the code can ship before the Apple Developer account exists.

## How the flow works

Apple requires `response_mode=form_post` when it shares the user's name or
email, so it POSTs the result to the API, not to the SPA:

1. The SPA calls `POST /api/auth/apple/initiate/` and the browser goes to Apple.
2. Apple POSTs `code`, `state` and, on the first sign-in only, the user's name to
   `POST /api/auth/apple/return/` (`APPLE_OAUTH_REDIRECT_URI`). The API stores
   the name on the state row and 303s the browser to
   `<origin>/auth/apple-callback#code=…&state=…`.
3. The callback page sends `code`/`state` to `POST /api/auth/apple/callback/`,
   which exchanges the code with a client secret JWT signed with the `.p8`
   key, verifies Apple's ID token and logs in, links or creates the user.

Apple only accepts HTTPS return URLs on a real domain, so a full round trip
does not work against `localhost`. Test on the production host, or on a dev
host that has a public HTTPS name.

## Apple Developer account

Apple's console labels change over time; the steps below may be worded
differently there.

You need a paid Apple Developer Program membership. In
**Certificates, Identifiers & Profiles**:

1. **App ID**: create one (or reuse one) with the *Sign in with Apple*
   capability enabled.
2. **Services ID**: create one, for example `com.lmerza.circles.web`. This is the
   `client_id`. Enable *Sign in with Apple*, choose the App ID as primary, then add:
   - Domain: `circles.lmerza.com`
   - Return URL: `https://circles.lmerza.com/api/auth/apple/return/`
3. **Key**: create a key with *Sign in with Apple* enabled and download the
   `.p8` file. Apple lets you download it only once. Note the 10-character Key ID.
4. Note the 10-character **Team ID** shown in the account's membership details.

## Environment

```
APPLE_OAUTH_CLIENT_ID=com.lmerza.circles.web          # Services ID
APPLE_OAUTH_TEAM_ID=ABCDE12345
APPLE_OAUTH_KEY_ID=FGHIJ67890
APPLE_OAUTH_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIGT...\n-----END PRIVATE KEY-----"
APPLE_OAUTH_REDIRECT_URI=https://circles.lmerza.com/api/auth/apple/return/
APPLE_OAUTH_ALLOWED_RETURN_URIS=https://circles.lmerza.com/auth/apple-callback
```

- `APPLE_OAUTH_PRIVATE_KEY` holds the contents of the `.p8` file. Literal `\n`
  sequences are converted to newlines, so it fits on one env line.
- `APPLE_OAUTH_ALLOWED_RETURN_URIS` is comma-separated, one entry per origin the SPA
  is served from. When `DEBUG` is on and the variable is unset, it defaults to the
  localhost dev origins.
- The client secret is minted for each request and expires after 5 minutes, so
  nothing needs rotating. The `.p8` key itself does not expire. Revoke it in the
  Apple console if it leaks.

Restart the web container after setting these. The button appears on the
login and signup pages within about 30 minutes, because that is how long the
SPA caches the providers response.

## Hide My Email (private relay)

Users may share an `@privaterelay.appleid.com` address, which then becomes
their account email. Apple forwards mail to these addresses only from sending
domains and addresses registered under **Services → Sign in with Apple for
Email Communication**. Register the domain Circles sends from (with SPF/DKIM
passing), or these users will not receive digests, invites or password resets.

## Account rules

These follow the Google rules (ADR-010):

- A known Apple ID logs in.
- An unknown Apple ID whose email matches a verified account links to it. A
  match on an unverified account is blocked.
- Otherwise a new passwordless account is created (`auth_provider="apple"`).
- Linking from a signed-in session (`POST /api/auth/apple/link/`) does not
  require the Apple email to match the account email, because relay addresses
  never match.
- Unlinking (`DELETE /api/auth/apple/unlink/`) requires the account password.
