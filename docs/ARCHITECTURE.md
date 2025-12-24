# Architecture Documentation

This document provides a technical overview of the Factorio.zone Discord bot architecture.

## System Overview

The bot consists of three main components:

1. **Discord Bot** (`bot.py`) - Handles Discord interactions
2. **Factorio.zone API Client** (`fz_client.py`) - Manages communication with factorio.zone
3. **State Manager** (`state_manager.py`) - Tracks server state and prevents concurrent launches

```
┌─────────────────┐
│  Discord Users  │
└────────┬────────┘
         │ Slash Commands
         ▼
┌─────────────────────────────────┐
│      Discord Bot (bot.py)       │
│  - Command handlers             │
│  - User interaction             │
│  - Error handling               │
└──────┬──────────────────┬───────┘
       │                  │
       │                  │ State queries/updates
       ▼                  ▼
┌──────────────┐   ┌──────────────────┐
│  FZ Client   │   │  State Manager   │
│ (fz_client)  │   │ (state_manager)  │
│              │   │                  │
│ - WebSocket  │   │ - SQLite DB      │
│ - REST API   │   │ - Locking        │
└──────┬───────┘   └──────────────────┘
       │
       │ WebSocket + HTTP
       ▼
┌──────────────────┐
│  factorio.zone   │
│  - Server mgmt   │
│  - Save storage  │
└──────────────────┘
```

## Component Details

### Discord Bot (`bot.py`)

**Responsibilities:**
- Handle slash command registration and execution
- Validate user inputs
- Coordinate between FZ client and state manager
- Provide user feedback
- Error handling and logging

**Key Classes:**
- `FactorioBot`: Main bot class extending `commands.Bot`

**Commands:**
- `/start-server` - Start server with validation and state checking
- `/stop-server` - Stop server with save preservation
- `/server-status` - Display current status
- `/list-saves` - Show available save slots
- `/help` - Display help information

**Flow Example (Start Server):**
```
User executes /start-server
    ↓
Bot defers response (thinking...)
    ↓
Check state_manager.is_server_running()
    ↓
If running → Error message
If not running:
    ↓
Call fz_client.start_server()
    ↓
Update state_manager.start_server()
    ↓
Send success message with details
```

### Factorio.zone API Client (`fz_client.py`)

**Responsibilities:**
- Maintain WebSocket connection to factorio.zone
- Handle authentication (visitSecret + userToken)
- Provide REST API methods for server control
- Real-time status updates via WebSocket
- Auto-reconnection on connection loss

**Key Classes:**
- `FactorioZoneClient`: Main API client
- `ServerStatus`: Enum for server states

**WebSocket Message Types:**
- `visit` - Initial connection, provides visitSecret
- `options` - Region/version/save data
- `mods` - Mod list
- `idle/starting/stopping/running` - Server status updates
- `log/info/warn/error` - Server logs

**Authentication Flow:**
```
Connect to wss://factorio.zone/ws
    ↓
Receive "visit" message with visitSecret
    ↓
POST to /api/user/login with userToken + visitSecret
    ↓
Receive updated userToken
    ↓
Use visitSecret for all subsequent API calls
```

**API Methods:**
- `connect()` - Establish WebSocket connection
- `disconnect()` - Close connection gracefully
- `start_server(region, version, save)` - Start instance
- `stop_server()` - Stop instance
- `get_status()` - Get current status

### State Manager (`state_manager.py`)

**Responsibilities:**
- Track active server state
- Prevent concurrent server launches
- Persist state across bot restarts
- Provide server history

**Database Schema:**
```sql
CREATE TABLE server_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Single row
    is_running BOOLEAN NOT NULL DEFAULT 0,
    launch_id TEXT,
    region TEXT,
    version TEXT,
    save_slot TEXT,
    server_address TEXT,
    started_by TEXT,
    started_at TEXT,
    updated_at TEXT
)
```

**Key Methods:**
- `initialize()` - Create database schema
- `is_server_running()` - Check if server is active
- `get_server_state()` - Get full server state
- `start_server()` - Mark server as started
- `stop_server()` - Mark server as stopped
- `update_server_address()` - Update connection details

**Locking Mechanism:**
The single-row design (`id = 1`) ensures only one server can be tracked at a time. The `is_running` boolean acts as a lock.

### Configuration (`config.py`)

**Responsibilities:**
- Load environment variables
- Validate required configuration
- Provide default values
- Ensure database directory exists

**Environment Variables:**
- `DISCORD_BOT_TOKEN` - Discord authentication
- `FACTORIO_USER_TOKEN` - Factorio.zone authentication
- `GUILD_ID` - Optional, for faster command sync
- `LOG_LEVEL` - Logging verbosity
- `DATABASE_PATH` - SQLite database location

## Data Flow

### Starting a Server

```
1. User: /start-server region:ap-south-1 version:2.0.72 save_slot:slot1
2. Bot: Defer response (show "thinking...")
3. Bot → State Manager: is_server_running()?
4. State Manager → Bot: False
5. Bot → FZ Client: start_server(ap-south-1, 2.0.72, slot1)
6. FZ Client → factorio.zone: POST /api/instance/start
7. factorio.zone → FZ Client: {launchId: 1102069}
8. FZ Client → Bot: launch_id
9. Bot → State Manager: start_server(launch_id, region, version, save, user)
10. State Manager: UPDATE server_state SET is_running=1, ...
11. Bot → User: "✅ Server starting! Launch ID: 1102069"
12. FZ Client (WebSocket): Receives "starting" message
13. FZ Client (WebSocket): Receives "running" message with server_address
14. Bot: Can now show server_address in /server-status
```

