import discord
import time
import asyncio
import random
from typing import List, Optional, Callable

class FastClickView(discord.ui.View):
    def __init__(self, players: List[discord.Member], on_end: Callable):
        super().__init__(timeout=60)
        self.players = players
        self.on_end = on_end
        self.start_time = None
        self.winner = None

    @discord.ui.button(label="WAIT...", style=discord.ButtonStyle.secondary, disabled=True)
    async def click(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            return await interaction.response.send_message("You are not in this game!", ephemeral=True)
        
        if button.label == "CLICK!":
            self.winner = interaction.user
            elapsed = time.time() - self.start_time
            self.stop()
            await self.calculate_winner(interaction, elapsed)
        else:
            await interaction.response.send_message("Too early!", ephemeral=True)

    async def calculate_winner(self, interaction: discord.Interaction, elapsed: float):
        from core.embeds import EmbedFactory
        embed = EmbedFactory.success_embed(f"{self.winner.mention} clicked in **{elapsed:.3f}s** and won! ⚡")
        await interaction.channel.send(embed=embed)
        await self.on_end(interaction, self.winner)

    async def start_countdown(self, message: discord.Message):
        await asyncio.sleep(random.uniform(2, 5))
        button = self.children[0]
        button.label = "CLICK!"
        button.style = discord.ButtonStyle.success
        button.disabled = False
        self.start_time = time.time()
        await message.edit(view=self)
