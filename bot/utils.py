"""
utils.py
--------
Cross-cog utility functions and shared enums / aliases.
No discord.py imports here — kept pure-Python so it is safe
to import from any context (including the HTTP dashboard thread).
"""

from enum import IntEnum
from datetime import datetime

import database as db
from database import (
    command_cooldowns,
    economy_data,
    analytics_data,
    user_stats,
    level_requirements,
    user_streaks,
    save_analytics,
    save_economy,
    save_user_stats,
    save_user_streaks,
)
from config import (
    XP_MULTIPLIER,
    WEEKEND_MULTIPLIER,
    SPECIAL_EVENT_MULTIPLIER,
    EVENT_ACTIVE,
    MOD_ROLE_ID,
)


# ─── Permission levels ────────────────────────────────────────────────────────
class PermLevel(IntEnum):
    MEMBER    = 0
    MODERATOR = 1
    ADMIN     = 2
    OWNER     = 3


# ─── Command aliases ──────────────────────────────────────────────────────────
ALIASES = {
    "rank":        ["rank", "stats", "level", "xp"],
    "daily":       ["daily", "claim"],
    "weekly":      ["weekly"],
    "balance":     ["balance", "bal", "coins", "wallet"],
    "shop":        ["shop", "store"],
    "buy":         ["buy", "purchase"],
    "coinflip":    ["coinflip", "cf", "flip"],
    "dice":        ["dice", "roll"],
    "slots":       ["slots", "slot"],
    "leaderboard": ["leaderboard", "lb", "top", "rankings"],
    "games":       ["games", "casino"],
}


# ─── Cooldown helper ─────────────────────────────────────────────────────────
def check_cooldown(user_id, command: str, seconds: float) -> float:
    """Return remaining seconds if on cooldown, 0 if the user may proceed.
    Side-effect: records the current timestamp as the new last-use time."""
    key  = (user_id, command)
    last = command_cooldowns.get(key)
    if last:
        elapsed = (datetime.now() - last).total_seconds()
        if elapsed < seconds:
            return seconds - elapsed
    command_cooldowns[key] = datetime.now()
    return 0.0


# ─── Permission helper ────────────────────────────────────────────────────────
def get_perm_level(member) -> PermLevel:
    if member.id == member.guild.owner_id:
        return PermLevel.OWNER
    if member.guild_permissions.administrator:
        return PermLevel.ADMIN
    if MOD_ROLE_ID and int(MOD_ROLE_ID) in [r.id for r in member.roles]:
        return PermLevel.MODERATOR
    return PermLevel.MEMBER


# ─── Analytics logging ────────────────────────────────────────────────────────
def log_command(command_name: str) -> None:
    hour_key = datetime.now().strftime("%Y-%m-%d %H")
    if command_name not in analytics_data:
        analytics_data[command_name] = {"total": 0, "hourly": {}}
    analytics_data[command_name]["total"] += 1
    analytics_data[command_name]["hourly"][hour_key] = (
        analytics_data[command_name]["hourly"].get(hour_key, 0) + 1
    )
    save_analytics()


# ─── Economy helpers ──────────────────────────────────────────────────────────
def get_economy(user_id) -> dict:
    user_id = str(user_id)
    if user_id not in economy_data:
        economy_data[user_id] = {
            "coins":       0,
            "total_earned": 0,
            "last_daily":  None,
            "last_weekly": None,
        }
    return economy_data[user_id]


def add_coins(user_id, amount: float) -> None:
    if amount <= 0:
        return
    econ = get_economy(user_id)
    econ["coins"]        += amount
    econ["total_earned"] += amount
    save_economy()


def remove_coins(user_id, amount: float) -> bool:
    if amount <= 0:
        return False
    econ = get_economy(user_id)
    if econ["coins"] >= amount:
        econ["coins"] -= amount
        save_economy()
        return True
    return False


