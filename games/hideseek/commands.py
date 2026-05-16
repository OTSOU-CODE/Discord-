import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import HideSeekView

class HideSeekCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hideseek", description="Start a game of Hide and Seek.")
    async def hideseek(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Hide and Seek...", embed=None, view=None)
            seeker = random.choice(players)
            hiders = [p for p in players if p != seeker]
            
            view = HideSeekView(seeker, hiders, lambda inter, winner: None)
            embed = EmbedFactory.create_embed(
                "Hide and Seek",
                f"🕵️ **{seeker.mention} is the seeker!**\nHiders, you have 30 seconds to hide!",
                discord.Color.blue()
            )
            await inter.channel.send(embed=embed, view=view)

        lobby = BaseLobbyView(interaction.user, "Hide and Seek", start_game, min_players=3)
        embed = EmbedFactory.game_lobby_embed("Hide and Seek", interaction.user, [interaction.user], rules="One seeker, multiple hiders. Hiders choose a spot, seeker tries to find them.")
        await interaction.response.send_message(embed=embed, view=lobby)

import random # Needed random here
async def setup(bot):
    await bot.add_cog(HideSeekCommands(bot))
