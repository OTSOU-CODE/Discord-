import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import MergeTextGame

class MergeTextCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mergetext", description="Mini game: merge the text fragments!")
    async def mergetext(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Merge Text...", embed=None, view=None)
            game = MergeTextGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Merge Text", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Merge Text", interaction.user, [interaction.user], rules="Combine the shuffled fragments into a single word.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(MergeTextCommands(bot))
