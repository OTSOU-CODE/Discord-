import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import TextReverseGame

class TextReverseCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="textreverse", description="Mini game: reverse the word!")
    async def textreverse(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Text Reverse...", embed=None, view=None)
            game = TextReverseGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Text Reverse", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Text Reverse", interaction.user, [interaction.user], rules="Reverse the shuffled word correctly.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(TextReverseCommands(bot))
