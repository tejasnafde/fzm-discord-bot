"""State management for tracking server status and preventing concurrent launches."""
import aiosqlite
import logging
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class StateManager:
    """Manages bot state using SQLite database."""
    
    def __init__(self, db_path: str):
        """
        Initialize state manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    is_running BOOLEAN NOT NULL DEFAULT 0,
                    launch_id TEXT,
                    region TEXT,
                    version TEXT,
                    save_slot TEXT,
                    server_address TEXT,
                    started_by TEXT,
                    channel_id TEXT,
                    started_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Insert default row if it doesn't exist
            await db.execute("""
                INSERT OR IGNORE INTO server_state (id, is_running)
                VALUES (1, 0)
            """)
            
            await db.commit()
            logger.info("State database initialized")
    
    async def is_server_running(self) -> bool:
        """
        Check if a server is currently running.
        
        Returns:
            True if server is running, False otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT is_running FROM server_state WHERE id = 1"
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False
    
    async def get_server_state(self) -> Optional[Dict]:
        """
        Get current server state.
        
        Returns:
            Dictionary with server state or None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM server_state WHERE id = 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def start_server(
        self,
        launch_id: str,
        region: str,
        version: str,
        save_slot: str,
        started_by: str,
        channel_id: str
    ):
        """
        Mark server as started.
        
        Args:
            launch_id: Launch ID from factorio.zone
            region: AWS region
            version: Factorio version
            save_slot: Save slot name
            started_by: Discord user who started the server
            channel_id: Discord channel ID where command was issued
        """
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE server_state
                SET is_running = 1,
                    launch_id = ?,
                    region = ?,
                    version = ?,
                    save_slot = ?,
                    started_by = ?,
                    channel_id = ?,
                    started_at = ?,
                    updated_at = ?
                WHERE id = 1
            """, (launch_id, region, version, save_slot, started_by, channel_id, now, now))
            
            await db.commit()
            logger.info(f"Server marked as started by {started_by}")
    
    async def update_server_address(self, server_address: str):
        """
        Update server address.
        
        Args:
            server_address: Server IP:port address
        """
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE server_state
                SET server_address = ?,
                    updated_at = ?
                WHERE id = 1
            """, (server_address, now))
            
            await db.commit()
            logger.info(f"Server address updated: {server_address}")
    
    async def stop_server(self):
        """Mark server as stopped."""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE server_state
                SET is_running = 0,
                    launch_id = NULL,
                    server_address = NULL,
                    updated_at = ?
                WHERE id = 1
            """, (now,))
            
            await db.commit()
            logger.info("Server marked as stopped")
    
    async def clear_state(self):
        """Clear all server state (for cleanup/reset)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE server_state
                SET is_running = 0,
                    launch_id = NULL,
                    region = NULL,
                    version = NULL,
                    save_slot = NULL,
                    server_address = NULL,
                    started_by = NULL,
                    started_at = NULL,
                    updated_at = NULL
                WHERE id = 1
            """)
            
            await db.commit()
            logger.info("Server state cleared")
