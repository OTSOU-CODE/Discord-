import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import FindLetterGame

class FindLetterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="findletter", description="Mini game: find the target letter!")
    async def findletter(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Find Letter...", embed=None, view=None)
            game = FindLetterGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Find Letter", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Find Letter", interaction.user, [interaction.user], rules="Locate the specific letter hidden in the text spam.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(FindLetterCommands(bot))
