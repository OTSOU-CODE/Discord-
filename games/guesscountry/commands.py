import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import GuessTheCountryGame

class GuessCountryCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="guesscountry", description="Start a Guess The Country game.")
    async def guesscountry(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Guess The Country...", embed=None, view=None)
            game = GuessTheCountryGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Guess The Country", start_game, min_players=1)
        embed = EmbedFactory.game_lobby_embed("Guess The Country", interaction.user, [interaction.user], rules="Guess the country based on the clues provided.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(GuessCountryCommands(bot))
