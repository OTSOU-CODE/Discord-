import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import FastTypeGame

class FastTypeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fasttype", description="Mini game: be the first to type the sentence!")
    async def fasttype(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Fast Type...", embed=None, view=None)
            
            async def on_end(msg, winner):
                pass

            game = FastTypeGame(self.bot, players, inter.channel, on_end)
            await game.start()

        lobby = BaseLobbyView(
            host=interaction.user,
            game_name="Fast Type",
            on_start=start_game,
            min_players=2
        )
        embed = EmbedFactory.game_lobby_embed(
            "Fast Type",
            interaction.user,
            [interaction.user],
            rules="Speed typing. First player to type the displayed sentence exactly wins."
        )
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(FastTypeCommands(bot))
