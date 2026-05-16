import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import TextSplitGame

class TextSplitCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="textsplit", description="Mini game: reconstruct the split word!")
    async def textsplit(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Text Split...", embed=None, view=None)
            game = TextSplitGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Text Split", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Text Split", interaction.user, [interaction.user], rules="Reconstruct the word from split parts.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(TextSplitCommands(bot))
