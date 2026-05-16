"""
database.py
-----------
All file paths, in-memory mirrors, ensure_db_files() bootstrap,
all save_*() wrappers, and the cache_member_name() helper.

Every cog imports the dict it needs directly:
    from database import economy_data, save_economy
Python dict imports are by reference, so mutations are shared automatically.
"""

import os
from config import data_dir, _atomic_save, _safe_load

# ─── File paths ───────────────────────────────────────────────────────────────
REQUIREMENTS_FILE   = os.path.join(data_dir, "level_requirements.json")
USER_STATS_FILE     = os.path.join(data_dir, "user_stats.json")
USER_STREAKS_FILE   = os.path.join(data_dir, "streaks.json")
WARNINGS_FILE       = os.path.join(data_dir, "warnings.json")
MOD_LOG_FILE        = os.path.join(data_dir, "mod_log.json")
AUTOMOD_FILE        = os.path.join(data_dir, "automod_config.json")
ECONOMY_FILE        = os.path.join(data_dir, "economy.json")
SHOP_FILE           = os.path.join(data_dir, "shop.json")
TICKETS_FILE        = os.path.join(data_dir, "tickets.json")
REACTION_ROLES_FILE = os.path.join(data_dir, "reaction_roles.json")
REMINDERS_FILE      = os.path.join(data_dir, "reminders.json")
ANALYTICS_FILE      = os.path.join(data_dir, "analytics.json")
USER_NAMES_FILE     = os.path.join(data_dir, "user_names.json")
LEADERBOARD_FILE    = os.path.join(data_dir, "leaderboard.json")
TEMP_DATA_FILE      = os.path.join(data_dir, "temp_channels.json")
STAFF_NOTES_FILE    = os.path.join(data_dir, "staff_notes.json")
TEMP_BANS_FILE      = os.path.join(data_dir, "temp_bans.json")

# ─── In-memory mirrors ────────────────────────────────────────────────────────
level_requirements: dict = {}
user_stats:         dict = {}
user_streaks:       dict = {}
warnings_data:      dict = {}
mod_log:            list = []
automod_config:     dict = {}
economy_data:       dict = {}
shop_items:         list = []
tickets_data:       dict = {}
reaction_roles:     dict = {}
reminders_list:     list = []
analytics_data:     dict = {}
user_names:         dict = {}   # uid → {"display_name", "username", "avatar"}
command_cooldowns:  dict = {}
staff_notes:        dict = {}
temp_bans:          dict = {}

# Temp-channel runtime state (not JSON-backed during runtime — saved on change)
temp_channels:       dict = {}   # channel_id(int) → owner_id(int)
channel_settings:    dict = {}   # channel_id(int) → settings dict
channel_whitelists:  dict = {}
channel_blacklists:  dict = {}
scheduled_deletions: dict = {}
channel_last_activity: dict = {}
muted_users:         dict = {}   # user_id → {"mute_start", "guild_id"}


# ─── Default level table (200 levels) ────────────────────────────────────────
def _make_default_levels() -> dict:
    out = {}
    for i in range(201):
        out[str(i)] = {
            "type":                   "hybrid",
            "voice_minutes_required": i * 60,
            "text_minutes_required":  i * 10,
            "role_id":                0,
        }
    return out


# ─── DB defaults ──────────────────────────────────────────────────────────────
_DB_DEFAULTS = {
    REQUIREMENTS_FILE:   None,   # handled separately (200-level table)
    USER_STATS_FILE:     {},
    USER_STREAKS_FILE:   {},
    WARNINGS_FILE:       {},
    MOD_LOG_FILE:        [],
    AUTOMOD_FILE:        {"mention_limit": 5, "message_cooldown_seconds": 2, "allowed_domains": []},
    ECONOMY_FILE:        {},
    SHOP_FILE:           [],
    TICKETS_FILE:        {},
    REACTION_ROLES_FILE: {},
    REMINDERS_FILE:      [],
    ANALYTICS_FILE:      {},
    USER_NAMES_FILE:     {},
    LEADERBOARD_FILE:    {},
    STAFF_NOTES_FILE:    {},
    TEMP_BANS_FILE:      {},
}


