import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import HotXOView
import random

class HotXOCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = []
        self.on_game = False

    @app_commands.command(name="hotxo", description="Start a tournament of HotXO.")
    async def hotxo(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting HotXO Tournament...", embed=None, view=None)
            self.players = players
            self.on_game = True
            await self.start_tournament_round(inter.channel)

        lobby = BaseLobbyView(interaction.user, "HotXO", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed(
            "HotXO Tournament", 
            interaction.user, 
            [interaction.user], 
            rules="1. Two players chosen randomly each round.\n2. Compete in HotXO (oldest mark deleted after 3 moves).\n3. Last player standing wins!"
        )
        await interaction.response.send_message(embed=embed, view=lobby)

    async def start_tournament_round(self, channel: discord.TextChannel):
        if len(self.players) < 2:
            winner = self.players[0] if self.players else None
            if winner:
                embed = EmbedFactory.success_embed(f"🏆 {winner.mention} is the HotXO Tournament Champion!")
                await channel.send(embed=embed)
            self.on_game = False
            return

        p1, p2 = random.sample(self.players, 2)
        
        async def on_win(game_inter, winner, status):
            loser = p1 if winner == p2 else p2
            self.players.remove(loser)
            embed = EmbedFactory.success_embed(f"{status}\n\n🏆 {winner.mention} won the match! {loser.mention} has been eliminated.")
            await game_inter.response.edit_message(embed=embed, view=None)
            await asyncio.sleep(3)
            await self.start_tournament_round(channel)
            
        async def on_draw(game_inter, status):
            # In case of draw, maybe just replay?
            embed = EmbedFactory.info_embed(f"{status}\n\n🤝 Draw! Replaying match...")
            await game_inter.response.edit_message(embed=embed, view=None)
            await asyncio.sleep(3)
            await self.start_tournament_round(channel)

        view = HotXOView(p1, p2, on_win, on_draw)
        embed = EmbedFactory.create_embed("HotXO Match", f"**{p1.mention} (❌) vs {p2.mention} (⭕)**\n\n**Turn:** {p1.mention}")
        await channel.send(embed=embed, view=view)

import asyncio
async def setup(bot):
    await bot.add_cog(HotXOCommands(bot))
