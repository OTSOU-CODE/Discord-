import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from core.storage import Storage
from .view import ReplicaView
import random

class ReplicaCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="replica", description="Start a game of Replica.")
    async def replica(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            prompts = await Storage.load_json("data/replica_prompts.json")
            prompt = random.choice(prompts)
            
            await inter.response.edit_message(content="Starting Replica...", embed=None, view=None)
            
            view = ReplicaView(prompt, players, lambda inter, winner: None)
            embed = EmbedFactory.create_embed(
                "Replica",
                f"**Prompt:** {prompt}\n\nEveryone, submit your funniest answer!",
                discord.Color.blue()
            )
            await inter.channel.send(embed=embed, view=view)

        lobby = BaseLobbyView(interaction.user, "Replica", start_game, min_players=3)
        embed = EmbedFactory.game_lobby_embed("Replica", interaction.user, [interaction.user], rules="Submit a funny answer to the prompt, then vote for the best one!")
        await interaction.response.send_message(embed=embed, view=lobby)

async def setup(bot):
    await bot.add_cog(ReplicaCommands(bot))
