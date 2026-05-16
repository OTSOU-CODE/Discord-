"""
cogs/economy.py
---------------
Slash commands: daily, weekly, balance, richlist, shop, buy,
addcoins, setcoins (admin), coinflip, dice, slots (top-level + /games group).
"""

import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands

from database import (
    economy_data, shop_items,
    save_economy, save_shop,
    user_stats, user_names,
    level_requirements,
)
from utils import (
    check_cooldown, log_command, get_economy, add_coins, remove_coins,
    get_perm_level, compute_sub_level, PermLevel,
)


class EconomyCog(commands.Cog, name="Economy"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── Daily ───────────────────────────────────────────────────────────────
    @app_commands.command(name="daily", description="Claim your daily coin reward")
    async def slash_daily(self, interaction: discord.Interaction):
        log_command("slash_daily")
        remaining = check_cooldown(interaction.user.id, "daily", 86400)
        if remaining > 0:
            hours = int(remaining) // 3600
            mins  = (int(remaining) % 3600) // 60
            await interaction.response.send_message(
                f"⏳ You already claimed your daily reward! Come back in `{hours}h {mins}m`.",
                ephemeral=True,
            )
            return
        econ = get_economy(interaction.user.id)
        add_coins(interaction.user.id, 100)
        econ["last_daily"] = datetime.now().isoformat()
        save_economy()
        await interaction.response.send_message("✅ Claimed **100 coins** as your daily reward! 🪙")

    # ─── Weekly ──────────────────────────────────────────────────────────────
    @app_commands.command(name="weekly", description="Claim your weekly coin reward")
    async def slash_weekly(self, interaction: discord.Interaction):
        log_command("slash_weekly")
        remaining = check_cooldown(interaction.user.id, "weekly", 604800)
        if remaining > 0:
            days  = int(remaining) // 86400
            hours = (int(remaining) % 86400) // 3600
            await interaction.response.send_message(
                f"⏳ You already claimed your weekly reward! Come back in `{days}d {hours}h`.",
                ephemeral=True,
            )
            return
        econ = get_economy(interaction.user.id)
        add_coins(interaction.user.id, 500)
        econ["last_weekly"] = datetime.now().isoformat()
        save_economy()
        await interaction.response.send_message("✅ Claimed **500 coins** as your weekly reward! 💸")

    # ─── Balance ─────────────────────────────────────────────────────────────
    @app_commands.command(name="balance", description="Check your or another user's coin balance")
    @app_commands.describe(user="The user to check (optional)")
    async def slash_balance(self, interaction: discord.Interaction, user: discord.Member = None):
        log_command("slash_balance")
        target = user if user else interaction.user
        econ   = get_economy(target.id)
        embed  = discord.Embed(title=f"💳 {target.display_name}'s Wallet", color=discord.Color.gold())
        embed.add_field(name="🪙 Balance",    value=f"**{econ['coins']}** coins",        inline=True)
        embed.add_field(name="📈 Total Earned", value=f"**{econ['total_earned']}** coins", inline=True)
        if target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ─── Rich list ───────────────────────────────────────────────────────────
    @app_commands.command(name="richlist", description="View the top 10 richest users")
    async def slash_richlist(self, interaction: discord.Interaction):
        log_command("slash_richlist")
        remaining = check_cooldown(interaction.user.id, "richlist", 10)
        if remaining > 0:
            await interaction.response.send_message(
                f"⏳ Please wait {int(remaining)}s.", ephemeral=True
            )
            return
        sorted_users = sorted(economy_data.items(), key=lambda x: x[1].get("coins", 0), reverse=True)[:10]
        desc = ""
        for idx, (uid, data) in enumerate(sorted_users, 1):
            desc += f"**{idx}.** <@{uid}> — **{data.get('coins', 0)}** 🪙\n"
        if not desc:
            desc = "No users have earned coins yet."
        embed = discord.Embed(title="💰 Top 10 Richest Users", description=desc, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    # ─── Shop ────────────────────────────────────────────────────────────────
    @app_commands.command(name="shop", description="View the coin shop")
    async def slash_shop(self, interaction: discord.Interaction):
        log_command("slash_shop")
        if not shop_items:
            await interaction.response.send_message("The shop is currently empty.", ephemeral=True)
            return
        desc = ""
        for idx, item in enumerate(shop_items, 1):
            desc += (
                f"**{idx}. {item['name']}** — 🪙 `{item['price']}` coins\n"
                f"*{item['description']}* (ID: `{item['id']}`)\n\n"
            )
        embed = discord.Embed(title="🛒 Coin Shop", description=desc, color=discord.Color.green())
        embed.set_footer(text="Use /buy <item_id> to purchase an item.")
        await interaction.response.send_message(embed=embed)

    # ─── Buy ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="buy", description="Buy an item from the coin shop")
    @app_commands.describe(item_id="The ID of the item to purchase")
    async def slash_buy(self, interaction: discord.Interaction, item_id: str):
        log_command("slash_buy")
        item_id = item_id.lower()
        item = next((i for i in shop_items if i["id"].lower() == item_id), None)
        if not item:
            await interaction.response.send_message("❌ Item not found in the shop.", ephemeral=True)
            return
        if not remove_coins(interaction.user.id, item["price"]):
            await interaction.response.send_message(
                f"❌ You don't have enough coins. That costs **{item['price']}** 🪙.", ephemeral=True
            )
            return
        econ = get_economy(interaction.user.id)
        if item_id == "xp_boost_24h":
            econ["xp_boost_active_until"] = (datetime.now() + timedelta(hours=24)).isoformat()
            save_economy()
            await interaction.response.send_message(
                f"✅ Purchased **{item['name']}** for **{item['price']}** 🪙! You now have 2x XP for 24 hours!"
            )
        elif item_id == "channel_rename_token":
            econ["rename_tokens"] = econ.get("rename_tokens", 0) + 1
            save_economy()
            await interaction.response.send_message(
                f"✅ Purchased **{item['name']}** for **{item['price']}** 🪙! Use `/channel rename` to use it."
            )
        else:
            await interaction.response.send_message(
                f"✅ Purchased **{item['name']}** for **{item['price']}** 🪙! *(Effect implementation pending)*"
            )

    # ─── Admin: addcoins ─────────────────────────────────────────────────────
    @app_commands.command(name="addcoins", description="[Admin] Add coins to a user")
    @app_commands.describe(user="Target user", amount="Coins to add (negative to remove)")
    @app_commands.default_permissions(administrator=True)
    async def slash_addcoins(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        log_command("slash_addcoins")
        if get_perm_level(interaction.user) < PermLevel.ADMIN:
            await interaction.response.send_message("❌ Admins only.", ephemeral=True); return
        if amount >= 0:
            add_coins(user.id, amount)
            await interaction.response.send_message(f"✅ Added **{amount}** 🪙 to **{user.display_name}**.", ephemeral=True)
        else:
            removed = remove_coins(user.id, abs(amount))
            if removed:
                await interaction.response.send_message(f"✅ Removed **{abs(amount)}** 🪙 from **{user.display_name}**.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ **{user.display_name}** doesn't have that many coins.", ephemeral=True)

    # ─── Admin: setcoins ─────────────────────────────────────────────────────
    @app_commands.command(name="setcoins", description="[Admin] Set a user's exact coin balance")
    @app_commands.describe(user="Target user", amount="New balance")
    @app_commands.default_permissions(administrator=True)
    async def slash_setcoins(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        log_command("slash_setcoins")
        if get_perm_level(interaction.user) < PermLevel.ADMIN:
            await interaction.response.send_message("❌ Admins only.", ephemeral=True); return
        econ = get_economy(user.id)
        econ["coins"] = max(0, amount)
        save_economy()
        await interaction.response.send_message(f"✅ Set **{user.display_name}**'s balance to **{amount}** 🪙.", ephemeral=True)

    # ─── Coin Flip (top-level) ────────────────────────────────────────────────
    @app_commands.command(name="coinflip", description="Bet coins on a coin flip")
    @app_commands.describe(bet="Amount of coins to bet", guess="Heads or Tails")
    @app_commands.choices(guess=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails"),
    ])
    async def slash_coinflip(self, interaction: discord.Interaction, bet: int, guess: str):
        log_command("slash_coinflip")
        if bet <= 0:
            await interaction.response.send_message("❌ Bet must be positive.", ephemeral=True); return
        if not remove_coins(interaction.user.id, bet):
            await interaction.response.send_message("❌ You don't have enough coins.", ephemeral=True); return
        result = random.choice(["heads", "tails"])
        if result == guess:
            add_coins(interaction.user.id, bet * 2)
            await interaction.response.send_message(f"🪙 **{result.title()}!** You won **{bet}** coins!")
        else:
            await interaction.response.send_message(f"🪙 **{result.title()}!** You lost **{bet}** coins.")

    # ─── Dice (top-level) ─────────────────────────────────────────────────────
    @app_commands.command(name="dice", description="Bet coins on a 6-sided dice roll")
    @app_commands.describe(bet="Amount of coins to bet", guess="Number between 1 and 6")
    async def slash_dice(self, interaction: discord.Interaction, bet: int, guess: int):
        log_command("slash_dice")
        if bet <= 0:
            await interaction.response.send_message("❌ Bet must be positive.", ephemeral=True); return
        if guess < 1 or guess > 6:
            await interaction.response.send_message("❌ Guess must be between 1 and 6.", ephemeral=True); return
        if not remove_coins(interaction.user.id, bet):
            await interaction.response.send_message("❌ You don't have enough coins.", ephemeral=True); return
        result = random.randint(1, 6)
        if result == guess:
            win_amount = bet * 5
            add_coins(interaction.user.id, win_amount + bet)
            await interaction.response.send_message(f"🎲 **{result}!** Perfect guess! You won **{win_amount}** coins! 💰")
        else:
            await interaction.response.send_message(f"🎲 **{result}!** Better luck next time. You lost **{bet}** coins.")


# ─── /games group ─────────────────────────────────────────────────────────────
class GamesCog(commands.Cog, name="Games"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    games_group = app_commands.Group(name="games", description="Casino games — bet your coins!")

    @games_group.command(name="coinflip", description="Flip a coin — double or nothing")
    @app_commands.describe(bet="Coins to bet", guess="Heads or Tails")
    @app_commands.choices(guess=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails"),
    ])
    async def games_coinflip(self, interaction: discord.Interaction, bet: int, guess: str):
        log_command("games_coinflip")
        if bet <= 0:
            await interaction.response.send_message("❌ Bet must be positive.", ephemeral=True); return
        if not remove_coins(interaction.user.id, bet):
            await interaction.response.send_message("❌ Not enough coins.", ephemeral=True); return
        result = random.choice(["heads", "tails"])
        win    = result == guess
        if win:
            add_coins(interaction.user.id, bet * 2)
        embed = discord.Embed(
            title=f"🪙 {'WIN!' if win else 'LOSS'} — Coin Flip",
            description=f"Result: **{result.title()}**\n{'You won' if win else 'You lost'} **{bet}** coins!",
            color=discord.Color.green() if win else discord.Color.red(),
        )
        embed.add_field(name="Balance", value=f"🪙 {get_economy(interaction.user.id)['coins']:,}")
        await interaction.response.send_message(embed=embed)

    @games_group.command(name="dice", description="Roll a 6-sided die — guess right and win 6x")
    @app_commands.describe(bet="Coins to bet", guess="Number 1–6")
    async def games_dice(self, interaction: discord.Interaction, bet: int, guess: int):
        log_command("games_dice")
        if bet <= 0:
            await interaction.response.send_message("❌ Bet must be positive.", ephemeral=True); return
        if not 1 <= guess <= 6:
            await interaction.response.send_message("❌ Guess must be 1–6.", ephemeral=True); return
        if not remove_coins(interaction.user.id, bet):
            await interaction.response.send_message("❌ Not enough coins.", ephemeral=True); return
        result = random.randint(1, 6)
        win    = result == guess
        if win:
            add_coins(interaction.user.id, bet * 6)
        embed = discord.Embed(
            title=f"🎲 {'WIN!' if win else 'LOSS'} — Dice Roll",
            description=(
                f"Result: **{result}**  |  You guessed: **{guess}**\n"
                f"{'You won' if win else 'You lost'} **{bet * 5 if win else bet}** coins!"
            ),
            color=discord.Color.green() if win else discord.Color.red(),
        )
        embed.add_field(name="Balance", value=f"🪙 {get_economy(interaction.user.id)['coins']:,}")
        await interaction.response.send_message(embed=embed)

    @games_group.command(name="slots", description="Spin the slot machine!")
    @app_commands.describe(bet="Coins to bet")
    async def games_slots(self, interaction: discord.Interaction, bet: int):
        log_command("games_slots")
        if bet <= 0:
            await interaction.response.send_message("❌ Bet must be positive.", ephemeral=True); return
        if not remove_coins(interaction.user.id, bet):
            await interaction.response.send_message("❌ Not enough coins.", ephemeral=True); return
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎"]
        weights = [30, 25, 20, 15, 8, 2]
        reels   = random.choices(symbols, weights=weights, k=3)
        if reels[0] == reels[1] == reels[2]:
            mult     = 20 if reels[0] == "💎" else 10 if reels[0] == "⭐" else 5
            winnings = bet * mult
            add_coins(interaction.user.id, winnings)
            title, color = f"🎰 JACKPOT! ×{mult}", discord.Color.gold()
            desc = f"**{' | '.join(reels)}**\nYou won **{winnings}** coins!"
        elif reels[0] == reels[1] or reels[1] == reels[2]:
            winnings = bet * 2
            add_coins(interaction.user.id, winnings)
            title, color = "🎰 Small win! ×2", discord.Color.green()
            desc = f"**{' | '.join(reels)}**\nYou won **{winnings}** coins!"
        else:
            title, color = "🎰 No match", discord.Color.red()
            desc = f"**{' | '.join(reels)}**\nYou lost **{bet}** coins."
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.add_field(name="Balance", value=f"🪙 {get_economy(interaction.user.id)['coins']:,}")
        await interaction.response.send_message(embed=embed)

    @games_group.command(name="info", description="See all available games and their payouts")
    async def games_info(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎮 Casino Games", color=discord.Color.purple())
        embed.add_field(name="🪙 Coin Flip — `/games coinflip`",
                        value="Guess heads or tails. Win = **×2** your bet.", inline=False)
        embed.add_field(name="🎲 Dice — `/games dice`",
                        value="Guess the exact number (1–6). Win = **×6** your bet.", inline=False)
        embed.add_field(name="🎰 Slots — `/games slots`",
                        value="3 matching symbols = **×5–×20**. 2 adjacent = **×2**.", inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
    await bot.add_cog(GamesCog(bot))
