import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import RouletteView

class RouletteCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roulette", description="Play a game of Casino Roulette.")
    async def roulette(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            async def on_end(game_inter, results):
                pass

            view = RouletteView(interaction.user, players, on_end)
            embed = EmbedFactory.create_embed("Roulette", "Place your bets! The host will spin the wheel when ready.")
            await inter.response.edit_message(embed=embed, view=view)

        lobby = BaseLobbyView(
            host=interaction.user,
            game_name="Roulette",
            on_start=start_game,
            min_players=1
        )
        embed = EmbedFactory.game_lobby_embed(
            "Roulette",
            interaction.user,
            [interaction.user],
            rules="Classic Casino Roulette. Bet on Red/Black, Even/Odd, or specific numbers. Everyone starts with 1000 credits."
        )
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(RouletteCommands(bot))
