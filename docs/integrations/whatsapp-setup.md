# WhatsApp Business Cloud API Integration Setup Guide

This guide provides step-by-step instructions for setting up WhatsApp Business Cloud API integration with the AI Assistant system.

## Overview

The WhatsApp integration enables the AI Assistant to:
- Send confirmation messages and notifications
- Receive user responses (Y/N/Cancel)
- Handle opt-in/opt-out requests
- Send daily summaries and insights
- Process interactive message templates

## Prerequisites

- Meta Business Account
- WhatsApp Business Account
- Verified business phone number
- Valid webhook endpoint with HTTPS
- Meta Developer Account

## Step 1: Meta Business Setup

### 1.1 Create Meta Business Account

1. Go to [Meta Business](https://business.facebook.com/)
2. Click "Create Account"
3. Enter business information:
   - Business name
   - Your name
   - Business email
4. Verify email and complete setup

### 1.2 Create WhatsApp Business Account

1. In Meta Business Manager, go to "Accounts" → "WhatsApp Accounts"
2. Click "Add" → "Create a new WhatsApp Business Account"
3. Enter account name and select business
4. Complete verification process

### 1.3 Add Phone Number

1. In WhatsApp Business Account, go to "Phone Numbers"
2. Click "Add Phone Number"
3. Enter business phone number
4. Complete verification via SMS or call
5. Set display name and profile information

## Step 2: Meta Developer App Setup

### 2.1 Create Developer App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Click "My Apps" → "Create App"
3. Select "Business" as app type
4. Fill in app details:
   - **App name**: AI Assistant WhatsApp
   - **App contact email**: Your email
   - **Business account**: Select your business

### 2.2 Add WhatsApp Product

1. In your app dashboard, click "Add Product"
2. Find "WhatsApp" and click "Set up"
3. Select your WhatsApp Business Account
4. Choose phone number to use

### 2.3 Generate Access Token

1. In WhatsApp → "API Setup"
2. Copy the temporary access token
3. For production, generate a permanent token:
   - Go to "System Users" in Business Manager
   - Create system user with WhatsApp permissions
   - Generate access token

## Step 3: Webhook Configuration

### 3.1 Set Up Webhook Endpoint

Configure your webhook URL in the app:

1. In WhatsApp → "Configuration"
2. Click "Edit" next to Webhook
3. Enter webhook URL: `https://your-domain.com/api/v1/whatsapp/webhook`
4. Enter verify token (create a random string)
5. Subscribe to webhook fields:
   - `messages`
   - `message_status`

### 3.2 Webhook Verification

Your webhook endpoint must handle verification:

```python
@router.get("/webhook")
async def verify_whatsapp_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(challenge)
    else:
        raise HTTPException(status_code=403, detail="Verification failed")
```

## Step 4: Backend Configuration

### 4.1 Environment Variables

Add to your `.env` file:

```bash
# WhatsApp Business Cloud API Configuration
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_WEBHOOK_SECRET=your_webhook_secret

# API Configuration
WHATSAPP_API_VERSION=v18.0
WHATSAPP_BASE_URL=https://graph.facebook.com
```

### 4.2 Update Configuration

Update `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # WhatsApp Settings
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_BUSINESS_ACCOUNT_ID: str
    WHATSAPP_VERIFY_TOKEN: str
    WHATSAPP_WEBHOOK_SECRET: str
    WHATSAPP_API_VERSION: str = "v18.0"
    WHATSAPP_BASE_URL: str = "https://graph.facebook.com"
    
    class Config:
        env_file = ".env"
```

### 4.3 Install Dependencies

```bash
pip install httpx cryptography
```

## Step 5: Message Templates

### 5.1 Create Message Templates

WhatsApp requires pre-approved templates for business-initiated messages:

1. In WhatsApp Business Manager → "Message Templates"
2. Click "Create Template"
3. Example confirmation template:

```
Name: confirmation_request
Category: UTILITY
Language: English

Template:
Hi {{1}}, 

The AI Assistant wants to {{2}}. 

Reply with:
• Y to confirm
• N to decline  
• CANCEL to stop

This action will {{3}}.
```

### 5.2 Template Variables

Common template patterns:

```python
TEMPLATES = {
    "confirmation_request": {
        "name": "confirmation_request",
        "language": "en",
        "components": [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{{user_name}}"},
                    {"type": "text", "text": "{{action_description}}"},
                    {"type": "text", "text": "{{action_details}}"}
                ]
            }
        ]
    },
    "daily_summary": {
        "name": "daily_summary", 
        "language": "en",
        "components": [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{{date}}"},
                    {"type": "text", "text": "{{completed_tasks}}"},
                    {"type": "text", "text": "{{upcoming_events}}"}
                ]
            }
        ]
    }
}
```

## Step 6: Implementation Examples

### 6.1 Send Text Message

```python
async def send_text_message(phone_number: str, message: str):
    url = f"{settings.WHATSAPP_BASE_URL}/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        return response.json()
```

### 6.2 Send Template Message

```python
async def send_template_message(phone_number: str, template_name: str, parameters: list):
    url = f"{settings.WHATSAPP_BASE_URL}/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": param} for param in parameters]
                }
            ]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        return response.json()
```

### 6.3 Process Incoming Messages

```python
async def process_incoming_message(webhook_data: dict):
    for entry in webhook_data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "messages":
                value = change.get("value", {})
                
                for message in value.get("messages", []):
                    from_number = message.get("from")
                    message_body = message.get("text", {}).get("body", "")
                    
                    # Process user response
                    if message_body.upper() in ["Y", "YES", "CONFIRM"]:
                        await handle_confirmation(from_number, "confirm")
                    elif message_body.upper() in ["N", "NO", "DECLINE"]:
                        await handle_confirmation(from_number, "decline")
                    elif message_body.upper() in ["CANCEL", "STOP"]:
                        await handle_opt_out(from_number)
```

## Step 7: Testing

### 7.1 Test Webhook

Use ngrok for local testing:

```bash
# Install ngrok
npm install -g ngrok

# Expose local server
ngrok http 8000

# Use the HTTPS URL for webhook configuration
```

### 7.2 Test Message Sending

```bash
curl -X POST "https://your-api.com/api/v1/whatsapp/send" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "+1234567890",
    "content": "Hello from AI Assistant!",
    "message_type": "text"
  }'
```

### 7.3 Test Template Messages

```bash
curl -X POST "https://your-api.com/api/v1/whatsapp/confirmation" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "calendar_create",
    "action_description": "schedule a meeting with John",
    "action_details": "tomorrow at 3 PM in Conference Room A",
    "timeout_minutes": 30
  }'
```

## Step 8: Production Deployment

### 8.1 Business Verification

For production use, complete business verification:

1. Submit business documents
2. Verify business phone number
3. Complete security review
4. Get production access approved

### 8.2 Rate Limits

WhatsApp API has rate limits:
- **Messaging**: 1000 messages per second
- **Business-initiated conversations**: Based on phone number tier
- **User-initiated conversations**: Unlimited

### 8.3 Monitoring

Monitor key metrics:
- Message delivery rates
- Template approval status
- Webhook delivery success
- User opt-in/opt-out rates

## Step 9: Compliance and Best Practices

### 9.1 User Consent

Always obtain explicit consent:

```python
async def handle_opt_in_request(phone_number: str, consent_message: str):
    # Store consent record
    consent = Consent(
        user_phone=phone_number,
        consent_type="whatsapp_messaging",
        granted=True,
        consent_text=consent_message,
        granted_at=datetime.utcnow()
    )
    db.add(consent)
    db.commit()
    
    # Send confirmation
    await send_text_message(
        phone_number,
        "Thank you for opting in to AI Assistant notifications. Reply STOP anytime to opt out."
    )
```

### 9.2 Opt-Out Handling

Implement automatic opt-out:

```python
async def handle_opt_out(phone_number: str):
    # Update consent record
    consent = db.query(Consent).filter(
        Consent.user_phone == phone_number,
        Consent.consent_type == "whatsapp_messaging"
    ).first()
    
    if consent:
        consent.granted = False
        consent.revoked_at = datetime.utcnow()
        db.commit()
    
    # Send confirmation
    await send_text_message(
        phone_number,
        "You have been unsubscribed from AI Assistant notifications."
    )
```

### 9.3 Message Quality

Follow WhatsApp guidelines:
- Keep messages relevant and valuable
- Use approved templates for business messages
- Respond to user messages within 24 hours
- Maintain high delivery and read rates

## Troubleshooting

### Common Issues

**1. Webhook Not Receiving Events**
- Check webhook URL is publicly accessible
- Verify SSL certificate is valid
- Ensure webhook returns 200 status code
- Check webhook subscription settings

**2. Message Delivery Failures**
- Verify phone number format (+country_code_number)
- Check if recipient has WhatsApp account
- Ensure message content follows guidelines
- Verify access token is valid

**3. Template Rejection**
- Follow template guidelines strictly
- Avoid promotional content in utility templates
- Use proper variable formatting
- Submit for review with clear use case

**4. Rate Limiting**
- Implement exponential backoff
- Monitor rate limit headers
- Distribute messages over time
- Use message queuing for high volume

### Debug Tools

Enable debug logging:

```python
import logging
logging.getLogger("whatsapp_service").setLevel(logging.DEBUG)
```

Use WhatsApp Business API test numbers for development.

## Support Resources

- [WhatsApp Business Platform Documentation](https://developers.facebook.com/docs/whatsapp)
- [Cloud API Reference](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Message Templates Guide](https://developers.facebook.com/docs/whatsapp/message-templates)
- [Webhook Reference](https://developers.facebook.com/docs/whatsapp/webhooks)
- [Business Policy](https://www.whatsapp.com/legal/business-policy)