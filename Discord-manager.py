import discord
import os
import json
import asyncio
import re
import random
import aiohttp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from datetime import datetime, timedelta
from enum import IntEnum
from PIL import Image, ImageFont, ImageDraw
from easy_pil import Editor, load_image_async, Font, Canvas

# --- CONFIGURATION ---
TOKEN = ""  # <-- Put your Discord bot token here
# ---------------------

# ─────────────────────────────────────────────────────────────────────────────
# DIRECTORY & DATA-FILE BOOTSTRAP
# Every JSON file is created with safe defaults if it does not exist.
# All writes use _atomic_save() so a crash never corrupts a file.
# ─────────────────────────────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir   = os.path.join(script_dir, 'Data')
os.makedirs(data_dir, exist_ok=True)

# One-time migration: move old root-level files into Data/
for _fn in ['config.json','level_requirements.json','user_stats.json','temp_channels.json',
            'config.json.example','warnings.json','mod_log.json','automod_config.json',
            'economy.json','shop.json','tickets.json','reaction_roles.json',
            'reminders.json','analytics.json']:
    _old, _new = os.path.join(script_dir, _fn), os.path.join(data_dir, _fn)
    if os.path.exists(_old) and not os.path.exists(_new):
        os.rename(_old, _new)
        print(f"[DB] Migrated {_fn} → Data/")

# ── Atomic write (write .tmp then rename → crash-safe) ──────────────────────
def _atomic_save(path, data):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[DB] Save error {os.path.basename(path)}: {e}")
        try: os.remove(tmp)
        except: pass

