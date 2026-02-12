# ChargeGhar Social Authentication Setup Guide

## 🎯 Overview

Your Django PowerBank project now supports **Google and Apple login** alongside the existing OTP-based authentication system. This guide will help you configure OAuth providers for production deployment.

## 🚀 Quick Setup Checklist

- [ ] Configure Google OAuth credentials
- [ ] Configure Apple OAuth credentials  
- [ ] Update production environment variables
- [ ] Test authentication endpoints
- [ ] Deploy to production

## 📋 Step 1: Google OAuth Setup

### 1.1 Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing "ChargeGhar" project
3. Enable required APIs:
   - Google+ API
   - Google OAuth2 API
   - Google Identity API

### 1.2 Create OAuth 2.0 Credentials
1. Navigate to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth 2.0 Client IDs**
3. Configure the OAuth consent screen first if prompted
4. Select **Application type**: **Web application**
5. Set **Name**: `ChargeGhar Web Client`
6. Add **Authorized redirect URIs**:
   ```
   Development: http://localhost:8010/accounts/google/login/callback/
   Production:  https://main.chargeghar.com/accounts/google/login/callback/
   ```
   
   **Important**: These are the exact URLs that django-allauth uses. Do NOT use custom callback URLs.
7. Click **CREATE**
8. Copy the **Client ID** and **Client Secret**

### 1.3 Update Environment Variables
Add to your `.env` file:
```bash
GOOGLE_OAUTH_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-your_actual_client_secret_here
```

## 🍎 Step 2: Apple OAuth Setup

