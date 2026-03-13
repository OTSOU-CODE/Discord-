# Discord Bot - Modular Version

This is a modularized version of the Discord bot, split into smaller, manageable files for better maintainability.

## Project Structure

```
├── __init__.py          # Main entry point
├── modules/
│   ├── config.py        # Configuration loading and constants
│   ├── data.py          # Data persistence and in-memory storage
│   ├── utils.py         # Helper functions (permissions, cooldowns, logging)
│   ├── economy.py       # Coin management system
│   ├── levels.py        # XP and leveling system
│   ├── moderation.py    # Warnings and moderation actions
│   ├── temp_channels.py # Temporary voice channel management
│   ├── tickets.py       # Support ticket system
│   ├── dashboard.py     # Web dashboard (HTTP server)
│   └── bot.py           # Main Discord client and commands
├── Data/                # JSON data files (auto-created)
│   ├── config.json
│   ├── user_stats.json
│   ├── economy.json
│   ├── warnings.json
│   └── ...
└── README.md
```

## Setup

1. **Install Dependencies:**
   ```bash
   pip install discord.py pillow easy-pil aiohttp
   ```

2. **Configure the Bot:**
   - Edit `Data/config.json` with your bot token and settings
   - Set `dashboard_secret` for web dashboard access
   - Configure channel IDs and other settings

3. **Run the Bot:**
   ```bash
   python __init__.py
   ```

## Features

- **Leveling System:** Voice and text activity tracking with XP and role rewards
- **Economy:** Coin system with daily rewards and shop
- **Moderation:** Warnings, mutes, kicks, bans with auto-escalation
- **Temp Channels:** Automatic voice channel management
- **Tickets:** Support ticket system
- **Dashboard:** Web interface for management (http://localhost:8080)
- **Analytics:** Command usage tracking

## Commands

Use `.help` in Discord for a full command list, or check the dashboard.

## Dashboard

If enabled in config, access the web dashboard at:
- **URL:** `http://localhost:8080` (or configured port)
- **Secret:** Set in `Data/config.json`

## Data Files

All data is stored in JSON files in the `Data/` directory:
- `config.json` - Bot configuration
- `user_stats.json` - User XP and activity data
- `economy.json` - Coin balances and transactions
- `warnings.json` - Moderation warnings
- `mod_log.json` - Moderation action log
- `temp_channels.json` - Temporary channel settings
- `tickets.json` - Support tickets
- `shop.json` - Economy shop items
- `reaction_roles.json` - Reaction role mappings
- `reminders.json` - User reminders
- `analytics.json` - Command usage statistics

## Development

Each module handles a specific aspect of the bot:
- **config.py:** Central configuration management
- **data.py:** Data loading/saving with atomic writes
- **utils.py:** Shared utility functions
- **economy.py:** Coin operations
- **levels.py:** XP calculations and level-ups
- **moderation.py:** Warning and punishment system
- **temp_channels.py:** Voice channel management
- **tickets.py:** Ticket creation and management
- **dashboard.py:** Web server for dashboard
- **bot.py:** Discord client, events, and commands

## Migration from Monolithic Version

This modular version maintains full compatibility with the original bot's data files. Simply replace the old `Discord-manager.py` with this structure and run `__init__.py`.

## Notes

- The bot uses atomic file saves to prevent data corruption
- All data is kept in memory for performance with periodic saves
- Dashboard runs on a separate thread for web access
- Commands start with `.` prefix
- Extensive permission checking for moderation commands
