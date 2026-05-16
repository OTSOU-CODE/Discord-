import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import GuessTheFlagGame

class GuessTheFlagCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="guesstheflag", description="Mini game: guess the country from the flag!")
    async def guesstheflag(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Guess The Flag...", embed=None, view=None)
            game = GuessTheFlagGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Guess The Flag", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Guess The Flag", interaction.user, [interaction.user], rules="Identify the country represented by the flag emoji.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(GuessTheFlagCommands(bot))