### 2.1 Create App ID
1. Go to [Apple Developer Console](https://developer.apple.com/account/)
2. Navigate to **Certificates, Identifiers & Profiles**
3. Click **Identifiers** → **+** (Add new)
4. Select **App IDs** → **Continue**
5. Select **App** → **Continue**
6. Configure:
   - **Bundle ID**: `com.chargeghar.app`
   - **Description**: `ChargeGhar PowerBank App`
   - Enable **Sign In with Apple**
7. Click **Continue** → **Register**

### 2.2 Create Service ID
1. In **Identifiers**, click **+** → **Services IDs** → **Continue**
2. Configure:
   - **Identifier**: `com.chargeghar.app.service`
   - **Description**: `ChargeGhar Web Service`
3. Enable **Sign In with Apple**
4. Click **Configure** next to Sign In with Apple
5. Select your App ID as **Primary App ID**
6. Add **Website URLs**:
   - **Domains**: `main.chargeghar.com`, `localhost:8010`
   - **Return URLs**: 
     - `https://main.chargeghar.com/accounts/apple/login/callback/`
     - `http://localhost:8010/accounts/apple/login/callback/`
7. Click **Save** → **Continue** → **Register**

### 2.3 Create Private Key
1. Navigate to **Keys** → **+** (Add new)
2. Configure:
   - **Key Name**: `ChargeGhar Sign In Key`
   - Enable **Sign In with Apple**
   - Click **Configure** → Select your App ID
3. Click **Save** → **Continue** → **Register**
4. **Download the .p8 file** (you can only download once!)
5. Note the **Key ID** (10-character string)

### 2.4 Get Team ID
1. In Apple Developer Console, your **Team ID** is displayed in the top-right corner
2. It's a 10-character alphanumeric string

### 2.5 Convert Private Key to Base64
```bash
# Convert the downloaded .p8 file to base64
base64 -i AuthKey_XXXXXXXXXX.p8 | tr -d '\n'
```

### 2.6 Update Environment Variables
Add to your `.env` file:
```bash
APPLE_OAUTH_CLIENT_ID=com.inflancer.chargeghar.service
APPLE_OAUTH_TEAM_ID=YOUR_TEAM_ID
APPLE_OAUTH_KEY_ID=YOUR_KEY_ID
APPLE_OAUTH_PRIVATE_KEY_BASE64=your_base64_encoded_private_key_here
# Optional backward-compatibility fallback
APPLE_OAUTH_CLIENT_SECRET=YOUR_KEY_ID
```

## 🔧 Step 3: Production Environment Configuration

### 3.1 Complete Environment Variables
Ensure your `.env` file has all required variables:
```bash
# Domain Configuration
HOST=main.chargeghar.com
ALLOWED_HOSTS=main.chargeghar.com,127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=https://main.chargeghar.com,http://main.chargeghar.com
CSRF_TRUSTED_ORIGINS=https://main.chargeghar.com,http://main.chargeghar.com

# Social Auth URLs
SOCIAL_AUTH_LOGIN_REDIRECT_URL=/api/auth/social/success
SOCIAL_AUTH_LOGIN_ERROR_URL=/api/auth/social/error
FRONTEND_URL=https://chargeghar.app

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret

# Apple OAuth
APPLE_OAUTH_CLIENT_ID=com.inflancer.chargeghar.service
APPLE_OAUTH_TEAM_ID=your_team_id
APPLE_OAUTH_KEY_ID=your_key_id
APPLE_OAUTH_PRIVATE_KEY_PATH=apple_auth_key.p8
APPLE_OAUTH_PRIVATE_KEY_BASE64=your_base64_encoded_private_key
# Optional backward-compatibility fallback
APPLE_OAUTH_CLIENT_SECRET=your_key_id
```

### 3.2 Deploy to Production
```bash
# Run the deployment script
sudo ./deploy-production.sh

# The script will automatically:
# - Configure production environment
# - Update domain settings
# - Add social auth variables if missing
# - Warn about placeholder values
```

## 🧪 Step 4: Testing

### 4.1 Test API Endpoints
```bash
# Test Google OAuth URL generation
curl https://main.chargeghar.com/api/auth/google/login

# Expected response:
{
  "success": true,
  "data": {
    "login_url": "https://main.chargeghar.com/accounts/google/login/",
    "provider": "google"
  }
}

# Test Apple OAuth URL generation
curl https://main.chargeghar.com/api/auth/apple/login

# Expected response:
{
  "success": true,
  "data": {
    "login_url": "https://main.chargeghar.com/accounts/apple/login/",
    "provider": "apple"
  }
}
```

### 4.2 Test OAuth Flow
1. **Google Test**:
   - Visit: `https://main.chargeghar.com/accounts/google/login/`
   - Complete Google OAuth
   - Should redirect to: `https://main.chargeghar.com/api/auth/social/success`
   - Should receive JWT tokens

2. **Apple Test**:
   - Visit: `https://main.chargeghar.com/accounts/apple/login/`
   - Complete Apple OAuth
   - Should redirect to: `https://main.chargeghar.com/api/auth/social/success`
   - Should receive JWT tokens

## 📱 Step 5: Mobile App Integration

### 5.1 Google Sign-In (React Native)
```javascript
// Backend uses redirect-based OAuth (NOT /api/auth/google/verify)
const startGoogleLogin = async () => {
  const res = await fetch('https://main.chargeghar.com/api/auth/google/login');
  const payload = await res.json();
  const loginUrl = payload.data.login_url;

  // Open loginUrl in in-app browser/webview.
  // Final redirect lands on:
  // https://chargeghar.app/social/login-status?status=success&token=...&refresh=...
};
```

### 5.2 Apple Sign-In (React Native)
```javascript
// Backend uses redirect-based OAuth (NOT /api/auth/apple/verify)
const startAppleLogin = async () => {
  const res = await fetch('https://main.chargeghar.com/api/auth/apple/login');
  const payload = await res.json();
  const loginUrl = payload.data.login_url;

  // Open loginUrl in in-app browser/webview.
  // Final redirect lands on:
  // https://chargeghar.app/social/login-status?status=success&token=...&refresh=...
};
```

## 🔄 How It Works

### Authentication Flow:
```
1. Mobile App → GET /api/auth/google/login → OAuth URL returned
2. User → Google/Apple OAuth → Callback to django-allauth
3. CustomAdapter → Creates/Links User → Triggers Welcome Task
4. Django-allauth → Redirects to Success → JWT Tokens Generated
5. Mobile App → Receives JWT Tokens → Can Access All APIs
```

### Available Endpoints:
- **Google Login**: `GET /api/auth/google/login`
- **Apple Login**: `GET /api/auth/apple/login`
- **Success Handler**: `GET /api/auth/social/success`
- **Error Handler**: `GET /api/auth/social/error`

### OAuth Callback URLs:
- **Google**: `https://main.chargeghar.com/accounts/google/login/callback/`
- **Apple Return URL (register in Apple Developer)**: `https://main.chargeghar.com/accounts/apple/login/callback/`
- **Apple Internal Finish URL (do NOT register in Apple Developer)**: `https://main.chargeghar.com/accounts/apple/login/callback/finish/`

## 🚨 Troubleshooting

### Common Issues:

1. **"Invalid redirect URI" Error**:
   - Verify redirect URIs in OAuth provider configuration
   - Ensure URLs match exactly (including trailing slashes)
   - Check HTTPS vs HTTP

2. **"Invalid client ID" Error**:
   - Verify environment variables are set correctly
   - Check for typos in client IDs
   - Ensure OAuth app is enabled

3. **"User creation fails"**:
   - Check database constraints
   - Verify required fields are provided
   - Review adapter implementation logs

4. **"Token validation fails"**:
   - Ensure proper token format
   - Check token expiration
   - Verify provider-specific validation

### Debug Commands:
```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs -f api

# Check environment variables
docker-compose -f docker-compose.prod.yml exec api env | grep OAUTH

# Test database connection
docker-compose -f docker-compose.prod.yml exec api python manage.py shell
```

## ✅ Production Checklist

- [ ] Google OAuth credentials configured
- [ ] Apple OAuth credentials configured
- [ ] Environment variables updated
- [ ] OAuth redirect URIs match production domain
- [ ] HTTPS enabled for production
- [ ] Social auth endpoints tested
- [ ] Mobile app integration tested
- [ ] Error handling verified
- [ ] Monitoring and logging enabled

## 🎉 Success!

Your ChargeGhar PowerBank system now supports:
- 📱 **OTP Authentication** (Email/Phone) - Existing
- 🔍 **Google OAuth** - New
- 🍎 **Apple OAuth** - New

All methods generate the same JWT tokens and provide identical API access! 🚀
