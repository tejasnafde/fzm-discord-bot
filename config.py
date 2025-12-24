"""Configuration management for the Discord bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    GUILD_ID = os.getenv("GUILD_ID")
    
    FACTORIO_USER_TOKEN = os.getenv("FACTORIO_USER_TOKEN")
    FACTORIO_ZONE_ENDPOINT = "factorio.zone"
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/bot.db")
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        required_vars = {
            "DISCORD_BOT_TOKEN": cls.DISCORD_BOT_TOKEN,
            "FACTORIO_USER_TOKEN": cls.FACTORIO_USER_TOKEN,
        }
        
        missing = [key for key, value in required_vars.items() if not value]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please check your .env file or environment configuration."
            )
        
        db_path = Path(cls.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        return True
