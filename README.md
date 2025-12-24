# Factorio.zone Discord Bot 🤖

A Discord bot to manage Factorio servers hosted on [factorio.zone](https://factorio.zone) directly from Discord. Start, stop, and monitor your server without leaving your Discord server!

## Features

- 🚀 **Start/Stop Servers** - Launch and stop Factorio servers with simple slash commands
- 💾 **Persistent Saves** - Saves are automatically preserved across server restarts
- 🔒 **Concurrent Protection** - Prevents multiple servers from running simultaneously
- 📊 **Real-time Status** - Check server status and get connection details
- 🌍 **Multi-region Support** - Choose from multiple AWS regions
- 📝 **Detailed Logging** - Comprehensive logging for debugging and monitoring

## Quick Start

### Prerequisites

- Python 3.10+
- Discord Bot Token ([How to create](docs/SETUP.md#creating-a-discord-bot))
- Factorio.zone User Token ([How to get](docs/AUTHENTICATION.md))
- Docker (optional, for containerized deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd fzm-discord-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## Available Commands

| Command | Description |
|---------|-------------|
| `/start-server` | Start a Factorio server with specified region, version, and save slot |
| `/stop-server` | Stop the currently running server |
| `/server-status` | Check current server status and get connection details |
| `/list-saves` | List all available save slots |
| `/help` | Show help information |

## Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed setup instructions
- **[Authentication](docs/AUTHENTICATION.md)** - How to get your Factorio.zone token
- **[Deployment](docs/DEPLOYMENT.md)** - Deploy to Fly.io or other platforms
- **[Architecture](docs/ARCHITECTURE.md)** - Technical architecture overview

## Example Usage

```
/start-server region:ap-south-1 version:2.0.72 save_slot:slot1
```

The bot will:
1. Check if a server is already running
2. Start the server on factorio.zone
3. Monitor the startup process
4. Provide the server address when ready

## Configuration

Key environment variables:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
FACTORIO_USER_TOKEN=your_factorio_zone_token
GUILD_ID=your_discord_server_id (optional)
LOG_LEVEL=INFO
```

See [`.env.example`](.env.example) for all options.

## Project Structure

```
fzm-discord-bot/
├── bot.py              # Main Discord bot
├── fz_client.py        # Factorio.zone API client
├── state_manager.py    # State management (SQLite)
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
├── fly.toml            # Fly.io deployment config
└── docs/               # Documentation
    ├── SETUP.md
    ├── AUTHENTICATION.md
    ├── DEPLOYMENT.md
    └── ARCHITECTURE.md
```

## Deployment Options

### Fly.io (Recommended - Free Tier)

See [Deployment Guide](docs/DEPLOYMENT.md) for detailed instructions.

```bash
flyctl launch
flyctl secrets set DISCORD_BOT_TOKEN=xxx FACTORIO_USER_TOKEN=xxx
flyctl deploy
```

### Other Platforms

- **Railway** - Docker-based deployment
- **Render** - Note: Has cold starts on free tier
- **Self-hosted** - Run with Docker or systemd

## Troubleshooting

**Bot not responding to commands?**
- Ensure bot has proper permissions in your Discord server
- Check that commands are synced (wait a few minutes after first start)
- Verify `GUILD_ID` is set correctly in `.env`

**Can't connect to Factorio.zone?**
- Verify your `FACTORIO_USER_TOKEN` is correct
- Check the logs for connection errors
- See [Authentication Guide](docs/AUTHENTICATION.md)

**Server won't start?**
- Ensure region, version, and save_slot are valid
- Check factorio.zone website to verify available options
- Review bot logs for detailed error messages

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Based on [FZ-Manager](https://github.com/michelsciortino/FZ-Manager) for API reverse engineering
- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Hosted on [factorio.zone](https://factorio.zone)

## Support

For issues and questions:
- Check the [documentation](docs/)
- Review bot logs (`bot.log`)
- Open an issue on GitHub
