# Authentication Guide

This guide explains how to obtain and manage your Factorio.zone authentication token.

## Overview

The Factorio.zone API requires authentication via a user token. Since factorio.zone doesn't provide an official API or token management interface, we need to extract the token from browser network traffic.

## How Factorio.zone Authentication Works

1. When you visit factorio.zone, a WebSocket connection is established
2. The server sends a `visitSecret` in the initial WebSocket message
3. You authenticate using your `userToken` (if you have one) or the site generates one
4. The `visitSecret` is used for subsequent API calls during that session

## Getting Your User Token

### Method 1: Extract from Network Traffic (Recommended)

#### Step 1: Open Developer Tools

1. Open [factorio.zone](https://factorio.zone) in your browser
2. Press `F12` or right-click → **Inspect** to open Developer Tools
3. Go to the **Network** tab
4. Check **"Preserve log"** to keep requests after page navigation

#### Step 2: Perform an Action

1. Start a server or perform any action on factorio.zone
2. In the Network tab, look for requests to:
   - `wss://factorio.zone/ws` (WebSocket)
   - `https://factorio.zone/api/instance/start` (or other API endpoints)

#### Step 3: Find the visitSecret

**For WebSocket (WS) connection:**
1. Click on the `ws` request in the Network tab
2. Go to the **Messages** tab
3. Look for the first message with `"type": "visit"`
4. Copy the `secret` value - this is your `visitSecret`

**Example WebSocket message:**
```json
{
  "type": "visit",
  "secret": "oUmPdH6j6RKe1Ypg4BiEIN"
}
```

**For API requests:**
1. Click on an API request (e.g., `/api/instance/start`)
2. Go to the **Payload** or **Request** tab
3. Look for `visitSecret` in the form data

**Example request payload:**
```
visitSecret: oUmPdH6j6RKe1Ypg4BiEIN
region: ap-south-1
version: 2.0.72
save: slot1
```

#### Step 4: Extract User Token (if available)

1. Look for `/api/user/login` request in the Network tab
2. Check the **Response** tab
3. Copy the `userToken` value

**Example login response:**
```json
{
  "userToken": "abc123def456ghi789...",
  "referralCode": "XYZ123"
}
```

### Method 2: Extract from Browser Storage

#### Using Browser Console

1. Open factorio.zone
2. Press `F12` to open Developer Tools
3. Go to the **Console** tab
4. Try running:
   ```javascript
   // Check localStorage
   console.log(localStorage);
   
   // Check sessionStorage
   console.log(sessionStorage);
   
   // Check cookies
   console.log(document.cookie);
   ```

5. Look for any keys related to authentication or user tokens

**Note:** As you discovered, factorio.zone may not store tokens in cookies. The `visitSecret` is session-based and obtained via WebSocket.

## Using the Token

### For Development

The bot needs the `FACTORIO_USER_TOKEN` to authenticate. However, based on the network traffic analysis, factorio.zone uses a session-based `visitSecret` that's obtained dynamically via WebSocket.

**Our bot handles this automatically:**
1. Connects to the WebSocket
2. Receives the `visitSecret`
3. Uses it for API authentication

**You still need a `userToken` for persistent authentication:**
- This allows the bot to maintain your user session
- Without it, each connection creates a new anonymous session
- Your saves and settings are tied to your user account

### Environment Configuration

Add to your `.env` file:

```env
# If you have a userToken (from /api/user/login response)
FACTORIO_USER_TOKEN=your_user_token_here

# If you only have a visitSecret (session-based, not recommended)
# The bot will get this automatically via WebSocket
```

## Token Persistence and Refresh

### Session-based visitSecret

- **Lifetime**: Single session (until WebSocket disconnects)
- **Refresh**: Automatically obtained on each WebSocket connection
- **Storage**: Not needed - bot gets it automatically

### User Token

- **Lifetime**: Persistent (tied to your factorio.zone account)
- **Refresh**: May expire after long periods of inactivity
- **Storage**: Store in `.env` file (keep secure!)

### If Your Token Expires

1. Revisit factorio.zone
2. Perform an action (start a server)
3. Capture the new `userToken` from `/api/user/login` response
4. Update `FACTORIO_USER_TOKEN` in `.env`
5. Restart the bot

## Security Considerations

### Protecting Your Token

⚠️ **Never share your user token publicly!**

- Don't commit `.env` to Git (already in `.gitignore`)
- Don't share screenshots with tokens visible
- Don't paste tokens in public Discord channels
- Use environment variables or secrets management in production

### Token Rotation

If you suspect your token is compromised:

1. Log out of factorio.zone (if possible)
2. Clear browser data for factorio.zone
3. Log back in and obtain a new token
4. Update your bot configuration

## Troubleshooting

### "Login failed" error

**Possible causes:**
- Invalid or expired `FACTORIO_USER_TOKEN`
- Network connectivity issues
- Factorio.zone API changes

**Solutions:**
1. Extract a fresh token from browser
2. Verify token is copied correctly (no extra spaces)
3. Check bot logs for detailed error messages

### WebSocket connection fails

**Possible causes:**
- Firewall blocking WebSocket connections
- SSL/TLS certificate issues
- Factorio.zone server issues

**Solutions:**
1. Check your firewall settings
2. Verify internet connection
3. Check factorio.zone status (try accessing in browser)

### "visitSecret is None" error

**Possible causes:**
- WebSocket connection not established
- Initial sync not complete

**Solutions:**
1. Wait for initial sync (bot logs will show "Initial sync complete")
2. Check WebSocket connection in logs
3. Restart the bot

## Advanced: Manual Token Testing

You can test your token manually using curl:

```bash
# Test with visitSecret (you'll need to get this from WebSocket first)
curl -X POST https://factorio.zone/api/user/login \
  -d "userToken=your_user_token" \
  -d "visitSecret=your_visit_secret" \
  -d "reconnected=false"
```

Expected response:
```json
{
  "userToken": "...",
  "referralCode": "..."
}
```

## Summary

1. **visitSecret**: Session-based, obtained automatically via WebSocket
2. **userToken**: Persistent, needs to be extracted from browser and configured
3. The bot handles WebSocket connection and visitSecret automatically
4. You only need to provide `FACTORIO_USER_TOKEN` in `.env`

For most users, capturing the `userToken` from the `/api/user/login` response is the best approach for persistent authentication.
