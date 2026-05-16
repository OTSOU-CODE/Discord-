import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import DeathWheelView

class DeathWheelCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="deathwheel", description="Start a game of Death Wheel.")
    async def deathwheel(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            await inter.response.edit_message(content="Starting Death Wheel...", embed=None, view=None)
            view = DeathWheelView(players, lambda inter, winner: None)
            await view.start_turn(inter.channel)

        lobby = BaseLobbyView(interaction.user, "Death Wheel", start_game, min_players=2)
        embed = EmbedFactory.game_lobby_embed(
            "Death Wheel", 
            interaction.user, 
            [interaction.user], 
            rules="1. A player is randomly chosen each turn.\n2. Chosen player must pick a box.\n3. Safe boxes let you live, Traps eliminate you.\n4. Last survivor wins!"
        )
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(DeathWheelCommands(bot))
