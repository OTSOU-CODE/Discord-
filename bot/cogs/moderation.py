"""
cogs/moderation.py
------------------
Slash commands: warn, warnings, clearwarn, ban, unban, kick,
                timeout, untimeout, purge, slowmode.
Background:     check_muted_users loop.
Helpers:        warn_user(), log_mod_action().
"""

import asyncio
from datetime import datetime, timedelta

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

from database import (
    warnings_data, mod_log, automod_config,
    save_warnings, save_mod_log,
    muted_users,
)
from config import MOD_LOG_WEBHOOK_URL, MOD_ROLE_ID
from utils import check_cooldown, log_command, get_perm_level, PermLevel


# ─── Shared helper: log a moderation action ───────────────────────────────────
async def log_mod_action(action: str, target: discord.Member, mod, reason: str):
    """Append to mod_log and optionally post to the webhook."""
    entry = {
        "timestamp":   datetime.now().isoformat(),
        "action":      action,
        "target_id":   str(target.id),
        "target_name": target.display_name,
        "mod_id":      str(mod.id),
        "mod_name":    mod.display_name,
        "reason":      reason,
    }
    mod_log.append(entry)
    save_mod_log()

    if MOD_LOG_WEBHOOK_URL:
        try:
            embed = {
                "title": f"🛠️ Moderation Action: {action.title()}",
                "color": 16711680 if action in ["ban", "kick"] else 16753920,
                "fields": [
                    {"name": "Target",    "value": f"{target.mention} ({target.id})", "inline": True},
                    {"name": "Moderator", "value": f"{mod.mention}",                  "inline": True},
                    {"name": "Reason",    "value": reason,                             "inline": False},
                ],
                "timestamp": datetime.utcnow().isoformat(),
            }
            async with aiohttp.ClientSession() as session:
                await session.post(MOD_LOG_WEBHOOK_URL, json={"embeds": [embed]})
        except Exception as e:
            print(f"[Mod] Webhook error: {e}")


# ─── Shared helper: warn a user ──────────────────────────────────────────────
async def warn_user(member: discord.Member, reason: str, mod):
    uid = str(member.id)
    if uid not in warnings_data:
        warnings_data[uid] = []
    warnings_data[uid].append({
        "timestamp": datetime.now().isoformat(),
        "reason":    reason,
        "mod_id":    str(mod.id),
    })
    save_warnings()
    total_warns = len(warnings_data[uid])
    await log_mod_action("warn", member, mod, f"Warn #{total_warns}: {reason}")

    # Notify via DM
    try:
        await member.send(
            f"⚠️ You have been warned in **{member.guild.name}**.\n"
            f"**Reason:** {reason}\n*You now have {total_warns} warning(s).*"
        )
    except Exception:
        pass

    # Escalation
    try:
        if total_warns >= 7:
            await member.ban(reason="Automod: Reached 7 warnings")
            await log_mod_action("ban", member, mod, "Automod Escalation (7 Warns)")
        elif total_warns >= 5:
            until = discord.utils.utcnow() + timedelta(hours=1)
            await member.timeout(until, reason="Automod: Reached 5 warnings")
            await log_mod_action("timeout", member, mod, "Automod Escalation (5 Warns - 1 Hour)")
        elif total_warns >= 3:
            until = discord.utils.utcnow() + timedelta(minutes=10)
            await member.timeout(until, reason="Automod: Reached 3 warnings")
            await log_mod_action("timeout", member, mod, "Automod Escalation (3 Warns - 10 Minutes)")
    except discord.Forbidden:
        print(f"[Mod] Bot lacks permissions to escalate for {member.display_name}")


