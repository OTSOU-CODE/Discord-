import discord
from typing import List, Dict, Optional, Callable

class RPSView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member, on_end: Callable):
        super().__init__(timeout=120)
        self.p1 = p1
        self.p2 = p2
        self.choices: Dict[int, str] = {}
        self.on_end = on_end

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        if interaction.user not in [self.p1, self.p2]:
            return await interaction.response.send_message("You are not in this game!", ephemeral=True)
        
        if interaction.user.id in self.choices:
            return await interaction.response.send_message("You already chose!", ephemeral=True)
            
        self.choices[interaction.user.id] = choice
        await interaction.response.send_message(f"You chose {choice}! ✌️✋✊", ephemeral=True)
        
        if len(self.choices) == 2:
            self.stop()
            await self.calculate_winner(interaction)

    @discord.ui.button(label="Rock ✊", style=discord.ButtonStyle.secondary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Rock")

    @discord.ui.button(label="Paper ✋", style=discord.ButtonStyle.secondary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Paper")

    @discord.ui.button(label="Scissors ✌️", style=discord.ButtonStyle.secondary)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Scissors")

    async def calculate_winner(self, interaction: discord.Interaction):
        c1 = self.choices[self.p1.id]
        c2 = self.choices[self.p2.id]
        
        rules = {"Rock": "Scissors", "Paper": "Rock", "Scissors": "Paper"}
        
        if c1 == c2:
            result = "It's a tie!"
            winner = None
        elif rules[c1] == c2:
            result = f"{self.p1.mention} wins!"
            winner = self.p1
        else:
            result = f"{self.p2.mention} wins!"
            winner = self.p2
            
        from core.embeds import EmbedFactory
        desc = f"{self.p1.mention}: {c1}\n{self.p2.mention}: {c2}\n\n**{result}**"
        embed = EmbedFactory.create_embed("Rock Paper Scissors Results", desc, discord.Color.gold() if winner else discord.Color.blue())
        await interaction.channel.send(embed=embed)
        await self.on_end(interaction, winner)
