"""
cogs/levels.py

NOTE: uses asyncio.create_task() — compatible with discord.py 2.x
--------------
XP tracking helpers, check_and_update_level(), level-up announcements,
and periodic voice-XP + flush background tasks.

Events handled here:
  • track_voice_minutes  (background loop, 60 s tick)
  • periodic_flush       (background loop, 5 min tick)
  • leaderboard_reset_task (background loop, 1 hr tick)
  • post_leaderboard     (helper)
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from discord.ext import tasks

import discord
from discord.ext import commands

import database as db
from database import (
    level_requirements, user_stats, economy_data, user_names,
    save_user_stats, save_user_streaks, save_economy, save_analytics,
    save_user_names, REQUIREMENTS_FILE, LEADERBOARD_FILE,
)
from config import (
    LEVELUP_CHANNEL_ID, LEVELUP_MESSAGE, MILESTONE_LEVELS, script_dir,
)
from utils import (
    get_user_stats, get_active_multiplier, update_streak, compute_sub_level,
    add_coins,
)
from config import _atomic_save


class LevelsCog(commands.Cog, name="Levels"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Cog startup ───────────────────────────────────────────────────────────
    async def cog_load(self):
        asyncio.create_task(self._track_voice_minutes())
        asyncio.create_task(self._periodic_flush())
        asyncio.create_task(self._leaderboard_reset_task())

    # ─────────────────────────────────────────────────────────────────────────
    # LEVEL COMPUTATION
    # ─────────────────────────────────────────────────────────────────────────

    async def check_level_up(self, member: discord.Member):
        """Recalculate levels, assign roles, announce on genuine level-up."""
        user_id = str(member.id)
        stats   = get_user_stats(user_id)

        voice_level, _, _ = compute_sub_level(stats.get("voice_minutes", 0),  "voice_minutes_required")
        text_level,  _, _ = compute_sub_level(stats.get("total_messages", 0), "text_minutes_required")

        core_level = min(voice_level, text_level)

        stats["voice_level"] = voice_level
        stats["text_level"]  = text_level

        prev_level   = stats.get("current_level", -1)
        is_new_level = core_level > prev_level
        stats["current_level"] = core_level

        req = level_requirements.get(str(core_level))
        if not req:
            return

        role_id  = req.get("role_id")
        new_role = None
        if role_id and role_id != 0:
            new_role = member.guild.get_role(int(role_id))

        if not new_role:
            role_name = f"Level {core_level}"
            new_role  = discord.utils.get(member.guild.roles, name=role_name)
            if not new_role:
                try:
                    new_role = await member.guild.create_role(
                        name=role_name,
                        color=discord.Color.gold(),
                        reason="Level System Auto-Creation",
                    )
                    print(f"[Levels] Created role '{role_name}' (ID: {new_role.id})")
                except discord.Forbidden:
                    print(f"[Levels] No permission to create role '{role_name}'")
                except Exception as e:
                    print(f"[Levels] Error creating role '{role_name}': {e}")
            if new_role:
                level_requirements[str(core_level)]["role_id"] = new_role.id
                _atomic_save(REQUIREMENTS_FILE, level_requirements)

        if new_role and new_role not in member.roles:
            try:
                # ── Remove previous level's role ──────────────────────────────
                if is_new_level and prev_level >= 0:
                    old_req     = level_requirements.get(str(prev_level), {})
                    old_role_id = old_req.get("role_id")
                    old_role    = None
                    if old_role_id and old_role_id != 0:
                        old_role = member.guild.get_role(int(old_role_id))
                    if not old_role:
                        old_role = discord.utils.get(member.guild.roles, name=f"Level {prev_level}")
                    if old_role and old_role in member.roles:
                        try:
                            await member.remove_roles(old_role, reason=f"Level up: {prev_level} → {core_level}")
                        except Exception:
                            pass

                # ── Tier logic ────────────────────────────────────────────────
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
                            all_tiers = {
                                r_data.get("tier").title()
                                for r_data in level_requirements.values()
                                if isinstance(r_data, dict) and r_data.get("tier")
                            }
                            old_tiers = [r for r in member.roles if r.name in all_tiers and r.name != tier_name.title()]
                            if old_tiers:
                                await member.remove_roles(*old_tiers)
                            await member.add_roles(tier_role)

                await member.add_roles(new_role)
                print(
                    f"[Levels] {member.display_name} → Core {core_level} "
                    f"(🎙️ Voice {voice_level} / ✍️ Text {text_level})"
                    + (" ✨ NEW" if is_new_level else " (role restored)")
                )
                save_user_stats()

                # ── Announce on genuine level-up ──────────────────────────────
                if is_new_level and LEVELUP_CHANNEL_ID and LEVELUP_CHANNEL_ID != 0:
                    levelup_channel = member.guild.get_channel(int(LEVELUP_CHANNEL_ID))
                    if levelup_channel:
                        embed = discord.Embed(
                            title="🎉 Level Up!",
                            description=LEVELUP_MESSAGE.format(
                                mention=member.mention, level=core_level
                            ),
                            color=discord.Color.gold(),
                        )
                        if member.display_avatar:
                            embed.set_thumbnail(url=member.display_avatar.url)
                        if core_level in MILESTONE_LEVELS:
                            embed.add_field(
                                name="🏆 MEGA MILESTONE REACHED!",
                                value=(
                                    f"Congratulations on reaching **Level {core_level}**! "
                                    f"You've been awarded **50 Coins**! 🪙"
                                ),
                                inline=False,
                            )
                            embed.color = discord.Color.purple()
                            add_coins(member.id, 50)
                        await levelup_channel.send(embed=embed)

            except discord.Forbidden:
                print(f"[Levels] No permission to assign '{new_role.name}' to {member.display_name}")

    # ─────────────────────────────────────────────────────────────────────────
    # BACKGROUND TASKS
    # ─────────────────────────────────────────────────────────────────────────

    async def _track_voice_minutes(self):
        """Every 60 s: award voice XP + coins to qualifying members."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                if level_requirements:
                    for guild in self.bot.guilds:
                        for channel in guild.voice_channels:
                            if len(channel.members) < 2:
                                continue
                            for member in channel.members:
                                if member.bot:
                                    continue
                                if member.voice and (
                                    member.voice.self_mute or member.voice.mute
                                    or member.voice.self_deaf or member.voice.deaf
                                ):
                                    continue
                                user_id = str(member.id)
                                db.cache_member_name(member)
                                stats = get_user_stats(user_id)

                                streak_mult = update_streak(user_id)
                                multiplier  = get_active_multiplier(user_id) * streak_mult
                                added_xp    = 1 * multiplier

                                stats["voice_minutes"]  += added_xp
                                stats["weekly_voice"]   += added_xp
                                stats["monthly_voice"]  += added_xp

                                add_coins(user_id, 2 * multiplier)
                                await self.check_level_up(member)
                    save_user_stats()
            except Exception as e:
                print(f"[Levels] Error in track_voice_minutes: {e}")
            await asyncio.sleep(60)

    async def _periodic_flush(self):
        """Every 5 minutes: flush all in-memory data to disk."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(300)
            try:
                save_user_stats()
                save_user_streaks()
                save_economy()
                save_analytics()
                save_user_names()
                print(f"[DB] Periodic flush at {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                print(f"[DB] Periodic flush error: {e}")

    async def _post_leaderboard(self, period: str):
        """Build leaderboard, save snapshot, post to level-up channel."""
        if not LEVELUP_CHANNEL_ID:
            return
        leaderboard_data = []
        for uid, stats in user_stats.items():
            v_key = f"{period}_voice"
            t_key = f"{period}_text"
            score = (stats.get(v_key, 0) * 2) + stats.get(t_key, 0)
            if score > 0:
                leaderboard_data.append({
                    "user_id": uid,
                    "score":   score,
                    "v":       stats.get(v_key, 0),
                    "t":       stats.get(t_key, 0),
                })
        leaderboard_data.sort(key=lambda x: x["score"], reverse=True)
        top_10 = leaderboard_data[:10]
        if not top_10:
            return

        # Save snapshot
        try:
            snapshot_data = {}
            if os.path.exists(LEADERBOARD_FILE):
                with open(LEADERBOARD_FILE, "r") as f:
                    snapshot_data = json.load(f)
            snapshot_date = datetime.now().strftime("%Y-%m-%d")
            snapshot_data[f"{period}_{snapshot_date}"] = top_10
            with open(LEADERBOARD_FILE, "w") as f:
                json.dump(snapshot_data, f, indent=4)
        except Exception as e:
            print(f"[Levels] Failed to save leaderboard snapshot: {e}")

        # Post embed
        channel = None
        for guild in self.bot.guilds:
            channel = guild.get_channel(LEVELUP_CHANNEL_ID)
            if channel:
                break
        if not channel:
            return

        desc = ""
        for idx, entry in enumerate(top_10, 1):
            desc += (
                f"**{idx}.** <@{entry['user_id']}> — Score: **{int(entry['score'])}** "
                f"(Voice: {int(entry['v'])}m | Text: {int(entry['t'])}m)\n"
            )
        embed = discord.Embed(
            title=f"🏆 {period.capitalize()} Leaderboard Snapshot",
            description=desc,
            color=discord.Color.blue(),
        )
        await channel.send(embed=embed)

    async def _leaderboard_reset_task(self):
        """Every hour: check if we should post & reset weekly/monthly leaderboards."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = datetime.now()
                if now.weekday() == 0 and now.hour == 0:
                    await self._post_leaderboard("weekly")
                    for uid in user_stats:
                        user_stats[uid]["weekly_voice"] = 0
                        user_stats[uid]["weekly_text"]  = 0
                    save_user_stats()
                if now.day == 1 and now.hour == 0:
                    await self._post_leaderboard("monthly")
                    for uid in user_stats:
                        user_stats[uid]["monthly_voice"] = 0
                        user_stats[uid]["monthly_text"]  = 0
                    save_user_stats()
            except Exception as e:
                print(f"[Levels] Error in leaderboard reset: {e}")
            await asyncio.sleep(3600)


async def setup(bot: commands.Bot):
    await bot.add_cog(LevelsCog(bot))
