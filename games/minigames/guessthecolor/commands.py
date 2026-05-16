import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import GuessTheColorGame

class GuessTheColorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="guessthecolor", description="Mini game: guess the color name!")
    async def guessthecolor(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Guess The Color...", embed=None, view=None)
            game = GuessTheColorGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Guess The Color", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Guess The Color", interaction.user, [interaction.user], rules="Identify the color displayed in the embed.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(GuessTheColorCommands(bot))
