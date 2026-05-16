import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import ChairsView

class ChairsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="chairs", description="Start a game of Musical Chairs.")
    async def chairs(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Musical Chairs...", embed=None, view=None)
            view = ChairsView(players, lambda inter, winner: None)
            await view.start_round(inter.channel)

        lobby = BaseLobbyView(interaction.user, "Musical Chairs", start_game, min_players=3)
        embed = EmbedFactory.game_lobby_embed("Musical Chairs", interaction.user, [interaction.user], rules="Wait for the music to stop, then be the first to sit on a chair!")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(ChairsCommands(bot))
