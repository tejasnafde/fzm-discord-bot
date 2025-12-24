# Deployment Guide

This guide covers deploying the Factorio.zone Discord bot to production environments.

## Deployment Options

### Option 1: Fly.io (Recommended - Free Tier Available)

Fly.io offers a generous free tier perfect for Discord bots:
- 3 shared-CPU VMs running 24/7
- 160GB outbound data transfer/month
- No cold starts (unlike some competitors)
- Persistent volumes for SQLite database

#### Prerequisites

1. Install flyctl CLI:
   ```bash
   # macOS
   brew install flyctl
   
   # Linux
   curl -L https://fly.io/install.sh | sh
   
   # Windows
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. Sign up and login:
   ```bash
   flyctl auth signup
   # or
   flyctl auth login
   ```

#### Deployment Steps

1. **Initialize Fly.io app** (if not already done)
   ```bash
   flyctl launch
   ```
   
   When prompted:
   - App name: Choose a unique name (e.g., `fzm-discord-bot-yourname`)
   - Region: Choose closest to you or your players
   - Don't deploy yet: Say "No" - we need to set secrets first

2. **Create persistent volume** (for SQLite database)
   ```bash
   flyctl volumes create bot_data --size 1
   ```

3. **Set environment secrets**
   ```bash
   flyctl secrets set DISCORD_BOT_TOKEN="your_discord_bot_token"
   flyctl secrets set FACTORIO_USER_TOKEN="your_factorio_zone_token"
   flyctl secrets set GUILD_ID="your_discord_server_id"
   ```

4. **Deploy the bot**
   ```bash
   flyctl deploy
   ```

5. **Verify deployment**
   ```bash
   # Check status
   flyctl status
   
   # View logs
   flyctl logs
   
   # Check if bot is running
   flyctl ssh console
   ps aux | grep python
   ```

#### Managing Your Fly.io Deployment

**View logs:**
```bash
flyctl logs
flyctl logs -f  # Follow logs in real-time
```

**Restart the bot:**
```bash
flyctl apps restart
```

**Update secrets:**
```bash
flyctl secrets set FACTORIO_USER_TOKEN="new_token"
```

**Scale resources (if needed):**
```bash
# Scale to 2 instances (for redundancy)
flyctl scale count 2

# Change VM size (will incur costs beyond free tier)
flyctl scale vm shared-cpu-2x
```

**SSH into the container:**
```bash
flyctl ssh console
```

**Destroy the app:**
```bash
flyctl apps destroy fzm-discord-bot
```

---

### Option 2: Railway

Railway offers $5 free trial credit, then $5/month.

#### Deployment Steps

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login:**
   ```bash
   railway login
   ```

3. **Initialize project:**
   ```bash
   railway init
   ```

4. **Set environment variables:**
   ```bash
   railway variables set DISCORD_BOT_TOKEN="your_token"
   railway variables set FACTORIO_USER_TOKEN="your_token"
   railway variables set GUILD_ID="your_guild_id"
   ```

5. **Deploy:**
   ```bash
   railway up
   ```

**Note:** Railway may have cold starts and shared IP rate limiting issues.

---

### Option 3: Render

Render offers 750 hours/month free tier.

#### Deployment Steps

1. **Create account** at [render.com](https://render.com)

2. **Create new Web Service:**
   - Connect your GitHub repository
   - Select "Docker" as environment
   - Choose free tier

3. **Set environment variables** in Render dashboard:
   - `DISCORD_BOT_TOKEN`
   - `FACTORIO_USER_TOKEN`
   - `GUILD_ID`

4. **Deploy** - Render will automatically build and deploy

**⚠️ Warning:** Render free tier has cold starts (15 min inactivity = sleep). Your bot will be unresponsive during wake-up (~30 seconds).

**Workaround:** Use UptimeRobot to ping your bot every 5 minutes (requires adding a health check endpoint).

---

### Option 4: Self-Hosted (VPS/Home Server)

#### Using Docker Compose

1. **Install Docker and Docker Compose** on your server

2. **Clone repository:**
   ```bash
   git clone <your-repo>
   cd fzm-discord-bot
   ```

3. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens
   ```

4. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

