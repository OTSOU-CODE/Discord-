import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import DiceView

class DiceCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dice", description="Start a dice battle.")
    async def dice(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            async def on_end(game_inter, winners):
                # Game ended
                pass

            view = DiceView(players, on_end)
            embed = EmbedFactory.create_embed("Dice Battle", "Everyone, click the button to roll your dice!")
            await inter.response.edit_message(embed=embed, view=view)

        lobby = BaseLobbyView(
            host=interaction.user,
            game_name="Dice Battle",
            on_start=start_game,
            min_players=2
        )
        embed = EmbedFactory.game_lobby_embed(
            "Dice Battle",
            interaction.user,
            [interaction.user],
            rules="Highest roll wins! Multiple players can play."
        )
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(DiceCommands(bot))
