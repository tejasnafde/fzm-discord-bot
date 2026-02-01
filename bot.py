"""Discord bot for managing Factorio.zone servers."""
import asyncio
import logging
import sys
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from fz_client import FactorioZoneClient, ServerStatus
from state_manager import StateManager


class ISTFormatter(logging.Formatter):
    """Custom formatter that shows both local time and IST time."""
    
    def formatTime(self, record, datefmt=None):
        """Format time with both local and IST timezone."""
        dt = datetime.fromtimestamp(record.created)
        ist_dt = dt.astimezone(ZoneInfo('Asia/Kolkata'))
        
        # Format: Local time | IST time
        local_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        ist_time = ist_dt.strftime('%Y-%m-%d %H:%M:%S IST')
        
        return f"{local_time} | {ist_time}"

formatter = ISTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
file_handler = logging.FileHandler('bot.log')
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)


class FactorioBot(commands.Bot):
    """Discord bot for Factorio server management."""
    
    def __init__(self):
        """Initialize the bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix="!", intents=intents)
        
        self.fz_client: Optional[FactorioZoneClient] = None
        self.state_manager: Optional[StateManager] = None
        
    async def setup_hook(self):
        """Setup hook called when bot is starting."""
        logger.info("Setting up bot...")
        
        self.state_manager = StateManager(Config.DATABASE_PATH)
        await self.state_manager.initialize()
        
        self.fz_client = FactorioZoneClient(
            user_token=Config.FACTORIO_USER_TOKEN,
            endpoint=Config.FACTORIO_ZONE_ENDPOINT
        )
        
        try:
            await self.fz_client.connect()
            logger.info("Connected to Factorio.zone")
        except Exception as e:
            logger.error(f"Failed to connect to Factorio.zone: {e}")
            raise
        
        # Register callback for server ready notifications
        self.fz_client.on_server_ready = self.on_server_ready
        
        # Register callback for server stopped notifications
        self.fz_client.on_server_stopped = self.on_server_stopped
        
        # Sync commands to guild (faster than global sync)
        if Config.GUILD_ID:
            guild = discord.Object(id=int(Config.GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Commands synced to guild {Config.GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Commands synced globally")
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Bot is ready! Logged in as {self.user}")
        logger.info(f"Bot is in {len(self.guilds)} guilds")
    
    async def on_server_ready(self, server_address: str):
        """Called when Factorio server is ready with IP address."""
        try:
            # Get server state to find the channel
            state = await self.state_manager.get_server_state()
            if not state or not state.get('channel_id'):
                logger.warning("No channel_id found in state, cannot send notification")
                return
            
            channel_id = int(state['channel_id'])
            channel = self.get_channel(channel_id)
            
            if not channel:
                logger.error(f"Could not find channel {channel_id}")
                return
            
            # Send notification
            try:
                await channel.send(
                    f"🎮 **Server is ready!**\n\n"
                    f"🔗 **Server Address**: `{server_address}`\n"
                    f"🌍 **Region**: {state['region']}\n"
                    f"🎮 **Version**: {state['version']}\n"
                    f"💾 **Save Slot**: {state['save_slot']}\n\n"
                    f"✅ **You can now connect to the server!**"
                )
                logger.info(f"Sent server ready notification to channel {channel_id}")
            except discord.errors.Forbidden:
                logger.error(
                    f"Missing permissions to send message in channel {channel_id}. "
                    f"Please ensure the bot has 'Send Messages' permission in that channel. "
                    f"Server is ready at: {server_address}"
                )
            
        except Exception as e:
            logger.error(f"Error sending server ready notification: {e}", exc_info=True)
    
    async def on_server_stopped(self):
        """Called when Factorio server has stopped."""
        try:
            # Get server state to find the channel
            state = await self.state_manager.get_server_state()
            if not state or not state.get('channel_id'):
                logger.warning("No channel_id found in state, cannot send stop notification")
                # Clear state anyway
                await self.state_manager.stop_server()
                return
            
            channel_id = int(state['channel_id'])
            channel = self.get_channel(channel_id)
            
            if not channel:
                logger.error(f"Could not find channel {channel_id}")
                await self.state_manager.stop_server()
                return
            
            save_slot = state.get('save_slot', 'unknown')
            
            # Send notification
            try:
                await channel.send(
                    f"⚫ **Server has stopped**\n\n"
                    f"💾 **Save preserved in**: {save_slot}\n"
                    f"✅ **Server shutdown complete**"
                )
                logger.info(f"Sent server stopped notification to channel {channel_id}")
            except discord.errors.Forbidden:
                logger.error(
                    f"Missing permissions to send message in channel {channel_id}. "
                    f"Please ensure the bot has 'Send Messages' permission in that channel. "
                    f"Server has stopped, save preserved in: {save_slot}"
                )
            
            # Clear state after notifying (or attempting to)
            await self.state_manager.stop_server()
            
        except Exception as e:
            logger.error(f"Error sending server stopped notification: {e}", exc_info=True)
            # Try to clear state even if notification failed
            try:
                await self.state_manager.stop_server()
            except:
                pass
        
    async def close(self):
        """Cleanup when bot is shutting down."""
        logger.info("Shutting down bot...")
        if self.fz_client:
            await self.fz_client.disconnect()
        await super().close()


bot = FactorioBot()


@bot.tree.command(name="start-server", description="Start a Factorio server")
@app_commands.describe(
    region="AWS region (e.g., us-east-1, eu-west-1, ap-south-1)",
    version="Factorio version (e.g., 2.0.72)",
    save_slot="Save slot to use (e.g., slot1, slot2)",
    elevated_rails="Enable Elevated Rails DLC (default: disabled)",
    quality="Enable Quality DLC (default: disabled)",
    space_age="Enable Space Age DLC (default: disabled)"
)
async def start_server(
    interaction: discord.Interaction,
    region: str = "ap-south-1",
    version: str = "2.0.72",
    save_slot: str = "slot1",
    elevated_rails: bool = False,
    quality: bool = False,
    space_age: bool = False
):
    """Start a Factorio server."""
    await interaction.response.defer(thinking=True)
    
    try:
        # Check if server is already running (check both DB state and FZ client)
        db_running = await bot.state_manager.is_server_running()
        fz_status = bot.fz_client.get_status()
        
        # Sync state if they're out of sync
        if db_running and fz_status['status'] == 'OFFLINE':
            logger.warning("State out of sync: DB says running but FZ says offline. Clearing state.")
            await bot.state_manager.stop_server()
            db_running = False
        
        if db_running or fz_status['status'] in ['STARTING', 'RUNNING', 'STOPPING']:
            state = await bot.state_manager.get_server_state()
            server_info = ""
            if state and state.get('server_address'):
                server_info = f"Server: `{state['server_address']}`\n"
            elif fz_status.get('server_address'):
                server_info = f"Server: `{fz_status['server_address']}`\n"
            
            await interaction.followup.send(
                f"❌ A server is already running!\n"
                f"Started by: {state.get('started_by', 'Unknown')}\n"
                f"Region: {state.get('region', 'Unknown')}\n"
                f"Version: {state.get('version', 'Unknown')}\n"
                f"{server_info}"
                f"Use `/stop-server` to stop it first."
            )
            return
        
        logger.info(f"Starting server: region={region}, version={version}, save={save_slot}")
        
        # Build mods options dictionary
        mods = {
            "elevated-rails": elevated_rails,
            "quality": quality,
            "space-age": space_age
        }
        
        # Start server via Factorio.zone API
        try:
            launch_id = bot.fz_client.start_server(
                region=region,
                version=version,
                save=save_slot,
                mods=mods
            )
        except Exception as e:
            if str(e) == "OPERATION_IN_PROGRESS":
                logger.warning("Factorio.zone reported a conflict (already running or operation in progress). Attempting to sync state...")
                # Wait up to 5 seconds for WebSocket to pick up changes
                for _ in range(10):
                    await asyncio.sleep(0.5)
                    status = bot.fz_client.get_status()
                    if status['status'] in ['STARTING', 'RUNNING'] and status['launch_id']:
                        launch_id = status['launch_id']
                        logger.info(f"Successfully synced with active server (launch_id: {launch_id})")
                        break
                else:
                    # If we still don't have a launch_id, it really failed
                    raise Exception("The server is already running or busy, and I couldn't sync with it. Please wait a minute and try again.")
            else:
                raise e
        
        # Update state
        await bot.state_manager.start_server(
            launch_id=launch_id,
            region=region,
            version=version,
            save_slot=save_slot,
            started_by=str(interaction.user),
            channel_id=str(interaction.channel_id)
        )
        
        # Build enabled mods list for message
        enabled_mods = []
        if elevated_rails:
            enabled_mods.append("Elevated Rails")
        if quality:
            enabled_mods.append("Quality")
        if space_age:
            enabled_mods.append("Space Age")
        
        mods_text = f"🎮 **Mods**: {', '.join(enabled_mods)}\n" if enabled_mods else ""
        
        await interaction.followup.send(
            f"✅ Server starting!\n"
            f"🌍 Region: {region}\n"
            f"🎮 Version: {version}\n"
            f"💾 Save: {save_slot}\n"
            f"{mods_text}"
            f"🔑 Launch ID: {launch_id}\n\n"
            f"⏳ Server is starting up... I'll notify you here when it's ready!"
        )
        
        logger.info(f"Server started successfully by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Failed to start server: {str(e)}\n"
            f"Please check the logs for more details."
        )


@bot.tree.command(name="stop-server", description="Stop the running Factorio server")
async def stop_server(interaction: discord.Interaction):
    """Stop the running Factorio server."""
    await interaction.response.defer(thinking=True)
    
    try:
        # Check both DB and FZ client status
        db_running = await bot.state_manager.is_server_running()
        fz_status = bot.fz_client.get_status()
        
        # If DB says not running but FZ client has a server, sync the state
        if not db_running and fz_status['status'] in ['STARTING', 'RUNNING', 'STOPPING']:
            logger.warning("State out of sync: DB says not running but FZ has active server")
            # Try to stop anyway using FZ client's launch_id
            if fz_status['launch_id']:
                bot.fz_client.launch_id = fz_status['launch_id']
        elif not db_running and fz_status['status'] == 'OFFLINE':
            await interaction.followup.send("❌ No server is currently running.")
            return
        
        state = await bot.state_manager.get_server_state()
        
        # Ensure FZ client has the correct launch_id
        if state and state.get('launch_id'):
            bot.fz_client.launch_id = state['launch_id']
        
        logger.info(f"Stopping server (launch_id: {bot.fz_client.launch_id})")
        
        # Stop server via Factorio.zone API
        bot.fz_client.stop_server()
        
        # Update state
        await bot.state_manager.stop_server()
        
        save_slot = state.get('save_slot', 'unknown') if state else 'unknown'
        await interaction.followup.send(
            f"✅ Server stopping!\n"
            f"💾 Save will be preserved in slot: {save_slot}\n\n"
            f"⏳ Server is shutting down... This may take a minute."
        )
        
        logger.info(f"Server stopped by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error stopping server: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Failed to stop server: {str(e)}\n"
            f"Please check the logs for more details."
        )


@bot.tree.command(name="server-status", description="Check the current server status")
async def server_status(interaction: discord.Interaction):
    """Check the current server status."""
    await interaction.response.defer(thinking=True)
    
    try:
        # Get state from database
        state = await bot.state_manager.get_server_state()
        
        # Get live status from Factorio.zone client
        fz_status = bot.fz_client.get_status()
        
        db_running = state['is_running'] if state else False
        fz_active = fz_status['status'] in ['STARTING', 'RUNNING', 'STOPPING']
        
        # Sync: If DB says running but FZ is offline, clear it
        if db_running and fz_status['status'] == 'OFFLINE':
            logger.warning("State out of sync in status check: DB says running but FZ says offline. Clearing state.")
            await bot.state_manager.stop_server()
            db_running = False
            state = await bot.state_manager.get_server_state()

        if not db_running and not fz_active:
            await interaction.followup.send("📊 **Server Status**: OFFLINE\n\nNo server is currently running.")
            return
        
        status_emoji = {
            "OFFLINE": "⚫",
            "STARTING": "🟡",
            "RUNNING": "🟢",
            "STOPPING": "🔴"
        }
        
        status = fz_status['status']
        emoji = status_emoji.get(status, "⚪")
        
        message = f"📊 **Server Status**: {emoji} {status}\n\n"
        
        # If we have state, show it. If not (but server is active), show what we have.
        if state and (db_running or fz_active):
            message += f"🌍 **Region**: {state.get('region', 'Unknown')}\n"
            message += f"🎮 **Version**: {state.get('version', 'Unknown')}\n"
            message += f"💾 **Save Slot**: {state.get('save_slot', 'Unknown')}\n"
            if state.get('started_by'):
                message += f"👤 **Started By**: {state['started_by']}\n"
            if state.get('started_at'):
                message += f"🕐 **Started At**: {state['started_at']}\n"
        
        if fz_status['server_address']:
            message += f"\n🔗 **Server Address**: `{fz_status['server_address']}`\n"
            message += f"✅ **Ready to connect!**"
        elif status == "STARTING":
            message += f"\n⏳ Server is still starting up..."
        elif status == "RUNNING" and not fz_status['server_address']:
            message += f"\n⏳ Server is running but address is not yet available..."
            
        await interaction.followup.send(message)
        
    except Exception as e:
        logger.error(f"Error getting server status: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Failed to get server status: {str(e)}"
        )


@bot.tree.command(name="list-saves", description="List available save slots")
async def list_saves(interaction: discord.Interaction):
    """List available save slots."""
    await interaction.response.defer(thinking=True)
    
    try:
        saves = bot.fz_client.saves
        
        if not saves:
            await interaction.followup.send("📂 No save slots found.")
            return
        
        message = "📂 **Available Save Slots**:\n\n"
        
        for slot_name, slot_info in saves.items():
            message += f"• `{slot_name}`"
            if isinstance(slot_info, dict):
                if 'name' in slot_info:
                    message += f" - {slot_info['name']}"
                if 'size' in slot_info:
                    size_mb = slot_info['size'] / (1024 * 1024)
                    message += f" ({size_mb:.2f} MB)"
            message += "\n"
        
        await interaction.followup.send(message)
        
    except Exception as e:
        logger.error(f"Error listing saves: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Failed to list saves: {str(e)}"
        )


@bot.tree.command(name="help", description="Show bot help and available commands")
async def help_command(interaction: discord.Interaction):
    """Show help information."""
    help_text = """
🤖 **Factorio.zone Discord Bot**

Manage your Factorio server hosted on factorio.zone directly from Discord!

**Available Commands:**

`/start-server` - Start a new Factorio server
  • region: AWS region (e.g., us-east-1, ap-south-1)
  • version: Factorio version (e.g., 2.0.72)
  • save_slot: Save slot to use (e.g., slot1)

`/stop-server` - Stop the running server
  • Saves are automatically preserved!

`/server-status` - Check current server status
  • Shows server address when ready to connect

`/list-saves` - List all available save slots

`/help` - Show this help message

**Notes:**
• Only one server can run at a time
• Saves are persistent across server restarts
• Server address will be shown when ready to connect
"""
    
    await interaction.response.send_message(help_text)


def main():
    """Main entry point."""
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
        
        logging.getLogger().setLevel(Config.LOG_LEVEL)
        
        logger.info("Starting bot...")
        bot.run(Config.DISCORD_BOT_TOKEN)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
