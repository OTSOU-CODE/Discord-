import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import XOView

class XOCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="xo", description="Play a game of Tic Tac Toe.")
    async def xo(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            p1, p2 = players[0], players[1]
            
            async def on_win(game_inter, winner, board):
                embed = EmbedFactory.success_embed(f"{winner.mention} won the game!")
                await game_inter.response.edit_message(embed=embed, view=None)
                # Here we would unregister from manager
                
            async def on_draw(game_inter, board):
                embed = EmbedFactory.info_embed("The game is a draw!")
                await game_inter.response.edit_message(embed=embed, view=None)

            view = XOView(p1, p2, on_win, on_draw)
            embed = EmbedFactory.create_embed("XO Game", f"**Turn:** {p1.mention} (❌)")
            await inter.response.edit_message(embed=embed, view=view)

        lobby = BaseLobbyView(
            host=interaction.user,
            game_name="XO",
            on_start=start_game,
            min_players=2,
            max_players=2
        )
        embed = EmbedFactory.game_lobby_embed(
            "XO",
            interaction.user,
            [interaction.user],
            max_players=2,
            rules="3x3 board. Align 3 marks (❌ or ⭕) to win."
        )
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(XOCommands(bot))
