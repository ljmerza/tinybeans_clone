# Google Cloud Console Setup Guide

This guide walks through setting up Google OAuth 2.0 credentials for the Tinybeans application.

## Prerequisites

- A Google account
- Access to [Google Cloud Console](https://console.cloud.google.com/)
- Admin access to configure OAuth settings

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown in the top navigation bar
3. Click "New Project"
4. Enter project details:
   - **Project name**: `tinybeans-dev` (for development) or `tinybeans-prod` (for production)
   - **Organization**: Leave as "No organization" unless you have one
5. Click "Create"
6. Wait for project creation (takes ~30 seconds)

## Step 2: Enable Required APIs

1. In the left sidebar, go to **APIs & Services** → **Library**
2. Search for and enable these APIs:
   - **Google+ API** (required for OAuth)
   - **Google OAuth2 API** (required for authentication)
3. Click "Enable" for each API

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type (unless you have a Google Workspace)
3. Click "Create"

### App Information
- **App name**: `Tinybeans` (or your app name)
- **User support email**: Your email address
- **App logo**: (Optional) Upload your app logo
- **Application home page**: `https://tinybeans.app` (or your domain)
- **Application privacy policy**: `https://tinybeans.app/privacy`
- **Application terms of service**: `https://tinybeans.app/terms`

### Developer Contact Information
- **Email addresses**: Your developer email

4. Click "Save and Continue"

### Scopes
5. On the Scopes page, click "Add or Remove Scopes"
6. Select these scopes:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
7. Click "Update" then "Save and Continue"

### Test Users (Development Only)
8. Add test users for development:
   - Click "Add Users"
   - Enter email addresses of developers who will test OAuth
   - Click "Add"
9. Click "Save and Continue"

### Summary
10. Review the consent screen configuration
11. Click "Back to Dashboard"

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click "Create Credentials" → "OAuth client ID"
3. Select **Application type**: "Web application"
4. Configure the OAuth client:

### For Development
- **Name**: `Tinybeans Web Client - Development`
- **Authorized JavaScript origins**:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- **Authorized redirect URIs**:
  - `http://localhost:3000/auth/google/callback`

### For Staging
- **Name**: `Tinybeans Web Client - Staging`
- **Authorized JavaScript origins**:
  - `https://staging.tinybeans.app`
- **Authorized redirect URIs**:
  - `https://staging.tinybeans.app/auth/google/callback`

### For Production
- **Name**: `Tinybeans Web Client - Production`
- **Authorized JavaScript origins**:
  - `https://tinybeans.app`
- **Authorized redirect URIs**:
  - `https://tinybeans.app/auth/google/callback`

5. Click "Create"

## Step 5: Save OAuth Credentials

After creating the OAuth client, a modal will appear with your credentials:

1. **Copy the Client ID**: Looks like `123456789-abcdefg.apps.googleusercontent.com`
2. **Copy the Client Secret**: Looks like `GOCSPX-abcdefghijklmnop`
3. Click "OK"

⚠️ **IMPORTANT**: Store these credentials securely! You'll need them for your application.

## Step 6: Configure Application Environment

### Development (.env file)
```bash
GOOGLE_OAUTH_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-abcdefghijklmnop
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

### Production (Environment Variables)
Set these as environment variables in your production environment:
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`

⚠️ **Never commit secrets to Git!** Add `.env` to your `.gitignore`.

## Step 7: Test OAuth Configuration

1. Start your Django backend:
   ```bash
   python manage.py runserver
   ```

2. Start your React frontend:
   ```bash
   cd web
   npm run dev
   ```

3. Try the OAuth flow:
   - Navigate to the login page
   - Click "Sign in with Google"
   - You should be redirected to Google's OAuth consent screen
   - After granting permissions, you should be redirected back to your app

## Troubleshooting

### Error: "redirect_uri_mismatch"
- Ensure the redirect URI in your app exactly matches the one configured in Google Cloud Console
- Check for trailing slashes, HTTP vs HTTPS, port numbers
- Update the authorized redirect URIs in Google Cloud Console if needed

### Error: "access_denied"
- The user denied the OAuth consent
- Check if user is added to test users list (if app is in testing mode)
- Review the scopes requested match what's configured

### Error: "invalid_client"
- Check that `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` are correct
- Verify environment variables are loaded properly
- Ensure you're using the correct credentials for the environment (dev/staging/prod)

### Error: "unauthorized_client"
- The OAuth client is not authorized for this grant type
- Ensure "Web application" was selected as the application type
- Verify authorized redirect URIs are configured

## Security Best Practices

1. **Separate Credentials**: Use different OAuth clients for dev, staging, and production
2. **Secret Management**: Store secrets in environment variables or a secrets manager
3. **HTTPS in Production**: Always use HTTPS for production OAuth redirect URIs
4. **Rotate Secrets**: Regularly rotate OAuth client secrets
5. **Monitor Usage**: Check Google Cloud Console for unusual OAuth activity
6. **Limit Scopes**: Only request the minimum scopes needed for your app

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [OAuth 2.0 Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [Google API Console](https://console.cloud.google.com/)
- [OAuth Playground](https://developers.google.com/oauthplayground/) - Test OAuth flows

## Support

If you encounter issues not covered in this guide:
1. Check the [Google OAuth documentation](https://developers.google.com/identity/protocols/oauth2/web-server)
2. Review application logs for detailed error messages
3. Contact the development team

---

**Last Updated**: 2025-01-12
**Document Version**: 1.0
