import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import TextRevealGame

class TextRevealCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="textreveal", description="Mini game: guess the word as it reveals!")
    async def textreveal(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Text Reveal...", embed=None, view=None)
            game = TextRevealGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Text Reveal", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Text Reveal", interaction.user, [interaction.user], rules="Guess the word as its letters are slowly revealed.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(TextRevealCommands(bot))