# ─── User-stats helper ────────────────────────────────────────────────────────
def get_user_stats(user_id) -> dict:
    user_id = str(user_id)
    if user_id not in user_stats:
        user_stats[user_id] = {
            "voice_minutes":   0,
            "total_messages":  0,
            "text_minutes":    0,
            "weekly_voice":    0,
            "weekly_text":     0,
            "monthly_voice":   0,
            "monthly_text":    0,
            "last_message_ts": None,
            "current_level":   -1,
            "display_name":    "Unknown",
            "voice_level":     0,
            "text_level":      0,
        }
    s = user_stats[user_id]
    # Back-fill missing fields from older saves
    if "total_messages"  not in s: s["total_messages"]  = 0
    if "text_minutes"    not in s: s["text_minutes"]    = 0
    if "weekly_voice"    not in s:
        s.update({"weekly_voice": 0, "weekly_text": 0,
                  "monthly_voice": 0, "monthly_text": 0})
    if "current_level"   not in s: s["current_level"]   = -1
    if "last_message_ts" not in s:
        s["last_message_ts"] = s.pop("last_message_minute", None)
    if "display_name"    not in s: s["display_name"]    = "Unknown"
    if "voice_level"     not in s: s["voice_level"]     = 0
    if "text_level"      not in s: s["text_level"]      = 0
    for stale in ("voice_xp", "text_xp", "last_message_minute"):
        s.pop(stale, None)
    return s


# ─── XP multiplier ────────────────────────────────────────────────────────────
def get_active_multiplier(user_id=None) -> float:
    """Return the effective XP multiplier for *user_id* right now."""
    base = XP_MULTIPLIER
    if EVENT_ACTIVE:
        base = SPECIAL_EVENT_MULTIPLIER
    elif datetime.now().weekday() >= 5:
        base = WEEKEND_MULTIPLIER
    if user_id:
        uid = str(user_id)
        boost_until = economy_data.get(uid, {}).get("xp_boost_active_until")
        if boost_until:
            try:
                if datetime.now() < datetime.fromisoformat(boost_until):
                    base *= 2.0
            except (ValueError, TypeError):
                pass
    return base


# ─── Streak helper ────────────────────────────────────────────────────────────
def update_streak(user_id) -> float:
    """Update daily streak and return the corresponding XP multiplier."""
    user_id   = str(user_id)
    today     = datetime.now().date()
    today_str = str(today)

    if user_id not in user_streaks:
        user_streaks[user_id] = {"last_active_date": today_str, "streak": 1}
        save_user_streaks()
        return 1.0

    streak_data      = user_streaks[user_id]
    last_active_str  = streak_data.get("last_active_date")
    streak_count     = streak_data.get("streak", 1)

    if last_active_str != today_str:
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

    if streak_count >= 30: return 2.0
    if streak_count >= 14: return 1.5
    if streak_count >= 7:  return 1.25
    return 1.0


# ─── Level computation ────────────────────────────────────────────────────────
def compute_sub_level(cumulative: float, type_key: str):
    """
    Exact port of the original compute_sub_level logic.

    Iterates every level entry in ascending order.
    Level 0 is skipped (baseline, no cost).
    For every other level, checks whether the user's cumulative value
    has reached (total_cost_so_far + this_level_cost).
    If yes  → they have this level, add cost to running total, advance.
    If no   → stop; this is where they are.

    Returns (sub_level, progress_within_current_level, cost_of_next_level).
    """
    sub_level  = 0
    total_cost = 0

    # Sort numerically; non-digit keys (shouldn't exist) are pushed to end
    keys = sorted(
        level_requirements.keys(),
        key=lambda x: int(x) if x.isdigit() else 99999,
    )

    for k in keys:
        if not k.isdigit():
            continue
        level_num = int(k)
        cost = level_requirements[k].get(type_key, 0)

        if level_num == 0:
            continue  # Level 0 is the starting point — no cost required

        if cumulative >= total_cost + cost:
            total_cost += cost
            sub_level   = level_num
        else:
            break

    progress   = max(0.0, cumulative - total_cost)
    next_entry = level_requirements.get(str(sub_level + 1))
    if next_entry is None:
        return sub_level, progress, float("inf")
    return sub_level, progress, float(next_entry.get(type_key, 0))
