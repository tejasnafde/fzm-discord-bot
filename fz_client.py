"""Factorio.zone API client with WebSocket and REST API support."""
import asyncio
import json
import logging
import ssl
from typing import Callable, Optional, Dict, List
from enum import Enum

import requests
from websockets import client
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class ServerStatus(Enum):
    """Server status enumeration."""
    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    STOPPING = "STOPPING"
    RUNNING = "RUNNING"


class FactorioZoneClient:
    """Client for interacting with factorio.zone API."""
    
    def __init__(self, user_token: str, endpoint: str = "factorio.zone"):
        """
        Initialize the Factorio.zone client.
        
        Args:
            user_token: User authentication token for factorio.zone
            endpoint: Factorio.zone endpoint (default: factorio.zone)
        """
        self.user_token = user_token
        self.endpoint = endpoint
        self.socket: Optional[client.WebSocketClientProtocol] = None
        self.visit_secret: Optional[str] = None
        self.referrer_code: Optional[str] = None
        
        # Server state
        self.regions: Dict = {}
        self.versions: Dict = {}
        self.saves: Dict = {}
        self.mods: List = []
        self.launch_id: Optional[str] = None
        self.server_address: Optional[str] = None
        self.server_status = ServerStatus.OFFLINE
        
        # Sync flags
        self.mods_synced = False
        self.saves_synced = False
        self.connected = False
        
        # Background task
        self._listen_task: Optional[asyncio.Task] = None
        
        # Callback for server ready notification
        self.on_server_ready: Optional[Callable] = None
        
        # Callback for server stopped notification
        self.on_server_stopped: Optional[Callable] = None
        
    async def connect(self):
        """Establish WebSocket connection to factorio.zone."""
        try:
            logger.info(f"Connecting to wss://{self.endpoint}/ws")
            ssl_context = ssl.SSLContext()
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.check_hostname = False
            
            self.socket = await client.connect(
                f"wss://{self.endpoint}/ws",
                ping_interval=30,
                ping_timeout=10,
                ssl=ssl_context
            )
            
            self.connected = True
            logger.info("WebSocket connection established")
            
            # Start listening for messages in background
            self._listen_task = asyncio.create_task(self._listen())
            
            # Wait for initial sync
            await self._wait_for_sync()
            
        except Exception as e:
            logger.error(f"Failed to connect to factorio.zone: {e}")
            raise
    
    async def disconnect(self):
        """Close WebSocket connection."""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self.socket:
            await self.socket.close()
            self.connected = False
            logger.info("WebSocket connection closed")
    
    async def _listen(self):
        """Listen for WebSocket messages."""
        try:
            while self.connected and self.socket:
                try:
                    message = await self.socket.recv()
                    await self._handle_message(message)
                except ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    self.connected = False
                    break
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Listen task cancelled")
            raise
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            logger.debug(f"Received message type: {msg_type}")
            
            if msg_type == "visit":
                self.visit_secret = data["secret"]
                logger.info(f"Received visit secret: {self.visit_secret[:10]}...")
                await self._login()
                
            elif msg_type == "options":
                option_name = data.get("name")
                if option_name == "regions":
                    self.regions = data["options"]
                    logger.info(f"Received {len(self.regions)} regions")
                elif option_name == "versions":
                    self.versions = data["options"]
                    logger.info(f"Received {len(self.versions)} versions")
                elif option_name == "saves":
                    self.saves = data["options"]
                    self.saves_synced = True
                    logger.info(f"Received {len(self.saves)} saves")
                    
            elif msg_type == "mods":
                self.mods = data["mods"]
                self.mods_synced = True
                logger.info(f"Received {len(self.mods)} mods")
                
            elif msg_type == "idle":
                self.server_status = ServerStatus.OFFLINE
                self.launch_id = None
                self.server_address = None
                logger.info("Server is now OFFLINE")
                
                # Trigger callback if registered
                if self.on_server_stopped:
                    try:
                        if asyncio.iscoroutinefunction(self.on_server_stopped):
                            await self.on_server_stopped()
                        else:
                            self.on_server_stopped()
                    except Exception as e:
                        logger.error(f"Error in on_server_stopped callback: {e}")
                
            elif msg_type == "starting":
                self.server_status = ServerStatus.STARTING
                self.launch_id = data.get("launchId")
                logger.info(f"Server is STARTING (launch_id: {self.launch_id})")
                
            elif msg_type == "stopping":
                self.server_status = ServerStatus.STOPPING
                self.launch_id = data.get("launchId")
                logger.info(f"Server is STOPPING (launch_id: {self.launch_id})")
                
            elif msg_type == "running":
                self.server_status = ServerStatus.RUNNING
                self.launch_id = data.get("launchId")
                self.server_address = data.get("socket")
                logger.info(f"Server is RUNNING at {self.server_address}")
                
                # Trigger callback if registered
                if self.on_server_ready and self.server_address:
                    try:
                        if asyncio.iscoroutinefunction(self.on_server_ready):
                            await self.on_server_ready(self.server_address)
                        else:
                            self.on_server_ready(self.server_address)
                    except Exception as e:
                        logger.error(f"Error in on_server_ready callback: {e}")
                
            elif msg_type in ["log", "info", "warn", "error"]:
                line = data.get("line", "")
                logger.debug(f"[{msg_type.upper()}] {line}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _wait_for_sync(self, timeout: int = 30):
        """Wait for initial data sync."""
        logger.info("Waiting for initial sync...")
        start_time = asyncio.get_event_loop().time()
        
        while not (self.mods_synced and self.saves_synced):
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError("Timeout waiting for initial sync")
            await asyncio.sleep(0.5)
        
        logger.info("Initial sync complete")
    
    async def _login(self):
        """Login to factorio.zone using user token."""
        try:
            logger.info("Logging in to factorio.zone...")
            resp = requests.post(
                url=f"https://{self.endpoint}/api/user/login",
                data={
                    "userToken": self.user_token,
                    "visitSecret": self.visit_secret,
                    "reconnected": False
                }
            )
            
            if resp.ok:
                body = resp.json()
                self.user_token = body["userToken"]
                self.referrer_code = body.get("referralCode")
                logger.info("Login successful")
            else:
                logger.error(f"Login failed: {resp.status_code} - {resp.text}")
                raise Exception(f"Login failed: {resp.text}")
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise
    
    def start_server(self, region: str, version: str, save: str, mods: Optional[Dict[str, bool]] = None) -> str:
        """
        Start a Factorio server instance.
        
        Args:
            region: AWS region code
            version: Factorio version
            save: Save slot name
            mods: Optional dictionary of mod names to enabled status
            
        Returns:
            Launch ID of the started instance
        """
        try:
            logger.info(f"Starting server: region={region}, version={version}, save={save}, mods={mods}")
            
            # Prepare request data
            data = {
                "visitSecret": self.visit_secret,
                "region": region,
                "version": version,
                "save": save
            }
            
            # Add mods options if provided
            if mods:
                data["options"] = json.dumps(mods)
            
            resp = requests.post(
                url=f"https://{self.endpoint}/api/instance/start",
                data=data
            )
            
            if resp.status_code != 200:
                logger.error(f"Failed to start server: {resp.status_code} - {resp.text}")
                error_text = resp.text.lower()
                if resp.status_code == 403 and ("another operation is in progress" in error_text or "already have 1 instance" in error_text):
                    raise Exception("OPERATION_IN_PROGRESS")
                raise Exception(f"Failed to start server: {resp.text}")
            
            launch_id = resp.json()["launchId"]
            self.launch_id = launch_id
            logger.info(f"Server start initiated (launch_id: {launch_id})")
            return launch_id
            
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            raise
    
    def stop_server(self):
        """Stop the running Factorio server instance."""
        try:
            if not self.launch_id:
                raise Exception("No server is currently running")
            
            logger.info(f"Stopping server (launch_id: {self.launch_id})")
            resp = requests.post(
                url=f"https://{self.endpoint}/api/instance/stop",
                data={
                    "visitSecret": self.visit_secret,
                    "launchId": self.launch_id,
                },
                timeout=3600
            )
            
            if resp.status_code != 200:
                logger.error(f"Failed to stop server: {resp.status_code} - {resp.text}")
                raise Exception(f"Failed to stop server: {resp.text}")
            
            logger.info("Server stop initiated")
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            raise
    
    def get_status(self) -> Dict:
        """
        Get current server status.
        
        Returns:
            Dictionary with server status information
        """
        return {
            "status": self.server_status.value,
            "launch_id": self.launch_id,
            "server_address": self.server_address,
            "connected": self.connected
        }
