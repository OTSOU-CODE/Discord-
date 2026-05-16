import discord
import random
from typing import List, Optional, Callable

class DiceView(discord.ui.View):
    def __init__(self, players: List[discord.Member], on_end: Callable):
        super().__init__(timeout=120)
        self.players = players
        self.on_end = on_end
        self.rolls = {}
        self.game_over = False

    @discord.ui.button(label="Roll Dice 🎲", style=discord.ButtonStyle.primary)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            return await interaction.response.send_message("You are not in this game!", ephemeral=True)
        
        if interaction.user.id in self.rolls:
            return await interaction.response.send_message("You already rolled!", ephemeral=True)
            
        roll = random.randint(1, 6)
        self.rolls[interaction.user.id] = roll
        
        await interaction.response.send_message(f"You rolled a **{roll}**! 🎲", ephemeral=True)
        
        if len(self.rolls) == len(self.players):
            self.game_over = True
            self.stop()
            await self.calculate_winner(interaction)

    async def calculate_winner(self, interaction: discord.Interaction):
        results = sorted(self.rolls.items(), key=lambda x: x[1], reverse=True)
        max_roll = results[0][1]
        winners = [interaction.client.get_user(uid) for uid, roll in self.rolls.items() if roll == max_roll]
        
        desc = "**Results:**\n"
        for uid, roll in self.rolls.items():
            user = interaction.client.get_user(uid)
            desc += f"{user.mention}: {roll}\n"
            
        if len(winners) > 1:
            winner_text = "It's a tie between: " + ", ".join([w.mention for w in winners])
        else:
            winner_text = f"The winner is {winners[0].mention}! 🏆"
            
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed("Dice Battle Results", f"{desc}\n{winner_text}", discord.Color.gold())
        await interaction.channel.send(embed=embed)
        await self.on_end(interaction, winners)
