import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import SortNumbersGame

class SortNumbersCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sortnumbers", description="Mini game: sort the numbers!")
    async def sortnumbers(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Sort Numbers...", embed=None, view=None)
            game = SortNumbersGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Sort Numbers", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Sort Numbers", interaction.user, [interaction.user], rules="Sort the given numbers from smallest to largest, separated by commas.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(SortNumbersCommands(bot))
