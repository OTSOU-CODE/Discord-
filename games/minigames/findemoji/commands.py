import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import FindEmojiGame

class FindEmojiCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="findemoji", description="Mini game: find the hidden emoji!")
    async def findemoji(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Find The Emoji...", embed=None, view=None)
            game = FindEmojiGame(self.bot, players, inter.channel, lambda m, w: None)
            await game.start()

        lobby = BaseLobbyView(interaction.user, "Find The Emoji", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed("Find The Emoji", interaction.user, [interaction.user], rules="Locate the specific emoji hidden in the spam.")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(FindEmojiCommands(bot))