# ─── Bootstrap ───────────────────────────────────────────────────────────────
def ensure_db_files() -> None:
    """Create any missing DB file with its default, then load all data into RAM."""
    global level_requirements, user_stats, user_streaks, warnings_data, mod_log
    global automod_config, economy_data, shop_items, tickets_data, reaction_roles
    global reminders_list, analytics_data, user_names, staff_notes, temp_bans

    if not os.path.exists(REQUIREMENTS_FILE):
        _atomic_save(REQUIREMENTS_FILE, _make_default_levels())
        print("[DB] Created level_requirements.json with 200 default levels.")

    for path, default in _DB_DEFAULTS.items():
        if default is None:
            continue
        if not os.path.exists(path):
            _atomic_save(path, default)
            print(f"[DB] Created {os.path.basename(path)}")

    # ── Load ──────────────────────────────────────────────────────────────────
    level_requirements = _safe_load(REQUIREMENTS_FILE, _make_default_levels())
    user_stats         = _safe_load(USER_STATS_FILE,    {})
    user_streaks       = _safe_load(USER_STREAKS_FILE,  {})
    warnings_data      = _safe_load(WARNINGS_FILE,      {})
    mod_log            = _safe_load(MOD_LOG_FILE,        [])
    automod_config     = _safe_load(
        AUTOMOD_FILE,
        {"mention_limit": 5, "message_cooldown_seconds": 2, "allowed_domains": []},
    )
    economy_data       = _safe_load(ECONOMY_FILE,        {})
    shop_items         = _safe_load(SHOP_FILE,           [])
    tickets_data       = _safe_load(TICKETS_FILE,        {})
    reaction_roles     = _safe_load(REACTION_ROLES_FILE, {})
    reminders_list     = _safe_load(REMINDERS_FILE,      [])
    analytics_data     = _safe_load(ANALYTICS_FILE,      {})
    user_names         = _safe_load(USER_NAMES_FILE,     {})
    staff_notes        = _safe_load(STAFF_NOTES_FILE,    {})
    temp_bans          = _safe_load(TEMP_BANS_FILE,      {})

    # ── Type guards (protect against manual file edits) ───────────────────────
    if not isinstance(mod_log,        list): mod_log        = []
    if not isinstance(shop_items,     list): shop_items     = []
    if not isinstance(reminders_list, list): reminders_list = []
    if not isinstance(user_stats,     dict): user_stats     = {}
    if not isinstance(economy_data,   dict): economy_data   = {}
    if not isinstance(warnings_data,  dict): warnings_data  = {}
    if not isinstance(user_names,     dict): user_names     = {}
    if not isinstance(staff_notes,    dict): staff_notes    = {}
    if not isinstance(temp_bans,      dict): temp_bans      = {}

    print(
        f"[DB] Loaded: {len(user_stats)} users, {len(economy_data)} economy entries, "
        f"{len(warnings_data)} warned users, {len(user_names)} cached names."
    )


# ─── Save wrappers ────────────────────────────────────────────────────────────
def save_user_stats():     _atomic_save(USER_STATS_FILE,      user_stats)
def save_user_streaks():   _atomic_save(USER_STREAKS_FILE,    user_streaks)
def save_warnings():       _atomic_save(WARNINGS_FILE,        warnings_data)
def save_mod_log():        _atomic_save(MOD_LOG_FILE,         mod_log)
def save_economy():        _atomic_save(ECONOMY_FILE,         economy_data)
def save_tickets():        _atomic_save(TICKETS_FILE,         tickets_data)
def save_reaction_roles(): _atomic_save(REACTION_ROLES_FILE,  reaction_roles)
def save_reminders():      _atomic_save(REMINDERS_FILE,       reminders_list)
def save_analytics():      _atomic_save(ANALYTICS_FILE,       analytics_data)
def save_user_names():     _atomic_save(USER_NAMES_FILE,      user_names)
def save_shop():           _atomic_save(SHOP_FILE,            shop_items)
def save_staff_notes():    _atomic_save(STAFF_NOTES_FILE,     staff_notes)
def save_temp_bans():      _atomic_save(TEMP_BANS_FILE,       temp_bans)


def save_temp_channels() -> None:
    """Persist temp_channels and channel_settings atomically."""
    try:
        data_to_save = {
            "channels": {str(k): v for k, v in temp_channels.items()},
            "settings":  {str(k): v for k, v in channel_settings.items()},
        }
        _atomic_save(TEMP_DATA_FILE, data_to_save)
    except Exception as e:
        print(f"[DB] Error saving temp channels: {e}")


def load_temp_channels() -> None:
    """Load temp_channels and channel_settings from disk into RAM."""
    global temp_channels, channel_settings
    if not os.path.exists(TEMP_DATA_FILE):
        temp_channels   = {}
        channel_settings = {}
        return
    try:
        import json
        with open(TEMP_DATA_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict) and "channels" in data:
            temp_channels    = {int(k): v for k, v in data.get("channels", {}).items()}
            channel_settings = {int(k): v for k, v in data.get("settings", {}).items()}
            print(f"[DB] Loaded {len(temp_channels)} temp channels and {len(channel_settings)} settings.")
        else:
            # Old format migration
            temp_channels    = {int(k): v for k, v in data.items()}
            channel_settings = {}
            print(f"[DB] Loaded {len(temp_channels)} temp channels (old format). Upgrading...")
            save_temp_channels()
    except Exception as e:
        print(f"[DB] Error loading temp channels: {e}")
        temp_channels    = {}
        channel_settings = {}


# ─── Name cache ───────────────────────────────────────────────────────────────
def cache_member_name(member) -> None:
    """Update user_names dict if the member's display data has changed."""
    uid  = str(member.id)
    name = member.display_name
    tag  = member.name
    avt  = str(member.display_avatar.url) if member.display_avatar else ""
    old  = user_names.get(uid, {})
    if old.get("display_name") != name or old.get("username") != tag:
        user_names[uid] = {"display_name": name, "username": tag, "avatar": avt}
        save_user_names()
        if uid in user_stats:
            user_stats[uid]["display_name"] = name
            save_user_stats()
