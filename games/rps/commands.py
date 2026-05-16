import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import RPSView

class RPSCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rps", description="Challenge someone to Rock Paper Scissors.")
    async def rps(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            p1, p2 = players[0], players[1]
            async def on_end(game_inter, winner):
                pass

            view = RPSView(p1, p2, on_end)
            embed = EmbedFactory.create_embed("Rock Paper Scissors", "Both players, choose your move!")
            await inter.response.edit_message(embed=embed, view=view)

        lobby = BaseLobbyView(
            host=interaction.user,
            game_name="Rock Paper Scissors",
            on_start=start_game,
            min_players=2,
            max_players=2
        )
        embed = EmbedFactory.game_lobby_embed(
            "Rock Paper Scissors",
            interaction.user,
            [interaction.user],
            max_players=2,
            rules="Classic Rock Paper Scissors. Simultaneously choose your move."
        )
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(RPSCommands(bot))
