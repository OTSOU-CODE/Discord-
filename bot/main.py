"""
main.py — Bot entry point.
Run from the project root:  python bot/main.py
"""

import sys
import os
import asyncio

# Make sure `bot/` is importable without installing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import discord
from discord.ext import commands

from config import TOKEN
from database import ensure_db_files, load_temp_channels

EXTENSIONS = [
    "cogs.levels",
    "cogs.economy",
    "cogs.moderation",
    "cogs.temp_channels",
    "cogs.tickets",
    "cogs.reaction_roles",
    "cogs.reminders",
    "cogs.welcome",
    "cogs.general",        # must be last (on_message dispatcher)
]


async def main():
    ensure_db_files()
    load_temp_channels()

    intents                  = discord.Intents.default()
    intents.members          = True
    intents.message_content  = True
    intents.voice_states     = True
    intents.reactions        = True

    bot = commands.Bot(command_prefix=[".", "!"], intents=intents)
    bot.remove_command("help")   # we supply our own /help

    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"[Main] ✅ Loaded {ext}")
        except Exception as e:
            print(f"[Main] ❌ Failed to load {ext}: {e}")

    if not TOKEN or TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("[Main] ERROR: Set your Discord token in bot/config.py")
        return

    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