class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        asyncio.create_task(self._check_muted_users())
        asyncio.create_task(self._check_temp_bans())

    async def _check_temp_bans(self):
        """Unban users whose tempban duration has expired."""
        from database import temp_bans, save_temp_bans
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = datetime.now()
                expired = []
                for uid, data in list(temp_bans.items()):
                    unban_time = datetime.fromisoformat(data["unban_time"])
                    if now >= unban_time:
                        expired.append((uid, data["guild_id"]))
                
                for uid, guild_id in expired:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        try:
                            user = await self.bot.fetch_user(int(uid))
                            await guild.unban(user, reason="Tempban expired.")
                            print(f"[Mod] Tempban expired for {user.name} ({uid}). Unbanned.")
                        except discord.NotFound:
                            pass # User not found or not banned
                        except discord.Forbidden:
                            print(f"[Mod] Forbidden to unban {uid}")
                        except Exception as e:
                            print(f"[Mod] Error unbanning {uid}: {e}")
                    temp_bans.pop(uid, None)
                
                if expired:
                    save_temp_bans()
                    
            except Exception as e:
                print(f"[Mod] Error in _check_temp_bans: {e}")
            await asyncio.sleep(60)

    # ─── Background: mute-time enforcement ───────────────────────────────────
    async def _check_muted_users(self):
        """Disconnect voice users who have been server-muted for ≥20 minutes."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now                  = datetime.now()
                users_to_disconnect  = []
                for uid, data in list(muted_users.items()):
                    if (now - data["mute_start"]).total_seconds() >= 1200:
                        users_to_disconnect.append((uid, data["guild_id"]))

                for uid, guild_id in users_to_disconnect:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        member = guild.get_member(uid)
                        if member and member.voice and member.voice.channel:
                            try:
                                await member.move_to(None, reason="Muted for more than 20 minutes.")
                                print(f"[Mod] Disconnected {member.display_name} (muted >20 min).")
                                try:
                                    await log_mod_action("auto-disconnect", member, self.bot.user,
                                                         "Muted for 20+ minutes in Temp Channel")
                                except Exception as e:
                                    print(f"[Mod] Log error: {e}")
                            except discord.Forbidden:
                                print(f"[Mod] Cannot disconnect {member.display_name}.")
                            except Exception as e:
                                print(f"[Mod] Disconnect error: {e}")
                    muted_users.pop(uid, None)
            except Exception as e:
                print(f"[Mod] Error in check_muted_users: {e}")
            await asyncio.sleep(60)

    # ─── /warn ────────────────────────────────────────────────────────────────
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(user="User to warn", reason="Reason for the warning")
    @app_commands.default_permissions(manage_messages=True)
    async def slash_warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        log_command("slash_warn")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        await interaction.response.defer()
        await warn_user(user, reason, interaction.user)
        await interaction.followup.send(f"✅ Warned {user.mention} for: {reason}")

    # ─── /warnings ───────────────────────────────────────────────────────────
    @app_commands.command(name="warnings", description="Check warnings for a user")
    @app_commands.describe(user="User to check")
    @app_commands.default_permissions(manage_messages=True)
    async def slash_warnings(self, interaction: discord.Interaction, user: discord.Member):
        log_command("slash_warnings")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        uid   = str(user.id)
        warns = warnings_data.get(uid, [])
        if not warns:
            await interaction.response.send_message(f"✅ {user.display_name} has no warnings.")
            return
        desc = ""
        for i, w in enumerate(warns, 1):
            desc += f"**{i}.** {w.get('timestamp','')[:10]} - {w.get('reason')} (Mod: {w.get('mod_id','?')})\n"
        embed = discord.Embed(title=f"Warnings for {user.display_name}", description=desc, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    # ─── /clearwarn ──────────────────────────────────────────────────────────
    @app_commands.command(name="clearwarn", description="Clear all warnings for a user")
    @app_commands.describe(user="User to clear warnings for")
    @app_commands.default_permissions(manage_messages=True)
    async def slash_clearwarn(self, interaction: discord.Interaction, user: discord.Member):
        log_command("slash_clearwarn")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        uid = str(user.id)
        if uid in warnings_data:
            del warnings_data[uid]
            save_warnings()
            await log_mod_action("clearwarn", user, interaction.user, "Cleared all warnings")
            await interaction.response.send_message(f"✅ Cleared all warnings for {user.display_name}.")
        else:
            await interaction.response.send_message(f"❌ {user.display_name} has no warnings.")

    # ─── /ban ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(user="Member to ban", reason="Reason", delete_days="Days of messages to delete (0-7)")
    @app_commands.default_permissions(ban_members=True)
    async def slash_ban(self, interaction: discord.Interaction, user: discord.Member,
                        reason: str = "No reason provided", delete_days: int = 0):
        log_command("slash_ban")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        if user == interaction.user:
            await interaction.response.send_message("❌ You cannot ban yourself.", ephemeral=True); return
        if get_perm_level(user) >= get_perm_level(interaction.user):
            await interaction.response.send_message("❌ Cannot ban someone with equal or higher permissions.", ephemeral=True); return
        try:
            await user.ban(reason=f"{reason} (by {interaction.user})", delete_message_days=max(0, min(7, delete_days)))
            await log_mod_action("ban", user, interaction.user, reason)
            embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
            embed.add_field(name="User",      value=f"{user.mention} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention,       inline=True)
            embed.add_field(name="Reason",    value=reason,                         inline=False)
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to ban that user.", ephemeral=True)

    # ─── /unban ───────────────────────────────────────────────────────────────
    @app_commands.command(name="unban", description="Unban a user by their ID")
    @app_commands.describe(user_id="User ID to unban", reason="Reason")
    @app_commands.default_permissions(ban_members=True)
    async def slash_unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        log_command("slash_unban")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        try:
            uid  = int(user_id)
            user = await interaction.client.fetch_user(uid)
            await interaction.guild.unban(user, reason=reason)
            await interaction.response.send_message(f"✅ Unbanned **{user}** ({uid}).")
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("❌ User not found or not banned.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to unban.", ephemeral=True)

    # ─── /kick ────────────────────────────────────────────────────────────────
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(user="Member to kick", reason="Reason")
    @app_commands.default_permissions(kick_members=True)
    async def slash_kick(self, interaction: discord.Interaction, user: discord.Member,
                         reason: str = "No reason provided"):
        log_command("slash_kick")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        if user == interaction.user:
            await interaction.response.send_message("❌ You cannot kick yourself.", ephemeral=True); return
        if get_perm_level(user) >= get_perm_level(interaction.user):
            await interaction.response.send_message("❌ Cannot kick someone with equal or higher permissions.", ephemeral=True); return
        try:
            await user.kick(reason=f"{reason} (by {interaction.user})")
            await log_mod_action("kick", user, interaction.user, reason)
            embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
            embed.add_field(name="User",      value=f"{user.mention} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention,       inline=True)
            embed.add_field(name="Reason",    value=reason,                         inline=False)
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to kick that user.", ephemeral=True)

    # ─── /timeout ─────────────────────────────────────────────────────────────
    @app_commands.command(name="timeout", description="Timeout (mute) a member")
    @app_commands.describe(user="Member to timeout", duration="Duration: 1m, 30m, 1h, 1d, 1w", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    async def slash_timeout(self, interaction: discord.Interaction, user: discord.Member,
                            duration: str, reason: str = "No reason provided"):
        log_command("slash_timeout")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        d = duration.lower()
        try:
            if   d.endswith("w"): secs = int(d[:-1]) * 604800
            elif d.endswith("d"): secs = int(d[:-1]) * 86400
            elif d.endswith("h"): secs = int(d[:-1]) * 3600
            elif d.endswith("m"): secs = int(d[:-1]) * 60
            elif d.endswith("s"): secs = int(d[:-1])
            else:                 raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Invalid duration. Use e.g. `10m`, `1h`, `1d`.", ephemeral=True); return
        secs = min(secs, 2419200)   # Discord max: 28 days
        try:
            until = discord.utils.utcnow() + timedelta(seconds=secs)
            await user.timeout(until, reason=reason)
            await log_mod_action("timeout", user, interaction.user, f"{duration} — {reason}")
            embed = discord.Embed(title="⏱️ Member Timed Out", color=discord.Color.yellow())
            embed.add_field(name="User",     value=f"{user.mention} ({user.id})", inline=True)
            embed.add_field(name="Duration", value=duration,                       inline=True)
            embed.add_field(name="Reason",   value=reason,                         inline=False)
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to timeout that user.", ephemeral=True)

    # ─── /untimeout ───────────────────────────────────────────────────────────
    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.describe(user="Member to untimeout")
    @app_commands.default_permissions(moderate_members=True)
    async def slash_untimeout(self, interaction: discord.Interaction, user: discord.Member):
        log_command("slash_untimeout")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        try:
            await user.timeout(None)
            await interaction.response.send_message(f"✅ Removed timeout from {user.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission.", ephemeral=True)

    # ─── /purge ───────────────────────────────────────────────────────────────
    @app_commands.command(name="purge", description="Delete recent messages in this channel")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    async def slash_purge(self, interaction: discord.Interaction, amount: int):
        log_command("slash_purge")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        amount = max(1, min(100, amount))
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.response.send_message(f"🗑️ Deleted **{len(deleted)}** message(s).", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to delete messages.", ephemeral=True)

    # ─── /slowmode ────────────────────────────────────────────────────────────
    @app_commands.command(name="slowmode", description="Set a slowmode for this channel")
    @app_commands.describe(preset="off, relaxed (5s), moderate (15s), strict (30s), or seconds")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_slowmode(self, interaction: discord.Interaction, preset: str):
        log_command("slash_slowmode")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            await interaction.response.send_message("❌ You lack permissions.", ephemeral=True); return
        delay = 0
        p = preset.lower()
        if   p in ["off",      "0"]:  delay = 0
        elif p in ["relaxed",  "5"]:  delay = 5
        elif p in ["moderate", "15"]: delay = 15
        elif p in ["strict",   "30"]: delay = 30
        else:
            try:
                delay = int(p)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid preset. Use: `off`, `relaxed`, `moderate`, `strict`, or a number.", ephemeral=True
                ); return
        try:
            await interaction.channel.edit(slowmode_delay=delay)
            status = f"{delay} seconds" if delay > 0 else "disabled"
            await interaction.response.send_message(f"✅ Slowmode is now {status}.")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to manage this channel.", ephemeral=True)

    # ─── /analytics ───────────────────────────────────────────────────────────
    @app_commands.command(name="analytics", description="[Admin] View command usage analytics")
    @app_commands.default_permissions(administrator=True)
    async def slash_analytics(self, interaction: discord.Interaction):
        from database import analytics_data
        log_command("slash_analytics")
        sorted_cmds = sorted(analytics_data.items(), key=lambda x: x[1].get("total", 0), reverse=True)[:15]
        desc = ""
        for idx, (cmd_name, data) in enumerate(sorted_cmds, 1):
            desc += f"**{idx}.** `/{cmd_name}` - **{data.get('total', 0)}** uses\n"
        if not desc:
            desc = "No command data available yet."
        embed = discord.Embed(title="📊 Command Usage Analytics", description=desc, color=discord.Color.purple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ─── /tempban ─────────────────────────────────────────────────────────────
    @app_commands.command(name="tempban", description="Temporarily ban a member")
    @app_commands.describe(user="Member to tempban", duration="Duration: 1d, 7d, 1m", reason="Reason")
    @app_commands.default_permissions(ban_members=True)
    async def slash_tempban(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "No reason provided"):
        from database import temp_bans, save_temp_bans
        log_command("slash_tempban")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            return await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
        if user == interaction.user:
            return await interaction.response.send_message("❌ You cannot ban yourself.", ephemeral=True)
        if get_perm_level(user) >= get_perm_level(interaction.user):
            return await interaction.response.send_message("❌ Cannot ban someone with equal or higher permissions.", ephemeral=True)
        
        d = duration.lower()
        secs = 0
        try:
            if   d.endswith("mo") or d.endswith("m"): secs = int(d.replace("mo","").replace("m","")) * 2592000
            elif d.endswith("w"): secs = int(d[:-1]) * 604800
            elif d.endswith("d"): secs = int(d[:-1]) * 86400
            elif d.endswith("h"): secs = int(d[:-1]) * 3600
            else:                 raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Invalid duration. Use e.g. `7d`, `1w`, `1m`.", ephemeral=True)

        until = datetime.now() + timedelta(seconds=secs)
        
        try:
            await user.ban(reason=f"[TempBan {duration}] {reason} (by {interaction.user})")
            temp_bans[str(user.id)] = {
                "guild_id": interaction.guild.id,
                "unban_time": until.isoformat()
            }
            save_temp_bans()
            await log_mod_action("tempban", user, interaction.user, f"{duration} - {reason}")
            
            embed = discord.Embed(title="⏳ Member Temporarily Banned", color=discord.Color.red())
            embed.add_field(name="User",      value=f"{user.mention} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention,       inline=True)
            embed.add_field(name="Duration",  value=duration,                       inline=True)
            embed.add_field(name="Reason",    value=reason,                         inline=False)
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to ban that user.", ephemeral=True)

    # ─── Staff Notes ──────────────────────────────────────────────────────────
    note_group = app_commands.Group(name="note", description="Manage staff notes for a user")

    @note_group.command(name="add", description="Add a silent note to a user's record")
    @app_commands.describe(user="User to note", note="The note content")
    @app_commands.default_permissions(manage_messages=True)
    async def note_add(self, interaction: discord.Interaction, user: discord.Member, note: str):
        from database import staff_notes, save_staff_notes
        log_command("note_add")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            return await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
            
        uid = str(user.id)
        if uid not in staff_notes:
            staff_notes[uid] = []
            
        staff_notes[uid].append({
            "timestamp": datetime.now().isoformat(),
            "mod_id": str(interaction.user.id),
            "note": note
        })
        save_staff_notes()
        
        await interaction.response.send_message(f"✅ Added silent note for {user.mention}.", ephemeral=True)

    @note_group.command(name="view", description="View all notes for a user")
    @app_commands.describe(user="User to view")
    @app_commands.default_permissions(manage_messages=True)
    async def note_view(self, interaction: discord.Interaction, user: discord.Member):
        from database import staff_notes
        log_command("note_view")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            return await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
            
        uid = str(user.id)
        notes = staff_notes.get(uid, [])
        if not notes:
            return await interaction.response.send_message(f"✅ {user.display_name} has no staff notes.", ephemeral=True)
            
        desc = ""
        for i, n in enumerate(notes, 1):
            desc += f"**{i}.** {n.get('timestamp','')[:10]} - {n.get('note')} (Mod: <@{n.get('mod_id')}>)\n"
            
        embed = discord.Embed(title=f"📝 Notes for {user.display_name}", description=desc, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ─── /lock ───────────────────────────────────────────────────────────────
    @app_commands.command(name="lock", description="Lock the current channel")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_lock(self, interaction: discord.Interaction):
        log_command("slash_lock")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            return await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
        
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("🔒 This channel has been locked.")

    # ─── /unlock ─────────────────────────────────────────────────────────────
    @app_commands.command(name="unlock", description="Unlock the current channel")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_unlock(self, interaction: discord.Interaction):
        log_command("slash_unlock")
        if get_perm_level(interaction.user) < PermLevel.MODERATOR:
            return await interaction.response.send_message("❌ You lack permissions.", ephemeral=True)
        
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("🔓 This channel has been unlocked.")


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
