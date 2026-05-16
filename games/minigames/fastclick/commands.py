import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .view import FastClickView

class FastClickCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fastclick", description="Mini game: be the first to click the button!")
    async def fastclick(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            async def on_end(game_inter, winner):
                pass

            view = FastClickView(players, on_end)
            embed = EmbedFactory.create_embed("Fast Click", "Get ready... wait for the button to change!")
            await inter.response.edit_message(embed=embed, view=view)
            
            # Start the countdown task
            msg = await inter.original_response()
            await view.start_countdown(msg)

        lobby = BaseLobbyView(
            host=interaction.user,
            game_name="Fast Click",
            on_start=start_game,
            min_players=2
        )
        embed = EmbedFactory.game_lobby_embed(
            "Fast Click",
            interaction.user,
            [interaction.user],
            rules="Reaction timing. First player to click the button when it changes wins."
        )
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(FastClickCommands(bot))
