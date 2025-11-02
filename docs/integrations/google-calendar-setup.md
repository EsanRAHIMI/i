# Google Calendar Integration Setup Guide

This guide walks you through setting up Google Calendar integration for the AI Assistant system.

## Overview

The Google Calendar integration enables the AI Assistant to:
- Read and write calendar events
- Receive real-time notifications via webhooks
- Provide intelligent scheduling suggestions
- Sync events bidirectionally

## Prerequisites

- Google Cloud Platform account
- Google Calendar API enabled
- OAuth 2.0 credentials configured
- Valid domain for webhook callbacks

## Step 1: Google Cloud Console Setup

### 1.1 Create a New Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `ai-assistant-calendar`
4. Click "Create"

### 1.2 Enable Google Calendar API

1. Navigate to "APIs & Services" → "Library"
2. Search for "Google Calendar API"
3. Click on "Google Calendar API"
4. Click "Enable"

### 1.3 Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Choose "External" user type
3. Fill in required information:
   - **App name**: AI Assistant
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/calendar.events`
5. Add test users (for development)
6. Save and continue

### 1.4 Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Configure:
   - **Name**: AI Assistant Calendar Client
   - **Authorized JavaScript origins**: 
     - `https://aidepartment.net`
     - `http://localhost:3000` (for development)
   - **Authorized redirect URIs**:
     - `https://aidepartment.net/api/v1/calendar/oauth/callback`
     - `http://localhost:8000/api/v1/calendar/oauth/callback` (for development)
5. Click "Create"
6. Download the JSON credentials file

## Step 2: Backend Configuration

### 2.1 Environment Variables

Add the following to your `.env` file:

```bash
# Google Calendar Configuration
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=https://aidepartment.net/api/v1/calendar/oauth/callback

# Webhook Configuration
CALENDAR_WEBHOOK_URL=https://aidepartment.net/api/v1/calendar/webhook
CALENDAR_WEBHOOK_SECRET=your_webhook_secret_here
```

### 2.2 Update Configuration

Update `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Google Calendar Settings
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    CALENDAR_WEBHOOK_URL: str
    CALENDAR_WEBHOOK_SECRET: str
    
    class Config:
        env_file = ".env"
```

### 2.3 Install Dependencies

Ensure you have the Google API client library:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Step 3: OAuth Flow Implementation

### 3.1 Initiate Connection

The OAuth flow starts when a user calls the `/calendar/connect` endpoint:

```bash
curl -X POST "https://your-api.com/api/v1/calendar/connect" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Response:
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
  "state": "csrf_token_123",
  "redirect_uri": "https://aidepartment.net/api/v1/calendar/oauth/callback"
}

```

### 3.2 User Authorization

1. Redirect user to the `authorization_url`
2. User grants calendar permissions
3. Google redirects to your callback URL with authorization code

### 3.3 Complete Connection

The callback endpoint automatically exchanges the code for tokens:

```bash
curl -X POST "https://your-api.com/api/v1/calendar/oauth/callback" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "authorization_code_from_google",
    "state": "csrf_token_123"
  }'
```

## Step 4: Webhook Setup

### 4.1 Domain Verification

1. Go to [Google Search Console](https://search.google.com/search-console)
2. Add and verify your domain
3. This is required for webhook notifications

### 4.2 Configure Webhook Endpoint

The webhook endpoint handles real-time calendar notifications:

```python
@router.post("/webhook")
async def handle_calendar_webhook(
    notification: CalendarWebhookNotification,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Process webhook notification
    # Trigger background sync if needed
    pass
```

### 4.3 Set Up Push Notifications

Call the watch endpoint to enable notifications:

```bash
curl -X POST "https://your-api.com/api/v1/calendar/watch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://aidepartment.net/api/v1/calendar/webhook",
    "expiration_time": "2024-12-31T23:59:59Z"
  }'
```

## Step 5: Testing the Integration

### 5.1 Test OAuth Flow

1. Call `/calendar/connect` endpoint
2. Visit the authorization URL
3. Grant permissions
4. Verify callback processes successfully
5. Check that calendar connection is created

### 5.2 Test Event Operations

Create an event:
```bash
curl -X POST "https://your-api.com/api/v1/calendar/events" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Meeting",
    "description": "Testing calendar integration",
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T11:00:00Z",
    "location": "Conference Room A"
  }'
```

### 5.3 Test Synchronization

1. Create an event in Google Calendar directly
2. Wait for webhook notification (or trigger manual sync)
3. Verify event appears in AI Assistant
4. Modify event in AI Assistant
5. Verify changes sync to Google Calendar

## Step 6: Production Deployment

### 6.1 Security Considerations

- Use HTTPS for all endpoints
- Validate webhook signatures
- Implement rate limiting
- Store tokens securely (encrypted)
- Regular token refresh

### 6.2 Monitoring

Monitor the following metrics:
- OAuth success/failure rates
- Webhook delivery success
- Sync operation latency
- API quota usage

### 6.3 Error Handling

Common error scenarios:
- **Token expiration**: Implement automatic refresh
- **Quota exceeded**: Implement exponential backoff
- **Webhook failures**: Retry with backoff
- **Sync conflicts**: Implement conflict resolution

## Troubleshooting

### Common Issues

**1. OAuth Redirect URI Mismatch**
- Ensure redirect URIs in Google Console match exactly
- Check for trailing slashes and protocol (http vs https)

**2. Insufficient Permissions**
- Verify all required scopes are requested
- Check OAuth consent screen configuration

**3. Webhook Not Receiving Events**
- Verify domain ownership in Google Search Console
- Check webhook URL is publicly accessible
- Validate SSL certificate

**4. Token Refresh Failures**
- Ensure refresh tokens are stored securely
- Implement proper error handling for expired refresh tokens

### Debug Mode

Enable debug logging in development:

```python
import logging
logging.getLogger('googleapiclient.discovery').setLevel(logging.DEBUG)
```

### API Quotas

Monitor your Google Calendar API usage:
- Default quota: 1,000,000 requests/day
- Per-user quota: 10,000 requests/100 seconds
- Implement exponential backoff for quota errors

## Best Practices

1. **Token Management**
   - Encrypt stored tokens
   - Implement automatic refresh
   - Handle revoked tokens gracefully

2. **Sync Strategy**
   - Use incremental sync with sync tokens
   - Implement conflict resolution
   - Batch operations when possible

3. **Error Handling**
   - Implement retry logic with exponential backoff
   - Log all API interactions for debugging
   - Provide meaningful error messages to users

4. **Performance**
   - Cache frequently accessed data
   - Use background tasks for heavy operations
   - Implement pagination for large datasets

## Support

For additional help:
- [Google Calendar API Documentation](https://developers.google.com/calendar/api)
- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google API Python Client](https://github.com/googleapis/google-api-python-client)