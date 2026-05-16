"""
cogs/reminders.py  —  /remind slash command + /remind prefix + background checker
"""
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands

from database import reminders_list, save_reminders
from utils import log_command


class RemindersCog(commands.Cog, name="Reminders"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        asyncio.create_task(self._check_reminders())

    # ─── Shared parser ────────────────────────────────────────────────────────
    @staticmethod
    def _parse_time(time_str: str):
        """Return total minutes or None on bad format."""
        s = time_str.lower()
        try:
            if   s.endswith("d"): return int(s[:-1]) * 1440
            elif s.endswith("h"): return int(s[:-1]) * 60
            elif s.endswith("m"): return int(s[:-1])
        except (ValueError, IndexError):
            pass
        return None

    # ─── /remind slash ────────────────────────────────────────────────────────
    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(time="Duration like 30m, 2h, 1d", message="What to remind you about")
    async def slash_remind(self, interaction: discord.Interaction, time: str, message: str):
        log_command("slash_remind")
        minutes = self._parse_time(time)
        if minutes is None or minutes <= 0:
            await interaction.response.send_message(
                "❌ Invalid time format. Use `30m`, `2h`, or `1d`.", ephemeral=True
            ); return
        remind_at = datetime.now() + timedelta(minutes=minutes)
        reminders_list.append({
            "user_id":   interaction.user.id,
            "remind_at": remind_at.isoformat(),
            "message":   message,
        })
        save_reminders()
        await interaction.response.send_message(f"✅ Okay! I'll remind you in **{time}** via DM.")

    # ─── Background checker ───────────────────────────────────────────────────
    async def _check_reminders(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now       = datetime.now()
                to_remove = []
                for i, reminder in enumerate(reminders_list):
                    if now >= datetime.fromisoformat(reminder["remind_at"]):
                        try:
                            user  = await self.bot.fetch_user(reminder["user_id"])
                            embed = discord.Embed(title="⏰ Reminder!", description=reminder["message"],
                                                  color=discord.Color.gold())
                            await user.send(embed=embed)
                        except Exception as e:
                            print(f"[Reminders] Could not send to {reminder['user_id']}: {e}")
                        to_remove.append(i)
                if to_remove:
                    for idx in reversed(to_remove):
                        del reminders_list[idx]
                    save_reminders()
            except Exception as e:
                print(f"[Reminders] Loop error: {e}")
            await asyncio.sleep(60)

    # ─── Prefix .remind ───────────────────────────────────────────────────────
    async def handle_prefix_remind(self, message: discord.Message):
        """Called from the on_message handler in general.py."""
        log_command("remind")
        parts = message.content.split(maxsplit=2)
        if len(parts) < 3:
            await message.reply("Usage: `.remind <time> <message>`\n*Examples: 30m, 2h, 1d*"); return
        minutes = self._parse_time(parts[1])
        if minutes is None or minutes <= 0:
            await message.reply("❌ Invalid time format. Use `30m`, `2h`, or `1d`."); return
        remind_at = datetime.now() + timedelta(minutes=minutes)
        reminders_list.append({
            "user_id":   message.author.id,
            "remind_at": remind_at.isoformat(),
            "message":   parts[2],
        })
        save_reminders()
        await message.reply(f"✅ Okay! I'll remind you in **{parts[1]}** via DM.")


async def setup(bot: commands.Bot):
    await bot.add_cog(RemindersCog(bot))