5. **View logs:**
   ```bash
   docker-compose logs -f
   ```

6. **Update and restart:**
   ```bash
   git pull
   docker-compose down
   docker-compose up -d --build
   ```

#### Using systemd (Linux)

1. **Create systemd service file:**
   ```bash
   sudo nano /etc/systemd/system/factorio-bot.service
   ```

2. **Add configuration:**
   ```ini
   [Unit]
   Description=Factorio Discord Bot
   After=network.target

   [Service]
   Type=simple
   User=your_user
   WorkingDirectory=/path/to/fzm-discord-bot
   Environment="PATH=/path/to/venv/bin"
   ExecStart=/path/to/venv/bin/python bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable factorio-bot
   sudo systemctl start factorio-bot
   ```

4. **Check status:**
   ```bash
   sudo systemctl status factorio-bot
   sudo journalctl -u factorio-bot -f
   ```

---

## Production Best Practices

### Monitoring

1. **Set up log aggregation:**
   - Fly.io: Built-in logging
   - Self-hosted: Use Loki, ELK stack, or CloudWatch

2. **Monitor bot uptime:**
   - Use UptimeRobot or similar
   - Set up Discord webhook for alerts

3. **Track errors:**
   - Review logs regularly
   - Set up error notifications

### Security

1. **Protect secrets:**
   - Never commit `.env` to Git
   - Use platform secret management (Fly.io secrets, Railway variables)
   - Rotate tokens periodically

2. **Limit bot permissions:**
   - Only grant necessary Discord permissions
   - Use role-based access in Discord

3. **Keep dependencies updated:**
   ```bash
   pip list --outdated
   pip install --upgrade -r requirements.txt
   ```

### Backup

1. **Backup SQLite database:**
   ```bash
   # Fly.io
   flyctl ssh console
   cat /data/bot.db > /tmp/backup.db
   flyctl ssh sftp get /tmp/backup.db
   
   # Docker
   docker cp factorio-discord-bot:/app/data/bot.db ./backup.db
   ```

2. **Backup configuration:**
   - Keep `.env.example` updated
   - Document any custom configurations

### Scaling

For most use cases (3-4 users, 2-3 days/week), a single instance is sufficient.

If you need to scale:
- **Vertical scaling:** Increase VM size (Fly.io: `flyctl scale vm`)
- **Horizontal scaling:** Not needed for Discord bots (stateful)

---

## Troubleshooting

### Bot not starting

**Check logs:**
```bash
# Fly.io
flyctl logs

# Docker
docker-compose logs

# systemd
sudo journalctl -u factorio-bot -n 50
```

**Common issues:**
- Missing environment variables
- Invalid tokens
- Port conflicts (if using health checks)

### Database errors

**Reset database:**
```bash
# Fly.io
flyctl ssh console
rm /data/bot.db
exit
flyctl apps restart

# Docker
docker-compose down
rm data/bot.db
docker-compose up -d
```

### Out of memory

**Increase memory limit:**
```bash
# Fly.io
flyctl scale memory 512  # 512MB
```

### Connection issues

**Check network:**
- Verify outbound connections are allowed
- Check firewall rules
- Ensure WebSocket connections aren't blocked

---

## Cost Comparison

| Platform | Free Tier | Paid Tier | Cold Starts | Best For |
|----------|-----------|-----------|-------------|----------|
| **Fly.io** | 3 VMs, 160GB transfer | $1.94/mo per VM | ❌ No | Production (Recommended) |
| **Railway** | $5 trial | $5/mo | ⚠️ Possible | Quick deployment |
| **Render** | 750 hrs/mo | $7/mo | ✅ Yes | Testing only |
| **Self-hosted** | Hardware cost | Electricity | ❌ No | Full control |

**Recommendation:** Use Fly.io for production. It offers the best free tier with no cold starts, perfect for Discord bots.

---

## Next Steps

After deployment:
1. Test all commands in Discord
2. Monitor logs for errors
3. Set up backup schedule
4. Document your deployment for team members
5. Consider setting up monitoring/alerting

For issues, check:
- [Troubleshooting section](#troubleshooting)
- Bot logs
- [Setup Guide](SETUP.md)
- [Authentication Guide](AUTHENTICATION.md)
