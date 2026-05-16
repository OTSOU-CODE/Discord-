import discord
import random
import asyncio
from typing import List, Dict, Optional, Callable

class RouletteView(discord.ui.View):
    def __init__(self, host: discord.Member, players: List[discord.Member], on_end: Callable):
        super().__init__(timeout=600)
        self.host = host
        self.players = players
        self.on_end = on_end
        self.bets: Dict[int, List[dict]] = {p.id: [] for p in players}
        self.player_credits: Dict[int, int] = {p.id: 1000 for p in players}
        self.state = "betting" # betting, spinning, results

    @discord.ui.button(label="Place Bet 💰", style=discord.ButtonStyle.primary)
    async def place_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            return await interaction.response.send_message("You are not in this game!", ephemeral=True)
        
        if self.state != "betting":
            return await interaction.response.send_message("Betting is closed!", ephemeral=True)
            
        await self.show_betting_modal(interaction)

    async def show_betting_modal(self, interaction: discord.Interaction):
        class BetModal(discord.ui.Modal, title="Place your Bet"):
            amount = discord.ui.TextInput(label="Amount", placeholder="Enter amount (min 10)", min_length=1)
            bet_type = discord.ui.TextInput(label="Type (Red, Black, Even, Odd, or 0-36)", placeholder="e.g. Red, 17")

            def __init__(self, parent):
                super().__init__()
                self.parent = parent

            async def on_submit(self, inter: discord.Interaction):
                try:
                    amt = int(self.amount.value)
                    if amt < 10 or amt > self.parent.player_credits[inter.user.id]:
                        return await inter.response.send_message(f"Invalid amount! You have {self.parent.player_credits[inter.user.id]} credits.", ephemeral=True)
                except ValueError:
                    return await inter.response.send_message("Please enter a valid number for amount.", ephemeral=True)
                
                type_val = self.bet_type.value.strip().capitalize()
                valid_types = ["Red", "Black", "Even", "Odd"]
                if type_val not in valid_types:
                    try:
                        num = int(type_val)
                        if num < 0 or num > 36: raise ValueError
                    except ValueError:
                        return await inter.response.send_message("Invalid type! Use Red, Black, Even, Odd, or 0-36.", ephemeral=True)
                
                self.parent.bets[inter.user.id].append({"amount": amt, "type": type_val})
                self.parent.player_credits[inter.user.id] -= amt
                await inter.response.send_message(f"✅ Bet of **{amt}** on **{type_val}** placed! Remaining: {self.parent.player_credits[inter.user.id]}", ephemeral=True)

        await interaction.response.send_modal(BetModal(self))

    @discord.ui.button(label="Spin 🎡", style=discord.ButtonStyle.success)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("Only the host can spin!", ephemeral=True)
        
        if self.state != "betting": return
            
        self.state = "spinning"
        self.clear_items()
        await interaction.response.edit_message(content="🎡 **SPINNING THE WHEEL...**", view=self)
        
        await asyncio.sleep(4)
        
        result = random.randint(0, 36)
        red_nums = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        color = "Green" if result == 0 else "Red" if result in red_nums else "Black"
        
        await self.process_winners(interaction, result, color)

    async def process_winners(self, interaction, result, color):
        results_text = f"🎡 The wheel stops at... **{result} ({color})**!\n\n"
        
        for pid, p_bets in self.bets.items():
            player = interaction.guild.get_member(pid)
            total_won = 0
            for bet in p_bets:
                won = False
                payout = 0
                if bet["type"] == color:
                    won = True; payout = bet["amount"] * 2
                elif bet["type"] == "Even" and result != 0 and result % 2 == 0:
                    won = True; payout = bet["amount"] * 2
                elif bet["type"] == "Odd" and result % 2 != 0:
                    won = True; payout = bet["amount"] * 2
                elif bet["type"] == str(result):
                    won = True; payout = bet["amount"] * 36
                
                if won: total_won += payout
            
            self.player_credits[pid] += total_won
            results_text += f"{player.mention}: Won **{total_won}** | Credits: **{self.player_credits[pid]}**\n"
            
        self.bets = {p.id: [] for p in self.players}
        self.state = "betting"
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed("Roulette Results", results_text, discord.Color.purple())
        
        # Re-add buttons for next round
        place_btn = discord.ui.Button(label="Place Bet 💰", style=discord.ButtonStyle.primary)
        place_btn.callback = self.place_bet.callback
        self.add_item(place_btn)
        
        spin_btn = discord.ui.Button(label="Spin 🎡", style=discord.ButtonStyle.success)
        spin_btn.callback = self.spin.callback
        self.add_item(spin_btn)
        
        await interaction.channel.send(embed=embed, view=self)
