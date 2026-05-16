"""
cogs/general.py
---------------
on_message dispatcher (prefix commands: rank, leaderboard, daily, weekly,
balance, coinflip, dice, slots, shop, buy, games, remind, warn*).
Also: /rank, /leaderboard, /help slash commands + on_ready handler.
"""

import os
import random
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

import database as db
from database import (
    user_stats, economy_data, user_names,
    level_requirements, warnings_data,
    shop_items, analytics_data,
)
from config import CREATOR_CHANNEL_ID, MOD_ROLE_ID
from utils import (
    check_cooldown, log_command, get_user_stats, get_economy,
    add_coins, remove_coins, compute_sub_level, get_active_multiplier,
    get_perm_level, PermLevel, ALIASES,
)

# Path to the rank card background:
#   __file__  →  bot/cogs/general.py
#   dirname×1 →  bot/cogs/
#   dirname×2 →  bot/
#   dirname×3 →  <project root>  ← PRO2.png lives here
_BG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "PRO2.png",
)


# ─── Small prefix-command helpers ────────────────────────────────────────────
def _resolve_alias(word: str) -> str:
    for cmd, names in ALIASES.items():
        if word in names:
            return cmd
    return word


class GeneralCog(commands.Cog, name="General"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── on_ready ──────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[Bot] Logged in as {self.bot.user} ({self.bot.user.id})")
        try:
            synced = await self.bot.tree.sync()
            print(f"[Bot] Synced {len(synced)} slash command(s).")
        except Exception as e:
            print(f"[Bot] Sync error: {e}")

    # ── AutoMod + on_message dispatcher ───────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Cache name
        if isinstance(message.author, discord.Member):
            db.cache_member_name(message.author)

        # ── AutoMod ──────────────────────────────────────────────────────────
        from database import automod_config
        await self._automod(message, automod_config)

        # ── LEVEL / XP — runs for EVERY message (not just prefix commands) ──
        stats = get_user_stats(message.author.id)
        stats["total_messages"] = stats.get("total_messages", 0) + 1

        # Text-XP cooldown: 1 text-minute per 60s of activity (matches original)
        last_msg_ts = stats.get("last_message_ts")
        elapsed = 999
        if last_msg_ts:
            try:
                elapsed = (datetime.now() - datetime.fromisoformat(last_msg_ts)).total_seconds()
            except (ValueError, TypeError):
                elapsed = 999

        if elapsed >= 60:
            mult = get_active_multiplier(message.author.id)
            stats["text_minutes"]    = stats.get("text_minutes", 0)    + (1 * mult)
            stats["weekly_text"]     = stats.get("weekly_text",  0)    + (1 * mult)
            stats["monthly_text"]    = stats.get("monthly_text", 0)    + (1 * mult)
            stats["last_message_ts"] = datetime.now().isoformat()
            add_coins(message.author.id, 1)

        from database import save_user_stats
        save_user_stats()

        if isinstance(message.author, discord.Member):
            levels_cog = self.bot.get_cog("Levels")
            if levels_cog:
                await levels_cog.check_level_up(message.author)

        # ── Only dispatch prefix commands for . and ! messages ───────────────
        content = message.content.strip()
        if not content or content[0] not in ('.', '!'):
            return

        parts        = content.split()
        cmd_raw      = parts[0][1:].lower()
        resolved_cmd = _resolve_alias(cmd_raw)

        # ── Prefix-command dispatch ───────────────────────────────────────────
        if resolved_cmd == "bot":
            if len(parts) > 1 and parts[1].lower() == "in":
                await self._handle_bot_in(message)
            elif len(parts) > 1 and parts[1].lower() == "out":
                await self._handle_bot_out(message)

        elif resolved_cmd == "rank":
            await self._handle_rank(message)

        elif resolved_cmd == "leaderboard":
            await self._handle_leaderboard(message)

        elif resolved_cmd == "daily":
            await self._handle_daily(message)

        elif resolved_cmd == "weekly":
            await self._handle_weekly(message)

        elif resolved_cmd == "balance":
            await self._handle_balance(message, parts)

        elif resolved_cmd == "coinflip":
            await self._handle_coinflip(message, parts)

        elif resolved_cmd == "dice":
            await self._handle_dice(message, parts)

        elif resolved_cmd == "slots":
            await self._handle_slots(message, parts)

        elif resolved_cmd == "shop":
            await self._handle_shop(message)

        elif resolved_cmd == "buy":
            await self._handle_buy(message, parts)

        elif resolved_cmd == "games":
            await self._handle_games(message)

        elif resolved_cmd == "remind":
            reminders_cog = self.bot.get_cog("Reminders")
            if reminders_cog:
                await reminders_cog.handle_prefix_remind(message)

        # ── Moderator prefix commands ─────────────────────────────────────────
        elif isinstance(message.author, discord.Member):
            perm = get_perm_level(message.author)
            if perm >= PermLevel.MODERATOR:
                await self._handle_mod_prefix(message, content)

    async def _handle_bot_in(self, message: discord.Message):
        log_command("bot in")
        if not message.author.voice or not message.author.voice.channel:
            await message.reply("❌ You must be in a voice channel to use this command.")
            return
        channel = message.author.voice.channel
        try:
            if message.guild.voice_client:
                if message.guild.voice_client.channel != channel:
                    await message.guild.voice_client.move_to(channel)
                    await message.reply(f"✅ Moved to {channel.mention}")
                else:
                    await message.reply(f"✅ Already connected to {channel.mention}")
            else:
                await channel.connect()
                await message.reply(f"✅ Connected to {channel.mention}")
        except Exception as e:
            await message.reply(f"❌ Failed to connect: {e}")

    async def _handle_bot_out(self, message: discord.Message):
        log_command("bot out")
        if message.guild.voice_client:
            await message.guild.voice_client.disconnect()
            await message.reply("✅ Disconnected from voice channel.")
        else:
            await message.reply("❌ I am not connected to a voice channel.")

    # ── AutoMod ───────────────────────────────────────────────────────────────
    async def _automod(self, message: discord.Message, cfg: dict):
        if not isinstance(message.author, discord.Member):
            return
        if get_perm_level(message.author) >= PermLevel.MODERATOR:
            return

        # Mention spam
        mention_limit = cfg.get("mention_limit", 5)
        if len(message.mentions) > mention_limit:
            await message.delete()
            await message.channel.send(
                f"⚠️ {message.author.mention} please do not mass-mention.", delete_after=5
            )
            return

        # URL filter
        allowed_domains = cfg.get("allowed_domains", [])
        if allowed_domains and ("http://" in message.content or "https://" in message.content):
            import re
            urls = re.findall(r'https?://[^\s]+', message.content)
            for url in urls:
                domain = url.split("/")[2] if len(url.split("/")) > 2 else ""
                if not any(domain.endswith(d) for d in allowed_domains):
                    await message.delete()
                    await message.channel.send(
                        f"⚠️ {message.author.mention} links to that domain are not allowed.",
                        delete_after=5,
                    )
                    return

        # Message cooldown spam
        cooldown_secs = cfg.get("message_cooldown_seconds", 2)
        cooldown_key  = (message.author.id, "automod_msg")
        from utils import command_cooldowns
        last = command_cooldowns.get(cooldown_key)
        if last and (datetime.now() - last).total_seconds() < cooldown_secs:
            await message.delete()
            return
        command_cooldowns[cooldown_key] = datetime.now()

    # ── Rank ──────────────────────────────────────────────────────────────────
    async def _handle_rank(self, message: discord.Message):
        log_command("rank")
        remaining = check_cooldown(message.author.id, "rank", 3)
        if remaining > 0:
            await message.reply(f"⏳ Wait {int(remaining)}s before checking rank again.",
                                delete_after=3)
            return

        target = message.mentions[0] if message.mentions else message.author
        t_stats = get_user_stats(target.id)

        # Voice level
        voice_level, voice_prog, voice_gap = compute_sub_level(
            t_stats.get("voice_minutes", 0), "voice_minutes_required"
        )
        if voice_gap == float("inf"):
            voice_percent      = 100
            voice_progress_str = f"{int(t_stats.get('voice_minutes', 0))} XP (MAX)"
        else:
            voice_percent      = min(100, max(0, (voice_prog / voice_gap) * 100))
            voice_progress_str = f"{int(voice_prog)} / {int(voice_gap)} XP"

        # Text level
        text_level, text_prog, text_gap = compute_sub_level(
            t_stats.get("total_messages", 0), "text_minutes_required"
        )
        if text_gap == float("inf"):
            text_percent      = 100
            text_progress_str = f"{int(t_stats.get('total_messages', 0))} XP (MAX)"
        else:
            text_percent      = min(100, max(0, (text_prog / text_gap) * 100))
            text_progress_str = f"{int(text_prog)} / {int(text_gap)} XP"

        if not os.path.exists(_BG_PATH):
            await message.channel.send("❌ Error: Background template not found!")
            return

        try:
            from easy_pil import Editor, load_image_async, Font
            editor = Editor(_BG_PATH)
            try:
                font_small = Font.poppins(size=18, variant="bold")
            except Exception:
                font_small = Font.poppins(size=18)

            # Voice bar (top)
            voice_y = 61
            editor.text((455, voice_y - 25), f"Voice Level: {voice_level}",
                        font=font_small, color="#FFFFFF")
            editor.text((910, voice_y - 25), voice_progress_str,
                        font=font_small, color="#FFFFFF", align="right")
            editor.bar((455, voice_y), max_width=458, height=27,
                       percentage=voice_percent, fill="#F1C40F", radius=16)
            editor.text((684, voice_y + 4), f"{int(voice_percent)}%",
                        font=font_small, color="#1A1A1A", align="center")

            # Text bar (bottom)
            text_y = 139
            editor.text((455, text_y - 25), f"Text Level: {text_level}",
                        font=font_small, color="#FFFFFF")
            editor.text((910, text_y - 25), text_progress_str,
                        font=font_small, color="#FFFFFF", align="right")
            editor.bar((455, text_y), max_width=458, height=27,
                       percentage=text_percent, fill="#D4AF37", radius=16)
            editor.text((684, text_y + 4), f"{int(text_percent)}%",
                        font=font_small, color="#1A1A1A", align="center")

            # Circular avatar
            try:
                profile_image = await load_image_async(str(target.display_avatar.url))
                profile = Editor(profile_image).resize((200, 200)).circle_image()
                editor.paste(profile, (0, 70))
            except Exception as e:
                print(f"[Rank] Avatar error: {e}")

            file = discord.File(fp=editor.image_bytes, filename="rank_card.png")
            await message.reply(file=file)

        except ImportError:
            # easy_pil not installed — fall back to embed
            embed = discord.Embed(
                title=f"📊 {target.display_name}'s Rank",
                color=discord.Color.from_rgb(88, 101, 242),
            )
            embed.add_field(name="🎙️ Voice Level",
                            value=f"**{voice_level}** ({voice_progress_str})", inline=False)
            embed.add_field(name="✍️ Text Level",
                            value=f"**{text_level}** ({text_progress_str})", inline=False)
            if target.display_avatar:
                embed.set_thumbnail(url=target.display_avatar.url)
            await message.reply(embed=embed)
        except Exception as e:
            await message.reply("❌ Error generating rank card!")
            print(f"[Rank] Error: {e}")

    # ── Leaderboard ───────────────────────────────────────────────────────────
    async def _handle_leaderboard(self, message: discord.Message):
        log_command("leaderboard")
        entries = []
        for uid, s in user_stats.items():
            vm = s.get("voice_minutes", 0); tm = s.get("total_messages", 0)
            vl, _, _ = compute_sub_level(vm, "voice_minutes_required")
            tl, _, _ = compute_sub_level(tm, "text_minutes_required")
            core = min(vl, tl)
            name = user_names.get(uid, {}).get("display_name") or f"ID:{uid}"
            entries.append((name, core, vm, tm))
        entries.sort(key=lambda x: x[1], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        desc   = ""
        for i, (name, core, vm, tm) in enumerate(entries[:10], 1):
            rank  = medals[i-1] if i <= 3 else f"`#{i}`"
            desc += f"{rank} **{name}** — Level **{core}** (🎙️{int(vm)}m / ✍️{int(tm)} msgs)\n"
        embed = discord.Embed(title="🏆 Level Leaderboard", description=desc or "No data yet.",
                              color=discord.Color.gold())
        await message.reply(embed=embed)

    # ── Daily / Weekly ────────────────────────────────────────────────────────
    async def _handle_daily(self, message: discord.Message):
        log_command("daily")
        remaining = check_cooldown(message.author.id, "daily", 86400)
        if remaining > 0:
            h = int(remaining) // 3600; m = (int(remaining) % 3600) // 60
            await message.reply(f"⏳ Come back in `{h}h {m}m`."); return
        add_coins(message.author.id, 100)
        await message.reply("✅ Claimed **100** 🪙 daily reward!")

    async def _handle_weekly(self, message: discord.Message):
        log_command("weekly")
        remaining = check_cooldown(message.author.id, "weekly", 604800)
        if remaining > 0:
            d = int(remaining) // 86400; h = (int(remaining) % 86400) // 3600
            await message.reply(f"⏳ Come back in `{d}d {h}h`."); return
        add_coins(message.author.id, 500)
        await message.reply("✅ Claimed **500** 🪙 weekly reward!")

    # ── Balance ───────────────────────────────────────────────────────────────
    async def _handle_balance(self, message: discord.Message, parts: list):
        log_command("balance")
        target = message.mentions[0] if message.mentions else message.author
        econ   = get_economy(target.id)
        await message.reply(f"💳 **{target.display_name}**: 🪙 **{econ['coins']}** coins (Total earned: {econ['total_earned']})")

    # ── Games ─────────────────────────────────────────────────────────────────
    async def _handle_coinflip(self, message: discord.Message, parts: list):
        log_command("coinflip")
        bet   = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
        guess = parts[2].lower() if len(parts) > 2 else random.choice(["heads", "tails"])
        if guess not in ("heads", "tails"):
            await message.reply("❌ Guess must be `heads` or `tails`."); return
        if not remove_coins(message.author.id, bet):
            await message.reply("❌ You don't have enough coins."); return
        result = random.choice(["heads", "tails"])
        if result == guess:
            add_coins(message.author.id, bet * 2)
            await message.reply(f"🪙 **{result.title()}!** You won **{bet}** coins!")
        else:
            await message.reply(f"🪙 **{result.title()}!** You lost **{bet}** coins.")

    async def _handle_dice(self, message: discord.Message, parts: list):
        log_command("dice")
        bet   = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
        guess = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        if not 1 <= guess <= 6:
            await message.reply("❌ Guess must be 1–6."); return
        if not remove_coins(message.author.id, bet):
            await message.reply("❌ Not enough coins."); return
        result = random.randint(1, 6)
        if result == guess:
            add_coins(message.author.id, bet * 6)
            await message.reply(f"🎲 **{result}!** Perfect! Won **{bet * 5}** coins! 💰")
        else:
            await message.reply(f"🎲 **{result}!** Better luck next time. Lost **{bet}** coins.")

    async def _handle_slots(self, message: discord.Message, parts: list):
        log_command("slots")
        bet     = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
        if bet <= 0:
            await message.reply("❌ Bet must be positive."); return
        if not remove_coins(message.author.id, bet):
            await message.reply("❌ Not enough coins."); return
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎"]
        weights = [30, 25, 20, 15, 8, 2]
        reels   = random.choices(symbols, weights=weights, k=3)
        if reels[0] == reels[1] == reels[2]:
            mult = 20 if reels[0] == "💎" else 10 if reels[0] == "⭐" else 5
            add_coins(message.author.id, bet * mult)
            await message.reply(f"🎰 **JACKPOT ×{mult}!** {' | '.join(reels)} — Won **{bet * mult}** coins!")
        elif reels[0] == reels[1] or reels[1] == reels[2]:
            add_coins(message.author.id, bet * 2)
            await message.reply(f"🎰 **Small win ×2!** {' | '.join(reels)} — Won **{bet * 2}** coins!")
        else:
            await message.reply(f"🎰 **No match.** {' | '.join(reels)} — Lost **{bet}** coins.")

    async def _handle_shop(self, message: discord.Message):
        log_command("shop")
        if not shop_items:
            await message.reply("The shop is currently empty."); return
        desc = ""
        for idx, item in enumerate(shop_items, 1):
            desc += f"**{idx}. {item['name']}** — 🪙 `{item['price']}`\n*{item['description']}* (ID: `{item['id']}`)\n\n"
        embed = discord.Embed(title="🛒 Coin Shop", description=desc, color=discord.Color.green())
        embed.set_footer(text="Use .buy <item_id> to purchase.")
        await message.reply(embed=embed)

    async def _handle_buy(self, message: discord.Message, parts: list):
        log_command("buy")
        if len(parts) < 2:
            await message.reply("Usage: `.buy <item_id>`"); return
        item_id = parts[1].lower()
        item    = next((i for i in shop_items if i["id"].lower() == item_id), None)
        if not item:
            await message.reply("❌ Item not found."); return
        if not remove_coins(message.author.id, item["price"]):
            await message.reply(f"❌ Not enough coins. That costs **{item['price']}** 🪙."); return
        from datetime import timedelta
        econ = get_economy(message.author.id)
        if item_id == "channel_rename_token":
            econ["rename_tokens"] = econ.get("rename_tokens", 0) + 1
        elif item_id == "xp_boost_24h":
            econ["xp_boost_active_until"] = (datetime.now() + timedelta(hours=24)).isoformat()
        from database import save_economy
        save_economy()
        await message.reply(f"✅ Purchased **{item['name']}** for **{item['price']}** 🪙!")

    async def _handle_games(self, message: discord.Message):
        log_command("games")
        embed = discord.Embed(title="🎮 Casino Games", color=discord.Color.purple())
        embed.add_field(name="🪙 Coin Flip", value="`.coinflip <bet> <heads/tails>` — Win = ×2", inline=False)
        embed.add_field(name="🎲 Dice",      value="`.dice <bet> <1-6>` — Exact guess = ×6",     inline=False)
        embed.add_field(name="🎰 Slots",     value="`.slots <bet>` — 3 match = ×5–×20, 2 adj = ×2", inline=False)
        await message.reply(embed=embed)

    # ── Mod prefix commands ───────────────────────────────────────────────────
    async def _handle_mod_prefix(self, message: discord.Message, content: str):
        base = content.lower()
        mod_cog = self.bot.get_cog("Moderation")
        if not mod_cog:
            return
        from cogs.moderation import warn_user

        if base.startswith('.warn '):
            parts = message.content.split(maxsplit=2)
            if len(parts) >= 3 and message.mentions:
                await warn_user(message.mentions[0], parts[2], message.author)
                await message.channel.send(f"✅ Warned {message.mentions[0].mention} for: {parts[2]}")
            else:
                await message.channel.send("Usage: `.warn @user [reason]`")

        elif base.startswith('.warnings '):
            if message.mentions:
                uid   = str(message.mentions[0].id)
                warns = warnings_data.get(uid, [])
                if not warns:
                    await message.channel.send(f"✅ {message.mentions[0].display_name} has no warnings.")
                else:
                    desc = ""
                    for i, w in enumerate(warns, 1):
                        desc += f"**{i}.** {w.get('timestamp','')[:10]} — {w.get('reason')} (Mod: {w.get('mod_id','?')})\n"
                    embed = discord.Embed(title=f"Warnings for {message.mentions[0].display_name}",
                                          description=desc, color=discord.Color.orange())
                    await message.channel.send(embed=embed)

        elif base.startswith('.clearwarn '):
            parts = message.content.split()
            if len(parts) >= 3 and message.mentions:
                target = message.mentions[0]
                uid    = str(target.id)
                try:
                    idx = int(parts[2]) - 1
                except ValueError:
                    await message.channel.send("Usage: `.clearwarn @user <index>`"); return
                if uid in warnings_data and 0 <= idx < len(warnings_data[uid]):
                    warnings_data[uid].pop(idx)
                    if not warnings_data[uid]:
                        del warnings_data[uid]
                    from database import save_warnings
                    save_warnings()
                    await message.channel.send(f"✅ Cleared warning #{idx + 1} for {target.display_name}.")
                else:
                    await message.channel.send(f"❌ {target.display_name} has no warning at that index.")

        elif base.startswith('.slowmode '):
            parts = message.content.split(maxsplit=1)
            if len(parts) > 1:
                preset = parts[1].lower()
                delay_map = {"off": 0, "0": 0, "relaxed": 5, "5": 5, "moderate": 15, "15": 15, "strict": 30, "30": 30}
                if preset in delay_map:
                    delay = delay_map[preset]
                else:
                    try:
                        delay = int(preset)
                    except ValueError:
                        await message.channel.send("❌ Invalid preset."); return
                await message.channel.edit(slowmode_delay=delay)
                status = f"{delay} seconds" if delay > 0 else "disabled"
                await message.channel.send(f"✅ Slowmode is now {status}.")

    # ── /bot slash group ──────────────────────────────────────────────────────
    voice_controls = app_commands.Group(name="bot", description="Bot voice controls")

    @voice_controls.command(name="in", description="Connect the bot to your current voice channel")
    async def slash_bot_in(self, interaction: discord.Interaction):
        log_command("slash_bot_in")
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel to use this command.", ephemeral=True)
            return
        
        channel = interaction.user.voice.channel
        
        try:
            if interaction.guild.voice_client:
                if interaction.guild.voice_client.channel != channel:
                    await interaction.guild.voice_client.move_to(channel)
                    await interaction.response.send_message(f"✅ Moved to {channel.mention}")
                else:
                    await interaction.response.send_message(f"✅ Already connected to {channel.mention}", ephemeral=True)
            else:
                await channel.connect()
                await interaction.response.send_message(f"✅ Connected to {channel.mention}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to connect: {e}", ephemeral=True)

    @voice_controls.command(name="out", description="Disconnect the bot from the voice channel")
    async def slash_bot_out(self, interaction: discord.Interaction):
        log_command("slash_bot_out")
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("✅ Disconnected from voice channel.")
        else:
            await interaction.response.send_message("❌ I am not connected to a voice channel.", ephemeral=True)

    # ── /rank slash ───────────────────────────────────────────────────────────
    @app_commands.command(name="rank", description="Check your or another user's level and rank")
    @app_commands.describe(user="The user to check the rank of (optional)")
    async def slash_rank(self, interaction: discord.Interaction, user: discord.Member = None):
        log_command("slash_rank")
        remaining = check_cooldown(interaction.user.id, "slash_rank", 3)
        if remaining > 0:
            await interaction.response.send_message(
                f"⏳ Please wait {int(remaining)}s before checking rank again.", ephemeral=True
            )
            return

        await interaction.response.defer()
        target  = user if user else interaction.user
        t_stats = get_user_stats(target.id)

        voice_level, voice_prog, voice_gap = compute_sub_level(
            t_stats.get("voice_minutes", 0), "voice_minutes_required"
        )
        if voice_gap == float("inf"):
            voice_percent      = 100
            voice_progress_str = f"{int(t_stats.get('voice_minutes', 0))} XP (MAX)"
        else:
            voice_percent      = min(100, max(0, (voice_prog / voice_gap) * 100))
            voice_progress_str = f"{int(voice_prog)} / {int(voice_gap)} XP"

        text_level, text_prog, text_gap = compute_sub_level(
            t_stats.get("total_messages", 0), "text_minutes_required"
        )
        if text_gap == float("inf"):
            text_percent      = 100
            text_progress_str = f"{int(t_stats.get('total_messages', 0))} XP (MAX)"
        else:
            text_percent      = min(100, max(0, (text_prog / text_gap) * 100))
            text_progress_str = f"{int(text_prog)} / {int(text_gap)} XP"

        if not os.path.exists(_BG_PATH):
            await interaction.followup.send("❌ Error: Background template not found!")
            return

        try:
            from easy_pil import Editor, load_image_async, Font
            editor = Editor(_BG_PATH)
            try:
                font_small = Font.poppins(size=18, variant="bold")
            except Exception:
                font_small = Font.poppins(size=18)

            voice_y = 61
            editor.text((455, voice_y - 25), f"Voice Level: {voice_level}",
                        font=font_small, color="#FFFFFF")
            editor.text((910, voice_y - 25), voice_progress_str,
                        font=font_small, color="#FFFFFF", align="right")
            editor.bar((455, voice_y), max_width=458, height=27,
                       percentage=voice_percent, fill="#F1C40F", radius=16)
            editor.text((684, voice_y + 4), f"{int(voice_percent)}%",
                        font=font_small, color="#1A1A1A", align="center")

            text_y = 139
            editor.text((455, text_y - 25), f"Text Level: {text_level}",
                        font=font_small, color="#FFFFFF")
            editor.text((910, text_y - 25), text_progress_str,
                        font=font_small, color="#FFFFFF", align="right")
            editor.bar((455, text_y), max_width=458, height=27,
                       percentage=text_percent, fill="#D4AF37", radius=16)
            editor.text((684, text_y + 4), f"{int(text_percent)}%",
                        font=font_small, color="#1A1A1A", align="center")

            try:
                profile_image = await load_image_async(str(target.display_avatar.url))
                profile = Editor(profile_image).resize((200, 200)).circle_image()
                editor.paste(profile, (0, 70))
            except Exception as e:
                print(f"[Rank] Avatar error: {e}")

            file = discord.File(fp=editor.image_bytes, filename="rank_card.png")
            await interaction.followup.send(file=file)

        except ImportError:
            embed = discord.Embed(title=f"📊 {target.display_name}'s Rank",
                                  color=discord.Color.from_rgb(88, 101, 242))
            embed.add_field(name="🎙️ Voice Level",
                            value=f"**{voice_level}** ({voice_progress_str})", inline=False)
            embed.add_field(name="✍️ Text Level",
                            value=f"**{text_level}** ({text_progress_str})", inline=False)
            if target.display_avatar:
                embed.set_thumbnail(url=target.display_avatar.url)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send("❌ Error generating rank card!")
            print(f"[Rank] Error: {e}")

    # ── /leaderboard slash ────────────────────────────────────────────────────
    @app_commands.command(name="leaderboard", description="View the top users by level")
    async def slash_leaderboard(self, interaction: discord.Interaction):
        log_command("slash_leaderboard")
        remaining = check_cooldown(interaction.user.id, "leaderboard_slash", 10)
        if remaining > 0:
            await interaction.response.send_message(f"⏳ Wait {int(remaining)}s.", ephemeral=True); return
        entries = []
        for uid, s in user_stats.items():
            vm = s.get("voice_minutes", 0); tm = s.get("total_messages", 0)
            vl, _, _ = compute_sub_level(vm, "voice_minutes_required")
            tl, _, _ = compute_sub_level(tm, "text_minutes_required")
            core = min(vl, tl)
            name = user_names.get(uid, {}).get("display_name") or f"ID:{uid}"
            entries.append((name, core, vm, tm))
        entries.sort(key=lambda x: x[1], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        desc   = ""
        for i, (name, core, vm, tm) in enumerate(entries[:10], 1):
            rank  = medals[i-1] if i <= 3 else f"`#{i}`"
            desc += f"{rank} **{name}** — Level **{core}** (🎙️{int(vm)}m / ✍️{int(tm)} msgs)\n"
        embed = discord.Embed(title="🏆 Level Leaderboard", description=desc or "No data yet.",
                              color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    # ── /help slash ───────────────────────────────────────────────────────────
    @app_commands.command(name="help", description="View all available commands")
    async def slash_help(self, interaction: discord.Interaction):
        log_command("slash_help")
        embed = discord.Embed(title="📚 Bot Commands", color=discord.Color.blurple())
        embed.add_field(name="📊 Levels", value="`/rank` `/leaderboard`", inline=False)
        embed.add_field(name="💰 Economy",
            value="`/daily` `/weekly` `/balance` `/richlist` `/shop` `/buy`", inline=False)
        embed.add_field(name="🎮 Games",
            value="`/coinflip` `/dice` `/games coinflip|dice|slots|info`", inline=False)
        embed.add_field(name="⏰ Reminders", value="`/remind`", inline=False)
        embed.add_field(name="🎫 Tickets",   value="`/ticket open` `/ticket close`", inline=False)
        embed.add_field(name="😊 Reaction Roles", value="`/reactionrole add`", inline=False)
        embed.add_field(name="🎙️ Temp Channels",
            value="`/channel rename|limit|mode|video|clone|kick|record`\n"
                  "Also: `.rename` `.limit` `.lock` `.unlock` `.give` `.claim` etc.", inline=False)
        embed.add_field(name="🛡️ Moderation",
            value="`/warn` `/warnings` `/clearwarn` `/ban` `/unban` `/kick` `/timeout` `/untimeout` `/purge` `/slowmode`",
            inline=False)
        embed.set_footer(text="Prefix commands: . or !")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /setup slash ──────────────────────────────────────────────────────────
    @app_commands.command(name="setup", description="[Admin] Modify bot configuration live")
    @app_commands.describe(
        setting="Which setting to modify",
        new_value="New ID or value (leave blank to view current)"
    )
    @app_commands.choices(setting=[
        app_commands.Choice(name="Ticket Category ID", value="ticket_category_id"),
        app_commands.Choice(name="Ticket Log Channel ID", value="ticket_log_channel_id"),
        app_commands.Choice(name="Ticket Panel Channel ID", value="ticket_panel_channel_id"),
        app_commands.Choice(name="Mod Role ID", value="mod_role_id"),
        app_commands.Choice(name="Creator Channel ID", value="creator_channel_id"),
        app_commands.Choice(name="Temp Channel Category ID", value="temp_channel_category_id")
    ])
    @app_commands.default_permissions(administrator=True)
    async def slash_setup(self, interaction: discord.Interaction, setting: str, new_value: str = None):
        from config import config, save_config
        log_command("slash_setup")
        if not new_value:
            curr = config.get(setting, "Not set")
            return await interaction.response.send_message(f"Current value for `{setting}` is: **{curr}**", ephemeral=True)
        
        try:
            val = int(new_value)
            config[setting] = val
            save_config()
            await interaction.response.send_message(f"✅ Updated `{setting}` to **{val}**.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Value must be a number (ID).", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))