### Stopping a Server

```
1. User: /stop-server
2. Bot: Defer response
3. Bot → State Manager: is_server_running()?
4. State Manager → Bot: True + server state
5. Bot → FZ Client: stop_server()
6. FZ Client → factorio.zone: POST /api/instance/stop
7. factorio.zone → FZ Client: 200 OK
8. Bot → State Manager: stop_server()
9. State Manager: UPDATE server_state SET is_running=0, ...
10. Bot → User: "✅ Server stopping! Save preserved in slot1"
11. FZ Client (WebSocket): Receives "stopping" message
12. FZ Client (WebSocket): Receives "idle" message
```

## Error Handling

### Levels of Error Handling

1. **API Level** (`fz_client.py`)
   - Catches HTTP errors
   - Handles WebSocket disconnections
   - Logs detailed error information
   - Raises exceptions with context

2. **Bot Level** (`bot.py`)
   - Catches exceptions from FZ client and state manager
   - Provides user-friendly error messages
   - Logs full stack traces
   - Prevents bot crashes

3. **State Level** (`state_manager.py`)
   - Handles database errors
   - Ensures data consistency
   - Logs database operations

### Error Scenarios

| Scenario | Handling |
|----------|----------|
| Server already running | Check state before starting, show error |
| Invalid region/version | Let factorio.zone API reject, show error |
| WebSocket disconnect | Auto-reconnect in background |
| Database locked | Retry with exponential backoff |
| API timeout | Catch and show user-friendly message |
| Token expired | Log error, prompt user to refresh token |

## Logging Strategy

### Log Levels

- **DEBUG**: WebSocket messages, API calls, state changes
- **INFO**: Bot lifecycle, command execution, connections
- **WARNING**: Recoverable errors, retries
- **ERROR**: Unrecoverable errors, exceptions

### Log Destinations

1. **Console** (`stdout`) - For Docker/Fly.io log aggregation
2. **File** (`bot.log`) - Local development and debugging

### Log Format

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Example:
```
2024-12-24 21:15:30 - fz_client - INFO - Connected to Factorio.zone
2024-12-24 21:15:35 - bot - INFO - Server started by User#1234
```

## Concurrency and Async

### Async Design

The bot uses `asyncio` for non-blocking I/O:

- **Discord.py**: Async by design
- **WebSocket**: Async connection and message handling
- **SQLite**: Using `aiosqlite` for async database operations
- **HTTP Requests**: Using synchronous `requests` (factorio.zone API is fast)

### Background Tasks

- **WebSocket Listener**: Runs continuously in background
  ```python
  self._listen_task = asyncio.create_task(self._listen())
  ```

### Thread Safety

- SQLite database is accessed via async operations
- Single-row design prevents race conditions
- No shared mutable state between commands

## Security Considerations

### Token Security

- Tokens stored in environment variables
- Never logged or exposed to users
- `.env` excluded from Git via `.gitignore`

### Input Validation

- Discord handles command parameter types
- Bot validates server state before operations
- Factorio.zone API validates region/version/save

### Permissions

- Bot requires minimal Discord permissions
- No admin or dangerous permissions needed
- Users can only control the single shared server

## Performance

### Resource Usage

- **Memory**: ~50-100MB (Python + dependencies)
- **CPU**: Minimal (event-driven)
- **Network**: WebSocket + occasional HTTP requests
- **Disk**: <1MB (SQLite database)

### Scalability

**Current Design:**
- Single server instance
- Single Discord guild (or global)
- 3-4 concurrent users

**Limitations:**
- One Factorio server at a time (by design)
- State stored in local SQLite (not distributed)

**If Scaling Needed:**
- Multiple bot instances → Use PostgreSQL instead of SQLite
- Multiple servers → Modify state manager for multi-server tracking
- High traffic → Add command rate limiting

## Deployment Architecture

### Fly.io Deployment

```
┌─────────────────────────────────┐
│         Fly.io Platform         │
│                                 │
│  ┌───────────────────────────┐  │
│  │   Docker Container        │  │
│  │                           │  │
│  │  ┌─────────────────────┐  │  │
│  │  │   Bot Application   │  │  │
│  │  │   (Python 3.10)     │  │  │
│  │  └─────────────────────┘  │  │
│  │                           │  │
│  │  ┌─────────────────────┐  │  │
│  │  │  Persistent Volume  │  │  │
│  │  │   /data/bot.db      │  │  │
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
│                                 │
│  Environment Secrets:           │
│  - DISCORD_BOT_TOKEN            │
│  - FACTORIO_USER_TOKEN          │
└─────────────────────────────────┘
         │                │
         │                │
         ▼                ▼
    Discord API    factorio.zone
```

## Future Enhancements

Potential improvements:

1. **Interactive Menus**: Use Discord select menus for region/version selection
2. **Scheduled Starts**: Allow scheduling server starts
3. **Auto-shutdown**: Stop server after inactivity
4. **Player Notifications**: Notify when server is ready
5. **Mod Management**: Upload/delete mods via Discord
6. **Save Management**: Upload/download saves
7. **Multi-server**: Support multiple concurrent servers (requires factorio.zone limits)
8. **Web Dashboard**: Optional web UI for monitoring

## References

- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Factorio.zone](https://factorio.zone)
- [FZ-Manager Source](https://github.com/michelsciortino/FZ-Manager)
- [Fly.io Documentation](https://fly.io/docs/)
