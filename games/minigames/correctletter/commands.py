import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import CorrectLetterGame

class CorrectLetterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="correctletter", description="Mini game: identify the different character!")
    async def correctletter(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Correct Letter...", embed=None, view=None)
            game = CorrectLetterGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Correct Letter", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Correct Letter", interaction.user, [interaction.user], rules="Identify the character that is different from all others.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(CorrectLetterCommands(bot))
