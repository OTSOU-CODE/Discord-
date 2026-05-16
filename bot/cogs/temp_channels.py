"""cogs/temp_channels.py — Temp voice channels + /channel group commands"""
import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord import app_commands

import database as db
from database import (
    temp_channels, channel_settings, channel_whitelists, channel_blacklists,
    scheduled_deletions, channel_last_activity, muted_users,
    save_temp_channels,
)
from config import CREATOR_CHANNEL_ID, TEMP_CHANNEL_CATEGORY_ID
from utils import get_economy, save_economy


def _is_owner(channel_id, author_id):
    return temp_channels.get(channel_id) == author_id

def _has_admin(member):
    return member.guild_permissions.administrator

def _check_owner(interaction):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
        return False, "You must be in a voice channel."
    vc = interaction.user.voice.channel
    if vc.id not in temp_channels:
        return False, "You are not in a temporary channel."
    if temp_channels[vc.id] != interaction.user.id:
        return False, "Only the channel owner can use this command."
    return True, vc


class VCRenameModal(discord.ui.Modal, title="Rename Channel"):
    name_input = discord.ui.TextInput(
        label="New Channel Name",
        style=discord.TextStyle.short,
        placeholder="Enter new name...",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        valid, vc = _check_owner(interaction)
        if not valid:
            return await interaction.response.send_message(vc, ephemeral=True)
        
        try:
            await vc.edit(name=self.name_input.value)
            await interaction.response.send_message(f"✅ Renamed to **{self.name_input.value}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

class VCLimitModal(discord.ui.Modal, title="Set User Limit"):
    limit_input = discord.ui.TextInput(
        label="User Limit (0 for unlimited)",
        style=discord.TextStyle.short,
        placeholder="e.g. 5",
        required=True,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        valid, vc = _check_owner(interaction)
        if not valid:
            return await interaction.response.send_message(vc, ephemeral=True)
        try:
            limit = int(self.limit_input.value)
            await vc.edit(user_limit=limit)
            await interaction.response.send_message(f"✅ User limit set to **{limit if limit > 0 else 'unlimited'}**", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)

class VoiceControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.danger, custom_id="vc_lock", emoji="🔒")
    async def lock_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        valid, vc = _check_owner(interaction)
        if not valid: return await interaction.response.send_message(vc, ephemeral=True)
        await vc.set_permissions(interaction.guild.default_role, connect=False)
        channel_settings.setdefault(vc.id, {})["mode"] = "private"
        save_temp_channels()
        await interaction.response.send_message("🔒 Channel locked. Only whitelisted users can join.", ephemeral=True)

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.success, custom_id="vc_unlock", emoji="🔓")
    async def unlock_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        valid, vc = _check_owner(interaction)
        if not valid: return await interaction.response.send_message(vc, ephemeral=True)
        await vc.set_permissions(interaction.guild.default_role, connect=True)
        channel_settings.setdefault(vc.id, {})["mode"] = "public"
        save_temp_channels()
        await interaction.response.send_message("🔓 Channel unlocked. Anyone can join.", ephemeral=True)

    @discord.ui.button(label="Hide", style=discord.ButtonStyle.secondary, custom_id="vc_hide", emoji="👻")
    async def hide_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        valid, vc = _check_owner(interaction)
        if not valid: return await interaction.response.send_message(vc, ephemeral=True)
        await vc.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message("👻 Channel is now hidden from the public.", ephemeral=True)

    @discord.ui.button(label="Unhide", style=discord.ButtonStyle.primary, custom_id="vc_unhide", emoji="👀")
    async def unhide_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        valid, vc = _check_owner(interaction)
        if not valid: return await interaction.response.send_message(vc, ephemeral=True)
        await vc.set_permissions(interaction.guild.default_role, view_channel=True)
        await interaction.response.send_message("👀 Channel is now visible to the public.", ephemeral=True)

    @discord.ui.button(label="Rename", style=discord.ButtonStyle.secondary, custom_id="vc_rename", emoji="✏️")
    async def rename_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        valid, vc = _check_owner(interaction)
        if not valid: return await interaction.response.send_message(vc, ephemeral=True)
        await interaction.response.send_modal(VCRenameModal())

    @discord.ui.button(label="Limit", style=discord.ButtonStyle.secondary, custom_id="vc_limit", emoji="👥")
    async def limit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        valid, vc = _check_owner(interaction)
        if not valid: return await interaction.response.send_message(vc, ephemeral=True)
        await interaction.response.send_modal(VCLimitModal())


async def _send_help(channel, guild):
    embed = discord.Embed(
        title="🎙️ Welcome to Your Voice Channel!",
        description="You own this temp channel. Use the panel below to quickly manage your privacy and settings.",
        color=0xD4AF37,  # Gold accent
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="⚙️ Advanced Commands", value=(
        "You can still use prefix commands in the chat for more control:\n"
        "👑 **`.give @u`** 🎯 **`.claim`** 👢 **`.kick @u`**\n"
        "✅ **`.allow @u`** ❌ **`.deny @u`**\n"
        "📋 **`.whitelist @u`** 🚫 **`.blacklist @u`**\n"
        "🗑️ **`.autodelete <min>`** ⏱️ **`.slowmode <s>`**"
    ), inline=False)
    embed.set_footer(text="💡 Only you can use these buttons and commands.")
    try:
        await channel.send(embed=embed, view=VoiceControlPanel())
    except Exception:
        pass


async def _manage_temp_channels(guild):
    category = guild.get_channel(TEMP_CHANNEL_CATEGORY_ID)
    if not category or not isinstance(category, discord.CategoryChannel):
        return
    creator = guild.get_channel(CREATOR_CHANNEL_ID)
    if not creator or not creator.members:
        return
    waiting = [m for m in creator.members if not m.bot]
    if not waiting:
        return
    waiting.sort(key=lambda m: m.top_role.position, reverse=True)
    member = waiting[0]
    try:
        overwrites = category.overwrites.copy()
        overwrites[member] = discord.PermissionOverwrite(
            manage_channels=True, kick_members=True,
            manage_permissions=True, view_channel=True, connect=True,
        )
        temp_ch = await guild.create_voice_channel(
            name=f"{member.display_name}'s Channel", category=category, overwrites=overwrites
        )
        await member.move_to(temp_ch)
        temp_channels[temp_ch.id] = member.id
        channel_settings[temp_ch.id] = {"mode": "public", "recording": False, "video": True}
        save_temp_channels()
        await _send_help(temp_ch, guild)
    except discord.Forbidden:
        pass
    except Exception as e:
        print(f"[TempCh] Error creating channel: {e}")


class TempChannelsCog(commands.Cog, name="TempChannels"):
    def __init__(self, bot):
        self.bot = bot

    # ── /channel group ────────────────────────────────────────────────────────
    channel_group = app_commands.Group(name="channel", description="Manage your temporary channel")

    @channel_group.command(name="rename", description="Rename your temp channel")
    @app_commands.describe(name="New channel name")
    async def ch_rename(self, interaction: discord.Interaction, name: str):
        valid, result = _check_owner(interaction)
        if not valid:
            return await interaction.response.send_message(result, ephemeral=True)
        try:
            await result.edit(name=name)
            await interaction.response.send_message(f"✅ Renamed to **{name}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

    @channel_group.command(name="limit", description="Set user limit for your channel")
    @app_commands.describe(limit="Number of users (0=unlimited)")
    async def ch_limit(self, interaction: discord.Interaction, limit: int):
        valid, result = _check_owner(interaction)
        if not valid:
            return await interaction.response.send_message(result, ephemeral=True)
        try:
            await result.edit(user_limit=limit)
            s = f"{limit} users" if limit > 0 else "unlimited"
            await interaction.response.send_message(f"✅ User limit set to **{s}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

    @channel_group.command(name="mode", description="Toggle public/private access")
    @app_commands.describe(access="Public or Private")
    @app_commands.choices(access=[
        app_commands.Choice(name="Public",  value="public"),
        app_commands.Choice(name="Private", value="private"),
    ])
    async def ch_mode(self, interaction: discord.Interaction, access: str):
        valid, result = _check_owner(interaction)
        if not valid:
            return await interaction.response.send_message(result, ephemeral=True)
        try:
            ow = result.overwrites
            if access == "private":
                ow[interaction.guild.default_role] = discord.PermissionOverwrite(connect=False)
            else:
                ow[interaction.guild.default_role] = discord.PermissionOverwrite(connect=True)
            await result.edit(overwrites=ow)
            channel_settings.setdefault(result.id, {})["mode"] = access
            save_temp_channels()
            await interaction.response.send_message(f"✅ Channel is now **{access.title()}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

    @channel_group.command(name="video", description="Toggle video/camera permissions")
    @app_commands.describe(toggle="Enable or Disable")
    @app_commands.choices(toggle=[
        app_commands.Choice(name="Enable",  value="on"),
        app_commands.Choice(name="Disable", value="off"),
    ])
    async def ch_video(self, interaction: discord.Interaction, toggle: str):
        valid, result = _check_owner(interaction)
        if not valid:
            return await interaction.response.send_message(result, ephemeral=True)
        enabled = toggle == "on"
        try:
            ow   = result.overwrites
            perm = ow.get(interaction.guild.default_role, discord.PermissionOverwrite())
            perm.stream = enabled
            ow[interaction.guild.default_role] = perm
            await result.edit(overwrites=ow)
            channel_settings.setdefault(result.id, {})["video"] = enabled
            save_temp_channels()
            await interaction.response.send_message(
                f"📹 Video sharing {'enabled' if enabled else 'disabled'}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I lack permissions.", ephemeral=True)

    @channel_group.command(name="clone", description="Clone your temporary channel")
    async def ch_clone(self, interaction: discord.Interaction):
        valid, result = _check_owner(interaction)
        if not valid:
            return await interaction.response.send_message(result, ephemeral=True)
        try:
            await interaction.response.defer(ephemeral=True)
            cloned = await interaction.guild.create_voice_channel(
                name=f"{result.name} (Clone)", category=result.category,
                bitrate=result.bitrate, user_limit=result.user_limit, overwrites=result.overwrites,
            )
            temp_channels[cloned.id] = interaction.user.id
            channel_settings[cloned.id] = channel_settings.get(result.id, {}).copy()
            save_temp_channels()
            await interaction.followup.send(f"✅ Cloned! You now own {cloned.mention}")
        except discord.Forbidden:
            await interaction.followup.send("❌ I lack permissions.", ephemeral=True)

    @channel_group.command(name="kick", description="Kick a user from your temp channel")
    @app_commands.describe(user_to_kick="The user to kick")
    async def ch_kick(self, interaction: discord.Interaction, user_to_kick: discord.Member):
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
            return await interaction.response.send_message("You must be in a voice channel.", ephemeral=True)
        vc = interaction.user.voice.channel
        if vc.id not in temp_channels:
            return await interaction.response.send_message("You are not in a temporary channel.", ephemeral=True)
        if not _is_owner(vc.id, interaction.user.id):
            return await interaction.response.send_message("Only the channel owner can use this.", ephemeral=True)
        if _has_admin(user_to_kick):
            return await interaction.response.send_message(
                f"❌ Cannot kick {user_to_kick.mention} — they have administrator permissions.", ephemeral=True)
        if user_to_kick in vc.members:
            await user_to_kick.move_to(None, reason=f"Kicked by channel owner {interaction.user.name}")
            await interaction.response.send_message(f"👢 Kicked {user_to_kick.mention} from your channel.")
        else:
            await interaction.response.send_message(f"{user_to_kick.mention} is not in this channel.", ephemeral=True)

    @channel_group.command(name="record", description="Start a recorded session and ask for consent")
    async def ch_record(self, interaction: discord.Interaction):
        valid, result = _check_owner(interaction)
        if not valid:
            return await interaction.response.send_message(result, ephemeral=True)
        await interaction.response.send_message("🔴 **Recording started!** Sending consent requests...", ephemeral=False)
        channel_settings.setdefault(result.id, {})["recording"] = True
        save_temp_channels()

        async def process_consent(member, dm_msg, vc):
            def check(r, u):
                return u == member and str(r.emoji) in ["✅", "❌"] and r.message.id == dm_msg.id
            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "❌":
                    if member in vc.members:
                        await member.move_to(None, reason="Recording consent denied.")
                        await member.send("⚠️ You were disconnected because you declined recording consent.")
                else:
                    await member.send("✅ Thank you for consenting to the recording.")
            except asyncio.TimeoutError:
                if member in vc.members:
                    await member.move_to(None, reason="Recording consent timed out.")
                    await member.send("⚠️ You were disconnected because you did not respond in time.")

        for mem in result.members:
            if mem.id == interaction.user.id or mem.bot:
                continue
            try:
                dm = await mem.send(
                    f"⚠️ **Recording Consent Required**\nThe channel **{result.name}** is being recorded.\n"
                    "React ✅ to consent or ❌ to decline. You will be removed in 60s if no response."
                )
                await dm.add_reaction("✅")
                await dm.add_reaction("❌")
                self.bot.loop.create_task(process_consent(mem, dm, result))
            except discord.Forbidden:
                if mem in result.members:
                    await mem.move_to(None, reason="Cannot verify recording consent (DMs closed).")

    # ── Voice state event ─────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        import database as db
        db.cache_member_name(member)

        # Mute detection
        if after.channel:
            was_muted = (before.mute or before.self_mute) if before.channel else False
            is_muted  = after.mute or after.self_mute
            if not was_muted and is_muted:
                muted_users[member.id] = {"mute_start": datetime.now(), "guild_id": member.guild.id}
            elif was_muted and not is_muted:
                muted_users.pop(member.id, None)
        if not after.channel:
            muted_users.pop(member.id, None)

        # Channel deletion
        if before.channel and before.channel.id in temp_channels:
            ch       = before.channel
            owner_id = temp_channels[ch.id]
            if not ch.members:
                try:
                    await ch.delete(reason="Temporary channel is empty.")
                    del temp_channels[ch.id]
                    channel_settings.pop(ch.id, None)
                    save_temp_channels()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    print(f"[TempCh] Cannot delete '{ch.name}'.")
                except Exception as e:
                    print(f"[TempCh] Error deleting: {e}")
            elif member.id == owner_id and after.channel != ch:
                await ch.send(
                    f"The owner, {member.mention}, has left. Another user can type `.claim` to take ownership.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )

        # Create channels for waiting users
        await _manage_temp_channels(member.guild)

    # ── on_message prefix commands for temp channels ──────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.content.startswith("."):
            return
        if not isinstance(message.author, discord.Member) or not message.author.voice:
            return
        vc = message.author.voice.channel
        if vc.id not in temp_channels:
            return

        channel = vc
        parts   = message.content[1:].split()
        command = parts[0].lower() if parts else ""
        args    = parts[1:]

        # --- claim (no owner required) ---
        if command == "claim":
            owner_id = temp_channels.get(channel.id)
            owner    = message.guild.get_member(owner_id) if owner_id else None
            if not owner or owner not in channel.members:
                temp_channels[channel.id] = message.author.id
                save_temp_channels()
                if owner:
                    await channel.set_permissions(owner, overwrite=None)
                await channel.set_permissions(
                    message.author, manage_channels=True, kick_members=True, manage_permissions=True)
                await message.reply(f"👑 {message.author.mention} has claimed ownership!")
            else:
                await message.reply("You can only claim if the original owner is not in the channel.")
            return

        if not _is_owner(channel.id, message.author.id):
            await message.reply("Only the channel owner can use this command.", delete_after=5)
            return

        try:
            if command == "rename":
                if not args:
                    await message.reply("Usage: `.rename <new-name>`"); return
                await channel.edit(name=" ".join(args))
                await message.reply(f"✏️ Renamed to `{' '.join(args)}`.")

            elif command == "limit":
                if not args or not args[0].isdigit():
                    await message.reply("Usage: `.limit <number>`"); return
                lim = int(args[0])
                await channel.edit(user_limit=lim)
                await message.reply(f"👥 Limit set to `{lim if lim > 0 else 'unlimited'}`.")

            elif command == "lock":
                await channel.set_permissions(message.guild.default_role, connect=False)
                await channel.set_permissions(message.author, connect=True)
                channel_settings.setdefault(channel.id, {})["mode"] = "private"
                save_temp_channels()
                await message.reply("🔒 Channel locked.")

            elif command == "unlock":
                await channel.set_permissions(message.guild.default_role, connect=True)
                channel_settings.setdefault(channel.id, {})["mode"] = "public"
                save_temp_channels()
                await message.reply("🔓 Channel unlocked.")

            elif command == "clone":
                cloned = await message.guild.create_voice_channel(
                    name=f"{channel.name} (Clone)", category=channel.category,
                    bitrate=channel.bitrate, user_limit=channel.user_limit, overwrites=channel.overwrites,
                )
                temp_channels[cloned.id] = message.author.id
                channel_settings[cloned.id] = channel_settings.get(channel.id, {
                    "mode": "public", "recording": False, "video": True}).copy()
                save_temp_channels()
                await message.reply(f"👯 Cloned to {cloned.mention}!")

            elif command in ("video", "screenshare"):
                if not args:
                    await message.reply("Usage: `.video on|off`"); return
                enabled = args[0] == "on"
                await channel.set_permissions(message.guild.default_role, stream=enabled)
                channel_settings.setdefault(channel.id, {})["video"] = enabled
                save_temp_channels()
                await message.reply(f"📹 Video {'enabled' if enabled else 'disabled'}.")

            elif command == "allow":
                if not message.mentions:
                    await message.reply("Usage: `.allow @user`"); return
                await channel.set_permissions(message.mentions[0], connect=True)
                await message.reply(f"✅ {message.mentions[0].mention} can now join.")

            elif command == "deny":
                if not message.mentions:
                    await message.reply("Usage: `.deny @user`"); return
                await channel.set_permissions(message.mentions[0], connect=None)
                await message.reply(f"❌ Permissions reset for {message.mentions[0].mention}.")

            elif command == "give":
                if not message.mentions:
                    await message.reply("Usage: `.give @user`"); return
                new_owner = message.mentions[0]
                if new_owner not in channel.members:
                    await message.reply(f"{new_owner.mention} is not in this channel."); return
                temp_channels[channel.id] = new_owner.id
                await channel.set_permissions(message.author, overwrite=None)
                await channel.set_permissions(new_owner, manage_channels=True, kick_members=True, manage_permissions=True)
                save_temp_channels()
                await message.reply(f"👑 Ownership transferred to {new_owner.mention}.")

            elif command == "lockchat":
                await channel.set_permissions(message.guild.default_role, send_messages=False)
                await message.reply("🔇 Chat locked.")

            elif command == "unlockchat":
                await channel.set_permissions(message.guild.default_role, send_messages=True)
                await message.reply("🔊 Chat unlocked.")

            elif command == "whitelist":
                if not message.mentions:
                    await message.reply("Usage: `.whitelist @user`"); return
                target = message.mentions[0]
                wl = channel_whitelists.setdefault(channel.id, [])
                if target.id not in wl:
                    wl.append(target.id)
                    await message.reply(f"✅ {target.mention} added to whitelist.")
                else:
                    await message.reply(f"{target.mention} is already whitelisted.")

            elif command == "blacklist":
                if not message.mentions:
                    await message.reply("Usage: `.blacklist @user`"); return
                target = message.mentions[0]
                if _has_admin(target):
                    await message.reply("❌ Cannot blacklist administrators."); return
                bl = channel_blacklists.setdefault(channel.id, [])
                if target.id not in bl:
                    bl.append(target.id)
                    await channel.set_permissions(target, connect=False)
                    await message.reply(f"🚫 {target.mention} blacklisted.")
                else:
                    await message.reply(f"{target.mention} is already blacklisted.")

            elif command == "unblacklist":
                if not message.mentions:
                    await message.reply("Usage: `.unblacklist @user`"); return
                target = message.mentions[0]
                bl = channel_blacklists.get(channel.id, [])
                if target.id in bl:
                    bl.remove(target.id)
                    await channel.set_permissions(target, connect=None)
                    await message.reply(f"✅ {target.mention} removed from blacklist.")
                else:
                    await message.reply(f"{target.mention} is not blacklisted.")

            elif command == "info":
                owner = message.guild.get_member(temp_channels[channel.id])
                embed = discord.Embed(title=f"📊 {channel.name} — Info", color=discord.Color.blue())
                embed.add_field(name="👤 Owner",      value=owner.mention if owner else "Unknown", inline=True)
                embed.add_field(name="👥 Members",    value=f"`{len(channel.members)}`",           inline=True)
                embed.add_field(name="📏 Limit",      value=f"`{channel.user_limit or 'Unlimited'}`", inline=True)
                embed.add_field(name="🔊 Bitrate",    value=f"`{channel.bitrate // 1000}` kbps",   inline=True)
                embed.add_field(name="📅 Created",    value=f"`{channel.created_at.strftime('%Y-%m-%d %H:%M')}`", inline=True)
                await message.reply(embed=embed)

            elif command in ("members", "list"):
                if not channel.members:
                    await message.reply("No members in this channel."); return
                ml    = "\n".join(f"• {m.mention}" for m in channel.members)
                embed = discord.Embed(title=f"👥 Members in {channel.name}", description=ml, color=discord.Color.green())
                embed.set_footer(text=f"Total: {len(channel.members)} members")
                await message.reply(embed=embed)

            elif command == "slowmode":
                if not args or not args[0].isdigit():
                    await message.reply("Usage: `.slowmode <seconds>` (0-21600)"); return
                sm = int(args[0])
                if not 0 <= sm <= 21600:
                    await message.reply("Slowmode must be 0–21600 seconds."); return
                await channel.edit(slowmode_delay=sm)
                await message.reply(f"⏱️ Slowmode set to `{sm}s`." if sm else "⏱️ Slowmode disabled.")

            elif command == "autodelete":
                if not args or not args[0].isdigit():
                    await message.reply("Usage: `.autodelete <minutes>`"); return
                minutes = int(args[0])
                channel_settings.setdefault(channel.id, {})["autodelete"] = minutes
                channel_last_activity[channel.id] = datetime.now()
                await message.reply(f"🗑️ Auto-delete after `{minutes}` min of inactivity.")

            elif command == "schedule-delete":
                if not args:
                    await message.reply("Usage: `.schedule-delete <minutes>`"); return
                try:
                    minutes = int(args[0])
                    scheduled_deletions[channel.id] = datetime.now() + timedelta(minutes=minutes)
                    await message.reply(f"⏰ Scheduled deletion in `{minutes}` minutes.")
                except ValueError:
                    await message.reply("Please provide a valid number of minutes.")

            elif command == "timer":
                if not args or not args[0].isdigit():
                    await message.reply("Usage: `.timer <minutes>`"); return
                minutes = int(args[0])
                embed   = discord.Embed(title="⏱️ Countdown Timer",
                                        description=f"Timer set for `{minutes}` minutes",
                                        color=discord.Color.red())
                await message.reply(embed=embed)
                await asyncio.sleep(minutes * 60)
                embed.description = "⏰ Time's up!"
                embed.color       = discord.Color.green()
                try:
                    await message.reply(embed=embed)
                except Exception:
                    pass

            elif command == "settings":
                embed = discord.Embed(title=f"⚙️ {channel.name} — Settings", color=discord.Color.purple())
                embed.add_field(name="👥 Limit",   value=f"`{channel.user_limit or 'Unlimited'}`", inline=True)
                embed.add_field(name="⏱️ Slowmode", value=f"`{channel.slowmode_delay}s`" if channel.slowmode_delay else "Disabled", inline=True)
                settings = channel_settings.get(channel.id, {})
                if "autodelete" in settings:
                    embed.add_field(name="🗑️ Auto-Delete", value=f"`{settings['autodelete']}` min", inline=True)
                embed.add_field(name="✅ Whitelisted", value=f"`{len(channel_whitelists.get(channel.id, []))}`", inline=True)
                embed.add_field(name="🚫 Blacklisted", value=f"`{len(channel_blacklists.get(channel.id, []))}`", inline=True)
                if channel.id in scheduled_deletions:
                    remaining = (scheduled_deletions[channel.id] - datetime.now()).total_seconds() / 60
                    embed.add_field(name="⏰ Sched Delete", value=f"In `{int(remaining)}` min", inline=False)
                await message.reply(embed=embed)

            elif command == "reset":
                await channel.edit(name=f"{message.author.display_name}'s Channel", user_limit=0, slowmode_delay=0)
                await channel.set_permissions(message.guild.default_role, connect=True, send_messages=True)
                channel_settings.pop(channel.id, None)
                channel_whitelists.pop(channel.id, None)
                channel_blacklists.pop(channel.id, None)
                scheduled_deletions.pop(channel.id, None)
                await message.reply("🔄 Channel reset to defaults.")

            elif command == "kick":
                if not message.mentions:
                    await message.reply("Usage: `.kick @user`"); return
                target = message.mentions[0]
                if _has_admin(target):
                    await message.reply("❌ Cannot kick administrators."); return
                if target in channel.members:
                    await target.move_to(None, reason=f"Kicked by channel owner {message.author.name}")
                    await message.reply(f"👢 {target.mention} kicked.")
                else:
                    await message.reply(f"{target.mention} is not in this channel.")

            elif command == "purge":
                limit   = int(args[0]) + 1 if args and args[0].isdigit() else 101
                deleted = await message.channel.purge(limit=limit)
                await message.channel.send(f"Deleted {len(deleted)} messages.", delete_after=5)

            elif command == "help":
                await _send_help(channel, message.guild)

        except discord.Forbidden:
            await message.reply("I don't have the required permissions.")
        except Exception as e:
            await message.reply("An unexpected error occurred.")
            print(f"[TempCh] Error in command '{command}': {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(TempChannelsCog(bot))
    bot.add_view(VoiceControlPanel())
