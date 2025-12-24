# Setup Guide

This guide will walk you through setting up the Factorio.zone Discord bot from scratch.

## Table of Contents

1. [Creating a Discord Bot](#creating-a-discord-bot)
2. [Getting Your Factorio.zone Token](#getting-your-factoriozone-token)
3. [Local Development Setup](#local-development-setup)
4. [Configuration](#configuration)

## Creating a Discord Bot

### Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Give your application a name (e.g., "Factorio Server Manager")
4. Click **"Create"**

### Step 2: Create a Bot User

1. In your application, go to the **"Bot"** tab
2. Click **"Add Bot"**
3. Confirm by clicking **"Yes, do it!"**
4. Under the bot's username, click **"Reset Token"** and copy the token
   - ⚠️ **Save this token securely** - you'll need it for `DISCORD_BOT_TOKEN`
   - Never share this token publicly!

### Step 3: Configure Bot Permissions

1. Still in the **"Bot"** tab, scroll down to **"Privileged Gateway Intents"**
2. Enable:
   - ✅ **Message Content Intent** (required for bot functionality)
3. Scroll to **"Bot Permissions"** and select:
   - ✅ Send Messages
   - ✅ Use Slash Commands
   - ✅ Read Message History

### Step 4: Invite Bot to Your Server

1. Go to the **"OAuth2"** → **"URL Generator"** tab
2. Under **"Scopes"**, select:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Under **"Bot Permissions"**, select:
   - ✅ Send Messages
   - ✅ Use Slash Commands
4. Copy the generated URL at the bottom
5. Open the URL in your browser and select your Discord server
6. Click **"Authorize"**

### Step 5: Get Your Guild ID (Optional but Recommended)

This makes command registration faster during development.

1. In Discord, go to **User Settings** → **Advanced**
2. Enable **"Developer Mode"**
3. Right-click your Discord server icon
4. Click **"Copy Server ID"**
5. Save this as `GUILD_ID` in your `.env` file

## Getting Your Factorio.zone Token

See the detailed [Authentication Guide](AUTHENTICATION.md) for step-by-step instructions on extracting your Factorio.zone user token.

**Quick summary:**
1. Open [factorio.zone](https://factorio.zone) in your browser
2. Open Developer Tools (F12)
3. Go to the **Network** tab
4. Start a server or perform any action
5. Look for WebSocket connection or API requests
6. Find the `visitSecret` or `userToken` in the request payload
7. Copy this token for use as `FACTORIO_USER_TOKEN`

## Local Development Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd fzm-discord-bot
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file**
   ```bash
   cp .env.example .env
   ```

5. **Edit `.env` file**
   ```env
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   GUILD_ID=your_discord_server_id_here
   FACTORIO_USER_TOKEN=your_factorio_zone_user_token_here
   LOG_LEVEL=INFO
   DATABASE_PATH=./data/bot.db
   ```

6. **Run the bot**
   ```bash
   python bot.py
   ```

### Verifying Setup

1. Check the console output for:
   ```
   INFO - Connected to Factorio.zone
   INFO - Commands synced to guild <your_guild_id>
   INFO - Bot is ready! Logged in as <your_bot_name>
   ```

2. In Discord, type `/` and you should see your bot's commands appear

3. Try `/help` to verify the bot is responding

## Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Yes | Discord bot token from Developer Portal | `MTIzNDU2Nzg5MDEyMzQ1Njc4OQ...` |
| `FACTORIO_USER_TOKEN` | Yes | Factorio.zone authentication token | `abc123def456...` |
| `GUILD_ID` | No | Discord server ID for faster command sync | `123456789012345678` |
| `LOG_LEVEL` | No | Logging verbosity (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `DATABASE_PATH` | No | Path to SQLite database file | `./data/bot.db` |

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about bot operation (default)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages only

## Troubleshooting

### Bot doesn't appear online in Discord

- Verify `DISCORD_BOT_TOKEN` is correct
- Check that the bot is invited to your server
- Ensure your internet connection is stable

### Commands don't appear

- Wait 5-10 minutes for global command sync
- Set `GUILD_ID` for instant sync during development
- Restart Discord client
- Check bot has "Use Slash Commands" permission

### "Failed to connect to Factorio.zone"

- Verify `FACTORIO_USER_TOKEN` is correct and not expired
- Check your internet connection
- See [Authentication Guide](AUTHENTICATION.md) for token refresh

### Database errors

- Ensure `data/` directory exists and is writable
- Check `DATABASE_PATH` in `.env` is correct
- Delete `data/bot.db` to reset state (will lose server state)

### Import errors

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify you're using Python 3.10+: `python --version`
- Try recreating virtual environment

## Next Steps

- [Authentication Guide](AUTHENTICATION.md) - Get your Factorio.zone token
- [Deployment Guide](DEPLOYMENT.md) - Deploy to Fly.io
- [Architecture](ARCHITECTURE.md) - Understand how the bot works