# ── Safe loader (returns default on missing/corrupt file) ───────────────────
def _safe_load(path, default):
    import copy
    if not os.path.exists(path):
        return copy.deepcopy(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        print(f"[DB] Corrupt/unreadable {os.path.basename(path)}, using defaults.")
        return copy.deepcopy(default)

# ── Config ───────────────────────────────────────────────────────────────────
_CONFIG_PATH = os.path.join(data_dir, 'config.json')
_CONFIG_DEFAULTS = {
    "creator_channel_id": 0, "temp_channel_category_id": 0,
    "xp_multiplier": 1.0, "weekend_multiplier": 2.0,
    "special_event_multiplier": 3.0, "event_active": False,
    "levelup_channel_id": 0,
    "levelup_message": "🎉 {mention} reached Level {level}!",
    "milestone_levels": [100, 200, 500], "mod_log_webhook_url": "",
    "mod_role_id": 0, "ticket_category_id": 0, "ticket_log_channel_id": 0,
    "welcome_channel_id": 0, "leave_channel_id": 0,
    "welcome_message": "Welcome {mention} to {server}! You are member #{count}.",
    "leave_message": "{name} has left the server.", "auto_roles": [],
    "dashboard_enabled": True, "dashboard_secret": "changeme123", "dashboard_port": 8080
}
if not os.path.exists(_CONFIG_PATH):
    _atomic_save(_CONFIG_PATH, _CONFIG_DEFAULTS)
    print("[DB] Created Data/config.json with defaults — fill in your IDs and restart.")

config = _safe_load(_CONFIG_PATH, _CONFIG_DEFAULTS)
for _k, _v in _CONFIG_DEFAULTS.items():   # back-fill any new keys
    config.setdefault(_k, _v)

CREATOR_CHANNEL_ID       = config['creator_channel_id']
TEMP_CHANNEL_CATEGORY_ID = config['temp_channel_category_id']
XP_MULTIPLIER            = config.get('xp_multiplier', 1.0)
WEEKEND_MULTIPLIER       = config.get('weekend_multiplier', 2.0)
SPECIAL_EVENT_MULTIPLIER = config.get('special_event_multiplier', 3.0)
EVENT_ACTIVE             = config.get('event_active', False)
LEVELUP_CHANNEL_ID       = config.get('levelup_channel_id', 0)
LEVELUP_MESSAGE          = config.get('levelup_message', "🎉 {mention} reached Level {level}!")
MILESTONE_LEVELS         = config.get('milestone_levels', [100, 200, 500])
MOD_LOG_WEBHOOK_URL      = config.get('mod_log_webhook_url', "")
MOD_ROLE_ID              = config.get('mod_role_id', 0)
TICKET_CATEGORY_ID       = config.get('ticket_category_id', 0)
TICKET_LOG_CHANNEL_ID    = config.get('ticket_log_channel_id', 0)
WELCOME_CHANNEL_ID       = config.get('welcome_channel_id', 0)
LEAVE_CHANNEL_ID         = config.get('leave_channel_id', 0)
WELCOME_MESSAGE          = config.get('welcome_message', "Welcome {mention} to {server}! You are member #{count}.")
LEAVE_MESSAGE            = config.get('leave_message', "{name} has left the server.")
AUTO_ROLES               = config.get('auto_roles', [])
DASHBOARD_ENABLED        = config.get('dashboard_enabled', True)
DASHBOARD_SECRET         = config.get('dashboard_secret', 'changeme123')
DASHBOARD_PORT           = int(config.get('dashboard_port', 8080))

if CREATOR_CHANNEL_ID == 0 or TEMP_CHANNEL_CATEGORY_ID == 0:
    print("[DB] WARNING: creator_channel_id / temp_channel_category_id are 0. "
          "Temp-channel feature disabled until set in config.json.")

# Channel ID for muted users
MUTE_TIMEOUT_CHANNEL_ID = 1348785950100291658
MUTE_TIMEOUT_DURATION = 1200  # 20 minutes in seconds

# --- LEVEL SYSTEM HELPERS ---
def get_active_multiplier(user_id=None):
    """Returns the active XP multiplier based on config events or weekend, plus personal boosters."""
    base = XP_MULTIPLIER
    if EVENT_ACTIVE:
        base = SPECIAL_EVENT_MULTIPLIER
    elif datetime.now().weekday() >= 5: # Saturday = 5, Sunday = 6
        base = WEEKEND_MULTIPLIER
        
    if user_id and economy_data.get(user_id, {}).get('xp_boost_active_until'):
        boost_expiry = datetime.fromisoformat(economy_data[user_id]['xp_boost_active_until'])
        if datetime.now() < boost_expiry:
            base *= 2.0  # Double XP from shop item
            
    return base

# A dictionary to keep track of temporary channels and their owners
temp_channels = {}

# A dictionary to track muted users and their mute start time
muted_users = {}



# Channel whitelists and blacklists (Channel ID -> List of User IDs)
channel_whitelists = {}
channel_blacklists = {}

# Channel settings (Channel ID -> Settings Dict)
channel_settings = {}

# Scheduled deletions (Channel ID -> Deletion Time)
scheduled_deletions = {}

# Auto-delete timers (Channel ID -> Last Activity Time)
channel_last_activity = {}

# Persistence File Path
TEMP_DATA_FILE = os.path.join(data_dir, 'temp_channels.json')

# --- LEVEL SYSTEM DATA ---
level_requirements = {}
user_stats = {}
user_streaks = {}
warnings_data = {}
mod_log = []
automod_config = {}
economy_data = {}
shop_items = {}
tickets_data = {}
reaction_roles = {}
reminders_list = []
analytics_data = {}
command_cooldowns = {}

ALIASES = {
    "rank": ["rank", "stats", "level", "xp"],
    "daily": ["daily", "claim"],
    "weekly": ["weekly"],
    "balance": ["balance", "bal", "coins", "wallet"],
    "shop": ["shop", "store"],
    "buy": ["buy", "purchase"]
}

class PermLevel(IntEnum):
    MEMBER = 0
    MODERATOR = 1
    ADMIN = 2
    OWNER = 3

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE FILE PATHS
# ─────────────────────────────────────────────────────────────────────────────
REQUIREMENTS_FILE    = os.path.join(data_dir, 'level_requirements.json')
USER_STATS_FILE      = os.path.join(data_dir, 'user_stats.json')
USER_STREAKS_FILE    = os.path.join(data_dir, 'streaks.json')
WARNINGS_FILE        = os.path.join(data_dir, 'warnings.json')
MOD_LOG_FILE         = os.path.join(data_dir, 'mod_log.json')
AUTOMOD_FILE         = os.path.join(data_dir, 'automod_config.json')
ECONOMY_FILE         = os.path.join(data_dir, 'economy.json')
SHOP_FILE            = os.path.join(data_dir, 'shop.json')
TICKETS_FILE         = os.path.join(data_dir, 'tickets.json')
REACTION_ROLES_FILE  = os.path.join(data_dir, 'reaction_roles.json')
REMINDERS_FILE       = os.path.join(data_dir, 'reminders.json')
ANALYTICS_FILE       = os.path.join(data_dir, 'analytics.json')
USER_NAMES_FILE      = os.path.join(data_dir, 'user_names.json')
LEADERBOARD_FILE     = os.path.join(data_dir, 'leaderboard.json')

# In-memory mirrors of every DB file
level_requirements = {}
user_stats         = {}
user_streaks       = {}
warnings_data      = {}
mod_log            = []
automod_config     = {}
economy_data       = {}
shop_items         = []
tickets_data       = {}
reaction_roles     = {}
reminders_list     = []
analytics_data     = {}
user_names         = {}   # uid → {"display_name", "username", "avatar"}
command_cooldowns  = {}

# ─────────────────────────────────────────────────────────────────────────────
# ENSURE ALL DB FILES EXIST WITH SAFE DEFAULTS
# Called once at startup before any other data access.
# ─────────────────────────────────────────────────────────────────────────────
def _make_default_levels():
    """Build a 200-level requirements table as the default."""
    out = {}
    for i in range(201):
        out[str(i)] = {
            "type": "hybrid",
            "voice_minutes_required": i * 60,
            "text_minutes_required": i * 10,
            "role_id": 0
        }
    return out

_DB_DEFAULTS = {
    REQUIREMENTS_FILE:   None,          # handled separately below
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
}

def ensure_db_files():
    """Create any missing DB file with its default value, then load all data."""
    global level_requirements, user_stats, user_streaks, warnings_data, mod_log
    global automod_config, economy_data, shop_items, tickets_data, reaction_roles
    global reminders_list, analytics_data, user_names

    # Level requirements get a special default (200-level table)
    if not os.path.exists(REQUIREMENTS_FILE):
        _atomic_save(REQUIREMENTS_FILE, _make_default_levels())
        print("[DB] Created level_requirements.json with 200 default levels.")

    for path, default in _DB_DEFAULTS.items():
        if default is None:
            continue          # already handled above
        if not os.path.exists(path):
            _atomic_save(path, default)
            print(f"[DB] Created {os.path.basename(path)}")

    # Now load everything
    level_requirements = _safe_load(REQUIREMENTS_FILE, _make_default_levels())
    user_stats         = _safe_load(USER_STATS_FILE,    {})
    user_streaks       = _safe_load(USER_STREAKS_FILE,  {})
    warnings_data      = _safe_load(WARNINGS_FILE,      {})
    mod_log            = _safe_load(MOD_LOG_FILE,        [])
    automod_config     = _safe_load(AUTOMOD_FILE,        {"mention_limit": 5, "message_cooldown_seconds": 2, "allowed_domains": []})
    economy_data       = _safe_load(ECONOMY_FILE,        {})
    shop_items         = _safe_load(SHOP_FILE,           [])
    tickets_data       = _safe_load(TICKETS_FILE,        {})
    reaction_roles     = _safe_load(REACTION_ROLES_FILE, {})
    reminders_list     = _safe_load(REMINDERS_FILE,      [])
    analytics_data     = _safe_load(ANALYTICS_FILE,      {})
    user_names         = _safe_load(USER_NAMES_FILE,     {})
    # Validate types (guard against manual edits corrupting the file)
    if not isinstance(mod_log,        list): mod_log        = []
    if not isinstance(shop_items,     list): shop_items     = []
    if not isinstance(reminders_list, list): reminders_list = []
    if not isinstance(user_stats,     dict): user_stats     = {}
    if not isinstance(economy_data,   dict): economy_data   = {}
    if not isinstance(warnings_data,  dict): warnings_data  = {}
    if not isinstance(user_names,     dict): user_names     = {}
    print(f"[DB] Loaded: {len(user_stats)} users, {len(economy_data)} economy entries, "
          f"{len(warnings_data)} warned users, {len(user_names)} cached names.")

# Run immediately so the bot never starts with missing files
ensure_db_files()

# ─────────────────────────────────────────────────────────────────────────────
# ATOMIC SAVE WRAPPERS  (used everywhere the bot writes data)
# ─────────────────────────────────────────────────────────────────────────────
def save_user_stats():    _atomic_save(USER_STATS_FILE,      user_stats)
def save_user_streaks():  _atomic_save(USER_STREAKS_FILE,    user_streaks)
def save_warnings():      _atomic_save(WARNINGS_FILE,        warnings_data)
def save_mod_log():       _atomic_save(MOD_LOG_FILE,         mod_log)
def save_economy():       _atomic_save(ECONOMY_FILE,         economy_data)
def save_tickets():       _atomic_save(TICKETS_FILE,         tickets_data)
def save_reaction_roles():_atomic_save(REACTION_ROLES_FILE,  reaction_roles)
def save_reminders():     _atomic_save(REMINDERS_FILE,       reminders_list)
def save_analytics():     _atomic_save(ANALYTICS_FILE,       analytics_data)
def save_user_names():    _atomic_save(USER_NAMES_FILE,      user_names)
def save_shop():          _atomic_save(SHOP_FILE,            shop_items)

# ─────────────────────────────────────────────────────────────────────────────
# USER-NAME CACHE  (keeps Data/user_names.json up-to-date)
# ─────────────────────────────────────────────────────────────────────────────
def cache_member_name(member):
    """Update the name cache for a member if anything has changed."""
    uid  = str(member.id)
    name = member.display_name
    tag  = member.name
    avt  = str(member.display_avatar.url) if member.display_avatar else ""
    old  = user_names.get(uid, {})
    if old.get("display_name") != name or old.get("username") != tag:
        user_names[uid] = {"display_name": name, "username": tag, "avatar": avt}
        save_user_names()

# --- COMMAND FRAMEWORK HELPERS ---
def check_cooldown(user_id, command, seconds) -> float:
    """Returns remaining seconds if on cooldown, 0 if OK."""
    key = (user_id, command)
    last = command_cooldowns.get(key)
    if last:
        elapsed = (datetime.now() - last).total_seconds()
        if elapsed < seconds:
            return seconds - elapsed
    command_cooldowns[key] = datetime.now()
    return 0
    
def get_perm_level(member):
    if member.id == member.guild.owner_id:
        return PermLevel.OWNER
    if member.guild_permissions.administrator:
        return PermLevel.ADMIN
    if MOD_ROLE_ID:
        mod_role_id = int(MOD_ROLE_ID)
        for r in member.roles:
            if r.id == mod_role_id:
                return PermLevel.MODERATOR
    return PermLevel.MEMBER

def log_command(command_name):
    hour_key = datetime.now().strftime("%Y-%m-%d %H")
    if command_name not in analytics_data:
        analytics_data[command_name] = {"total": 0, "hourly": {}}
    analytics_data[command_name]["total"] += 1
    analytics_data[command_name]["hourly"][hour_key] = analytics_data[command_name]["hourly"].get(hour_key, 0) + 1
    save_analytics()

# --- ECONOMY SYSTEM HELPERS ---
def get_economy(user_id):
    user_id = str(user_id)
    if user_id not in economy_data:
        economy_data[user_id] = {
            "coins": 0,
            "total_earned": 0,
            "last_daily": None,
            "last_weekly": None
        }
    return economy_data[user_id]

def add_coins(user_id, amount):
    if amount <= 0: return
    econ = get_economy(user_id)
    econ["coins"] += amount
    econ["total_earned"] += amount
    save_economy()

def remove_coins(user_id, amount):
    if amount <= 0: return False
    econ = get_economy(user_id)
    if econ["coins"] >= amount:
        econ["coins"] -= amount
        save_economy()
        return True
    return False

# --- MODERATION HELPERS ---
async def log_mod_action(action: str, target: discord.Member, mod: discord.Member, reason: str):
    """Logs action to JSON and sends a webhook if configured."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "target_id": str(target.id),
        "target_name": target.display_name,
        "mod_id": str(mod.id),
        "mod_name": mod.display_name,
        "reason": reason
    }
    mod_log.append(entry)
    save_mod_log()
    
    if MOD_LOG_WEBHOOK_URL:
        try:
            embed = {
                "title": f"🛠️ Moderation Action: {action.title()}",
                "color": 16711680 if action in ["ban", "kick"] else 16753920,
                "fields": [
                    {"name": "Target", "value": f"{target.mention} ({target.id})", "inline": True},
                    {"name": "Moderator", "value": f"{mod.mention}", "inline": True},
                    {"name": "Reason", "value": reason, "inline": False}
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            async with aiohttp.ClientSession() as session:
                payload = {'embeds': [embed]}
                await session.post(MOD_LOG_WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Failed to push to Mod Log Webhook: {e}")

# --- TICKET SYSTEM (BUTTON VIEW) ---
class TicketCloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Prevent double clicks
        if interaction.channel.id in [data.get('channel_id') for data in tickets_data.values()]:
            guild = interaction.guild
            ticket_id = next((tid for tid, data in tickets_data.items() if data['channel_id'] == interaction.channel.id), None)
            
            if ticket_id:
                ticket_info = tickets_data[ticket_id]
                ticket_info["status"] = "closed"
                save_tickets()
                
                # Log the closure
                if TICKET_LOG_CHANNEL_ID:
                    log_channel = guild.get_channel(int(TICKET_LOG_CHANNEL_ID))
                    if log_channel:
                        opener = guild.get_member(ticket_info['opener_id'])
                        log_embed = discord.Embed(title=f"Ticket Closed: {interaction.channel.name}", color=discord.Color.red())
                        log_embed.add_field(name="Opened By", value=f"{opener.mention if opener else 'Unknown User'}", inline=True)
                        log_embed.add_field(name="Closed By", value=f"{interaction.user.mention}", inline=True)
                        log_embed.add_field(name="Ticket ID", value=ticket_id, inline=True)
                        await log_channel.send(embed=log_embed)
                
                await interaction.response.send_message("Closing ticket in 5 seconds...", ephemeral=False)
                await asyncio.sleep(5)
                await interaction.channel.delete(reason=f"Ticket {ticket_id} closed by {interaction.user.display_name}")
            else:
                 await interaction.response.send_message("Ticket data not found.", ephemeral=True)
        else:
            await interaction.response.send_message("This isn't a valid ticket channel. I can't close it.", ephemeral=True)

# --- WARNING SYSTEM HELPERS ---
async def warn_user(member: discord.Member, reason: str, mod: discord.Member):
    """Warns a user and handles automated timeout escalations based on total warns."""
    uid = str(member.id)
    if uid not in warnings_data:
        warnings_data[uid] = []
        
    warnings_data[uid].append({
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "mod_id": str(mod.id)
    })
    save_warnings()
    
    total_warns = len(warnings_data[uid])
    await log_mod_action("warn", member, mod, f"Warn #{total_warns}: {reason}")
    
    # Notify User via DM
    try:
        await member.send(f"⚠️ You have been warned in **{member.guild.name}**.\n**Reason:** {reason}\n*You now have {total_warns} warning(s).*")
    except:
        pass
        
    # Escalation Logic
    try:
        if total_warns >= 7:
            await member.ban(reason="Automod: Reached 7 warnings")
            await log_mod_action("ban", member, mod, "Automod Escalation (7 Warns)")
        elif total_warns >= 5:
            timeout_until = discord.utils.utcnow() + timedelta(hours=1)
            await member.timeout(timeout_until, reason="Automod: Reached 5 warnings")
            await log_mod_action("timeout", member, mod, "Automod Escalation (5 Warns - 1 Hour)")
        elif total_warns >= 3:
            timeout_until = discord.utils.utcnow() + timedelta(minutes=10)
            await member.timeout(timeout_until, reason="Automod: Reached 3 warnings")
            await log_mod_action("timeout", member, mod, "Automod Escalation (3 Warns - 10 Minutes)")
    except discord.Forbidden:
        print(f"Bot lacks permissions to escalate punishment for {member.display_name}")

def get_user_stats(user_id):
    user_id = str(user_id)
    if user_id not in user_stats:
        user_stats[user_id] = {
            "voice_minutes": 0,
            "text_minutes": 0,
            "total_messages": 0,
            "weekly_voice": 0,
            "weekly_text": 0,
            "monthly_voice": 0,
            "monthly_text": 0,
            "last_message_minute": None,
            "current_level": -1   # -1 = never assigned; tracks last announced level
        }
    # Back-fill fields missing from older saved data
    s = user_stats[user_id]
    if "total_messages" not in s: s["total_messages"] = 0
    if "weekly_voice" not in s:
        s.update({"weekly_voice": 0, "weekly_text": 0,
                  "monthly_voice": 0, "monthly_text": 0})
    if "current_level" not in s: s["current_level"] = -1
    return s

def update_streak(user_id):
    """Updates user streak and returns the streak multiplier."""
    user_id = str(user_id)
    today = datetime.now().date()
    today_str = str(today)
    
    if user_id not in user_streaks:
        user_streaks[user_id] = {"last_active_date": today_str, "streak": 1}
        save_user_streaks()
        return 1.0
        
    streak_data = user_streaks[user_id]
    last_active_str = streak_data.get("last_active_date")
    streak_count = streak_data.get("streak", 1)
    
    if last_active_str == today_str:
        # Already active today, return current multiplier
        pass
    else:
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d").date()
            if (today - last_active).days == 1:
                streak_count += 1
            else:
                streak_count = 1
        except Exception:
            streak_count = 1
            
        user_streaks[user_id] = {"last_active_date": today_str, "streak": streak_count}
        save_user_streaks()

    # Calculate streak multiplier
    if streak_count >= 30: return 2.0
    if streak_count >= 14: return 1.5
    if streak_count >= 7: return 1.25
    return 1.0

def get_level_data(current_val, type_key):
    current_level = 0
    next_req = float('inf')
    for level in range(200):
        lvl_str = str(level)
        next_lvl_str = str(level + 1)
        if next_lvl_str not in level_requirements:
            break
        req = level_requirements[next_lvl_str].get(type_key, 0)
        if current_val >= req:
            current_level = level + 1
        else:
            next_req = req
            break
    return current_level, next_req

async def check_level_up(member: discord.Member):
    user_id = str(member.id)
    stats = get_user_stats(user_id)
    current_voice = stats.get("voice_minutes", 0)
    current_text  = stats.get("text_minutes", 0)
    prev_level    = stats.get("current_level", -1)

    # ── Calculate the highest level the user qualifies for ──────────────────
    # We iterate sorted numerically so we stop at the first level they can't
    # reach — no need to scan all 200 levels every time.
    real_eligible_level = -1
    for lvl_str in sorted(level_requirements.keys(), key=lambda x: int(x) if x.isdigit() else -1):
        if not lvl_str.isdigit():
            continue
        reqs = level_requirements[lvl_str]
        v_req = reqs.get("voice_minutes_required", 0)
        t_req = reqs.get("text_minutes_required", 0)
        if current_voice >= v_req and current_text >= t_req:
            real_eligible_level = int(lvl_str)
        else:
            break   # levels are ordered; once we fail one we won't pass higher

    # Nothing to do — user hasn't earned even level 0 yet (shouldn't happen
    # since level 0 requires 0/0, but guard anyway)
    if real_eligible_level < 0:
        return

    # Always silently ensure the user has the correct role, but only
    # ANNOUNCE the level-up when the level actually increased.
    is_new_level = real_eligible_level > prev_level

    # Update stored level immediately so we never double-announce
    stats["current_level"] = real_eligible_level

    # ── Find / create the role for this level ────────────────────────────────
    req = level_requirements.get(str(real_eligible_level))
    if not req:
        return

    role_id = req.get("role_id")
    role = None
    if role_id and role_id != 0:
        role = member.guild.get_role(int(role_id))

    if not role:
        role_name = f"Level {real_eligible_level}"
        role = discord.utils.get(member.guild.roles, name=role_name)
        if not role:
            try:
                role = await member.guild.create_role(
                    name=role_name, color=discord.Color.gold(),
                    reason="Level System Auto-Creation"
                )
                print(f"[Levels] Created role '{role_name}' (ID: {role.id})")
            except discord.Forbidden:
                print(f"[Levels] No permission to create role '{role_name}'")
            except Exception as e:
                print(f"[Levels] Error creating role '{role_name}': {e}")
        if role:
            level_requirements[str(real_eligible_level)]["role_id"] = role.id
            _atomic_save(REQUIREMENTS_FILE, level_requirements)

    if role and role not in member.roles:
        try:
            # ── Tier logic (only when actually levelling up) ────────────────
            if is_new_level:
                tier_name = req.get("tier")
                if tier_name:
                    tier_role = discord.utils.get(member.guild.roles, name=tier_name.title())
                    if not tier_role:
                        try:
                            tier_role = await member.guild.create_role(
                                name=tier_name.title(), reason="Tier System Auto-Creation"
                            )
                        except discord.Forbidden:
                            tier_role = None
                    if tier_role and tier_role not in member.roles:
                        all_tiers = {r_data.get("tier").title()
                                     for r_data in level_requirements.values()
                                     if isinstance(r_data, dict) and r_data.get("tier")}
                        old_tier_roles = [r for r in member.roles
                                          if r.name in all_tiers and r.name != tier_name.title()]
                        if old_tier_roles:
                            await member.remove_roles(*old_tier_roles)
                        await member.add_roles(tier_role)

            await member.add_roles(role)
            print(f"[Levels] {member.display_name} → Level {real_eligible_level}"
                  + (" (NEW)" if is_new_level else " (role restored)"))
            save_user_stats()

            # ── Announce only on genuine level-up ───────────────────────────
            if is_new_level and LEVELUP_CHANNEL_ID and LEVELUP_CHANNEL_ID != 0:
                levelup_channel = member.guild.get_channel(int(LEVELUP_CHANNEL_ID))
                if levelup_channel:
                    embed = discord.Embed(
                        title="🎉 Level Up!",
                        description=LEVELUP_MESSAGE.format(
                            mention=member.mention, level=real_eligible_level
                        ),
                        color=discord.Color.gold()
                    )
                    if member.display_avatar:
                        embed.set_thumbnail(url=member.display_avatar.url)
                    if real_eligible_level in MILESTONE_LEVELS:
                        embed.add_field(
                            name="🏆 MEGA MILESTONE REACHED!",
                            value=(f"Congratulations on reaching **Level {real_eligible_level}**!"
                                   f" You've been awarded **50 Coins**! 🪙"),
                            inline=False
                        )
                        embed.color = discord.Color.purple()
                        add_coins(member.id, 50)
                    await levelup_channel.send(embed=embed)

        except discord.Forbidden:
            print(f"[Levels] No permission to assign '{role.name}' to {member.display_name}")

# --- TEMP CHANNELS PERSISTENCE ---
def save_temp_channels():
    str_temp_channels = {str(k): v for k, v in temp_channels.items()}
    str_settings = {str(k): v for k, v in channel_settings.items()}
    
    data_to_save = {
        "channels": str_temp_channels,
        "settings": str_settings
    }
    with open(TEMP_DATA_FILE, 'w') as f:
        json.dump(data_to_save, f, indent=4)

def load_temp_channels():
    """Loads temporary channels and settings from the JSON file."""
    global temp_channels, channel_settings
    if os.path.exists(TEMP_DATA_FILE):
        try:
            with open(TEMP_DATA_FILE, 'r') as f:
                data = json.load(f)
                # Check if it's the old format (just direct dict) or new format
                if isinstance(data, dict) and "channels" in data:
                    # New format
                    channels_data = data.get("channels", {})
                    settings_data = data.get("settings", {})
                    
                    temp_channels = {int(k): v for k, v in channels_data.items()}
                    channel_settings = {int(k): v for k, v in settings_data.items()}
                    print(f"Loaded {len(temp_channels)} temporary channels and {len(channel_settings)} channel settings from storage (new format).")
                else:
                    # Old format migration
                    temp_channels = {int(k): v for k, v in data.items()}
                    channel_settings = {} # Initialize empty for old format
                    print(f"Loaded {len(temp_channels)} temporary channels from storage (old format). Migrating...")
                    save_temp_channels() # Upgrade file format
        except json.JSONDecodeError:
            print(f"Error: TEMP_DATA_FILE is corrupted or empty. Initializing empty data.")
            temp_channels = {}
            channel_settings = {}
        except Exception as e:
            print(f"Error loading temp channels: {e}")
            temp_channels = {}
            channel_settings = {}
    else:
        temp_channels = {}

def save_temp_channels():
    """Saves temporary channels and their settings to disk atomically."""
    try:
        data_to_save = {
            "channels": {str(k): v for k, v in temp_channels.items()},
            "settings":  {str(k): v for k, v in channel_settings.items()}
        }
        _atomic_save(TEMP_DATA_FILE, data_to_save)
    except Exception as e:
        print(f"[DB] Error saving temp channels: {e}")

# temp channels are loaded in on_ready after the client is fully initialised

# --- Bot Setup ---
intents = discord.Intents.default()
intents.voice_states = True # Required to track voice channel joins/leaves
intents.message_content = True  # Required to read message content
intents.messages = True      # Required to read messages for commands
intents.guilds = True
intents.members = True       # Required to get member objects reliably

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketCloseButton())
        await self.tree.sync()
        client.loop.create_task(track_voice_minutes())
        client.loop.create_task(check_muted_users())
        client.loop.create_task(leaderboard_reset_task())
        client.loop.create_task(check_reminders())

client = MyClient(intents=intents)

# --- SLASH COMMANDS ---
ticket_group = discord.app_commands.Group(name="ticket", description="Ticket system commands")

@ticket_group.command(name="open", description="Open a new support ticket")
async def ticket_open(interaction: discord.Interaction):
    if not TICKET_CATEGORY_ID:
        await interaction.response.send_message("❌ Ticket system is not configured. (Missing category ID)", ephemeral=True)
        return
        
    guild = interaction.guild
    category = discord.utils.get(guild.categories, id=int(TICKET_CATEGORY_ID))
    
    if not category:
        await interaction.response.send_message("❌ Ticket category not found.", ephemeral=True)
        return
        
    # Check if user already has an open ticket
    for data in tickets_data.values():
        if data.get("opener_id") == interaction.user.id and data.get("status") == "open":
             await interaction.response.send_message("❌ You already have an open ticket.", ephemeral=True)
             return

    # Generate a unique Ticket ID
    ticket_id = f"ticket-{len(tickets_data) + 1:04d}"
    
    # Set up permissions (Only User + Mods/Admins can see)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    # Add Mod role if configured
    if MOD_ROLE_ID:
        mod_role = guild.get_role(int(MOD_ROLE_ID))
        if mod_role:
             overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    try:
        ticket_channel = await guild.create_text_channel(
            name=f"{interaction.user.name}-{ticket_id}",
            category=category,
            overwrites=overwrites
        )
        
        # Save to database
        tickets_data[ticket_id] = {
            "opener_id": interaction.user.id,
            "channel_id": ticket_channel.id,
            "status": "open",
            "opened_at": datetime.utcnow().isoformat()
        }
        save_tickets()
        
        # Send initial message with button
        embed = discord.Embed(
            title=f"🎫 {ticket_id}",
            description=f"Welcome {interaction.user.mention}! Please describe your issue. Support will be with you shortly.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(embed=embed, view=TicketCloseButton())
        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot lacks permission to create channels.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

@ticket_group.command(name="close", description="Close the current support ticket")
async def ticket_close(interaction: discord.Interaction):
    # Call the button's logic directly
    dummy_button = discord.ui.Button(custom_id="close_ticket_btn")
    view = TicketCloseButton()
    await view.close_ticket(interaction, dummy_button)

client.tree.add_command(ticket_group)

reactionrole_group = discord.app_commands.Group(name="reactionrole", description="Manage reaction roles")

@reactionrole_group.command(name="add", description="Add a reaction role to a message")
@discord.app_commands.describe(
    message_id="The ID of the message",
    emoji="The emoji to react with",
    role="The role to give"
)
@discord.app_commands.default_permissions(manage_roles=True)
async def reactionrole_add(interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
    try:
        # Validate message by trying to fetch it
        message = await interaction.channel.fetch_message(int(message_id))
        
        # Add reaction to message
        await message.add_reaction(emoji)
        
        # Save to database
        if message_id not in reaction_roles:
            reaction_roles[message_id] = {}
        reaction_roles[message_id][emoji] = role.id
        save_reaction_roles()
        
        await interaction.response.send_message(f"✅ Bound {role.mention} to {emoji} on message `{message_id}`.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ Message not found. Make sure you run this command in the same channel as the message.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to add reactions to that message.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

client.tree.add_command(reactionrole_group)

# --- GLOBAL SLASH COMMANDS ---

@client.tree.command(name="rank", description="Check your or another user's level and rank")
@discord.app_commands.describe(user="The user to check the rank of (optional)")
async def slash_rank(interaction: discord.Interaction, user: discord.Member = None):
    log_command("slash_rank")
    remaining = check_cooldown(interaction.user.id, "slash_rank", 3)
    if remaining > 0:
        await interaction.response.send_message(f"⏳ Please wait {int(remaining)}s before checking rank again.", ephemeral=True)
        return

    await interaction.response.defer()
    target_member = user if user else interaction.user
    t_stats = get_user_stats(target_member.id)
    
    msgs = t_stats.get('total_messages', 0)
    text_lvl, next_msg_req = get_level_data(msgs, "text_minutes_required")
    mins = t_stats.get('voice_minutes', 0)
    voice_lvl, next_voice_req = get_level_data(mins, "voice_minutes_required")

    prev_msg_req = level_requirements.get(str(text_lvl), {}).get("text_minutes_required", 0)
    if next_msg_req == float('inf'):
        text_percent = 100
        text_progress_str = f"{msgs} (MAX)"
    else:
        total_step = next_msg_req - prev_msg_req
        current_step = msgs - prev_msg_req
        text_percent = min(100, max(0, (current_step / total_step) * 100)) if total_step > 0 else 100
        text_progress_str = f"{msgs} / {int(next_msg_req)} Msgs"

    prev_voice_req = level_requirements.get(str(voice_lvl), {}).get("voice_minutes_required", 0)
    if next_voice_req == float('inf'):
        voice_percent = 100
        voice_progress_str = f"{mins}m (MAX)"
    else:
        total_step_v = next_voice_req - prev_voice_req
        current_step_v = mins - prev_voice_req
        voice_percent = min(100, max(0, (current_step_v / total_step_v) * 100)) if total_step_v > 0 else 100
        voice_progress_str = f"{mins} / {int(next_voice_req)} Mins"

    bg_path = os.path.join(script_dir, "PRO2.png")
    if not os.path.exists(bg_path):
        await interaction.followup.send("❌ Error: Background template not found!")
        return

    try:
        editor = Editor(bg_path)
        try:
            font_small = Font.poppins(size=18, variant="bold")
        except:
            font_small = Font.poppins(size=18)

        voice_y = 61
        editor.text((455, voice_y - 25), f"Voice Level: {voice_lvl}", font=font_small, color="#FFFFFF")
        editor.text((910, voice_y - 25), voice_progress_str, font=font_small, color="#FFFFFF", align="right")
        editor.bar((455, voice_y), max_width=458, height=27, percentage=voice_percent, fill="#F1C40F", radius=16)
        editor.text((684, voice_y + 4), f"{int(voice_percent)}%", font=font_small, color="#1A1A1A", align="center")

        text_y = 139
        editor.text((455, text_y - 25), f"Text Level: {text_lvl}", font=font_small, color="#FFFFFF")
        editor.text((910, text_y - 25), text_progress_str, font=font_small, color="#FFFFFF", align="right")
        editor.bar((455, text_y), max_width=458, height=27, percentage=text_percent, fill="#D4AF37", radius=16)
        editor.text((684, text_y + 4), f"{int(text_percent)}%", font=font_small, color="#1A1A1A", align="center")

        try:
            profile_image = await load_image_async(str(target_member.display_avatar.url))
            profile = Editor(profile_image).resize((200, 200)).circle_image()
            editor.paste(profile, (0, 70))
        except Exception as e:
            print(f"Error loading avatar: {e}")
        
        file = discord.File(fp=editor.image_bytes, filename="rank_card.png")
        await interaction.followup.send(file=file)
    except Exception as e:
        await interaction.followup.send(f"❌ Error generating rank card!")
        print(f"Error generating rank card: {e}")

@client.tree.command(name="daily", description="Claim your daily coin reward")
async def slash_daily(interaction: discord.Interaction):
    log_command("slash_daily")
    remaining = check_cooldown(interaction.user.id, "daily", 86400)
    if remaining > 0:
        hours = int(remaining) // 3600
        mins = (int(remaining) % 3600) // 60
        await interaction.response.send_message(f"⏳ You already claimed your daily reward! Come back in `{hours}h {mins}m`.", ephemeral=True)
        return

    econ = get_economy(interaction.user.id)
    add_coins(interaction.user.id, 100)
    econ["last_daily"] = datetime.now().isoformat()
    save_economy()
    await interaction.response.send_message("✅ Claimed **100 coins** as your daily reward! 🪙")

@client.tree.command(name="weekly", description="Claim your weekly coin reward")
async def slash_weekly(interaction: discord.Interaction):
    log_command("slash_weekly")
    remaining = check_cooldown(interaction.user.id, "weekly", 604800)
    if remaining > 0:
        days = int(remaining) // 86400
        hours = (int(remaining) % 86400) // 3600
        await interaction.response.send_message(f"⏳ You already claimed your weekly reward! Come back in `{days}d {hours}h`.", ephemeral=True)
        return

    econ = get_economy(interaction.user.id)
    add_coins(interaction.user.id, 500)
    econ["last_weekly"] = datetime.now().isoformat()
    save_economy()
    await interaction.response.send_message("✅ Claimed **500 coins** as your weekly reward! 💸")

@client.tree.command(name="balance", description="Check your or another user's coin balance")
@discord.app_commands.describe(user="The user to check the balance of (optional)")
async def slash_balance(interaction: discord.Interaction, user: discord.Member = None):
    log_command("slash_balance")
    target = user if user else interaction.user
    econ = get_economy(target.id)
    embed = discord.Embed(title=f"💳 {target.display_name}'s Wallet", color=discord.Color.gold())
    embed.add_field(name="🪙 Balance", value=f"**{econ['coins']}** coins", inline=True)
    embed.add_field(name="📈 Total Earned", value=f"**{econ['total_earned']}** coins", inline=True)
    if target.display_avatar:
        embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="richlist", description="View the top 10 richest users")
async def slash_richlist(interaction: discord.Interaction):
    log_command("slash_richlist")
    remaining = check_cooldown(interaction.user.id, "richlist", 10)
    if remaining > 0:
        await interaction.response.send_message(f"⏳ Please wait {int(remaining)}s before viewing the richlist again.", ephemeral=True)
        return
        
    sorted_users = sorted(economy_data.items(), key=lambda x: x[1].get('coins', 0), reverse=True)[:10]
    desc = ""
    for idx, (uid, data) in enumerate(sorted_users, 1):
        coins = data.get('coins', 0)
        desc += f"**{idx}.** <@{uid}> — **{coins}** 🪙\n"
    if not desc:
        desc = "No users have earned coins yet."
    embed = discord.Embed(title="💰 Top 10 Richest Users", description=desc, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="analytics", description="[Admin] View command usage analytics")
@discord.app_commands.default_permissions(administrator=True)
async def slash_analytics(interaction: discord.Interaction):
    log_command("slash_analytics")
    sorted_cmds = sorted(analytics_data.items(), key=lambda x: x[1].get('total', 0), reverse=True)[:15]
    desc = ""
    for idx, (cmd_name, data) in enumerate(sorted_cmds, 1):
        desc += f"**{idx}.** `/{cmd_name}` - **{data.get('total', 0)}** uses\n"
    if not desc:
        desc = "No command data available yet."
    embed = discord.Embed(title="📊 Command Usage Analytics", description=desc, color=discord.Color.purple())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@client.tree.command(name="coinflip", description="Bet coins on a coin flip")
@discord.app_commands.describe(bet="Amount of coins to bet", guess="Heads or Tails")
@discord.app_commands.choices(guess=[
    discord.app_commands.Choice(name="Heads", value="heads"),
    discord.app_commands.Choice(name="Tails", value="tails")
])
async def slash_coinflip(interaction: discord.Interaction, bet: int, guess: str):
    log_command("slash_coinflip")
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be positive.", ephemeral=True)
        return
        
    if not remove_coins(interaction.user.id, bet):
        await interaction.response.send_message("❌ You don't have enough coins to make that bet.", ephemeral=True)
    else:
        result = random.choice(["heads", "tails"])
        if result == guess:
            add_coins(interaction.user.id, bet * 2)
            await interaction.response.send_message(f"🪙 **{result.title()}!** You won **{bet}** coins!")
        else:
            await interaction.response.send_message(f"🪙 **{result.title()}!** You lost **{bet}** coins.")

@client.tree.command(name="dice", description="Bet coins on a 6-sided dice roll")
@discord.app_commands.describe(bet="Amount of coins to bet", guess="Number between 1 and 6")
async def slash_dice(interaction: discord.Interaction, bet: int, guess: int):
    log_command("slash_dice")
    if bet <= 0:
        await interaction.response.send_message("❌ Bet must be positive.", ephemeral=True)
        return
    if guess < 1 or guess > 6:
        await interaction.response.send_message("❌ Guess must be between 1 and 6.", ephemeral=True)
        return
        
    if not remove_coins(interaction.user.id, bet):
        await interaction.response.send_message("❌ You don't have enough coins to make that bet.", ephemeral=True)
    else:
        result = random.randint(1, 6)
        if result == guess:
            win_amount = bet * 5
            add_coins(interaction.user.id, win_amount + bet)
            await interaction.response.send_message(f"🎲 **{result}!** Perfect guess! You won **{win_amount}** coins! 💰")
        else:
            await interaction.response.send_message(f"🎲 **{result}!** Better luck next time. You lost **{bet}** coins.")

@client.tree.command(name="poll", description="Create a poll")
@discord.app_commands.describe(question="The overall poll question", options="Separated by | up to 10 options. E.g. Apples | Oranges")
async def slash_poll(interaction: discord.Interaction, question: str, options: str = None):
    log_command("slash_poll")
    if not options:
        embed = discord.Embed(title="📊 Poll", description=f"**{question}**", color=discord.Color.blue())
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message("Poll created!", ephemeral=True)
        poll_msg = await interaction.channel.send(embed=embed)
        await poll_msg.add_reaction("👍")
        await poll_msg.add_reaction("👎")
    else:
        opt_list = [opt.strip() for opt in options.split('|') if opt.strip()]
        if len(opt_list) > 10:
            await interaction.response.send_message("Too many options! Max 10.", ephemeral=True)
            return
            
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = f"**{question}**\n\n"
        for i, opt in enumerate(opt_list):
            desc += f"{emojis[i]} {opt}\n"
            
        embed = discord.Embed(title="📊 Poll", description=desc, color=discord.Color.blue())
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message("Poll created!", ephemeral=True)
        poll_msg = await interaction.channel.send(embed=embed)
        
        for i in range(len(opt_list)):
            await poll_msg.add_reaction(emojis[i])

@client.tree.command(name="remind", description="Set a reminder")
@discord.app_commands.describe(time="Duration like 30m, 2h, 1d", message="What to remind you about")
async def slash_remind(interaction: discord.Interaction, time: str, message: str):
    log_command("slash_remind")
    time_str = time.lower()
    minutes = 0
    if time_str.endswith('m'):
        minutes = int(time_str[:-1])
    elif time_str.endswith('h'):
        minutes = int(time_str[:-1]) * 60
    elif time_str.endswith('d'):
        minutes = int(time_str[:-1]) * 60 * 24
    else:
        await interaction.response.send_message("❌ Invalid time format. Use something like `30m`, `2h`, or `1d`.", ephemeral=True)
        return
        
    if minutes <= 0:
        await interaction.response.send_message("❌ Time must be positive.", ephemeral=True)
        return
        
    remind_at = datetime.now() + timedelta(minutes=minutes)
    reminders_list.append({
        "user_id": interaction.user.id,
        "remind_at": remind_at.isoformat(),
        "message": message
    })
    save_reminders()
    await interaction.response.send_message(f"✅ Okay! I'll remind you in **{time_str}** via DM.")


@client.tree.command(name="warn", description="Warn a user")
@discord.app_commands.describe(user="User to warn", reason="Reason for the warning")
@discord.app_commands.default_permissions(manage_messages=True)
async def slash_warn(interaction: discord.Interaction, user: discord.Member, reason: str):
    log_command("slash_warn")
    if get_perm_level(interaction.user) < PermLevel.MODERATOR:
        await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
        return
    await interaction.response.defer()
    await warn_user(user, reason, interaction.user)
    await interaction.followup.send(f"✅ Warned {user.mention} for: {reason}")

@client.tree.command(name="warnings", description="Check warnings for a user")
@discord.app_commands.describe(user="User to check")
@discord.app_commands.default_permissions(manage_messages=True)
async def slash_warnings(interaction: discord.Interaction, user: discord.Member):
    log_command("slash_warnings")
    if get_perm_level(interaction.user) < PermLevel.MODERATOR:
        await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
        return
        
    uid = str(user.id)
    warns = warnings_data.get(uid, [])
    if not warns:
        await interaction.response.send_message(f"✅ {user.display_name} has no warnings.")
    else:
        desc = ""
        for i, w in enumerate(warns, 1):
            desc += f"**{i}.** {w.get('timestamp', 'Unknown')[:10]} - {w.get('reason')} (Mod ID: {w.get('mod_id', 'Unknown')})\n"
        embed = discord.Embed(title=f"Warnings for {user.display_name}", description=desc, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

@client.tree.command(name="clearwarn", description="Clear all warnings for a user")
@discord.app_commands.describe(user="User to clear warnings for")
@discord.app_commands.default_permissions(manage_messages=True)
async def slash_clearwarn(interaction: discord.Interaction, user: discord.Member):
    log_command("slash_clearwarn")
    if get_perm_level(interaction.user) < PermLevel.MODERATOR:
        await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
        return
        
    uid = str(user.id)
    if uid in warnings_data:
        del warnings_data[uid]
        save_warnings()
        await log_mod_action("clearwarn", user, interaction.user, "Cleared all warnings")
        await interaction.response.send_message(f"✅ Cleared all warnings for {user.display_name}.")
    else:
        await interaction.response.send_message(f"❌ {user.display_name} has no warnings to clear.")


@client.tree.command(name="slowmode", description="Set a slowmode for this channel")
@discord.app_commands.describe(preset="off, relaxed (5s), moderate (15s), strict (30s) or seconds")
@discord.app_commands.default_permissions(manage_channels=True)
async def slash_slowmode(interaction: discord.Interaction, preset: str):
    log_command("slash_slowmode")
    if get_perm_level(interaction.user) < PermLevel.MODERATOR:
        await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
        return
        
    delay = 0
    p = preset.lower()
    if p in ["off", "0"]: delay = 0
    elif p in ["relaxed", "5"]: delay = 5
    elif p in ["moderate", "15"]: delay = 15
    elif p in ["strict", "30"]: delay = 30
    else:
        try:
            delay = int(p)
        except ValueError:
            await interaction.response.send_message("❌ Invalid preset. Use: `off`, `relaxed`, `moderate`, `strict` or a number.", ephemeral=True)
            return

    try:
        await interaction.channel.edit(slowmode_delay=delay)
        status = f"{delay} seconds" if delay > 0 else "disabled"
        await interaction.response.send_message(f"✅ Slowmode is now {status} in this channel.")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I do not have permission to manage this channel.", ephemeral=True)

@client.tree.command(name="shop", description="View the coin shop")
async def slash_shop(interaction: discord.Interaction):
    log_command("slash_shop")
    if not shop_items:
        await interaction.response.send_message("The shop is currently empty.", ephemeral=True)
        return
    desc = ""
    for idx, item in enumerate(shop_items, 1):
        desc += f"**{idx}. {item['name']}** — 🪙 `{item['price']}` coins\n*{item['description']}* (ID: `{item['id']}`)\n\n"
    embed = discord.Embed(title="🛒 Coin Shop", description=desc, color=discord.Color.green())
    embed.set_footer(text="Use /buy <item_id> to purchase an item.")
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="buy", description="Buy an item from the coin shop")
@discord.app_commands.describe(item_id="The ID of the item to purchase")
async def slash_buy(interaction: discord.Interaction, item_id: str):
    log_command("slash_buy")
    item_id = item_id.lower()
    item = next((i for i in shop_items if i['id'].lower() == item_id), None)
    if not item:
        await interaction.response.send_message("❌ Item not found in the shop.", ephemeral=True)
        return
        
    if not remove_coins(interaction.user.id, item['price']):
        await interaction.response.send_message(f"❌ You don't have enough coins. That costs **{item['price']}** 🪙.", ephemeral=True)
    else:
        if item_id == "xp_boost_24h":
            econ = get_economy(interaction.user.id)
            econ['xp_boost_active_until'] = (datetime.now() + timedelta(hours=24)).isoformat()
            save_economy()
            await interaction.response.send_message(f"✅ Successfully purchased **{item['name']}** for **{item['price']}** 🪙! You now have 2x XP for 24 hours!")
        elif item_id == "channel_rename_token":
            econ = get_economy(interaction.user.id)
            econ['rename_tokens'] = econ.get('rename_tokens', 0) + 1
            save_economy()
            await interaction.response.send_message(f"✅ Successfully purchased **{item['name']}** for **{item['price']}** 🪙! Use `/channel rename` to use it.")
        else:
            await interaction.response.send_message(f"✅ Successfully purchased **{item['name']}** for **{item['price']}** 🪙! *(Note: Effect implementation pending)*")

channel_group = discord.app_commands.Group(name="channel", description="Manage your temporary channel")

def check_temp_owner(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
        return False, "You must be in a voice channel."
    vc = interaction.user.voice.channel
    if vc.id not in temp_channels:
        return False, "You are not in a temporary channel."
    if temp_channels[vc.id] != interaction.user.id:
        return False, "Only the channel owner can use this command."
    return True, vc

@channel_group.command(name="rename", description="Rename your temporary channel")
@discord.app_commands.describe(name="New channel name")
async def channel_rename(interaction: discord.Interaction, name: str):
    valid, result = check_temp_owner(interaction)
    if not valid:
        return await interaction.response.send_message(result, ephemeral=True)

    econ = get_economy(interaction.user.id)
    if econ.get('rename_tokens', 0) <= 0:
        return await interaction.response.send_message(f"❌ You need a **Channel Rename Token** to rename your channel. Buy one from the `/shop`!", ephemeral=True)

    try:
        await result.edit(name=name)
        econ['rename_tokens'] -= 1
        save_economy()
        await interaction.response.send_message(f"✅ Channel renamed to **{name}**. (1 Rename Token consumed)", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

@channel_group.command(name="limit", description="Set a user limit for your channel")
@discord.app_commands.describe(limit="Number of users (0 for unlimited)")
async def channel_limit(interaction: discord.Interaction, limit: int):
    valid, result = check_temp_owner(interaction)
    if not valid:
        return await interaction.response.send_message(result, ephemeral=True)
    try:
        await result.edit(user_limit=limit)
        sts = f"{limit} users" if limit > 0 else "unlimited"
        await interaction.response.send_message(f"✅ User limit set to **{sts}**", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

@channel_group.command(name="mode", description="Toggle public/private access")
@discord.app_commands.describe(access="Public or Private")
@discord.app_commands.choices(access=[
    discord.app_commands.Choice(name="Public", value="public"),
    discord.app_commands.Choice(name="Private", value="private")
])
async def channel_mode(interaction: discord.Interaction, access: str):
    valid, result = check_temp_owner(interaction)
    if not valid:
        return await interaction.response.send_message(result, ephemeral=True)
    try:
        overwrites = result.overwrites
        if access == "private":
            overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(connect=False)
        else:
            overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(connect=True)
            
        await result.edit(overwrites=overwrites)
        if result.id not in channel_settings: channel_settings[result.id] = {}
        channel_settings[result.id]["mode"] = access
        save_temp_channels()
        await interaction.response.send_message(f"✅ Channel is now **{access.title()}**", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

@channel_group.command(name="video", description="Toggle video/camera permissions for users")
@discord.app_commands.describe(toggle="Enable or Disable")
@discord.app_commands.choices(toggle=[
    discord.app_commands.Choice(name="Enable", value="on"),
    discord.app_commands.Choice(name="Disable", value="off")
])
async def channel_video(interaction: discord.Interaction, toggle: str):
    valid, result = check_temp_owner(interaction)
    if not valid:
        return await interaction.response.send_message(result, ephemeral=True)
    enabled = toggle == "on"
    try:
        overwrites = result.overwrites
        perms = overwrites.get(interaction.guild.default_role, discord.PermissionOverwrite())
        perms.stream = enabled
        overwrites[interaction.guild.default_role] = perms
        await result.edit(overwrites=overwrites)
        
        if result.id not in channel_settings: channel_settings[result.id] = {}
        channel_settings[result.id]["video"] = enabled
        save_temp_channels()
        await interaction.response.send_message(f"📹 Video sharing {'enabled' if enabled else 'disabled'}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

@channel_group.command(name="clone", description="Clone your temporary channel")
async def channel_clone(interaction: discord.Interaction):
    valid, result = check_temp_owner(interaction)
    if not valid:
        return await interaction.response.send_message(result, ephemeral=True)
    
    try:
        await interaction.response.defer(ephemeral=True)
        cloned = await interaction.guild.create_voice_channel(
            name=f"{result.name} (Clone)",
            category=result.category,
            bitrate=result.bitrate,
            user_limit=result.user_limit,
            overwrites=result.overwrites
        )
        temp_channels[cloned.id] = interaction.user.id
        channel_settings[cloned.id] = channel_settings.get(result.id, {}).copy()
        save_temp_channels()
        await interaction.followup.send(f"✅ Cloned! You now own {cloned.mention}")
    except discord.Forbidden:
        await interaction.followup.send("❌ I lack permissions.", ephemeral=True)

@channel_group.command(name="record", description="Start a recorded session and ask for consent")
async def channel_record(interaction: discord.Interaction):
    valid, result = check_temp_owner(interaction)
    if not valid:
        return await interaction.response.send_message(result, ephemeral=True)
    
    await interaction.response.send_message(f"🔴 **Recording started!** Sending consent requests to all members in the voice channel...", ephemeral=False)
    
    if result.id not in channel_settings: channel_settings[result.id] = {}
    channel_settings[result.id]["recording"] = True
    save_temp_channels()
    
    for member in result.members:
        if member.bot or member == interaction.user: continue
        try:
            embed = discord.Embed(
                title="🔴 Recording Consent",
                description=f"The owner of **{result.name}** has started recording the channel.\\n\\nPlease react with ✅ to consent, or ❌ to decline. If you don't respond in 60s, you will be removed.",
                color=discord.Color.red()
            )
            dm_msg = await member.send(embed=embed)
            await dm_msg.add_reaction("✅")
            await dm_msg.add_reaction("❌")
            
            def check(reaction, user):
                return user == member and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == dm_msg.id
                
            try:
                reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
                if str(reaction.emoji) == "❌":
                    if member in result.members:
                        await member.move_to(None, reason="Declined recording consent")
                        await member.send("You have been disconnected because you declined the recording.")
                else:
                    await member.send("✅ Thank you for consenting to the recording.")
            except asyncio.TimeoutError:
                if member in result.members:
                    await member.move_to(None, reason="Failed to consent to recording in time")
                    await member.send("⏳ You have been disconnected because you did not consent in time.")
        except discord.Forbidden:
            if member in result.members:
                await member.move_to(None, reason="Could not send DM for recording consent")

client.tree.add_command(channel_group)

def is_channel_owner(channel_id, author_id):
    """Checks if the author is the owner of the temporary channel."""
    if channel_id in temp_channels and temp_channels[channel_id] == author_id:
        return True
    return False

def has_admin_role(member):
    """Checks if a member has administrator permissions."""
    return member.guild_permissions.administrator

@client.tree.command(name="kick", description="Kicks a user from your channel.")
@discord.app_commands.describe(user_to_kick="The user to kick")
async def kick(interaction: discord.Interaction, user_to_kick: discord.Member):
    """Kicks a user from the temporary channel."""
    # Check if the user is in a voice channel
    if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
        await interaction.response.send_message("You must be in a voice channel to use this command.", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel

    # Check if they're in a temp channel
    if voice_channel.id not in temp_channels:
        await interaction.response.send_message("You are not in a temporary channel.", ephemeral=True)
        return

    # Check if the command is used in a temporary channel by its owner
    if not is_channel_owner(voice_channel.id, interaction.user.id):
        await interaction.response.send_message("Only the channel owner can use this command.", ephemeral=True)
        return

    # Check if the user to kick has admin role
    if has_admin_role(user_to_kick):
        warning_embed = discord.Embed(
            title="⚠️ Cannot Kick Administrator",
            description=f"You cannot kick {user_to_kick.mention} because they have administrator permissions.",
            color=discord.Color.red()
        )
        warning_embed.add_field(
            name="Reason",
            value="Users with administrator roles are protected from being kicked from temporary channels.",
            inline=False
        )
        if interaction.guild and interaction.guild.icon:
            warning_embed.set_thumbnail(url=interaction.guild.icon.url)
        warning_embed.set_footer(text="This message is only visible to you")
        
        await interaction.response.send_message(embed=warning_embed, ephemeral=True)
        print(f"{interaction.user.display_name} tried to kick admin {user_to_kick.display_name}")
        return
    
    # Normal kick for non-admin users
    if user_to_kick in voice_channel.members:
        await user_to_kick.move_to(None, reason=f"Kicked by channel owner {interaction.user.name}")
        await interaction.response.send_message(f"Kicked {user_to_kick.mention}.")
    else:
        await interaction.response.send_message(f"{user_to_kick.mention} is not in this channel.", ephemeral=True)

@client.event
async def on_ready():
    """Bot connected and ready."""
    print(f'[BOT] Logged in as {client.user}')
    print(f'[BOT] Connected to {len(client.guilds)} guild(s).')

    # Seed user_names.json from every member currently in all guilds
    added = 0
    for guild in client.guilds:
        for member in guild.members:
            if not member.bot:
                uid = str(member.id)
                old = user_names.get(uid, {})
                if old.get("display_name") != member.display_name or old.get("username") != member.name:
                    user_names[uid] = {
                        "display_name": member.display_name,
                        "username": member.name,
                        "avatar": str(member.display_avatar.url) if member.display_avatar else "",
                    }
                    added += 1
    if added:
        save_user_names()
        print(f"[DB] Seeded / updated {added} member name(s) in user_names.json")

    # Load temp-channel state
    load_temp_channels()

    # Start background tasks
    client.loop.create_task(check_muted_users())
    client.loop.create_task(track_voice_minutes())
    client.loop.create_task(leaderboard_reset_task())
    client.loop.create_task(check_reminders())
    client.loop.create_task(periodic_flush())

    # Start built-in web dashboard
    if DASHBOARD_ENABLED:
        start_dashboard()

    print('[BOT] All systems ready.')

@client.event
async def on_member_join(member):
    # Cache display name for dashboard
    cache_member_name(member)
    # Utilities: Welcome Message
    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(int(WELCOME_CHANNEL_ID))
        if channel:
            try:
                embed = discord.Embed(
                    title="👋 Welcome!",
                    description=WELCOME_MESSAGE.format(
                        mention=member.mention,
                        server=member.guild.name,
                        count=member.guild.member_count
                    ),
                    color=discord.Color.green()
                )
                if member.display_avatar:
                    embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Error sending welcome message: {e}")
                
    # Utilities: Auto-Roles
    for role_id in AUTO_ROLES:
        role = member.guild.get_role(int(role_id))
        if role:
            try:
                await member.add_roles(role)
            except Exception as e:
                 print(f"Error assigning auto-role {role.name}: {e}")

    # Level System: Default Role
    req_0 = level_requirements.get("0")
    if req_0:
        role_id = req_0.get("role_id")
        role = None
        if role_id and role_id != 0:
             role = member.guild.get_role(role_id)
        if not role:
             role = discord.utils.get(member.guild.roles, name="Level 0")
        if role:
            try:
                await member.add_roles(role)
            except:
                pass

@client.event
async def on_member_remove(member):
    # Utilities: Leave Message
    if LEAVE_CHANNEL_ID:
        channel = member.guild.get_channel(int(LEAVE_CHANNEL_ID))
        if channel:
            try:
                embed = discord.Embed(
                    title="👋 Goodbye!",
                    description=LEAVE_MESSAGE.format(
                        name=member.display_name,
                        server=member.guild.name
                    ),
                    color=discord.Color.red()
                )
                if member.display_avatar:
                    embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Error sending leave message: {e}")

@client.event
async def on_raw_reaction_add(payload):
    if payload.member.bot:
        return
        
    msg_id = str(payload.message_id)
    if msg_id in reaction_roles:
        emoji_name = str(payload.emoji.name)
        if emoji_name in reaction_roles[msg_id]:
            role_id = reaction_roles[msg_id][emoji_name]
            guild = client.get_guild(payload.guild_id)
            if guild:
                role = guild.get_role(role_id)
                if role:
                    try:
                        await payload.member.add_roles(role)
                    except Exception as e:
                        print(f"Error giving reaction role: {e}")

@client.event
async def on_raw_reaction_remove(payload):
    msg_id = str(payload.message_id)
    if msg_id in reaction_roles:
        emoji_name = str(payload.emoji.name)
        if emoji_name in reaction_roles[msg_id]:
            role_id = reaction_roles[msg_id][emoji_name]
            guild = client.get_guild(payload.guild_id)
            if guild:
                role = guild.get_role(role_id)
                member = guild.get_member(payload.user_id)
                if role and member and not member.bot:
                    try:
                        await member.remove_roles(role)
                    except Exception as e:
                        print(f"Error removing reaction role: {e}")

async def track_voice_minutes():
    """Background task to track voice minutes for leveling."""
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            if level_requirements:
                for guild in client.guilds:
                    for channel in guild.voice_channels:
                        if len(channel.members) < 2:
                            continue
                        for member in channel.members:
                            if member.bot: continue
                            if member.voice and (member.voice.self_mute or member.voice.mute or member.voice.self_deaf or member.voice.deaf):
                                continue
                            user_id = str(member.id)
                            cache_member_name(member)   # keep name cache fresh
                            stats = get_user_stats(user_id)
                            
                            streak_multiplier = update_streak(user_id)
                            multiplier = get_active_multiplier(user_id) * streak_multiplier
                            added_xp = (1 * multiplier)
                            
                            stats["voice_minutes"] += added_xp
                            stats["weekly_voice"] += added_xp
                            stats["monthly_voice"] += added_xp
                            
                            add_coins(user_id, 2) # Adding 2 coins per voice minute

                            await check_level_up(member)
                save_user_stats()
        except Exception as e:
            print(f"Error in track_voice_minutes loop: {e}")
        await asyncio.sleep(60)

async def periodic_flush():
    """Flush all in-memory data to disk every 5 minutes.
    This ensures that even if the bot is killed unexpectedly,
    no more than ~5 minutes of activity is ever lost."""
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.sleep(300)   # 5 minutes
        try:
            save_user_stats()
            save_user_streaks()
            save_economy()
            save_analytics()
            save_user_names()
            print(f"[DB] Periodic flush complete at {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[DB] Periodic flush error: {e}")

async def check_muted_users():
    """Background task to check for users who have been muted for 20+ minutes."""
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            current_time = datetime.now()
            users_to_disconnect = []

            for user_id, data in list(muted_users.items()):
                mute_start = data['mute_start']
                if (current_time - mute_start).total_seconds() >= 1200: # 20 minutes
                    users_to_disconnect.append((user_id, data['guild_id']))

            for user_id, guild_id in users_to_disconnect:
                guild = client.get_guild(guild_id)
                if guild:
                    member = guild.get_member(user_id)
                    if member and member.voice and member.voice.channel:
                        try:
                            await member.move_to(None, reason="Muted for more than 20 minutes.")
                            print(f"Disconnected {member.display_name} for being muted too long.")
                            
                            # Log action
                            try:
                                await log_mod_action("auto-disconnect", member, client.user, "Muted for 20+ minutes in Temp Channel")
                            except Exception as e:
                                print(f"Error logging mute disconnect: {e}")
                        except discord.Forbidden:
                            print(f"Failed to disconnect {member.display_name}. Missing permissions.")
                        except Exception as e:
                            print(f"Error disconnecting {member.display_name}: {e}")
                
                # Remove from tracking list regardless of success to avoid infinite loops
                del muted_users[user_id]
                
        except Exception as e:
             print(f"Error in check_muted_users loop: {e}")
        await asyncio.sleep(60)

async def check_reminders():
    """Background task to check and send reminders."""
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            now = datetime.now()
            to_remove = []
            
            for i, reminder in enumerate(reminders_list):
                remind_at = datetime.fromisoformat(reminder['remind_at'])
                if now >= remind_at:
                    user_id = reminder['user_id']
                    message = reminder['message']
                    try:
                        user = client.get_user(user_id) or await client.fetch_user(user_id)
                        embed = discord.Embed(title="⏰ Reminder!", description=message, color=discord.Color.gold())
                        await user.send(embed=embed)
                    except Exception as e:
                        print(f"Could not send reminder to {user_id}: {e}")
                    to_remove.append(i)
                    
            if to_remove:
                for idx in reversed(to_remove):
                    del reminders_list[idx]
                save_reminders()
                
        except Exception as e:
             print(f"Error in check_reminders loop: {e}")
        await asyncio.sleep(60)

async def post_leaderboard(period):
    """Posts the leaderboard and saves the snapshot to JSON."""
    if not LEVELUP_CHANNEL_ID: return
    
    # Calculate a composite score for sorting (e.g. 1 min text = 1 xp, 1 min voice = 2 xp)
    leaderboard_data = []
    for uid, stats in user_stats.items():
        v_key = f"{period}_voice"
        t_key = f"{period}_text"
        score = (stats.get(v_key, 0) * 2) + stats.get(t_key, 0)
        if score > 0:
            leaderboard_data.append({"user_id": uid, "score": score, "v": stats.get(v_key, 0), "t": stats.get(t_key, 0)})
            
    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)
    top_10 = leaderboard_data[:10]
    
    if not top_10: return
    
    # Save Snapshot
    try:
        snapshot_data = {}
        if os.path.exists(leaderboard_file):
            with open(leaderboard_file, "r") as f:
                snapshot_data = json.load(f)
        snapshot_date = datetime.now().strftime("%Y-%m-%d")
        snapshot_data[f"{period}_{snapshot_date}"] = top_10
        with open(leaderboard_file, "w") as f:
            json.dump(snapshot_data, f, indent=4)
    except Exception as e:
        print(f"Failed to save leaderboard snapshot: {e}")

    # Send Embed to 1st available guild the channel is in
    channel = None
    for guild in client.guilds:
        channel = guild.get_channel(LEVELUP_CHANNEL_ID)
        if channel: break
        
    if not channel: return
    
    desc = ""
    for idx, entry in enumerate(top_10, 1):
        desc += f"**{idx}.** <@{entry['user_id']}> — Score: **{int(entry['score'])}** (Voice: {int(entry['v'])}m | Text: {int(entry['t'])}m)\n"
        
    embed = discord.Embed(
        title=f"🏆 {period.capitalize()} Leaderboard Snapshot",
        description=desc,
        color=discord.Color.blue()
    )
    await channel.send(embed=embed)


async def leaderboard_reset_task():
    """Background task to post and reset weekly/monthly leaderboards."""
    await client.wait_until_ready()
    # Check every hour
    while not client.is_closed():
        try:
            now = datetime.now()
            # Weekly check: Monday at 00:xx
            if now.weekday() == 0 and now.hour == 0:
                # To prevent multiple postings in the same hour, we could store the last_reset_time, 
                # but for simplicity assuming the bot doesn't restart during this hour.
                await post_leaderboard("weekly")
                for uid in user_stats:
                    user_stats[uid]["weekly_voice"] = 0
                    user_stats[uid]["weekly_text"] = 0
                save_user_stats()
                
            # Monthly check: 1st day of month at 00:xx
            if now.day == 1 and now.hour == 0:
                await post_leaderboard("monthly")
                for uid in user_stats:
                    user_stats[uid]["monthly_voice"] = 0
                    user_stats[uid]["monthly_text"] = 0
                save_user_stats()
                
        except Exception as e:
            print(f"Error in leaderboard reset loop: {e}")
            
        await asyncio.sleep(3600)

async def send_help_message(channel, guild):
    """Sends a help message to the newly created channel."""
    embed = discord.Embed(
        title="🎙️ Welcome to Your Voice Channel!",
        description="You are the proud owner of this temporary channel. Customize and control it with the commands below!",
        color=discord.Color.from_rgb(102, 200, 255)
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    # Basic Settings
    embed.add_field(
        name="⚙️ **BASIC SETTINGS**",
        value=(
            "✏️ **`.rename <name>`** - Rename your channel\n"
            "👥 **`.limit <number>`** - Set member limit (0 = unlimited)\n"
            "⏱️ **`.slowmode <seconds>`** - Chat slowmode\n"
            "🔄 **`.reset`** - Reset to defaults"
        ),
        inline=False
    )

    # Privacy & Access
    embed.add_field(
        name="🔐 **PRIVACY & ACCESS**",
        value=(
            "🔒 **`.lock`** - Make channel private\n"
            "🔓 **`.unlock`** - Make channel public\n"
            "✅ **`.allow @user`** - Grant user access\n"
            "❌ **`.deny @user`** - Revoke access\n"
            "📋 **`.whitelist @user`** - Add to whitelist\n"
            "🚫 **`.blacklist @user`** - Block user\n"
            "♻️ **`.unblacklist @user`** - Unblock user"
        ),
        inline=False
    )

    # Chat Management
    embed.add_field(
        name="💬 **CHAT MANAGEMENT**",
        value=(
            "🔇 **`.lockchat`** - Lock text chat\n"
            "🔊 **`.unlockchat`** - Unlock text chat\n"
            "🗑️ **`.purge <number>`** - Delete messages"
        ),
        inline=False
    )

    # Ownership & Info
    embed.add_field(
        name="👑 **OWNERSHIP & INFO**",
        value=(
            "👑 **`.give @user`** - Transfer ownership\n"
            "🎯 **`.claim`** - Claim if owner left\n"
            "👢 **`.kick @user`** - Kick user\n"
            "📊 **`.info`** - View channel info\n"
            "👥 **`.members`** - List members\n"
            "⚙️ **`.settings`** - Show all settings"
        ),
        inline=False
    )

    # Advanced Features
    embed.add_field(
        name="🚀 **ADVANCED FEATURES**",
        value=(
            "🗑️ **`.autodelete <minutes>`** - Auto-delete on inactivity\n"
            "⏰ **`.schedule-delete <minutes>`** - Schedule deletion\n"
            "⏱️ **`.timer <minutes>`** - Countdown timer\n"
            "❓ **`.help`** - Show full help menu"
        ),
        inline=False
    )

    embed.set_footer(
        text="💡 Tip: You are the owner! Only you can use these commands."
    )

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        print(f"Error: Bot lacks permissions to send messages in '{channel.name}'.")
    except Exception as e:
        print(f"An unexpected error occurred while sending help message: {e}")

async def manage_temp_channels(guild):
    """
    Manages the temporary channel category:
    1. Cleans up unauthorized channels.
    2. Creates channels for users waiting in the creator channel (Prioritizing by role).
    """
    category = guild.get_channel(TEMP_CHANNEL_CATEGORY_ID)
    if not category or not isinstance(category, discord.CategoryChannel):
        print(f"Error: Category with ID {TEMP_CHANNEL_CATEGORY_ID} not found or is not a category.")
        return

    # --- Process Waiting Users (Priority Queue) ---
    creator_channel = guild.get_channel(CREATOR_CHANNEL_ID)
    if creator_channel and creator_channel.members:
        # Filter out bots
        waiting_members = [m for m in creator_channel.members if not m.bot]
        
        if waiting_members:
            # Sort by Role Hierarchy: Highest role first
            waiting_members.sort(key=lambda m: m.top_role.position, reverse=True)
            
            member_to_move = waiting_members[0]
            
            try:
                # Inherit permissions from the category and add owner permissions
                overwrites = category.overwrites.copy()
                overwrites[member_to_move] = discord.PermissionOverwrite(
                    manage_channels=True,
                    kick_members=True,
                    manage_permissions=True,
                    view_channel=True,
                    connect=True
                )

                # Create the new temporary channel
                temp_channel = await guild.create_voice_channel(
                    name=f"{member_to_move.display_name}'s Channel",
                    category=category,
                    overwrites=overwrites
                )

                # Move the user to their new channel
                await member_to_move.move_to(temp_channel)

                # Store the channel ID and its owner
                temp_channels[temp_channel.id] = member_to_move.id
                channel_settings[temp_channel.id] = {
                    "mode": "public",
                    "recording": False,
                    "video": True
                }
                save_temp_channels()
                print(f"Created temporary channel '{temp_channel.name}' for {member_to_move.display_name} (Priority Create)")

                # Send the help message to the new channel
                await send_help_message(temp_channel, guild)

            except discord.Forbidden:
                print(f"Error: Bot lacks permissions to create channels or move members in '{guild.name}'.")
            except Exception as e:
                print(f"An unexpected error occurred during channel creation: {e}")

@client.event
async def on_voice_state_update(member, before, after):
    """
    Event handler for when a member's voice state changes.
    This is used to create and delete temporary channels and track mute status.
    """
    # Cache display name for dashboard
    cache_member_name(member)
    
    # --- Mute Detection Logic ---
    if after.channel:
        was_muted = (before.mute or before.self_mute) if before.channel else False
        is_muted = after.mute or after.self_mute
        
        if not was_muted and is_muted:
            muted_users[member.id] = {
                'mute_start': datetime.now(),
                'guild_id': member.guild.id
            }
            print(f"{member.display_name} was muted. Tracking for 20 minutes.")
        
        elif was_muted and not is_muted:
            if member.id in muted_users:
                del muted_users[member.id]
                print(f"{member.display_name} was unmuted. Stopped tracking.")
    
    # User left voice channel - stop tracking
    if not after.channel and member.id in muted_users:
        del muted_users[member.id]
    
    # --- Channel Deletion Logic ---
    if before.channel and before.channel.id in temp_channels:
        channel = before.channel
        owner_id = temp_channels[channel.id]

        if not channel.members:
            try:
                await channel.delete(reason="Temporary channel is empty.")
                del temp_channels[channel.id]
                save_temp_channels()
                print(f"Deleted empty temporary channel '{channel.name}'")
            except discord.NotFound:
                pass
            except discord.Forbidden:
                print(f"Error: Bot lacks permissions to delete channel '{channel.name}'.")
            except Exception as e:
                print(f"An unexpected error occurred during channel deletion: {e}")
        elif member.id == owner_id and after.channel != channel:
            await channel.send(f"The owner, {member.mention}, has left. Another user can type `.claim` to take ownership.", allowed_mentions=discord.AllowedMentions.none())

    # --- Run Unified Channel Manager ---
    await manage_temp_channels(member.guild)

@client.event
async def on_message(message):
    """Event handler for messages to process commands."""
    if message.author.bot:
        return

    # Cache display name for dashboard
    if isinstance(message.author, discord.Member):
        cache_member_name(message.author)



    # --- LEVEL SYTEM TRACKING ---
    user_id = str(message.author.id)
    stats = get_user_stats(user_id)
    stats["total_messages"] += 1
    current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
    if stats.get("last_message_minute") != current_minute:
        streak_multiplier = update_streak(user_id)
        multiplier = get_active_multiplier(user_id) * streak_multiplier
        added_xp = (1 * multiplier)
        
        stats["text_minutes"] += added_xp
        stats["weekly_text"] += added_xp
        stats["monthly_text"] += added_xp
        
        add_coins(user_id, 1) # Adding 1 coin per text minute
        
        stats["last_message_minute"] = current_minute
        save_user_stats()
        if isinstance(message.author, discord.Member):
            await check_level_up(message.author)
    else:
        save_user_stats()
        
    # --- AUTO MODERATION ---
    if isinstance(message.author, discord.Member) and not message.author.guild_permissions.manage_messages:
        # 1. Message Cooldown
        uid = str(message.author.id)
        now = datetime.now()
        cooldown_sec = automod_config.get("message_cooldown_seconds", 2)
        
        # We need a global dict for fast cooldown tracking
        if not hasattr(client, 'user_cooldowns'):
            client.user_cooldowns = {}
            
        last_msg_time = client.user_cooldowns.get(uid)
        if last_msg_time and (now - last_msg_time).total_seconds() < cooldown_sec:
            try:
                await message.delete()
                warning_msg = await message.channel.send(f"⚠️ {message.author.mention}, you're messaging too fast!")
                await asyncio.sleep(3)
                await warning_msg.delete()
            except discord.Forbidden:
                pass
            return # Stop processing
            
        client.user_cooldowns[uid] = now
        
        # 2. Mention Spam Detection
        mention_limit = automod_config.get("mention_limit", 5)
        if len(message.mentions) >= mention_limit:
            try:
                await message.delete()
                await warn_user(message.author, "Mention Spam", client.user)
                await message.channel.send(f"🚨 {message.author.mention} was warned for mention spam.")
            except discord.Forbidden:
                pass
            return
            
        # 3. Link & Invite Filtering
        content = message.content.lower()
        BLOCKED_PATTERNS = [
            r"discord\.gg/\w+",          
            r"https?://\S+\.(tk|ml|cf)" 
        ]
        
        is_blocked = False
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                is_blocked = True
                break
                
        if is_blocked:
            allowed_domains = automod_config.get("allowed_domains", [])
            # Exception for explicitly whitelisted domains in the config
            if any(domain.lower() in content for domain in allowed_domains):
                is_blocked = False
                
        if is_blocked:
            try:
                await message.delete()
                await warn_user(message.author, "Posting Unauthorized Links/Invites", client.user)
                warning_msg = await message.channel.send(f"🚫 {message.author.mention}, unauthorized links or invites are blocked here.")
                await asyncio.sleep(5)
                await warning_msg.delete()
            except discord.Forbidden:
                pass
            return

    # --- GLOBAL COMMANDS ---
    msg_parts = message.content.lower().split()
    cmd = msg_parts[0] if msg_parts else ""
    
    # Resolve aliases
    resolved_cmd = cmd.lstrip(".!")
    for canonical, aliases in ALIASES.items():
        if resolved_cmd in aliases:
            resolved_cmd = canonical
            break
            
    if resolved_cmd == "rank" and cmd.startswith(('.', '!')):
        log_command("rank")
        remaining = check_cooldown(message.author.id, "rank", 3)
        if remaining > 0:
            await message.reply(f"⏳ Wait {int(remaining)}s before checking rank again.", delete_after=3)
            return
            
        target_member = message.author
        if message.mentions:
            target_member = message.mentions[0]
            
        t_stats = get_user_stats(target_member.id)
        msgs = t_stats.get('total_messages', 0)
        text_lvl, next_msg_req = get_level_data(msgs, "text_minutes_required")
        mins = t_stats.get('voice_minutes', 0)
        voice_lvl, next_voice_req = get_level_data(mins, "voice_minutes_required")

        # Text Bar Percentage
        prev_msg_req = level_requirements.get(str(text_lvl), {}).get("text_minutes_required", 0)
        if next_msg_req == float('inf'):
            text_percent = 100
            text_progress_str = f"{msgs} (MAX)"
        else:
            total_step = next_msg_req - prev_msg_req
            current_step = msgs - prev_msg_req
            text_percent = min(100, max(0, (current_step / total_step) * 100)) if total_step > 0 else 100
            text_progress_str = f"{msgs} / {int(next_msg_req)} Msgs"

        # Voice Bar Percentage
        prev_voice_req = level_requirements.get(str(voice_lvl), {}).get("voice_minutes_required", 0)
        if next_voice_req == float('inf'):
            voice_percent = 100
            voice_progress_str = f"{mins}m (MAX)"
        else:
            total_step_v = next_voice_req - prev_voice_req
            current_step_v = mins - prev_voice_req
            voice_percent = min(100, max(0, (current_step_v / total_step_v) * 100)) if total_step_v > 0 else 100
            voice_progress_str = f"{mins} / {int(next_voice_req)} Mins"

        bg_path = os.path.join(script_dir, "PRO2.png")
        if not os.path.exists(bg_path):
            await message.channel.send("❌ Error: Background template not found!")
            return

        try:
            editor = Editor(bg_path)
            try:
                font_large = Font.poppins(size=36, variant="bold")
                font_medium = Font.poppins(size=24, variant="bold")
                font_small = Font.poppins(size=18, variant="bold")
            except:
                font_large = Font.poppins(size=36)
                font_medium = Font.poppins(size=24)
                font_small = Font.poppins(size=18)

            voice_y = 61
            editor.text((455, voice_y - 25), f"Voice Level: {voice_lvl}", font=font_small, color="#FFFFFF")
            editor.text((910, voice_y - 25), voice_progress_str, font=font_small, color="#FFFFFF", align="right")
            editor.bar((455, voice_y), max_width=458, height=27, percentage=voice_percent, fill="#F1C40F", radius=16)
            editor.text((684, voice_y + 4), f"{int(voice_percent)}%", font=font_small, color="#1A1A1A", align="center")

            text_y = 139
            editor.text((455, text_y - 25), f"Text Level: {text_lvl}", font=font_small, color="#FFFFFF")
            editor.text((910, text_y - 25), text_progress_str, font=font_small, color="#FFFFFF", align="right")
            editor.bar((455, text_y), max_width=458, height=27, percentage=text_percent, fill="#D4AF37", radius=16)
            editor.text((684, text_y + 4), f"{int(text_percent)}%", font=font_small, color="#1A1A1A", align="center")

            try:
                profile_image = await load_image_async(str(target_member.display_avatar.url))
                profile = Editor(profile_image).resize((200, 200)).circle_image()
                editor.paste(profile, (0, 70))
            except Exception as e:
                print(f"Error loading avatar: {e}")
            
            file = discord.File(fp=editor.image_bytes, filename="rank_card.png")
            await message.reply(file=file)
        except Exception as e:
            await message.reply(f"❌ Error generating rank card!")
            print(f"Error generating rank card: {e}")
            
        return

    # --- TEMP CHANNEL COMMANDS ---
    if not message.content.startswith('.'):
        return

    if not isinstance(message.author, discord.Member) or not message.author.voice:
        return
    
    voice_channel = message.author.voice.channel
    
    if voice_channel.id not in temp_channels:
        return
    
    channel_id = voice_channel.id
    channel = voice_channel

    command, *args = message.content[1:].lower().split()

    # --- Claim Command Logic (Special Case) ---
    if command == "claim":
        if channel.id in temp_channels:
            owner_id = temp_channels[channel.id]
            owner = message.guild.get_member(owner_id)
            if not owner or owner not in channel.members:
                temp_channels[channel.id] = message.author.id
                save_temp_channels()
                if owner:
                    await channel.set_permissions(owner, overwrite=None)
                await channel.set_permissions(message.author, manage_channels=True, kick_members=True, manage_permissions=True)
                await message.reply(f"👑 {message.author.mention} has claimed ownership of this channel!")
            else:
                await message.reply("You can only claim this channel if the original owner is not in it.")
        else:
            await message.reply("This is not a temporary channel that can be claimed.", delete_after=10)
        return

    if not is_channel_owner(channel.id, message.author.id):
        await message.reply("Only the channel owner can use this command.", delete_after=5)
        return

    try:
        if command == "rename":
            if not args:
                await message.reply("Usage: `.rename <new-name>`")
                return
            new_name = " ".join(args)
            await channel.edit(name=new_name)
            await message.reply(f"✏️ Channel renamed to `{new_name}`.")

        elif command == "limit":
            if not args or not args[0].isdigit():
                await message.reply("Usage: `.limit <number>`")
                return
            limit = int(args[0])
            await channel.edit(user_limit=limit)
            await message.reply(f"👥 Channel user limit set to `{limit if limit > 0 else 'unlimited'}`.")

        elif command == "lock":
            await channel.set_permissions(message.guild.default_role, connect=False)
            await channel.set_permissions(message.author, connect=True)
            if channel.id in channel_settings:
                channel_settings[channel.id]["mode"] = "private"
                save_temp_channels()
            await message.reply("🔒 Channel is now locked. Only users with explicit permission can join.")

        elif command == "unlock":
            await channel.set_permissions(message.guild.default_role, connect=True)
            if channel.id in channel_settings:
                channel_settings[channel.id]["mode"] = "public"
                save_temp_channels()
            await message.reply("🔓 Channel is now unlocked and public.")

        elif command == "clone":
            try:
                cloned = await message.guild.create_voice_channel(
                    name=f"{channel.name} (Clone)",
                    category=channel.category,
                    bitrate=channel.bitrate,
                    user_limit=channel.user_limit,
                    overwrites=channel.overwrites
                )
                temp_channels[cloned.id] = message.author.id
                if channel.id in channel_settings:
                    channel_settings[cloned.id] = channel_settings[channel.id].copy()
                else:
                    channel_settings[cloned.id] = {"mode": "public", "recording": False, "video": True}
                save_temp_channels()
                await message.reply(f"👯 Successfully cloned channel to {cloned.mention}!")
            except Exception as e:
                await message.reply("❌ Failed to clone channel.")
                print(f"Clone error: {e}")

        elif command == "video" or command == "screenshare":
            if not args:
                await message.reply("Usage: `.video on|off`")
                return
            enabled = args[0] == "on"
            try:
                await channel.set_permissions(message.guild.default_role, stream=enabled)
                if channel.id not in channel_settings:
                    channel_settings[channel.id] = {"mode": "public", "recording": False, "video": True}
                channel_settings[channel.id]["video"] = enabled
                save_temp_channels()
                state = "enabled" if enabled else "disabled"
                await message.reply(f"📹 Video/Screenshare has been **{state}** for everyone else.")
            except Exception as e:
                await message.reply(f"❌ Error updating permissions: {e}")

        elif command == "record":
            if not args:
                await message.reply("Usage: `.record on|off`")
                return
            
            enable_rec = args[0] == "on"
            
            if channel.id not in channel_settings:
                channel_settings[channel.id] = {"mode": "public", "recording": False, "video": True}
                
            if not enable_rec:
                channel_settings[channel.id]["recording"] = False
                save_temp_channels()
                await message.reply("⏹️ Recording mode disabled. Consent is no longer required.")
                return
                
            channel_settings[channel.id]["recording"] = True
            save_temp_channels()
            
            embed = discord.Embed(
                title="🔴 RECORDING IN PROGRESS",
                description="The channel owner has enabled Recording Mode. Check your DMs to provide consent. Users who do not consent will be disconnected in 60 seconds.",
                color=discord.Color.red()
            )
            await message.reply(embed=embed)
            
            async def process_consent(member, dm_msg, vc):
                def check(r, u):
                    return u == member and str(r.emoji) in ["✅", "❌"] and r.message.id == dm_msg.id
                try:
                    reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
                    if str(reaction.emoji) == "❌":
                        if member in vc.members:
                            await member.move_to(None, reason="Recording consent denied.")
                            await member.send("⚠️ You have been disconnected from the channel because you declined recording consent.")
                    else:
                        await member.send("✅ Thank you for your consent. You may remain in the channel.")
                except asyncio.TimeoutError:
                    if member in vc.members:
                        await member.move_to(None, reason="Recording consent timed out.")
                        await member.send("⚠️ You have been disconnected from the channel because you did not answer the recording consent prompt.")
                        
            for mem in channel.members:
                if mem.id == message.author.id or mem.bot:
                    continue
                try:
                    dm_msg = await mem.send(f"⚠️ **Recording Consent Required**\nThe temporary channel **{channel.name}** in **{message.guild.name}** is now being recorded.\nReact with ✅ to consent and stay in the channel.\nReact with ❌ to decline.\n*You will be disconnected if you do not consent within 60 seconds.*")
                    await dm_msg.add_reaction("✅")
                    await dm_msg.add_reaction("❌")
                    
                    client.loop.create_task(process_consent(mem, dm_msg, channel))
                except discord.Forbidden:
                    # Can't DM user, disconnect them immediately
                    if mem in channel.members:
                        await mem.move_to(None, reason="Cannot verify recording consent due to closed DMs.")

        elif command == "allow":
            if not message.mentions:
                await message.reply("Usage: `.allow @user`")
                return
            target_user = message.mentions[0]
            await channel.set_permissions(target_user, connect=True)
            await message.reply(f"✅ {target_user.mention} can now connect to this channel.")

        elif command == "deny":
            if not message.mentions:
                await message.reply("Usage: `.deny @user`")
                return
            target_user = message.mentions[0]
            await channel.set_permissions(target_user, connect=None)
            await message.reply(f"❌ Permissions for {target_user.mention} have been reset.")

        elif command == "give":
            if not message.mentions:
                await message.reply("Usage: `.give @user`")
                return
            new_owner = message.mentions[0]
            if new_owner not in channel.members:
                await message.reply(f"{new_owner.mention} is not in this channel.")
                return
            temp_channels[channel.id] = new_owner.id
            await channel.set_permissions(message.author, overwrite=None)
            await channel.set_permissions(new_owner, manage_channels=True, kick_members=True, manage_permissions=True)
            await message.reply(f"👑 Ownership transferred to {new_owner.mention}.")

        elif command == "lockchat":
            await channel.set_permissions(message.guild.default_role, send_messages=False)
            await message.reply("🔇 Channel chat has been locked.")

        elif command == "unlockchat":
            await channel.set_permissions(message.guild.default_role, send_messages=True)
            await message.reply("🔊 Channel chat has been unlocked.")

        elif command == "whitelist":
            if not message.mentions:
                await message.reply("Usage: `.whitelist @user`")
                return
            target_user = message.mentions[0]
            if channel.id not in channel_whitelists:
                channel_whitelists[channel.id] = []
            if target_user.id not in channel_whitelists[channel.id]:
                channel_whitelists[channel.id].append(target_user.id)
                await message.reply(f"✅ {target_user.mention} has been added to the whitelist.")
            else:
                await message.reply(f"{target_user.mention} is already whitelisted.")

        elif command == "blacklist":
            if not message.mentions:
                await message.reply("Usage: `.blacklist @user`")
                return
            target_user = message.mentions[0]
            if has_admin_role(target_user):
                await message.reply("❌ You cannot blacklist administrators.")
                return
            if channel.id not in channel_blacklists:
                channel_blacklists[channel.id] = []
            if target_user.id not in channel_blacklists[channel.id]:
                channel_blacklists[channel.id].append(target_user.id)
                await channel.set_permissions(target_user, connect=False)
                await message.reply(f"🚫 {target_user.mention} has been blacklisted.")
            else:
                await message.reply(f"{target_user.mention} is already blacklisted.")

        elif command == "unblacklist":
            if not message.mentions:
                await message.reply("Usage: `.unblacklist @user`")
                return
            target_user = message.mentions[0]
            if channel.id in channel_blacklists and target_user.id in channel_blacklists[channel.id]:
                channel_blacklists[channel.id].remove(target_user.id)
                await channel.set_permissions(target_user, connect=None)
                await message.reply(f"✅ {target_user.mention} has been removed from the blacklist.")
            else:
                await message.reply(f"{target_user.mention} is not blacklisted.")

        elif command == "info":
            owner_id = temp_channels[channel.id]
            owner = message.guild.get_member(owner_id)
            embed = discord.Embed(title=f"📊 {channel.name} - Channel Info", color=discord.Color.blue())
            embed.add_field(name="👤 Owner", value=f"{owner.mention if owner else 'Unknown'}", inline=True)
            embed.add_field(name="👥 Members", value=f"`{len(channel.members)}`", inline=True)
            embed.add_field(name="📏 User Limit", value=f"`{channel.user_limit if channel.user_limit > 0 else 'Unlimited'}`", inline=True)
            embed.add_field(name="🔊 Bitrate", value=f"`{channel.bitrate // 1000}` kbps", inline=True)
            embed.add_field(name="🌍 Region", value=f"`{channel.region or 'Default'}`", inline=True)
            embed.add_field(name="📅 Created", value=f"`{channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}`", inline=True)
            if message.guild.icon:
                embed.set_thumbnail(url=message.guild.icon.url)
            await message.reply(embed=embed)

        elif command == "members" or command == "list":
            if not channel.members:
                await message.reply("No members in this channel.")
                return
            member_list = "\n".join([f"• {m.mention}" for m in channel.members])
            embed = discord.Embed(title=f"👥 Members in {channel.name}", description=member_list, color=discord.Color.green())
            embed.set_footer(text=f"Total: {len(channel.members)} members")
            await message.reply(embed=embed)

        elif command == "slowmode":
            if not args or not args[0].isdigit():
                await message.reply("Usage: `.slowmode <seconds>` (0-21600)")
                return
            slowmode = int(args[0])
            if slowmode < 0 or slowmode > 21600:
                await message.reply("Slowmode must be between 0 and 21600 seconds.")
                return
            await channel.edit(slowmode_delay=slowmode)
            slowmode_text = f"`{slowmode}` seconds" if slowmode > 0 else "disabled"
            await message.reply(f"⏱️ Chat slowmode set to {slowmode_text}.")

        elif command == "autodelete":
            if not args or not args[0].isdigit():
                await message.reply("Usage: `.autodelete <minutes>`")
                return
            minutes = int(args[0])
            if channel.id not in channel_settings:
                channel_settings[channel.id] = {}
            channel_settings[channel.id]['autodelete'] = minutes
            channel_last_activity[channel.id] = datetime.now()
            await message.reply(f"🗑️ Channel will auto-delete after `{minutes}` minutes of inactivity.")

        elif command == "schedule-delete":
            if not args:
                await message.reply("Usage: `.schedule-delete <minutes>`")
                return
            try:
                minutes = int(args[0])
                delete_time = datetime.now() + timedelta(minutes=minutes)
                scheduled_deletions[channel.id] = delete_time
                await message.reply(f"⏰ Channel scheduled for deletion in `{minutes}` minutes.")
            except ValueError:
                await message.reply("Please provide a valid number of minutes.")

        elif command == "timer":
            if not args or not args[0].isdigit():
                await message.reply("Usage: `.timer <minutes>`")
                return
            minutes = int(args[0])
            embed = discord.Embed(title="⏱️ Countdown Timer", description=f"Timer set for `{minutes}` minutes", color=discord.Color.red())
            await message.reply(embed=embed)
            
            total_seconds = minutes * 60
            for i in range(total_seconds, 0, -1):
                await asyncio.sleep(1)
            
            embed.description = "⏰ Time's up!"
            embed.color = discord.Color.green()
            try:
                await message.reply(embed=embed)
            except:
                pass

        elif command == "settings":
            embed = discord.Embed(title=f"⚙️ {channel.name} - Settings", color=discord.Color.purple())
            embed.add_field(name="🔒 Privacy", value="Locked ✅" if channel.changed_roles else "Unlocked 🔓", inline=True)
            embed.add_field(name="👥 User Limit", value=f"`{channel.user_limit if channel.user_limit > 0 else 'Unlimited'}`", inline=True)
            embed.add_field(name="⏱️ Slowmode", value=f"`{channel.slowmode_delay}s`" if channel.slowmode_delay > 0 else "Disabled", inline=True)
            
            if channel.id in channel_settings:
                settings = channel_settings[channel.id]
                if 'autodelete' in settings:
                    embed.add_field(name="🗑️ Auto-Delete", value=f"`{settings['autodelete']}` minutes", inline=True)
            
            whitelist_count = len(channel_whitelists.get(channel.id, []))
            blacklist_count = len(channel_blacklists.get(channel.id, []))
            embed.add_field(name="✅ Whitelisted", value=f"`{whitelist_count}` users", inline=True)
            embed.add_field(name="🚫 Blacklisted", value=f"`{blacklist_count}` users", inline=True)
            
            if channel.id in scheduled_deletions:
                delete_time = scheduled_deletions[channel.id]
                time_remaining = (delete_time - datetime.now()).total_seconds() / 60
                embed.add_field(name="⏰ Scheduled Delete", value=f"In `{int(time_remaining)}` minutes", inline=False)
            
            await message.reply(embed=embed)

        elif command == "reset":
            await channel.edit(name=f"{message.author.display_name}'s Channel", user_limit=0, slowmode_delay=0)
            await channel.set_permissions(message.guild.default_role, connect=True, send_messages=True)
            if channel.id in channel_settings:
                del channel_settings[channel.id]
            if channel.id in channel_whitelists:
                del channel_whitelists[channel.id]
            if channel.id in channel_blacklists:
                del channel_blacklists[channel.id]
            if channel.id in scheduled_deletions:
                del scheduled_deletions[channel.id]
            await message.reply("🔄 Channel has been reset to default settings.")

        elif command == "help":
            embed = discord.Embed(
                inline=False
            )
            embed.add_field(
                name="🔐 PRIVACY & ACCESS CONTROL",
                value=(
                    "• **🔒 `.lock`** - Private mode (owner only)\n"
                    "• **🔓 `.unlock`** - Public mode (anyone can join)\n"
                    "• **✅ `.allow @user`** - Grant user access\n"
                    "• **❌ `.deny @user`** - Revoke user access\n"
                    "• **📋 `.whitelist @user`** - Add to approved list\n"
                    "• **🚫 `.blacklist @user`** - Block user\n"
                    "• **♻️ `.unblacklist @user`** - Unblock user"
                ),
                inline=False
            )
            embed.add_field(
                name="💬 CHAT MANAGEMENT",
                value=(
                    "• **🔇 `.lockchat`** - Disable text chat\n"
                    "• **🔊 `.unlockchat`** - Enable text chat\n"
                    "• **🗑️ `.purge <number>`** - Delete messages (max 100)"
                ),
                inline=False
            )
            embed.add_field(
                name="👑 OWNERSHIP & INFORMATION",
                value=(
                    "• **👑 `.give @user`** - Transfer full ownership\n"
                    "• **🎯 `.claim`** - Claim channel if owner left\n"
                    "• **👢 `.kick @user`** - Kick user from channel\n"
                    "• **📊 `.info`** - Detailed channel information\n"
                    "• **👥 `.members` / `.list`** - List all members\n"
                    "• **⚙️ `.settings`** - View current configuration"
                ),
                inline=False
            )
            embed.add_field(
                name="🚀 ADVANCED FEATURES",
                value=(
                    "• **🗑️ `.autodelete <minutes>`** - Auto-delete after inactivity\n"
                    "• **⏰ `.schedule-delete <minutes>`** - Schedule channel deletion\n"
                    "• **⏱️ `.timer <minutes>`** - Start a countdown timer"
                ),
                inline=False
            )
            embed.add_field(
                name="📌 IMPORTANT NOTES",
                value=(
                    "✅ Only the channel owner can use these commands\n"
                    "⏱️ Channels auto-delete when everyone leaves\n"
                    "🔐 Use whitelist for private channels\n"
                    "📊 Use `.settings` to view current configuration"
                ),
                inline=False
            )
            if message.guild.icon:
                embed.set_thumbnail(url=message.guild.icon.url)
            embed.set_footer(text="💡 Need help? Use individual commands for more details!")
            await message.reply(embed=embed)

        elif command == "kick":
            if not message.mentions:
                await message.reply("Usage: `.kick @user`")
                return
            user_to_kick = message.mentions[0]
            
            if has_admin_role(user_to_kick):
                await message.reply("❌ You cannot kick administrators.")
                return
            
            if user_to_kick in channel.members:
                await user_to_kick.move_to(None, reason=f"Kicked by channel owner {message.author.name}")
                await message.reply(f"👢 {user_to_kick.mention} has been kicked from the channel.")
            else:
                await message.reply(f"{user_to_kick.mention} is not in this channel.")

        elif command == "purge":
            limit = int(args[0]) + 1 if args and args[0].isdigit() else 101
            deleted = await message.channel.purge(limit=limit)
            await message.channel.send(f"Deleted {len(deleted)} messages.", delete_after=5)

    except discord.Forbidden:
        await message.reply("I don't have the required permissions to do that.")
    except Exception as e:
        await message.reply("An unexpected error occurred.")
        print(f"Error processing command '{command}': {e}")
        
    # --- UTILITIES COMMANDS ---
    if resolved_cmd == "poll" and cmd.startswith(('.', '!')):
        log_command("poll")
        parts = message.content.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: `.poll <question> | <option1> | <option2> ...`")
            return
            
        poll_content = parts[1].strip()
        options_parts = poll_content.split('|')
        
        question = options_parts[0].strip()
        options = [opt.strip() for opt in options_parts[1:] if opt.strip()]
        
        if not options:
            # Simple Yes/No poll
            embed = discord.Embed(title="📊 Poll", description=f"**{question}**", color=discord.Color.blue())
            embed.set_footer(text=f"Requested by {message.author.display_name}")
            poll_msg = await message.channel.send(embed=embed)
            await poll_msg.add_reaction("👍")
            await poll_msg.add_reaction("👎")
            await message.delete()
        else:
            # Multi-choice poll
            if len(options) > 10:
                await message.reply("Too many options! Max 10.")
                return
                
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            desc = f"**{question}**\n\n"
            for i, opt in enumerate(options):
                desc += f"{emojis[i]} {opt}\n"
                
            embed = discord.Embed(title="📊 Poll", description=desc, color=discord.Color.blue())
            embed.set_footer(text=f"Requested by {message.author.display_name}")
            poll_msg = await message.channel.send(embed=embed)
            
            for i in range(len(options)):
                await poll_msg.add_reaction(emojis[i])
            await message.delete()
            
    elif resolved_cmd == "remind" and cmd.startswith(('.', '!')):
        log_command("remind")
        parts = message.content.split(maxsplit=2)
        if len(parts) < 3:
            await message.reply("Usage: `.remind <time> <message>`\n*Examples: 30m, 2h, 1d*")
            return
            
        time_str = parts[1].lower()
        reminder_msg = parts[2]
        
        minutes = 0
        if time_str.endswith('m'):
            minutes = int(time_str[:-1])
        elif time_str.endswith('h'):
            minutes = int(time_str[:-1]) * 60
        elif time_str.endswith('d'):
            minutes = int(time_str[:-1]) * 60 * 24
        else:
            await message.reply("❌ Invalid time format. Use something like `30m`, `2h`, or `1d`.")
            return
            
        if minutes <= 0:
            await message.reply("❌ Time must be positive.")
            return
            
        remind_at = datetime.now() + timedelta(minutes=minutes)
        reminders_list.append({
            "user_id": message.author.id,
            "remind_at": remind_at.isoformat(),
            "message": reminder_msg
        })
        save_reminders()
        
        await message.reply(f"✅ Okay! I'll remind you in **{time_str}** via DM.")

    # --- ECONOMY COMMANDS ---
    if resolved_cmd == "daily" and cmd.startswith(('.', '!')):
        log_command("daily")
        remaining = check_cooldown(message.author.id, "daily", 86400)
        if remaining > 0:
            hours = int(remaining) // 3600
            mins = (int(remaining) % 3600) // 60
            await message.reply(f"⏳ You already claimed your daily reward! Come back in `{hours}h {mins}m`.")
            return

        econ = get_economy(message.author.id)
        add_coins(message.author.id, 100)
        econ["last_daily"] = datetime.now().isoformat()
        save_economy()
        await message.reply("✅ Claimed **100 coins** as your daily reward! 🪙")
            
    elif resolved_cmd == "weekly" and cmd.startswith(('.', '!')):
        log_command("weekly")
        remaining = check_cooldown(message.author.id, "weekly", 604800)
        if remaining > 0:
            days = int(remaining) // 86400
            hours = (int(remaining) % 86400) // 3600
            await message.reply(f"⏳ You already claimed your weekly reward! Come back in `{days}d {hours}h`.")
            return

        econ = get_economy(message.author.id)
        add_coins(message.author.id, 500)
        econ["last_weekly"] = datetime.now().isoformat()
        save_economy()
        await message.reply("✅ Claimed **500 coins** as your weekly reward! 💸")
            
    elif resolved_cmd == "balance" and cmd.startswith(('.', '!')):
        log_command("balance")
        target = message.mentions[0] if message.mentions else message.author
        econ = get_economy(target.id)
        embed = discord.Embed(title=f"💳 {target.display_name}'s Wallet", color=discord.Color.gold())
        embed.add_field(name="🪙 Balance", value=f"**{econ['coins']}** coins", inline=True)
        embed.add_field(name="📈 Total Earned", value=f"**{econ['total_earned']}** coins", inline=True)
        if target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)
        await message.reply(embed=embed)
        
    elif resolved_cmd == "richlist" and cmd.startswith(('.', '!')):
        log_command("richlist")
        remaining = check_cooldown(message.author.id, "richlist", 10)
        if remaining > 0:
            await message.reply(f"⏳ Please wait {int(remaining)}s before viewing the richlist again.", delete_after=5)
            return
            
        sorted_users = sorted(economy_data.items(), key=lambda x: x[1].get('coins', 0), reverse=True)[:10]
        desc = ""
        for idx, (uid, data) in enumerate(sorted_users, 1):
            coins = data.get('coins', 0)
            desc += f"**{idx}.** <@{uid}> — **{coins}** 🪙\n"
        if not desc:
            desc = "No users have earned coins yet."
        embed = discord.Embed(title="💰 Top 10 Richest Users", description=desc, color=discord.Color.gold())
        await message.reply(embed=embed)
        
    elif resolved_cmd == "coinflip" and cmd.startswith(('.', '!')):
        log_command("coinflip")
        parts = message.content.split()
        bet = 10
        guess = "heads"
        if len(parts) > 1 and parts[1].isdigit():
            bet = int(parts[1])
        if len(parts) > 2 and parts[2].lower() in ["heads", "tails"]:
            guess = parts[2].lower()
            
        if not remove_coins(message.author.id, bet):
            await message.reply("❌ You don't have enough coins to make that bet.")
        else:
            result = random.choice(["heads", "tails"])
            if result == guess:
                add_coins(message.author.id, bet * 2)
                await message.reply(f"🪙 **{result.title()}!** You won **{bet}** coins!")
            else:
                await message.reply(f"🪙 **{result.title()}!** You lost **{bet}** coins.")
                
    elif resolved_cmd == "dice" and cmd.startswith(('.', '!')):
        log_command("dice")
        parts = message.content.split()
        bet = 10
        guess = 1
        if len(parts) > 1 and parts[1].isdigit():
            bet = int(parts[1])
        if len(parts) > 2 and parts[2].isdigit():
            guess = int(parts[2])
            if guess < 1 or guess > 6:
                await message.reply("❌ Guess must be between 1 and 6.")
                return
                
        if not remove_coins(message.author.id, bet):
            await message.reply("❌ You don't have enough coins to make that bet.")
        else:
            result = random.randint(1, 6)
            if result == guess:
                win_amount = bet * 5
                add_coins(message.author.id, win_amount + bet)
                await message.reply(f"🎲 **{result}!** Perfect guess! You won **{win_amount}** coins! 💰")
            else:
                await message.reply(f"🎲 **{result}!** Better luck next time. You lost **{bet}** coins.")

    elif resolved_cmd == "shop" and cmd.startswith(('.', '!')):
        log_command("shop")
        if not shop_items:
            await message.reply("The shop is currently empty.")
            return
        desc = ""
        for idx, item in enumerate(shop_items, 1):
            desc += f"**{idx}. {item['name']}** — 🪙 `{item['price']}` coins\n*{item['description']}* (ID: `{item['id']}`)\n\n"
        embed = discord.Embed(title="🛒 Coin Shop", description=desc, color=discord.Color.green())
        embed.set_footer(text="Use .buy <item_id> to purchase an item.")
        await message.reply(embed=embed)
        
    elif resolved_cmd == "buy" and cmd.startswith(('.', '!')):
        log_command("buy")
        parts = message.content.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: `.buy <item_id>`")
            return
        item_id = parts[1].lower()
        item = next((i for i in shop_items if i['id'].lower() == item_id), None)
        if not item:
            await message.reply("❌ Item not found in the shop.")
            return
            
        if not remove_coins(message.author.id, item['price']):
            await message.reply(f"❌ You don't have enough coins. That costs **{item['price']}** 🪙.")
        else:
            econ = economy_data[str(message.author.id)]
            
            if item_id == "channel_rename_token":
                econ['rename_tokens'] = econ.get('rename_tokens', 0) + 1
                await message.reply(f"✅ Successfully purchased **{item['name']}** for **{item['price']}** 🪙! You can now use `/temp rename`.")
                
            elif item_id == "xp_boost_24h":
                expiry = datetime.now() + timedelta(hours=24)
                econ['xp_boost_active_until'] = expiry.isoformat()
                await message.reply(f"✅ Successfully purchased **{item['name']}** for **{item['price']}** 🪙! You will earn double XP for the next 24 hours.")
                
            save_economy()

    # --- MODERATION COMMANDS ---
    base_cmd = message.content.lower()
    
    # Check if user has moderation previleges
    is_mod = False
    if isinstance(message.author, discord.Member):
        if message.author.guild_permissions.manage_messages:
            is_mod = True
        elif MOD_ROLE_ID:
            mod_role_id = int(MOD_ROLE_ID)
            for r in message.author.roles:
                if r.id == mod_role_id:
                    is_mod = True
                    break

    if is_mod:
        if base_cmd.startswith('.warn '):
            parts = message.content.split(maxsplit=2)
            if len(parts) >= 3 and message.mentions:
                target = message.mentions[0]
                reason = parts[2]
                await warn_user(target, reason, message.author)
                await message.channel.send(f"✅ Warned {target.mention} for: {reason}")
            else:
                await message.channel.send("Usage: `.warn @user [reason]`")
            return

        elif base_cmd.startswith('.warnings '):
            if message.mentions:
                target = message.mentions[0]
                uid = str(target.id)
                warns = warnings_data.get(uid, [])
                if not warns:
                    await message.channel.send(f"✅ {target.display_name} has no warnings.")
                else:
                    desc = ""
                    for i, w in enumerate(warns, 1):
                        desc += f"**{i}.** {w.get('timestamp', 'Unknown')[:10]} - {w.get('reason')} (Mod ID: {w.get('mod_id', 'Unknown')})\n"
                    embed = discord.Embed(title=f"Warnings for {target.display_name}", description=desc, color=discord.Color.orange())
                    await message.channel.send(embed=embed)
            return

        elif base_cmd.startswith('.clearwarn '):
            parts = message.content.split()
            if len(parts) >= 3 and message.mentions:
                target = message.mentions[0]
                uid = str(target.id)
                try:
                    warn_index = int(parts[2]) - 1
                except ValueError:
                    await message.channel.send("Usage: `.clearwarn @user <index>`")
                    return
                    
                if uid in warnings_data and 0 <= warn_index < len(warnings_data[uid]):
                    removed_warn = warnings_data[uid].pop(warn_index)
                    if not warnings_data[uid]:
                        del warnings_data[uid]
                    save_warnings()
                    await log_mod_action("clearwarn", target, message.author, "Cleared warning index " + str(warn_index + 1))
                    await message.channel.send(f"✅ Cleared warning #{warn_index + 1} for {target.display_name}.")
                else:
                    await message.channel.send(f"❌ {target.display_name} has no warning at that index.")
            else:
                 await message.channel.send("Usage: `.clearwarn @user <index>`")
            return

        elif base_cmd.startswith('.slowmode '):
            parts = message.content.split(maxsplit=1)
            if len(parts) > 1:
                preset = parts[1].lower()
                delay = 0
                if preset == "off" or preset == "0": delay = 0
                elif preset == "relaxed" or preset == "5": delay = 5
                elif preset == "moderate" or preset == "15": delay = 15
                elif preset == "strict" or preset == "30": delay = 30
                else:
                    try:
                        delay = int(preset)
                    except ValueError:
                        await message.channel.send("❌ Invalid preset. Use: `off`, `relaxed`, `moderate`, `strict` or a number in seconds.")
                        return

                try:
                    await message.channel.edit(slowmode_delay=delay)
                    status = f"{delay} seconds" if delay > 0 else "disabled"
                    await message.channel.send(f"✅ Slowmode is now {status} in this channel.")
                except discord.Forbidden:
                    await message.channel.send("❌ I do not have permission to manage this channel.")
            else:
                await message.channel.send("Usage: `.slowmode [off|relaxed|moderate|strict|seconds]`")
            return

# ══════════════════════════════════════════════════════════════════════════════
# BUILT-IN WEB DASHBOARD  (stdlib only — zero extra packages)
#
# Activate by adding to Data/config.json:
#   "dashboard_enabled": true,
#   "dashboard_secret":  "yourpassword",
#   "dashboard_port":    8080
#
# Then open  http://your-server-ip:8080  in a browser.
# ══════════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BOTCTL Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#060b12;--bg2:#0a1120;--sidebar:#0c1422;--card:#0f1929;--card2:#111f33;--border:#1a2d47;--border2:#243855;--accent:#00d9ff;--adim:rgba(0,217,255,.12);--aglow:rgba(0,217,255,.25);--purple:#a855f7;--pdim:rgba(168,85,247,.12);--green:#10b981;--gdim:rgba(16,185,129,.12);--yellow:#f59e0b;--ydim:rgba(245,158,11,.12);--red:#ef4444;--rdim:rgba(239,68,68,.12);--text:#e2e8f0;--dim:#94a3b8;--muted:#4a6080;--r:8px;--mono:'IBM Plex Mono',monospace;--display:'Rajdhani',sans-serif;--sw:235px}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--mono);background:var(--bg);color:var(--text);min-height:100vh;display:flex;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,217,255,.02) 1px,transparent 1px),linear-gradient(90deg,rgba(0,217,255,.02) 1px,transparent 1px);background-size:50px 50px;pointer-events:none;z-index:0}
.sidebar{width:var(--sw);min-height:100vh;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;position:fixed;left:0;top:0;bottom:0;z-index:30;overflow-y:auto}
.sb-brand{padding:20px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;flex-shrink:0}
.b-icon{width:36px;height:36px;background:linear-gradient(135deg,var(--accent),var(--purple));border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;box-shadow:0 0 14px rgba(0,217,255,.3)}
.b-name{font-family:var(--display);font-size:19px;font-weight:700;letter-spacing:2px}
.b-ver{font-size:9px;color:var(--muted);letter-spacing:1px;margin-top:1px}
.nav{flex:1;padding:8px;display:flex;flex-direction:column;gap:1px}
.ns{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:2px;padding:12px 10px 4px}
.ni{display:flex;align-items:center;gap:9px;padding:8px 11px;border-radius:var(--r);cursor:pointer;color:var(--dim);font-size:11.5px;transition:all .15s;border:1px solid transparent;user-select:none}
.ni:hover{background:rgba(255,255,255,.04);color:var(--text)}
.ni.active{background:var(--adim);color:var(--accent);border-color:rgba(0,217,255,.2)}
.ni-ic{font-size:13px;width:16px;text-align:center;flex-shrink:0}
.sb-foot{padding:8px;border-top:1px solid var(--border);flex-shrink:0}
.logout{display:flex;align-items:center;gap:9px;padding:8px 11px;border-radius:var(--r);cursor:pointer;color:var(--red);font-size:11.5px;transition:all .15s;background:transparent;border:none;width:100%;font-family:var(--mono)}
.logout:hover{background:var(--rdim)}
.main{margin-left:var(--sw);flex:1;position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column}
.pg-hdr{padding:20px 28px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:rgba(6,11,18,.85);backdrop-filter:blur(6px);position:sticky;top:0;z-index:10}
.pg-title{font-family:var(--display);font-size:22px;font-weight:700;letter-spacing:2px}
.pg-sub{font-size:10px;color:var(--muted);letter-spacing:1px;margin-top:2px}
.sdot{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--muted)}
.dg{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 7px var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.pg-body{padding:22px 28px;flex:1}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:18px;margin-bottom:14px}
.card:hover{border-color:var(--border2)}
.ct{font-family:var(--display);font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:2px;margin-bottom:14px}
.sg{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:12px;margin-bottom:14px}
.sc{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:16px 18px;position:relative;overflow:hidden;transition:all .2s}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--c,var(--accent));opacity:.7}
.sc:hover{border-color:var(--c,var(--accent));transform:translateY(-1px);box-shadow:0 6px 24px rgba(0,0,0,.3)}
.sc-i{font-size:18px;margin-bottom:8px}
.sc-v{font-family:var(--display);font-size:26px;font-weight:700;color:var(--c,var(--accent));line-height:1}
.sc-l{font-size:9px;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:1px}
.tw{overflow-x:auto;border-radius:6px}
table{width:100%;border-collapse:collapse;font-size:11.5px}
th{text-align:left;padding:8px 11px;color:var(--muted);font-size:8.5px;text-transform:uppercase;letter-spacing:2px;border-bottom:1px solid var(--border);white-space:nowrap;font-weight:600;background:var(--bg2)}
td{padding:9px 11px;border-bottom:1px solid rgba(26,45,71,.4);color:var(--dim)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.025);color:var(--text)}
.btn{display:inline-flex;align-items:center;gap:5px;padding:7px 13px;border-radius:var(--r);font-family:var(--mono);font-size:10.5px;cursor:pointer;border:none;transition:all .15s;white-space:nowrap;font-weight:500}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-p{background:var(--accent);color:#000}.btn-p:hover:not(:disabled){opacity:.85;box-shadow:0 0 10px var(--aglow)}
.btn-g{background:transparent;color:var(--dim);border:1px solid var(--border)}.btn-g:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}
.btn-d{background:var(--red);color:#fff}.btn-d:hover:not(:disabled){opacity:.82}
.btn-s{background:var(--green);color:#000}.btn-s:hover:not(:disabled){opacity:.85}
.btn-sm{padding:4px 9px;font-size:9.5px}
.tabs{display:flex;gap:3px;margin-bottom:18px;flex-wrap:wrap}
.tab{padding:7px 14px;border-radius:var(--r);font-family:var(--mono);font-size:10.5px;cursor:pointer;color:var(--muted);background:transparent;border:1px solid var(--border);transition:all .15s}
.tab:hover{color:var(--text);border-color:var(--border2)}
.tab.active{background:var(--adim);color:var(--accent);border-color:rgba(0,217,255,.3)}
.fg{display:flex;flex-direction:column;gap:4px;margin-bottom:2px}
label{font-size:8.5px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;font-weight:600}
input,textarea,select{background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);color:var(--text);font-family:var(--mono);font-size:11.5px;padding:8px 11px;outline:none;transition:border-color .15s;width:100%}
input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--adim)}
.search-wrap{position:relative;margin-bottom:12px}
.search-wrap input{padding-left:32px;background:var(--bg2)}
.search-ic{position:absolute;left:11px;top:50%;transform:translateY(-50%);font-size:13px;pointer-events:none;opacity:.5}
.toggle{width:40px;height:21px;background:var(--border);border-radius:11px;position:relative;cursor:pointer;transition:background .2s;border:none;flex-shrink:0}
.toggle.on{background:var(--accent)}
.toggle::after{content:'';position:absolute;width:15px;height:15px;background:#fff;border-radius:50%;top:3px;left:3px;transition:transform .2s;box-shadow:0 1px 3px rgba(0,0,0,.3)}
.toggle.on::after{transform:translateX(19px)}
.badge{display:inline-block;padding:2px 6px;border-radius:4px;font-size:8.5px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.bg{background:var(--gdim);color:var(--green)}.br{background:var(--rdim);color:var(--red)}.by{background:var(--ydim);color:var(--yellow)}.bb{background:var(--adim);color:var(--accent)}.bp{background:var(--pdim);color:var(--purple)}
#toast-root{position:fixed;bottom:22px;right:22px;display:flex;flex-direction:column;gap:7px;z-index:9999}
.toast{background:var(--card2);border:1px solid var(--border2);border-radius:var(--r);padding:11px 15px;font-size:11.5px;display:flex;align-items:center;gap:9px;min-width:210px;max-width:330px;animation:tIn .2s ease;box-shadow:0 8px 24px rgba(0,0,0,.5)}
.toast.s{border-left:3px solid var(--green)}.toast.e{border-left:3px solid var(--red)}.toast.i{border-left:3px solid var(--accent)}
@keyframes tIn{from{transform:translateX(110%);opacity:0}to{transform:translateX(0);opacity:1}}
.modal-back{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(3px)}
.modal{background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:28px;width:420px;max-width:95vw;box-shadow:0 20px 60px rgba(0,0,0,.6)}
.modal-title{font-family:var(--display);font-size:17px;font-weight:700;margin-bottom:8px}
.modal-msg{font-size:12px;color:var(--dim);margin-bottom:22px;line-height:1.6}
.modal-actions{display:flex;gap:8px;justify-content:flex-end}
.uavatar-ph{width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--purple));display:flex;align-items:center;justify-content:center;font-size:11px;color:#fff;flex-shrink:0;font-weight:700}
.urow{display:flex;align-items:center;gap:8px}
.uname{font-size:12px;color:var(--text);font-weight:500}
.utag{font-size:9.5px;color:var(--muted)}
.prog-wrap{flex:1;background:var(--border);border-radius:3px;height:5px;overflow:hidden;min-width:60px}
.prog-fill{height:100%;border-radius:3px;transition:width .5s ease}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.flex{display:flex}.aic{align-items:center}.jb{justify-content:space-between}
.mb3{margin-bottom:12px}.mb4{margin-bottom:16px}.mb5{margin-bottom:20px}
.muted{color:var(--muted);font-size:10.5px}.accent{color:var(--accent)}
.spin{width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:sp .5s linear infinite;display:inline-block}
@keyframes sp{to{transform:rotate(360deg)}}
.loading{display:flex;align-items:center;justify-content:center;padding:60px}
.empty{text-align:center;padding:40px 20px}.empty .ei{font-size:32px;margin-bottom:8px}.empty p{font-size:11px;color:var(--muted)}
.lw{min-height:100vh;display:flex;align-items:center;justify-content:center;position:relative;z-index:1}
.lb{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:44px 38px;width:370px;text-align:center;box-shadow:0 0 60px rgba(0,0,0,.7),0 0 40px rgba(0,217,255,.06)}
.ll{width:64px;height:64px;background:linear-gradient(135deg,var(--accent),var(--purple));border-radius:16px;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;font-size:28px;box-shadow:0 0 28px rgba(0,217,255,.4)}
.lt{font-family:var(--display);font-size:24px;font-weight:700;letter-spacing:3px}
.ls{font-size:10px;color:var(--muted);margin-top:3px;margin-bottom:26px;letter-spacing:1px}
.le{color:var(--red);font-size:10.5px;margin-bottom:9px}
.lh{margin-top:20px;font-size:9.5px;color:var(--muted);line-height:1.9}
.br-row{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid rgba(26,45,71,.35)}
.br-row:last-child{border-bottom:none}
.br-lbl{font-size:10.5px;color:var(--dim);width:110px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.br-tr{flex:1;background:var(--border);border-radius:3px;height:5px;overflow:hidden}
.br-fill{height:100%;border-radius:3px;transition:width .45s ease}
.br-num{font-size:10px;color:var(--muted);width:36px;text-align:right;flex-shrink:0}
.ii{padding:4px 8px;font-size:10.5px;background:var(--bg2);border:1px solid var(--border);border-radius:4px;color:var(--text);font-family:var(--mono);outline:none;transition:border-color .15s}
.ii:focus{border-color:var(--accent)}
.lvl-badge{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;border:2px solid var(--c,var(--accent));font-family:var(--display);font-size:13px;font-weight:700;color:var(--c,var(--accent));flex-shrink:0}
.refresh-btn{font-size:12px;cursor:pointer;color:var(--muted);background:none;border:none;padding:4px;border-radius:4px;transition:all .15s}
.refresh-btn:hover{color:var(--accent);transform:rotate(180deg)}
::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
</style>
</head>
<body>
<div id="root"></div>
<div id="toast-root"></div>
<script src="https://unpkg.com/react@18/umd/react.development.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<script type="text/babel">
const {useState,useEffect,useRef,useCallback}=React;
const hdr=()=>({'X-Dashboard-Secret':localStorage.getItem('ds_tok')||'','Content-Type':'application/json'});
const api={
  get:p=>fetch(p,{headers:hdr()}).then(r=>{if(!r.ok)throw r.status;return r.json()}),
  patch:(p,b)=>fetch(p,{method:'PATCH',headers:hdr(),body:JSON.stringify(b)}).then(r=>{if(!r.ok)throw r.status;return r.json()}),
  post:(p,b)=>fetch(p,{method:'POST',headers:hdr(),body:JSON.stringify(b)}).then(r=>{if(!r.ok)throw r.status;return r.json()}),
  del:p=>fetch(p,{method:'DELETE',headers:hdr()}).then(r=>{if(!r.ok)throw r.status;return r.json()}),
};
let _addToast=null;
const toast={ok:m=>_addToast?.({t:'s',m}),err:m=>_addToast?.({t:'e',m}),inf:m=>_addToast?.({t:'i',m})};
function Toasts(){
  const[list,setList]=useState([]);const id=useRef(0);
  useEffect(()=>{_addToast=item=>{const i=++id.current;setList(p=>[...p,{...item,id:i}]);setTimeout(()=>setList(p=>p.filter(x=>x.id!==i)),3400);};},[]);
  const ic={s:'✓',e:'✕',i:'·'};const cl={s:'var(--green)',e:'var(--red)',i:'var(--accent)'};
  return ReactDOM.createPortal(list.map(x=><div key={x.id} className={`toast ${x.t}`}><span style={{color:cl[x.t],fontWeight:700}}>{ic[x.t]}</span>{x.m}</div>),document.getElementById('toast-root'));
}
let _showConfirm=null;
function ConfirmModal(){
  const[cfg,setCfg]=useState(null);
  useEffect(()=>{_showConfirm=c=>setCfg(c);},[]);
  if(!cfg)return null;
  return<div className="modal-back" onClick={()=>setCfg(null)}><div className="modal" onClick={e=>e.stopPropagation()}>
    <div className="modal-title">{cfg.title}</div><div className="modal-msg">{cfg.msg}</div>
    <div className="modal-actions"><button className="btn btn-g" onClick={()=>setCfg(null)}>Cancel</button>
    <button className={`btn ${cfg.danger?'btn-d':'btn-p'}`} onClick={()=>{cfg.onOk();setCfg(null);}}>Confirm</button></div>
  </div></div>;
}
const confirm=(title,msg,onOk,danger=false)=>_showConfirm?.({title,msg,onOk,danger});
const Spin=({s=16})=><div className="spin" style={{width:s,height:s}}/>;
const Loading=()=><div className="loading"><Spin s={22}/></div>;
const Empty=({icon='📭',msg='No data'})=><div className="empty"><div className="ei">{icon}</div><p>{msg}</p></div>;
const RefreshBtn=({onClick})=><button className="refresh-btn" onClick={onClick} title="Refresh">↻</button>;
function Badge({type='b',children}){return<span className={`badge b${type}`}>{children}</span>;}
function Search({value,onChange,placeholder='Search...'}){return<div className="search-wrap"><span className="search-ic">🔍</span><input value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}/></div>;}
function UserCell({uid,users}){
  const u=users?.[uid];
  const init=(u?.display_name||u?.username||uid).substring(0,2).toUpperCase();
  return<div className="urow"><div className="uavatar-ph">{init}</div>
    <div><div className="uname">{u?.display_name||u?.username||<span style={{color:'var(--muted)',fontSize:10}}>{uid}</span>}</div>
    <div className="utag">{u?.username?`@${u.username}`:uid}</div></div></div>;
}
function calcLevel(v,t,reqs){
  let lvl=0;const keys=Object.keys(reqs).map(Number).sort((a,b)=>a-b);
  for(const k of keys){const r=reqs[String(k)];if(v>=r.voice_minutes_required&&t>=r.text_minutes_required)lvl=k;else break;}
  return lvl;
}
function lvlColor(l){if(l>=100)return'var(--yellow)';if(l>=50)return'var(--purple)';if(l>=25)return'var(--accent)';if(l>=10)return'var(--green)';return'var(--dim)';}
function Login({onLogin}){
  const[sec,setSec]=useState('');const[busy,setBusy]=useState(false);const[err,setErr]=useState('');
  const go=async e=>{e.preventDefault();setBusy(true);setErr('');
    try{const r=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({secret:sec})});
      if(!r.ok)throw 0;localStorage.setItem('ds_tok',sec);onLogin();}catch{setErr('Wrong secret.');}setBusy(false);};
  return<div className="lw"><div className="lb"><div className="ll">🤖</div><div className="lt">BOTCTL</div>
    <div className="ls">DASHBOARD — ENTER SECRET</div>
    <form onSubmit={go}><div className="fg" style={{textAlign:'left',marginBottom:9}}><label>Secret Key</label>
    <input type="password" value={sec} onChange={e=>setSec(e.target.value)} required autoFocus/></div>
    {err&&<div className="le">{err}</div>}
    <button type="submit" className="btn btn-p" style={{width:'100%',justifyContent:'center',padding:10}} disabled={busy}>{busy?<Spin/>:'→ ENTER'}</button></form>
    <div className="lh">Set in Data/config.json:<br/><span className="accent">"dashboard_secret": "yourpassword"</span></div>
  </div></div>;
}
const NAV=[
  {id:'overview',icon:'⬡',label:'Overview'},
  {s:'Manage'},{id:'config',icon:'⚙',label:'Config'},
  {id:'moderation',icon:'🛡',label:'Moderation'},
  {id:'economy',icon:'🪙',label:'Economy'},
  {id:'levels',icon:'⬆',label:'Levels'},
  {s:'Features'},{id:'channels',icon:'🎙',label:'Temp Channels'},
  {id:'tickets',icon:'🎫',label:'Tickets'},
  {id:'shop',icon:'🏪',label:'Shop'},
  {id:'rxroles',icon:'😊',label:'Reaction Roles'},
  {s:'Insights'},{id:'analytics',icon:'📊',label:'Analytics'},
];
function Sidebar({page,setPage,logout}){
  return<div className="sidebar">
    <div className="sb-brand"><div className="b-icon">🤖</div><div><div className="b-name">BOTCTL</div><div className="b-ver">v3 · PERSISTENT DB</div></div></div>
    <div className="nav">{NAV.map((n,i)=>n.s?<div key={i} className="ns">{n.s}</div>:<div key={n.id} className={`ni ${page===n.id?'active':''}`} onClick={()=>setPage(n.id)}><span className="ni-ic">{n.icon}</span>{n.label}</div>)}</div>
    <div className="sb-foot"><button className="logout" onClick={logout}><span className="ni-ic">⏻</span>Logout</button></div>
  </div>;
}
function OverviewPage({users}){
  const[ov,setOv]=useState(null);const[an,setAn]=useState({});const[loading,setLoading]=useState(true);
  const load=()=>{setLoading(true);Promise.all([api.get('/api/overview'),api.get('/api/analytics')])
    .then(([o,a])=>{setOv(o);setAn(a||{});}).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));};
  useEffect(()=>load(),[]);
  if(loading)return<Loading/>;
  const stats=[
    {icon:'👥',label:'Users Tracked',val:ov?.total_users??0,c:'var(--accent)'},
    {icon:'🪙',label:'Total Coins',val:(ov?.total_coins??0).toLocaleString(),c:'var(--yellow)'},
    {icon:'🎙',label:'Active Channels',val:ov?.active_channels??0,c:'var(--purple)'},
    {icon:'🎫',label:'Open Tickets',val:ov?.open_tickets??0,c:'var(--green)'},
    {icon:'⚠️',label:'Total Warnings',val:ov?.total_warnings??0,c:'var(--red)'},
    {icon:'🏆',label:'Top Command',val:ov?.top_command??'—',c:'var(--accent)'},
  ];
  const cmds=Object.entries(an).sort((a,b)=>b[1].total-a[1].total).slice(0,10);
  const maxV=cmds[0]?.[1]?.total||1;
  return<div className="pg-body">
    <div className="sg">{stats.map((s,i)=><div key={i} className="sc" style={{'--c':s.c}}><div className="sc-i">{s.icon}</div><div className="sc-v">{s.val}</div><div className="sc-l">{s.label}</div></div>)}</div>
    <div className="card"><div className="flex jb aic" style={{marginBottom:14}}><div className="ct" style={{marginBottom:0}}>Command Usage</div><RefreshBtn onClick={load}/></div>
      {!cmds.length?<Empty icon="📊" msg="No analytics yet"/>:cmds.map(([cmd,d])=><div key={cmd} className="br-row">
        <div className="br-lbl"><code style={{color:'var(--accent)',fontSize:10.5}}>.{cmd}</code></div>
        <div className="br-tr"><div className="br-fill" style={{width:`${(d.total/maxV)*100}%`,background:'var(--accent)'}}/></div>
        <div className="br-num">{d.total}</div></div>)}
    </div>
  </div>;
}
function ConfigPage(){
  const[cfg,setCfg]=useState(null);const[loading,setLoading]=useState(true);const[saving,setSaving]=useState(false);
  useEffect(()=>{api.get('/api/config').then(setCfg).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));},[]);
  const save=async()=>{setSaving(true);try{await api.patch('/api/config',cfg);toast.ok('Saved ✓');}catch{toast.err('Failed');}setSaving(false);};
  if(loading)return<Loading/>;
  const F=({k,label,type='text'})=><div className="fg"><label>{label}</label>
    <input type={type} step={type==='number'?'0.1':undefined} value={cfg?.[k]??''}
      onChange={e=>setCfg({...cfg,[k]:type==='number'?parseFloat(e.target.value)||0:e.target.value})}/></div>;
  return<div className="pg-body">
    <div className="flex jb aic mb5"><span className="muted">Changes saved to Data/config.json</span>
      <button className="btn btn-p" onClick={save} disabled={saving}>{saving?<Spin/>:'💾 Save All'}</button></div>
    <div className="g2 mb4">
      <div className="card"><div className="ct">Channel IDs</div><div style={{display:'flex',flexDirection:'column',gap:10}}>
        <F k="creator_channel_id" label="Creator Channel ID"/><F k="temp_channel_category_id" label="Temp Category ID"/>
        <F k="levelup_channel_id" label="Level Up Channel ID"/></div></div>
      <div className="card"><div className="ct">Moderation / Tickets</div><div style={{display:'flex',flexDirection:'column',gap:10}}>
        <F k="mod_role_id" label="Moderator Role ID"/><F k="ticket_category_id" label="Ticket Category ID"/>
        <F k="ticket_log_channel_id" label="Ticket Log Channel ID"/></div></div>
    </div>
    <div className="g2 mb4">
      <div className="card"><div className="ct">Welcome / Leave</div><div style={{display:'flex',flexDirection:'column',gap:10}}>
        <F k="welcome_channel_id" label="Welcome Channel ID"/><F k="leave_channel_id" label="Leave Channel ID"/>
        <F k="welcome_message" label="Welcome Message"/><F k="leave_message" label="Leave Message"/></div></div>
      <div className="card"><div className="ct">XP & Multipliers</div><div style={{display:'flex',flexDirection:'column',gap:10}}>
        <F k="xp_multiplier" label="Base XP Multiplier" type="number"/>
        <F k="weekend_multiplier" label="Weekend Multiplier" type="number"/>
        <F k="special_event_multiplier" label="Event Multiplier" type="number"/>
        <F k="levelup_message" label="Level Up Message"/>
        <div className="flex jb aic" style={{padding:'10px 0',borderTop:'1px solid var(--border)',marginTop:4}}>
          <div><div style={{fontSize:12,marginBottom:2}}>Special Event Active</div><div className="muted">Enables event multiplier</div></div>
          <button className={`toggle ${cfg?.event_active?'on':''}`} onClick={()=>setCfg({...cfg,event_active:!cfg?.event_active})}/>
        </div></div></div>
    </div>
    <div className="card"><div className="ct">Dashboard</div><div className="g3" style={{gap:12}}>
      <F k="dashboard_port" label="Dashboard Port" type="number"/>
      <F k="dashboard_secret" label="Dashboard Secret"/>
      <div className="fg"><label>Dashboard Enabled</label>
        <button className={`toggle ${cfg?.dashboard_enabled?'on':''}`} onClick={()=>setCfg({...cfg,dashboard_enabled:!cfg?.dashboard_enabled})} style={{marginTop:8}}/>
      </div></div></div>
  </div>;
}
function ModerationPage({users}){
  const[tab,setTab]=useState('warnings');
  const[warns,setWarns]=useState({});const[log,setLog]=useState([]);const[am,setAm]=useState({});
  const[loading,setLoading]=useState(true);const[q,setQ]=useState('');
  const load=()=>{setLoading(true);Promise.all([api.get('/api/moderation/warnings'),api.get('/api/moderation/mod-log'),api.get('/api/moderation/automod')])
    .then(([w,ml,a])=>{setWarns(w||{});setLog(Array.isArray(ml)?ml:[]);setAm(a||{});}).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));};
  useEffect(()=>load(),[]);
  const clearWarn=uid=>confirm('Clear Warnings','Remove ALL warnings for this user?',async()=>{
    try{await api.del(`/api/moderation/warnings/${uid}`);const w={...warns};delete w[uid];setWarns(w);toast.ok('Cleared');}catch{toast.err('Failed');}},true);
  const saveAm=async()=>{try{await api.patch('/api/moderation/automod',am);toast.ok('AutoMod saved');}catch{toast.err('Failed');}};
  if(loading)return<Loading/>;
  const getName=uid=>users?.[uid]?.display_name||users?.[uid]?.username||uid;
  const filtW=Object.entries(warns).filter(([uid])=>{const n=getName(uid).toLowerCase();return n.includes(q.toLowerCase())||uid.includes(q);});
  const filtL=[...log].reverse().slice(0,200).filter(e=>{const s=q.toLowerCase();return(e.target_name||'').toLowerCase().includes(s)||(e.mod_name||'').toLowerCase().includes(s)||(e.action||'').includes(s)||(e.reason||'').toLowerCase().includes(s);});
  return<div className="pg-body">
    <div className="tabs">
      {[['warnings',`⚠️ Warnings (${Object.keys(warns).length})`],['mod-log',`📋 Log (${log.length})`],['automod','🤖 AutoMod']].map(([id,lbl])=>
        <button key={id} className={`tab ${tab===id?'active':''}`} onClick={()=>{setTab(id);setQ('')}}>{lbl}</button>)}
      <button className="refresh-btn" onClick={load} style={{marginLeft:'auto',padding:'7px 10px'}}>↻</button>
    </div>
    {tab==='warnings'&&<div className="card"><Search value={q} onChange={setQ} placeholder="Search by name or ID..."/>
      {!filtW.length?<Empty icon="✅" msg="No warnings"/>:
      <div className="tw"><table><thead><tr><th>User</th><th>Warnings</th><th>Latest Reason</th><th>Date</th><th>Action</th></tr></thead>
      <tbody>{filtW.sort((a,b)=>b[1].length-a[1].length).map(([uid,w])=>{const last=w[w.length-1];return<tr key={uid}>
        <td><UserCell uid={uid} users={users}/></td>
        <td><Badge type={w.length>=5?'r':w.length>=3?'y':'b'}>{w.length}</Badge></td>
        <td style={{maxWidth:200,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:11}}>{last?.reason||'—'}</td>
        <td style={{fontSize:10,color:'var(--muted)'}}>{last?.timestamp?.slice(0,10)||'—'}</td>
        <td><button className="btn btn-d btn-sm" onClick={()=>clearWarn(uid)}>🗑 Clear</button></td>
      </tr>;})}
      </tbody></table></div>}
    </div>}
    {tab==='mod-log'&&<div className="card"><Search value={q} onChange={setQ} placeholder="Search action, user, reason..."/>
      {!filtL.length?<Empty icon="📋" msg="No log entries"/>:
      <div className="tw"><table><thead><tr><th>Time</th><th>Action</th><th>Target</th><th>Moderator</th><th>Reason</th></tr></thead>
      <tbody>{filtL.slice(0,100).map((e,i)=><tr key={i}>
        <td style={{whiteSpace:'nowrap',fontSize:10}}>{e.timestamp?new Date(e.timestamp).toLocaleString():'—'}</td>
        <td><Badge type={['ban','kick'].includes(e.action)?'r':['warn','timeout'].includes(e.action)?'y':'b'}>{e.action||'—'}</Badge></td>
        <td style={{fontSize:11}}>{e.target_id?users?.[e.target_id]?.display_name||e.target_name||e.target_id:e.target_name||'—'}</td>
        <td style={{fontSize:11,color:'var(--muted)'}}>{e.mod_id?users?.[e.mod_id]?.display_name||e.mod_name||e.mod_id:e.mod_name||'—'}</td>
        <td style={{maxWidth:220,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:10,color:'var(--muted)'}}>{e.reason||'—'}</td>
      </tr>)}</tbody></table></div>}
    </div>}
    {tab==='automod'&&<div className="card"><div className="ct">AutoMod Rules</div>
      <div style={{maxWidth:520,display:'flex',flexDirection:'column',gap:14}}>
        <div className="fg"><label>Mention Limit</label><input type="number" min={1} max={50} value={am.mention_limit??5} onChange={e=>setAm({...am,mention_limit:parseInt(e.target.value)||5})}/></div>
        <div className="fg"><label>Message Cooldown (seconds)</label><input type="number" min={0} max={60} value={am.message_cooldown_seconds??2} onChange={e=>setAm({...am,message_cooldown_seconds:parseInt(e.target.value)||2})}/></div>
        <div className="fg"><label>Allowed Domains (comma-separated)</label>
          <textarea rows={3} value={(am.allowed_domains||[]).join(', ')} onChange={e=>setAm({...am,allowed_domains:e.target.value.split(',').map(s=>s.trim()).filter(Boolean)})} placeholder="github.com, youtube.com"/></div>
        <button className="btn btn-p" onClick={saveAm}>💾 Save AutoMod</button>
      </div></div>}
  </div>;
}
function EconomyPage({users}){
  const[data,setData]=useState({});const[loading,setLoading]=useState(true);
  const[editId,setEditId]=useState(null);const[editVal,setEditVal]=useState('');
  const[addModal,setAddModal]=useState(null);const[addVal,setAddVal]=useState('');const[q,setQ]=useState('');
  const load=()=>{setLoading(true);api.get('/api/economy').then(setData).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));};
  useEffect(()=>load(),[]);
  const saveCoins=async uid=>{const val=parseInt(editVal);if(isNaN(val))return toast.err('Invalid number');
    try{const r=await api.patch(`/api/economy/${uid}`,{coins:val});setData({...data,[uid]:{...data[uid],coins:r.coins}});setEditId(null);toast.ok('Updated');}catch{toast.err('Failed');}};
  const addCoins=async(uid,amount)=>{const cur=data[uid]?.coins||0;
    try{const r=await api.patch(`/api/economy/${uid}`,{coins:cur+amount});setData({...data,[uid]:{...data[uid],coins:r.coins}});setAddModal(null);toast.ok(`${amount>0?'+':''}${amount} coins`);}catch{toast.err('Failed');}};
  if(loading)return<Loading/>;
  const sorted=Object.entries(data).sort((a,b)=>(b[1]?.coins||0)-(a[1]?.coins||0));
  const total=sorted.reduce((s,[,d])=>s+(d?.coins||0),0);
  const getName=uid=>users?.[uid]?.display_name||users?.[uid]?.username||'';
  const filtered=sorted.filter(([uid])=>{const n=getName(uid).toLowerCase();return n.includes(q.toLowerCase())||uid.includes(q);});
  return<div className="pg-body">
    <div className="sg" style={{gridTemplateColumns:'repeat(3,1fr)',maxWidth:540,marginBottom:14}}>
      <div className="sc" style={{'--c':'var(--yellow)'}}><div className="sc-i">🪙</div><div className="sc-v">{total.toLocaleString()}</div><div className="sc-l">Total Coins</div></div>
      <div className="sc" style={{'--c':'var(--accent)'}}><div className="sc-i">👥</div><div className="sc-v">{sorted.length}</div><div className="sc-l">Users</div></div>
      <div className="sc" style={{'--c':'var(--green)'}}><div className="sc-i">💎</div><div className="sc-v">{(sorted[0]?.[1]?.coins||0).toLocaleString()}</div><div className="sc-l">Richest</div></div>
    </div>
    <div className="card"><div className="flex jb aic mb3"><Search value={q} onChange={setQ} placeholder="Search users..."/><RefreshBtn onClick={load}/></div>
      {!filtered.length?<Empty icon="🪙"/>:
      <div className="tw"><table><thead><tr><th>#</th><th>User</th><th>Coins</th><th>Total Earned</th><th>Last Daily</th><th>Actions</th></tr></thead>
      <tbody>{filtered.map(([uid,d],i)=><tr key={uid}>
        <td style={{color:'var(--muted)',width:36}}>{i===0?'🥇':i===1?'🥈':i===2?'🥉':`#${i+1}`}</td>
        <td><UserCell uid={uid} users={users}/></td>
        <td>{editId===uid?<span style={{display:'flex',gap:6,alignItems:'center'}}>
          <input className="ii" type="number" value={editVal} onChange={e=>setEditVal(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')saveCoins(uid);if(e.key==='Escape')setEditId(null);}} autoFocus style={{width:80}}/>
          <button className="btn btn-s btn-sm" onClick={()=>saveCoins(uid)}>✓</button>
          <button className="btn btn-g btn-sm" onClick={()=>setEditId(null)}>✕</button></span>:
          <span style={{color:'var(--yellow)',fontWeight:600}}>🪙 {(d?.coins||0).toLocaleString()}</span>}
        </td>
        <td style={{color:'var(--muted)'}}>{(d?.total_earned||0).toLocaleString()}</td>
        <td style={{fontSize:10,color:'var(--muted)'}}>{d?.last_daily?new Date(d.last_daily).toLocaleDateString():'Never'}</td>
        <td><span style={{display:'flex',gap:4}}>
          <button className="btn btn-g btn-sm" onClick={()=>{setEditId(uid);setEditVal(d?.coins||0);}}>✏️</button>
          <button className="btn btn-s btn-sm" onClick={()=>setAddModal({uid,op:1})}>+</button>
          <button className="btn btn-d btn-sm" onClick={()=>setAddModal({uid,op:-1})}>−</button>
        </span></td>
      </tr>)}</tbody></table></div>}
    </div>
    {addModal&&<div className="modal-back" onClick={()=>setAddModal(null)}><div className="modal" onClick={e=>e.stopPropagation()}>
      <div className="modal-title">{addModal.op>0?'Add':'Remove'} Coins</div>
      <div className="modal-msg">Current: <span style={{color:'var(--yellow)'}}>🪙 {(data[addModal.uid]?.coins||0).toLocaleString()}</span></div>
      <div className="fg mb4"><label>Amount</label><input type="number" min={1} placeholder="100" value={addVal} onChange={e=>setAddVal(e.target.value)} autoFocus/></div>
      <div className="modal-actions"><button className="btn btn-g" onClick={()=>setAddModal(null)}>Cancel</button>
        <button className={`btn ${addModal.op>0?'btn-s':'btn-d'}`} onClick={()=>{const v=parseInt(addVal);if(!v||v<=0)return;addCoins(addModal.uid,addModal.op*v);setAddVal('');}}>Confirm</button></div>
    </div></div>}
  </div>;
}
function LevelsPage({users}){
  const[stats,setStats]=useState({});const[reqs,setReqs]=useState({});const[loading,setLoading]=useState(true);const[q,setQ]=useState('');
  const load=()=>{setLoading(true);Promise.all([api.get('/api/levels/stats'),api.get('/api/levels/requirements')])
    .then(([s,r])=>{setStats(s||{});setReqs(r||{});}).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));};
  useEffect(()=>load(),[]);
  if(loading)return<Loading/>;
  const getName=uid=>users?.[uid]?.display_name||users?.[uid]?.username||'';
  const enriched=Object.entries(stats).map(([uid,s])=>{
    const v=s?.voice_minutes||0;const t=s?.text_minutes||0;
    return{uid,v,t,lvl:calcLevel(v,t,reqs),msgs:s?.total_messages||0,score:v+t};
  }).sort((a,b)=>b.score-a.score);
  const filtered=enriched.filter(({uid})=>{const n=getName(uid).toLowerCase();return n.includes(q.toLowerCase())||uid.includes(q);});
  const progPct=(uid,lvl,type)=>{
    const s=stats[uid];const cur=reqs[String(lvl)];const nxt=reqs[String(lvl+1)];
    if(!nxt||!cur)return 100;
    const val=type==='v'?s?.voice_minutes||0:s?.text_minutes||0;
    const key=type==='v'?'voice_minutes_required':'text_minutes_required';
    const base=cur[key]||0;const req=nxt[key]||1;
    return Math.min(100,Math.max(0,((val-base)/(req-base))*100));
  };
  return<div className="pg-body"><div className="card">
    <div className="flex jb aic mb3"><Search value={q} onChange={setQ} placeholder="Search users..."/><RefreshBtn onClick={load}/></div>
    {!filtered.length?<Empty icon="⬆️" msg="No level data"/>:
    <div className="tw"><table><thead><tr><th>#</th><th>User</th><th>Level</th><th>Voice Progress</th><th>Text Progress</th><th>Messages</th><th>Score</th></tr></thead>
    <tbody>{filtered.map(({uid,v,t,lvl,msgs,score},i)=>{const lc=lvlColor(lvl);const vp=progPct(uid,lvl,'v');const tp=progPct(uid,lvl,'t');return<tr key={uid}>
      <td style={{color:'var(--muted)',width:36}}>{i===0?'🥇':i===1?'🥈':i===2?'🥉':`#${i+1}`}</td>
      <td><UserCell uid={uid} users={users}/></td>
      <td><div className="lvl-badge" style={{'--c':lc}}>{lvl}</div></td>
      <td><div style={{display:'flex',flexDirection:'column',gap:3,minWidth:110}}>
        <div style={{display:'flex',justifyContent:'space-between',fontSize:9,color:'var(--muted)'}}><span>🎙 {Math.round(v)}m</span><span>{Math.round(vp)}%</span></div>
        <div className="prog-wrap"><div className="prog-fill" style={{width:`${vp}%`,background:'var(--purple)'}}/></div></div></td>
      <td><div style={{display:'flex',flexDirection:'column',gap:3,minWidth:110}}>
        <div style={{display:'flex',justifyContent:'space-between',fontSize:9,color:'var(--muted)'}}><span>💬 {Math.round(t)}m</span><span>{Math.round(tp)}%</span></div>
        <div className="prog-wrap"><div className="prog-fill" style={{width:`${tp}%`,background:'var(--green)'}}/></div></div></td>
      <td style={{color:'var(--muted)'}}>{msgs.toLocaleString()}</td>
      <td style={{fontWeight:600,color:'var(--accent)'}}>{Math.round(score).toLocaleString()}</td>
    </tr>;})}
    </tbody></table></div>}
  </div></div>;
}
function ChannelsPage({users}){
  const[data,setData]=useState({});const[loading,setLoading]=useState(true);
  const load=()=>{setLoading(true);api.get('/api/channels').then(setData).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));};
  useEffect(()=>load(),[]);if(loading)return<Loading/>;
  const ch=data?.channels||(typeof data==='object'&&!data?.settings?data:{});
  const settings=data?.settings||{};const entries=Object.entries(ch);
  return<div className="pg-body">
    <div className="flex jb aic mb4"><span style={{fontSize:22,fontFamily:'var(--display)',fontWeight:700}}>{entries.length}</span><span className="muted" style={{marginLeft:8}}>active sessions</span><RefreshBtn onClick={load}/></div>
    <div className="card">{!entries.length?<Empty icon="🎙" msg="No active temp channels"/>:
      <div className="tw"><table><thead><tr><th>Channel ID</th><th>Owner</th><th>Mode</th></tr></thead>
      <tbody>{entries.map(([ch,owner])=><tr key={ch}>
        <td><code style={{color:'var(--accent)',fontSize:10.5}}>{ch}</code></td>
        <td><UserCell uid={String(owner)} users={users}/></td>
        <td><Badge type={settings[ch]?.mode==='private'?'r':'g'}>{settings[ch]?.mode||'public'}</Badge></td>
      </tr>)}</tbody></table></div>}
    </div></div>;
}
function TicketsPage({users}){
  const[data,setData]=useState({});const[loading,setLoading]=useState(true);const[q,setQ]=useState('');
  const load=()=>{setLoading(true);api.get('/api/tickets').then(setData).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));};
  useEffect(()=>load(),[]);
  const close=id=>confirm('Close Ticket',`Close ticket #${id}?`,async()=>{
    try{await api.del(`/api/tickets/${id}`);setData({...data,[id]:{...data[id],status:'closed',closed_at:new Date().toISOString()}});toast.ok('Closed');}catch{toast.err('Failed');}});
  if(loading)return<Loading/>;
  const getName=uid=>users?.[uid]?.display_name||users?.[uid]?.username||uid;
  const entries=Object.entries(data).filter(([id,t])=>{const s=q.toLowerCase();return id.includes(s)||getName(String(t.opener_id||'')).toLowerCase().includes(s);}).sort((a,b)=>a[1].status==='open'?-1:1);
  const open=Object.values(data).filter(t=>t.status==='open').length;
  return<div className="pg-body">
    <div className="sg" style={{gridTemplateColumns:'repeat(3,1fr)',maxWidth:500,marginBottom:14}}>
      <div className="sc" style={{'--c':'var(--green)'}}><div className="sc-i">🟢</div><div className="sc-v">{open}</div><div className="sc-l">Open</div></div>
      <div className="sc" style={{'--c':'var(--muted)'}}><div className="sc-i">🔒</div><div className="sc-v">{Object.keys(data).length-open}</div><div className="sc-l">Closed</div></div>
      <div className="sc" style={{'--c':'var(--accent)'}}><div className="sc-i">🎫</div><div className="sc-v">{Object.keys(data).length}</div><div className="sc-l">Total</div></div>
    </div>
    <div className="card"><div className="flex jb aic mb3"><Search value={q} onChange={setQ} placeholder="Search..."/><RefreshBtn onClick={load}/></div>
      {!entries.length?<Empty icon="🎫"/>:
      <div className="tw"><table><thead><tr><th>ID</th><th>Opened By</th><th>Status</th><th>Opened</th><th>Action</th></tr></thead>
      <tbody>{entries.map(([id,t])=><tr key={id}>
        <td><code style={{fontSize:10.5}}>#{id}</code></td>
        <td><UserCell uid={String(t.opener_id||'')} users={users}/></td>
        <td><Badge type={t.status==='open'?'g':'r'}>{t.status}</Badge></td>
        <td style={{fontSize:10,color:'var(--muted)'}}>{t.opened_at?new Date(t.opened_at).toLocaleString():'—'}</td>
        <td>{t.status==='open'&&<button className="btn btn-d btn-sm" onClick={()=>close(id)}>Close</button>}</td>
      </tr>)}</tbody></table></div>}
    </div></div>;
}
function ShopPage(){
  const[items,setItems]=useState([]);const[loading,setLoading]=useState(true);const[adding,setAdding]=useState(false);
  const[f,setF]=useState({id:'',name:'',price:'',description:''});
  useEffect(()=>{api.get('/api/shop').then(d=>setItems(Array.isArray(d)?d:[])).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));},[]);
  const add=async()=>{
    if(!f.id.trim()||!f.name.trim())return toast.err('ID and name required');
    if(!f.price||parseInt(f.price)<=0)return toast.err('Price must be > 0');
    if(items.find(i=>i.id===f.id.trim()))return toast.err('ID already exists');
    try{const r=await api.post('/api/shop',{...f,id:f.id.trim(),price:parseInt(f.price)});setItems(Array.isArray(r)?r:[...items,{...f,price:parseInt(f.price)}]);setF({id:'',name:'',price:'',description:''});setAdding(false);toast.ok('Added');}catch{toast.err('Failed');}};
  const remove=id=>confirm('Remove Item',`Remove "${items.find(i=>i.id===id)?.name}"?`,async()=>{
    try{const r=await api.del(`/api/shop/${id}`);setItems(Array.isArray(r)?r:items.filter(i=>i.id!==id));toast.ok('Removed');}catch{toast.err('Failed');}},true);
  if(loading)return<Loading/>;
  return<div className="pg-body">
    <div className="flex jb aic mb4"><span className="muted">{items.length} items</span><button className="btn btn-p" onClick={()=>setAdding(!adding)}>{adding?'✕ Cancel':'+ Add Item'}</button></div>
    {adding&&<div className="card mb4"><div className="ct">New Item</div>
      <div className="g2" style={{gap:12,marginBottom:12}}>
        {[['id','Item ID','my_item'],['name','Display Name','My Item']].map(([k,l,p])=><div key={k} className="fg"><label>{l}</label><input placeholder={p} value={f[k]} onChange={e=>setF({...f,[k]:e.target.value})}/></div>)}
        <div className="fg"><label>Price</label><input type="number" min={1} value={f.price} onChange={e=>setF({...f,price:e.target.value})}/></div>
        <div className="fg"><label>Description</label><input value={f.description} onChange={e=>setF({...f,description:e.target.value})}/></div>
      </div><button className="btn btn-s" onClick={add}>✓ Add</button></div>}
    <div className="card"><div className="ct">Items</div>
      {!items.length?<Empty icon="🏪" msg="Shop empty"/>:
      <div className="tw"><table><thead><tr><th>ID</th><th>Name</th><th>Price</th><th>Description</th><th>Action</th></tr></thead>
      <tbody>{items.map((item,i)=><tr key={i}>
        <td><code className="accent" style={{fontSize:10.5}}>{item.id}</code></td>
        <td style={{fontWeight:500,color:'var(--text)'}}>{item.name}</td>
        <td><span style={{color:'var(--yellow)',fontWeight:600}}>🪙 {(item.price||0).toLocaleString()}</span></td>
        <td style={{maxWidth:240,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:10.5,color:'var(--muted)'}}>{item.description||'—'}</td>
        <td><button className="btn btn-d btn-sm" onClick={()=>remove(item.id)}>Remove</button></td>
      </tr>)}</tbody></table></div>}
    </div></div>;
}
function RxRolesPage(){
  const[data,setData]=useState({});const[loading,setLoading]=useState(true);const[adding,setAdding]=useState(false);
  const[f,setF]=useState({message_id:'',emoji:'',role_id:''});
  useEffect(()=>{api.get('/api/reaction-roles').then(setData).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));},[]);
  const add=async()=>{if(!f.message_id.trim()||!f.emoji.trim()||!f.role_id.trim())return toast.err('All fields required');
    try{const r=await api.post('/api/reaction-roles',f);setData(r);setF({message_id:'',emoji:'',role_id:''});setAdding(false);toast.ok('Added');}catch{toast.err('Failed');}};
  const remove=msgId=>confirm('Remove','Remove all mappings for this message?',async()=>{
    try{await api.del(`/api/reaction-roles/${msgId}`);const n={...data};delete n[msgId];setData(n);toast.ok('Removed');}catch{toast.err('Failed');}},true);
  if(loading)return<Loading/>;
  return<div className="pg-body">
    <div className="flex jb aic mb4"><span className="muted">{Object.keys(data).length} messages</span><button className="btn btn-p" onClick={()=>setAdding(!adding)}>{adding?'✕ Cancel':'+ Add'}</button></div>
    {adding&&<div className="card mb4"><div className="ct">New Reaction Role</div>
      <div className="g3" style={{gap:12,marginBottom:12}}>
        <div className="fg"><label>Message ID</label><input placeholder="1234567890" value={f.message_id} onChange={e=>setF({...f,message_id:e.target.value})}/></div>
        <div className="fg"><label>Emoji</label><input placeholder="🎮" value={f.emoji} onChange={e=>setF({...f,emoji:e.target.value})}/></div>
        <div className="fg"><label>Role ID</label><input placeholder="987654321" value={f.role_id} onChange={e=>setF({...f,role_id:e.target.value})}/></div>
      </div><button className="btn btn-s" onClick={add}>✓ Add</button></div>}
    <div className="card">{!Object.keys(data).length?<Empty icon="😊" msg="No reaction roles"/>:
      <div className="tw"><table><thead><tr><th>Message ID</th><th>Mappings</th><th>Count</th><th>Action</th></tr></thead>
      <tbody>{Object.entries(data).map(([msgId,mappings])=><tr key={msgId}>
        <td><code className="accent" style={{fontSize:10.5}}>{msgId}</code></td>
        <td>{Object.entries(mappings||{}).map(([emoji,roleId])=><span key={emoji} style={{display:'inline-flex',alignItems:'center',gap:3,marginRight:10,fontSize:12,background:'var(--bg2)',padding:'2px 8px',borderRadius:4,border:'1px solid var(--border)'}}>{emoji}<span style={{color:'var(--muted)',fontSize:9}}>→</span><code style={{color:'var(--purple)',fontSize:10}}>{roleId}</code></span>)}</td>
        <td><Badge type="b">{Object.keys(mappings||{}).length}</Badge></td>
        <td><button className="btn btn-d btn-sm" onClick={()=>remove(msgId)}>Remove</button></td>
      </tr>)}</tbody></table></div>}
    </div></div>;
}
function AnalyticsPage(){
  const[data,setData]=useState({});const[loading,setLoading]=useState(true);
  const load=()=>{setLoading(true);api.get('/api/analytics').then(setData).catch(()=>toast.err('Failed')).finally(()=>setLoading(false));};
  useEffect(()=>load(),[]);if(loading)return<Loading/>;
  const cmds=Object.entries(data).sort((a,b)=>b[1].total-a[1].total);
  const total=cmds.reduce((s,[,d])=>s+d.total,0);const maxV=cmds[0]?.[1]?.total||1;
  return<div className="pg-body">
    <div className="g4 mb4">
      <div className="sc" style={{'--c':'var(--accent)'}}><div className="sc-i">📊</div><div className="sc-v">{total}</div><div className="sc-l">Total Runs</div></div>
      <div className="sc" style={{'--c':'var(--purple)'}}><div className="sc-i">⌨️</div><div className="sc-v">{cmds.length}</div><div className="sc-l">Commands</div></div>
      <div className="sc" style={{'--c':'var(--green)'}}><div className="sc-i">🏆</div><div className="sc-v" style={{fontSize:17}}>{cmds[0]?.[0]||'—'}</div><div className="sc-l">Most Used</div></div>
      <div className="sc" style={{'--c':'var(--yellow)'}}><div className="sc-i">📈</div><div className="sc-v">{cmds[0]?.[1]?.total||0}</div><div className="sc-l">Top Uses</div></div>
    </div>
    <div className="g2">
      <div className="card"><div className="flex jb aic" style={{marginBottom:14}}><div className="ct" style={{marginBottom:0}}>Chart</div><RefreshBtn onClick={load}/></div>
        {!cmds.length?<Empty/>:cmds.map(([cmd,d])=><div key={cmd} className="br-row">
          <div className="br-lbl"><code style={{color:'var(--accent)',fontSize:10.5}}>.{cmd}</code></div>
          <div className="br-tr"><div className="br-fill" style={{width:`${(d.total/maxV)*100}%`,background:'var(--purple)'}}/></div>
          <div className="br-num">{d.total}</div></div>)}
      </div>
      <div className="card"><div className="ct">Breakdown</div>
        <div className="tw"><table><thead><tr><th>Rank</th><th>Command</th><th>Uses</th><th>Share</th></tr></thead>
        <tbody>{cmds.map(([cmd,d],i)=><tr key={cmd}>
          <td style={{color:'var(--muted)'}}>{i===0?'🥇':i===1?'🥈':i===2?'🥉':`#${i+1}`}</td>
          <td><code className="accent">.{cmd}</code></td>
          <td style={{fontWeight:600}}>{d.total.toLocaleString()}</td>
          <td><div style={{display:'flex',alignItems:'center',gap:6}}>
            <div className="prog-wrap" style={{minWidth:50}}><div className="prog-fill" style={{width:`${(d.total/total)*100}%`,background:'var(--accent)'}}/></div>
            <span style={{fontSize:10,color:'var(--muted)'}}>{((d.total/total)*100).toFixed(1)}%</span></div></td>
        </tr>)}</tbody></table></div>
      </div>
    </div></div>;
}
const PAGES={
  overview:{title:'OVERVIEW',sub:'Server health at a glance',C:OverviewPage,u:true},
  config:{title:'CONFIG',sub:'Bot settings — saved to Data/config.json',C:ConfigPage,u:false},
  moderation:{title:'MODERATION',sub:'Warnings, mod log, automod',C:ModerationPage,u:true},
  economy:{title:'ECONOMY',sub:'Coin balances',C:EconomyPage,u:true},
  levels:{title:'LEVELS',sub:'XP and activity',C:LevelsPage,u:true},
  channels:{title:'TEMP CHANNELS',sub:'Active voice sessions',C:ChannelsPage,u:true},
  tickets:{title:'TICKETS',sub:'Support tickets',C:TicketsPage,u:true},
  shop:{title:'SHOP',sub:'Economy shop items',C:ShopPage,u:false},
  rxroles:{title:'REACTION ROLES',sub:'Emoji → role mappings',C:RxRolesPage,u:false},
  analytics:{title:'ANALYTICS',sub:'Command usage',C:AnalyticsPage,u:false},
};
function App(){
  const[authed,setAuthed]=useState(!!localStorage.getItem('ds_tok'));
  const[page,setPage]=useState('overview');const[users,setUsers]=useState({});
  useEffect(()=>{if(authed)api.get('/api/users').then(setUsers).catch(()=>{});},[authed]);
  const logout=()=>{localStorage.removeItem('ds_tok');setAuthed(false);};
  if(!authed)return<><Login onLogin={()=>setAuthed(true)}/><Toasts/><ConfirmModal/></>;
  const{title,sub,C,u}=PAGES[page]||PAGES.overview;
  return<>
    <Sidebar page={page} setPage={setPage} logout={logout}/>
    <div className="main">
      <div className="pg-hdr"><div><div className="pg-title">{title}</div><div className="pg-sub">{sub}</div></div>
        <div className="sdot"><div className="dg"/>Connected · {location.hostname}:{location.port||80}</div></div>
      <C users={u?users:undefined}/>
    </div>
    <Toasts/><ConfirmModal/>
  </>;
}
ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
</script></body></html>"""


# ─── Low-level helpers used by the HTTP handler ───────────────────────────────
def _dash_load(filename, default=None):
    return _safe_load(os.path.join(data_dir, filename), default if default is not None else {})

def _dash_save(filename, data):
    _atomic_save(os.path.join(data_dir, filename), data)


# ─── HTTP request handler ─────────────────────────────────────────────────────
class DashHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass   # silence access log

    def _auth(self):
        return self.headers.get("X-Dashboard-Secret", "") == DASHBOARD_SECRET

    def _send(self, status, ctype, body):
        if isinstance(body, str): body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status=200):
        self._send(status, "application/json", json.dumps(data, ensure_ascii=False))

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try: return json.loads(raw)
        except: return {}

    def do_OPTIONS(self): self._send(204, "text/plain", b"")

    # ── GET ──────────────────────────────────────────────────────────────────
    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path in ("/", "/dashboard"):
            self._send(200, "text/html; charset=utf-8", DASHBOARD_HTML); return

        if not self._auth():
            self._json({"detail": "Unauthorized"}, 401); return

        if path == "/auth/verify":
            self._json({"ok": True})

        elif path == "/api/users":
            self._json(user_names)

        elif path == "/api/overview":
            ch = temp_channels  # temp_channels keys are channel IDs
            self._json({
                "total_users":     len(user_stats),
                "total_coins":     sum(v.get("coins", 0) for v in economy_data.values() if isinstance(v, dict)),
                "active_channels": len(ch),
                "open_tickets":    sum(1 for t in tickets_data.values() if isinstance(t, dict) and t.get("status") == "open"),
                "total_warnings":  sum(len(v) for v in warnings_data.values() if isinstance(v, list)),
                "top_command":     (max(analytics_data.items(), key=lambda x: x[1].get("total", 0))[0] if analytics_data else None),
            })

        elif path == "/api/config":
            # Config is read from disk so dashboard sees saved values
            self._json(_dash_load("config.json"))
        elif path == "/api/analytics":
            self._json(analytics_data)
        elif path == "/api/moderation/warnings":
            self._json(warnings_data)
        elif path == "/api/moderation/mod-log":
            self._json(mod_log)
        elif path == "/api/moderation/automod":
            self._json(automod_config)
        elif path == "/api/economy":
            self._json(economy_data)
        elif path == "/api/levels/stats":
            self._json(user_stats)
        elif path == "/api/levels/requirements":
            self._json(level_requirements)
        elif path == "/api/channels":
            self._json({
                "channels": {str(k): v for k, v in temp_channels.items()},
                "settings":  {str(k): v for k, v in channel_settings.items()},
            })
        elif path == "/api/tickets":
            self._json(tickets_data)
        elif path == "/api/shop":
            self._json(shop_items if isinstance(shop_items, list) else [])
        elif path == "/api/reaction-roles":
            self._json(reaction_roles)
        else:
            self._json({"detail": "Not found"}, 404)

    # ── POST ─────────────────────────────────────────────────────────────────
    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        body = self._body()

        if path == "/auth/login":
            if body.get("secret") == DASHBOARD_SECRET:
                self._json({"ok": True, "token": DASHBOARD_SECRET})
            else:
                self._json({"detail": "Invalid secret"}, 401)
            return

        if not self._auth():
            self._json({"detail": "Unauthorized"}, 401); return

        if path == "/api/shop":
            if not isinstance(shop_items, list):
                # shouldn't happen but guard anyway
                pass
            else:
                shop_items.append(body)
                save_shop()
                self._json(shop_items)

        elif path == "/api/reaction-roles":
            msg_id  = body.get("message_id")
            emoji   = body.get("emoji")
            role_id = body.get("role_id")
            if not all([msg_id, emoji, role_id]):
                self._json({"detail": "message_id, emoji, role_id required"}, 400); return
            reaction_roles.setdefault(msg_id, {})[emoji] = role_id
            save_reaction_roles()
            self._json(reaction_roles)
        else:
            self._json({"detail": "Not found"}, 404)

    # ── PATCH ─────────────────────────────────────────────────────────────────
    def do_PATCH(self):
        path = urlparse(self.path).path.rstrip("/")
        body = self._body()
        if not self._auth():
            self._json({"detail": "Unauthorized"}, 401); return

        if path == "/api/config":
            cfg = _dash_load("config.json")
            cfg.update(body)
            _dash_save("config.json", cfg)
            self._json(cfg)

        elif path == "/api/moderation/automod":
            automod_config.update(body)
            _atomic_save(AUTOMOD_FILE, automod_config)
            self._json(automod_config)

        elif path == "/api/levels/requirements":
            level_requirements.update(body)
            _atomic_save(REQUIREMENTS_FILE, level_requirements)
            self._json(level_requirements)

        elif path.startswith("/api/economy/"):
            uid = path.split("/api/economy/")[-1]
            economy_data.setdefault(uid, {"coins": 0, "total_earned": 0,
                                          "last_daily": None, "last_weekly": None})
            if "coins" in body:
                economy_data[uid]["coins"] = max(0, int(body["coins"]))
            save_economy()
            self._json(economy_data[uid])
        else:
            self._json({"detail": "Not found"}, 404)

    # ── DELETE ────────────────────────────────────────────────────────────────
    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        if not self._auth():
            self._json({"detail": "Unauthorized"}, 401); return

        if path.startswith("/api/moderation/warnings/"):
            uid = path.split("/api/moderation/warnings/")[-1]
            warnings_data.pop(uid, None)
            save_warnings()
            self._json({"ok": True})

        elif path.startswith("/api/tickets/"):
            tid = path.split("/api/tickets/")[-1]
            if tid in tickets_data:
                tickets_data[tid]["status"]    = "closed"
                tickets_data[tid]["closed_at"] = datetime.now().isoformat()
                save_tickets()
            self._json({"ok": True})

        elif path.startswith("/api/shop/"):
            item_id = path.split("/api/shop/")[-1]
            # shop_items is a list — remove matching id
            to_remove = [i for i, item in enumerate(shop_items) if item.get("id") == item_id]
            for idx in reversed(to_remove):
                shop_items.pop(idx)
            save_shop()
            self._json(shop_items)

        elif path.startswith("/api/reaction-roles/"):
            msg_id = path.split("/api/reaction-roles/")[-1]
            reaction_roles.pop(msg_id, None)
            save_reaction_roles()
            self._json({"ok": True})
        else:
            self._json({"detail": "Not found"}, 404)


def start_dashboard():
    try:
        server = HTTPServer(("0.0.0.0", DASHBOARD_PORT), DashHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"[Dashboard] ✅  http://0.0.0.0:{DASHBOARD_PORT}  "
              f"(secret: {'*' * len(DASHBOARD_SECRET)})")
    except Exception as e:
        print(f"[Dashboard] ❌ Failed to start: {e}")


# ─── Start the bot ────────────────────────────────────────────────────────────
if not TOKEN or TOKEN == "PASTE_YOUR_TOKEN_HERE":
    print("Error: Please set your Discord token at the top of the file.")
else:
    client.run(TOKEN)