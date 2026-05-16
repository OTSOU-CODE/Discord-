"""
cogs/tickets.py  —  Ticket open / close / log system
"""
import asyncio
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

from database import tickets_data, save_tickets
from config import (
    TICKET_CATEGORY_ID, TICKET_LOG_CHANNEL_ID, MOD_ROLE_ID,
    TICKET_PANEL_CHANNEL_ID, config, save_config,
)
from utils import log_command


# ─── Shared: open a ticket ────────────────────────────────────────────────────
async def _open_ticket(interaction: discord.Interaction, category_name: str = "General"):
    """Called by both the panel menu and /ticket open."""
    log_command("ticket_open")

    tc_id = config.get("ticket_category_id", 0)
    if not tc_id or int(tc_id) == 0:
        await interaction.response.send_message(
            "❌ The ticket system has not been configured yet. "
            "Ask an admin to set `ticket_category_id` in config.",
            ephemeral=True,
        )
        return

    guild    = interaction.guild
    category = guild.get_channel(int(tc_id))

    if not category or not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message(
            "❌ Ticket category not found. Please check `ticket_category_id` in config.",
            ephemeral=True,
        )
        return

    # Guard: user already has an open ticket?
    for data in tickets_data.values():
        if (
            data.get("opener_id") == interaction.user.id
            and data.get("status") == "open"
        ):
            existing_ch = guild.get_channel(data.get("channel_id"))
            mention     = existing_ch.mention if existing_ch else "your existing ticket"
            await interaction.response.send_message(
                f"❌ You already have an open ticket: {mention}", ephemeral=True
            )
            return

    # Collision-safe ticket ID
    existing_nums = []
    for tid in tickets_data:
        try:
            existing_nums.append(int(tid.split("-")[-1]))
        except (ValueError, IndexError):
            pass
    ticket_num = (max(existing_nums) + 1) if existing_nums else 1
    ticket_id  = f"ticket-{ticket_num:04d}"

    # Channel permission overwrites
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user:   discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True,
            read_message_history=True
        ),
    }
    mr_id = config.get("mod_role_id", 0)
    if mr_id and int(mr_id) != 0:
        mod_role = guild.get_role(int(mr_id))
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )

    try:
        ch = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"[{category_name}] Support ticket for {interaction.user.display_name} | ID: {ticket_id}",
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to create channels in that category.", ephemeral=True
        )
        return
    except Exception as e:
        await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)
        return

    # Persist to database
    tickets_data[ticket_id] = {
        "opener_id":  interaction.user.id,
        "channel_id": ch.id,
        "status":     "open",
        "opened_at":  datetime.utcnow().isoformat(),
    }
    save_tickets()

    # Welcome embed inside the ticket channel
    embed = discord.Embed(
        title=f"🎫 Ticket #{ticket_num:04d}",
        description=(
            f"Welcome {interaction.user.mention}!\n\n"
            f"**Category:** {category_name}\n"
            "Please describe your issue and a moderator will assist you shortly.\n\n"
            "Click **Close Ticket** when your issue is resolved."
        ),
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    embed.set_footer(text=f"Ticket ID: {ticket_id}")

    try:
        await ch.send(embed=embed, view=TicketCloseButton())
    except Exception as e:
        print(f"[Tickets] Could not send welcome message: {e}")

    await interaction.response.send_message(
        f"✅ Your ticket has been created: {ch.mention}", ephemeral=True
    )

    # Notify the bot owner via DM
    try:
        app_info = await interaction.client.application_info()
        owner = app_info.owner
        if owner:
            dm_embed = discord.Embed(
                title="🚨 New Ticket Opened",
                description=(
                    f"**Ticket ID:** `{ticket_id}`\n"
                    f"**User:** {interaction.user.mention} ({interaction.user.name})\n"
                    f"**Category:** {category_name}\n"
                    f"**Ticket:** {ch.mention}"
                ),
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await owner.send(embed=dm_embed)
    except Exception as e:
        print(f"[Tickets] Failed to notify owner via DM: {e}")


# ─── Shared: close a ticket ───────────────────────────────────────────────────
async def _close_ticket(interaction: discord.Interaction):
    """Find the ticket owning the current channel, mark it closed, log it, delete after 5 s."""
    channel   = interaction.channel
    ticket_id = next(
        (tid for tid, d in tickets_data.items()
         if d.get("channel_id") == channel.id and d.get("status") == "open"),
        None,
    )

    if not ticket_id:
        await interaction.response.send_message(
            "❌ This channel is not an open ticket.", ephemeral=True
        )
        return

    await interaction.response.send_message("🔒 Ticket will be closed in **5 seconds**... ")

    import chat_exporter
    import io
    
    transcript = None
    try:
        # Generate transcript using chat-exporter
        transcript_str = await chat_exporter.export(channel)
        if transcript_str:
            transcript = discord.File(io.BytesIO(transcript_str.encode()), filename=f"transcript-{ticket_id}.html")
    except Exception as e:
        print(f"[Tickets] Transcript generation failed: {e}")

    info           = tickets_data[ticket_id]
    info["status"] = "closed"
    info["closed_at"] = datetime.utcnow().isoformat()
    save_tickets()

    # Post to log channel
    tl_id = config.get("ticket_log_channel_id", 0)
    if tl_id:
        log_ch = interaction.guild.get_channel(int(tl_id))
        if log_ch:
            opener = interaction.guild.get_member(info.get("opener_id"))
            embed  = discord.Embed(
                title=f"🔒 Ticket Closed — {channel.name}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow(),
            )
            embed.add_field(name="Ticket ID", value=ticket_id,                               inline=True)
            embed.add_field(name="Opened By", value=opener.mention if opener else "Unknown", inline=True)
            embed.add_field(name="Closed By", value=interaction.user.mention,                inline=True)
            embed.add_field(
                name="Opened At",
                value=info.get("opened_at", "—")[:19].replace("T", " "),
                inline=False,
            )
            try:
                if transcript:
                    await log_ch.send(embed=embed, file=transcript)
                else:
                    await log_ch.send(embed=embed)
            except Exception as e:
                print(f"[Tickets] Log send error: {e}")

    await asyncio.sleep(5)

    try:
        await channel.delete(
            reason=f"Ticket {ticket_id} closed by {interaction.user.display_name}"
        )
    except discord.NotFound:
        pass
    except discord.Forbidden:
        print(f"[Tickets] Cannot delete channel for {ticket_id} — missing permissions.")


# ─── Fixed panel embed ────────────────────────────────────────────────────────
def _build_panel_embed(guild: discord.Guild) -> discord.Embed:
    """
    The authoritative, fixed ticket-panel embed.
    Edit only this function to redesign the panel for the whole bot.
    """
    embed = discord.Embed(
        title="🎫  Open a Support Ticket",
        description=(
            "> 👋  Welcome to the **OTSOU** support ticket system!\n"
            "> If you have any issue, question, or special request, click the button below.\n"
            "\u200b"
        ),
        color=0xD4AF37,   # OTSOU gold
    )

    embed.add_field(
        name="❓  When should you open a ticket?",
        value=(
            "︱You have a technical or account issue\n"
            "︱You want to report someone\n"
            "︱You have a special request or complaint\n"
            "︱You need help from the staff team"
        ),
        inline=True,
    )
    embed.add_field(
        name="⚠️  Important Notes",
        value=(
            "︱Only **one** open ticket at a time\n"
            "︱Do not open a ticket without a valid reason\n"
            "︱Staff will respond as soon as possible\n"
            "︱Close your ticket once the issue is resolved"
        ),
        inline=True,
    )
    embed.add_field(
        name="📍  How does it work?",
        value=(
            "**1.**  Click the **🎫 Open a Ticket** button below\n"
            "**2.**  A private channel will be created just for you\n"
            "**3.**  Describe your issue clearly to the team\n"
            "**4.**  Wait for a staff member to respond\n"
            "**5.**  Press **🔒 Close Ticket** when you're done"
        ),
        inline=False,
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(
        text=f"{guild.name}  •  Support System  •  We hope you have a great experience ✨",
        icon_url=guild.icon.url if guild.icon else None,
    )
    return embed


# ─── Persistent views ─────────────────────────────────────────────────────────
class TicketCategorySelect(discord.ui.Select):
    """
    Dropdown menu to choose ticket category.
    """
    def __init__(self):
        options = [
            discord.SelectOption(label="Technical Support", value="Technical Support", description="Get help with technical issues", emoji="🔧"),
            discord.SelectOption(label="Partnership", value="Partnership", description="Discuss partnership opportunities", emoji="📝"),
            discord.SelectOption(label="Report a User", value="Report a User", description="Report rule-breaking behavior", emoji="⚠️"),
            discord.SelectOption(label="Other", value="Other Inquiries", description="Any other inquiries", emoji="❔"),
        ]
        super().__init__(
            placeholder="Choose a ticket category...",
            min_values=1, max_values=1,
            options=options,
            custom_id="ticket_category_select"
        )

    async def callback(self, interaction: discord.Interaction):
        category_value = self.values[0]
        await _open_ticket(interaction, category_name=category_value)


class TicketPanelMenu(discord.ui.View):
    """
    Panel view with a Select menu — posted once in the support channel via /ticket panel.
    Persistent (survives restarts) via custom_id on the select.
    """
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


class TicketCloseButton(discord.ui.View):
    """Persistent close button posted inside each ticket channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket_btn",
        emoji="🔒",
    )
    async def close_ticket_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await _close_ticket(interaction)


# ─── Cog ─────────────────────────────────────────────────────────────────────
class TicketsCog(commands.Cog, name="Tickets"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        """Schedule panel (re)post once the bot is fully ready."""
        import asyncio
        asyncio.create_task(self._post_panel())
        asyncio.create_task(self._check_inactive_tickets())

    async def _check_inactive_tickets(self):
        """Auto-close tickets inactive for 5+ minutes."""
        import asyncio
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = datetime.utcnow()
                open_tickets = [
                    (tid, d) for tid, d in list(tickets_data.items()) if d.get("status") == "open"
                ]
                for tid, d in open_tickets:
                    channel = self.bot.get_channel(d.get("channel_id"))
                    if not channel:
                        continue
                    
                    # Check if anyone other than the bot has sent a message
                    has_user_message = False
                    try:
                        async for msg in channel.history(limit=20):
                            if msg.author != self.bot.user:
                                has_user_message = True
                                break
                    except discord.Forbidden:
                        continue
                    
                    if has_user_message:
                        # Someone spoke in the ticket, do not auto-close
                        continue
                    
                    # No user message found. Check how long it's been open.
                    opened_at_str = d.get("opened_at")
                    if opened_at_str:
                        opened_at = datetime.fromisoformat(opened_at_str).replace(tzinfo=None)
                        if (now - opened_at).total_seconds() >= 300: # 5 minutes
                            print(f"[Tickets] Auto-closing ghost ticket {tid}")
                            
                            try:
                                await channel.send("🔒 **Ticket auto-closing...** (No message sent for 5 minutes)")
                            except:
                                pass

                            # Generate transcript
                            import chat_exporter
                            import io
                            transcript = None
                            try:
                                transcript_str = await chat_exporter.export(channel)
                                if transcript_str:
                                    transcript = discord.File(io.BytesIO(transcript_str.encode()), filename=f"transcript-{tid}.html")
                            except Exception as e:
                                print(f"[Tickets] Transcript generation failed for auto-close: {e}")
                                
                            # Update DB
                            d["status"] = "closed"
                            d["closed_at"] = datetime.utcnow().isoformat()
                            save_tickets()
                            
                            # Log
                            tl_id = config.get("ticket_log_channel_id", 0)
                            if tl_id:
                                log_ch = channel.guild.get_channel(int(tl_id))
                                if log_ch:
                                    opener = channel.guild.get_member(d.get("opener_id"))
                                    embed  = discord.Embed(
                                        title=f"🔒 Ticket Closed — {channel.name}",
                                        description="Auto-closed (Ghost ticket / No user reply in 5 minutes).",
                                        color=discord.Color.red(),
                                        timestamp=datetime.utcnow(),
                                    )
                                    embed.add_field(name="Ticket ID", value=tid, inline=True)
                                    embed.add_field(name="Opened By", value=opener.mention if opener else "Unknown", inline=True)
                                    embed.add_field(name="Closed By", value="Auto-Close System", inline=True)
                                    try:
                                        if transcript:
                                            await log_ch.send(embed=embed, file=transcript)
                                        else:
                                            await log_ch.send(embed=embed)
                                    except Exception:
                                        pass
                                        
                            try:
                                await asyncio.sleep(5)
                                await channel.delete(reason="Auto-closed ghost ticket")
                            except Exception:
                                pass
            except Exception as e:
                print(f"[Tickets] Error in _check_inactive_tickets: {e}")
                
            await asyncio.sleep(60) # check every minute

    async def _post_panel(self):
        """Wait for ready, delete the old panel message, post a fresh one, save the ID."""
        await self.bot.wait_until_ready()

        tp_id = config.get("ticket_panel_channel_id", 0)
        if not tp_id or int(tp_id) == 0:
            return

        channel = self.bot.get_channel(int(tp_id))
        if not channel:
            print(f"[Tickets] Panel channel {tp_id} not found.")
            return

        # Delete the previous panel message if we know its ID
        old_id = config.get("ticket_panel_message_id", 0)
        if old_id:
            try:
                old_msg = await channel.fetch_message(int(old_id))
                await old_msg.delete()
                print(f"[Tickets] Deleted old panel message (id={old_id}).")
            except (discord.NotFound, discord.HTTPException):
                pass  # already gone — that's fine

        # Post the fixed panel embed
        embed = _build_panel_embed(channel.guild)

        try:
            new_msg = await channel.send(embed=embed, view=TicketPanelMenu())
            config["ticket_panel_message_id"] = new_msg.id
            save_config()
            print(f"[Tickets] Panel posted in #{channel.name} (id={new_msg.id}).")
        except Exception as e:
            print(f"[Tickets] Failed to post panel: {e}")

    ticket_group = app_commands.Group(name="ticket", description="Ticket system commands")

    # ── /ticket panel ─────────────────────────────────────────────────────────
    @ticket_group.command(
        name="panel",
        description="[Admin] Post the ticket creation panel in a channel",
    )
    @app_commands.describe(channel="The channel to post the panel in (leave blank for current)")
    @app_commands.default_permissions(administrator=True)
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None,
    ):
        log_command("ticket_panel")
        target_ch = channel or interaction.channel
        embed = _build_panel_embed(interaction.guild)

        try:
            await target_ch.send(embed=embed, view=TicketPanelMenu())
            await interaction.response.send_message(
                f"✅ Ticket panel posted in {target_ch.mention}.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ I don't have permission to send messages in {target_ch.mention}.",
                ephemeral=True,
            )

    # ── /ticket open ──────────────────────────────────────────────────────────
    @ticket_group.command(name="open", description="Open a new support ticket")
    async def ticket_open(self, interaction: discord.Interaction):
        await _open_ticket(interaction)

    # ── /ticket close ─────────────────────────────────────────────────────────
    @ticket_group.command(name="close", description="Close the current support ticket")
    async def ticket_close(self, interaction: discord.Interaction):
        log_command("ticket_close")
        await _close_ticket(interaction)

    # ── /ticket list (mod only) ───────────────────────────────────────────────
    @ticket_group.command(name="list", description="[Mod] List all open tickets")
    @app_commands.default_permissions(manage_messages=True)
    async def ticket_list(self, interaction: discord.Interaction):
        log_command("ticket_list")
        open_tickets = [
            (tid, d) for tid, d in tickets_data.items() if d.get("status") == "open"
        ]
        if not open_tickets:
            await interaction.response.send_message("✅ No open tickets.", ephemeral=True)
            return
        desc = ""
        for tid, d in open_tickets:
            ch     = interaction.guild.get_channel(d.get("channel_id"))
            ch_str = ch.mention if ch else "`(channel deleted)`"
            opened = d.get("opened_at", "")[:10]
            desc  += f"• **{tid}** — {ch_str} — <@{d['opener_id']}> — `{opened}`\n"
        embed = discord.Embed(
            title=f"🎫 Open Tickets ({len(open_tickets)})",
            description=desc,
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /ticket claim ─────────────────────────────────────────────────────────
    @ticket_group.command(name="claim", description="[Mod] Claim the current ticket")
    @app_commands.default_permissions(manage_messages=True)
    async def ticket_claim(self, interaction: discord.Interaction):
        log_command("ticket_claim")
        channel = interaction.channel
        ticket_id = next(
            (tid for tid, d in tickets_data.items()
             if d.get("channel_id") == channel.id and d.get("status") == "open"),
            None,
        )
        if not ticket_id:
            return await interaction.response.send_message("❌ This channel is not an open ticket.", ephemeral=True)
        
        info = tickets_data[ticket_id]
        if info.get("claimed_by"):
            return await interaction.response.send_message(f"❌ Ticket already claimed by <@{info['claimed_by']}>.", ephemeral=True)
        
        info["claimed_by"] = interaction.user.id
        save_tickets()

        embed = discord.Embed(
            title="✅ Ticket Claimed",
            description=f"This ticket will now be handled by {interaction.user.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    # ── /ticket add ─────────────────────────────────────────────────────────
    @ticket_group.command(name="add", description="Add a user to the current ticket")
    @app_commands.describe(user="The user to add")
    @app_commands.default_permissions(manage_messages=True)
    async def ticket_add(self, interaction: discord.Interaction, user: discord.Member):
        log_command("ticket_add")
        channel = interaction.channel
        ticket_id = next(
            (tid for tid, d in tickets_data.items()
             if d.get("channel_id") == channel.id and d.get("status") == "open"),
            None,
        )
        if not ticket_id:
            return await interaction.response.send_message("❌ This channel is not an open ticket.", ephemeral=True)
        
        await channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(f"✅ Added {user.mention} to the ticket.")

    # ── /ticket remove ─────────────────────────────────────────────────────────
    @ticket_group.command(name="remove", description="Remove a user from the current ticket")
    @app_commands.describe(user="The user to remove")
    @app_commands.default_permissions(manage_messages=True)
    async def ticket_remove(self, interaction: discord.Interaction, user: discord.Member):
        log_command("ticket_remove")
        channel = interaction.channel
        ticket_id = next(
            (tid for tid, d in tickets_data.items()
             if d.get("channel_id") == channel.id and d.get("status") == "open"),
            None,
        )
        if not ticket_id:
            return await interaction.response.send_message("❌ This channel is not an open ticket.", ephemeral=True)
        
        await channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"✅ Removed {user.mention} from the ticket.")

    # ── /ticket transfer ──────────────────────────────────────────────────────
    @ticket_group.command(name="transfer", description="[Admin] Transfer ticket ownership to a new user")
    @app_commands.describe(new_owner="The user to transfer this ticket to")
    @app_commands.default_permissions(manage_messages=True)
    async def ticket_transfer(self, interaction: discord.Interaction, new_owner: discord.Member):
        log_command("ticket_transfer")
        channel = interaction.channel
        ticket_id = next(
            (tid for tid, d in tickets_data.items()
             if d.get("channel_id") == channel.id and d.get("status") == "open"),
            None,
        )
        if not ticket_id:
            return await interaction.response.send_message("❌ This channel is not an open ticket.", ephemeral=True)
        
        info = tickets_data[ticket_id]
        old_owner_id = info.get("opener_id")
        
        if old_owner_id == new_owner.id:
            return await interaction.response.send_message("❌ This user is already the owner of the ticket.", ephemeral=True)
            
        old_owner = interaction.guild.get_member(old_owner_id)
        
        # Remove old owner's permissions
        if old_owner:
            await channel.set_permissions(old_owner, overwrite=None)
            
        # Add new owner's permissions
        await channel.set_permissions(new_owner, view_channel=True, send_messages=True, read_message_history=True)
        
        # Update database
        info["opener_id"] = new_owner.id
        save_tickets()
        
        # Optionally update the channel topic
        topic = channel.topic or ""
        if old_owner:
            topic = topic.replace(old_owner.display_name, new_owner.display_name)
        await channel.edit(topic=topic)
        
        await interaction.response.send_message(f"✅ Ticket transferred from {'<@'+str(old_owner_id)+'>'} to {new_owner.mention}.")

# ─── Extension setup ─────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
    # Register both persistent views so buttons/selects survive bot restarts
    bot.add_view(TicketCloseButton())
    bot.add_view(TicketPanelMenu())