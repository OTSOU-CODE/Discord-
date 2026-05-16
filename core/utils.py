import discord
from typing import List, Optional

def format_list(items: List[str]) -> str:
    """Formats a list into a string."""
    return "\n".join(items)

def get_ordinal(n: int) -> str:
    """Returns the ordinal representation of a number."""
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix

def get_emoji(name: str) -> str:
    """Returns a specific emoji by name (helper for consistency)."""
    emojis = {
        "loading": "⏳",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "crown": "👑",
        "trophy": "🏆",
        "money": "💰",
        "star": "⭐",
        "game": "🎮"
    }
    return emojis.get(name, "🔹")
