"""
config.py
---------
All configuration constants, safe-load / atomic-save primitives,
and the one-time migration that moves old root-level JSON files
into the Data/ sub-directory.

Every other module should import from here — NEVER hardcode paths
or constant values elsewhere.
"""

import os
import json
import copy

# ─── Token ───────────────────────────────────────────────────────────────────
TOKEN = ""

# ─── Directory layout ─────────────────────────────────────────────────────────
# bot/ is one level below the project root, so we go up one directory.
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir   = os.path.join(script_dir, "Data")
os.makedirs(data_dir, exist_ok=True)

# ─── One-time migration: move old root-level files into Data/ ─────────────────
for _fn in [
    "config.json", "level_requirements.json", "user_stats.json",
    "temp_channels.json", "config.json.example", "warnings.json",
    "mod_log.json", "automod_config.json", "economy.json", "shop.json",
    "tickets.json", "reaction_roles.json", "reminders.json", "analytics.json",
]:
    _old = os.path.join(script_dir, _fn)
    _new = os.path.join(data_dir, _fn)
    if os.path.exists(_old) and not os.path.exists(_new):
        os.rename(_old, _new)
        print(f"[DB] Migrated {_fn} → Data/")


# ─── Atomic write ────────────────────────────────────────────────────────────
def _atomic_save(path: str, data) -> None:
    """Write data as JSON via a .tmp file; crash-safe."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[DB] Save error {os.path.basename(path)}: {e}")
        try:
            os.remove(tmp)
        except Exception:
            pass


# ─── Safe loader ─────────────────────────────────────────────────────────────
def _safe_load(path: str, default):
    """Return parsed JSON or a deep-copy of *default* on error / missing file."""
    if not os.path.exists(path):
        return copy.deepcopy(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        print(f"[DB] Corrupt/unreadable {os.path.basename(path)}, using defaults.")
        return copy.deepcopy(default)


# ─── Config bootstrap ────────────────────────────────────────────────────────
_CONFIG_PATH = os.path.join(data_dir, "config.json")
_CONFIG_DEFAULTS = {
    "creator_channel_id":        0,
    "temp_channel_category_id":  0,
    "xp_multiplier":             1.0,
    "weekend_multiplier":        2.0,
    "special_event_multiplier":  3.0,
    "event_active":              False,
    "levelup_channel_id":        0,
    "levelup_message":           "🎉 {mention} reached Level {level}!",
    "milestone_levels":          [100, 200, 500],
    "mod_log_webhook_url":       "",
    "mod_role_id":               0,
    "ticket_category_id":        0,
    "ticket_log_channel_id":     0,
    "ticket_panel_channel_id":   0,
    "ticket_panel_message_id":   0,
    "welcome_channel_id":        0,
    "leave_channel_id":          0,
    "welcome_message":           "Welcome {mention} to {server}! You are member #{count}.",
    "leave_message":             "{name} has left the server.",
    "auto_roles":                [],
    "dashboard_enabled":         True,
    "dashboard_secret":          "changeme123",
    "dashboard_port":            8080,
}

if not os.path.exists(_CONFIG_PATH):
    _atomic_save(_CONFIG_PATH, _CONFIG_DEFAULTS)
    print("[DB] Created Data/config.json with defaults — fill in your IDs and restart.")

config = _safe_load(_CONFIG_PATH, _CONFIG_DEFAULTS)
for _k, _v in _CONFIG_DEFAULTS.items():       # back-fill any new keys
    config.setdefault(_k, _v)

# ─── Expose every config key as a module-level constant ──────────────────────
CREATOR_CHANNEL_ID       = config["creator_channel_id"]
TEMP_CHANNEL_CATEGORY_ID = config["temp_channel_category_id"]
XP_MULTIPLIER            = config.get("xp_multiplier",           1.0)
WEEKEND_MULTIPLIER       = config.get("weekend_multiplier",       2.0)
SPECIAL_EVENT_MULTIPLIER = config.get("special_event_multiplier", 3.0)
EVENT_ACTIVE             = config.get("event_active",             False)
LEVELUP_CHANNEL_ID       = config.get("levelup_channel_id",      0)
LEVELUP_MESSAGE          = config.get("levelup_message",         "🎉 {mention} reached Level {level}!")
MILESTONE_LEVELS         = config.get("milestone_levels",         [100, 200, 500])
MOD_LOG_WEBHOOK_URL      = config.get("mod_log_webhook_url",      "")
MOD_ROLE_ID              = config.get("mod_role_id",              0)
TICKET_CATEGORY_ID       = config.get("ticket_category_id",       0)
TICKET_LOG_CHANNEL_ID    = config.get("ticket_log_channel_id",    0)
TICKET_PANEL_CHANNEL_ID  = config.get("ticket_panel_channel_id",  0)
TICKET_PANEL_MESSAGE_ID  = config.get("ticket_panel_message_id",  0)
WELCOME_CHANNEL_ID       = config.get("welcome_channel_id",       0)
LEAVE_CHANNEL_ID         = config.get("leave_channel_id",         0)
WELCOME_MESSAGE          = config.get("welcome_message",          "Welcome {mention} to {server}! You are member #{count}.")
LEAVE_MESSAGE            = config.get("leave_message",            "{name} has left the server.")
AUTO_ROLES               = config.get("auto_roles",               [])
DASHBOARD_ENABLED        = config.get("dashboard_enabled",        True)
DASHBOARD_SECRET         = config.get("dashboard_secret",         "changeme123")
DASHBOARD_PORT           = int(config.get("dashboard_port",       8080))

# ─── Hardcoded operational constants ─────────────────────────────────────────
MUTE_TIMEOUT_CHANNEL_ID = 1348785950100291658
MUTE_TIMEOUT_DURATION   = 1200   # 20 minutes in seconds

if CREATOR_CHANNEL_ID == 0 or TEMP_CHANNEL_CATEGORY_ID == 0:
    print(
        "[DB] WARNING: creator_channel_id / temp_channel_category_id are 0. "
        "Temp-channel feature disabled until set in config.json."
    )


# ─── Runtime config save (for persisting auto-generated values) ───────────────
def save_config() -> None:
    """Persist the current in-memory *config* dict back to Data/config.json atomically."""
    _atomic_save(_CONFIG_PATH, config)
