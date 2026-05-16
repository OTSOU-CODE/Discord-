import discord
from discord import app_commands
from discord.ext import commands
from .embeds import EmbedFactory
from .views import BaseLobbyView
from games import GAMES_REGISTRY

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="games", description="Show all available games.")
    async def games(self, interaction: discord.Interaction):
        game_list = "\n".join([f"- **{info['name']}**: {info['rules']}" for info in GAMES_REGISTRY.values()])
        desc = f"**Available Games:**\n{game_list}\n\n**Mini Games:**\nFast Click, Fast Type, Text Split, Merge Text, Text Reverse, Find Letter, Correct Letter, Guess The Flag, Guess The Color, Find The Emoji, Sort Numbers, Text Reveal"
        embed = EmbedFactory.create_embed("🎮 Available Games", desc)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="play", description="Start a game.")
    @app_commands.describe(game="The name of the game to play.")
    async def play(self, interaction: discord.Interaction, game: str):
        game_key = game.lower()
        if game_key not in GAMES_REGISTRY:
            return await interaction.response.send_message(f"Game '{game}' not found. Use `/games` to see available games.", ephemeral=True)
            
        game_info = GAMES_REGISTRY[game_key]
        
        # Load the cog if not loaded
        cog_path = game_info['cog_path']
        if cog_path not in self.bot.extensions:
            try:
                await self.bot.load_extension(cog_path)
                await self.bot.tree.sync()
            except Exception as e:
                return await interaction.response.send_message(f"Failed to load game {game}: {e}", ephemeral=True)

        # Trigger the command (we can just tell the user to use the specific command or try to invoke it)
        # But usually it's better to just have the /play command start the lobby directly if we can
        
        # For now, let's just tell them to use the command
        await interaction.response.send_message(f"Please use `/{game_key}` to start the game.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop the current game in this channel.")
    async def stop(self, interaction: discord.Interaction):
        game = self.bot.game_manager.get_game_in_channel(interaction.channel_id)
        if not game:
            return await interaction.response.send_message("No active game in this channel.", ephemeral=True)
            
        if interaction.user != game.host and not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("Only the host or a moderator can stop the game.", ephemeral=True)
            
        await self.bot.game_manager.unregister_game(game.game_id)
        await interaction.response.send_message(f"Game '{game.game_id}' has been stopped.")

    @app_commands.command(name="help", description="Show help information.")
    async def help(self, interaction: discord.Interaction):
        desc = """
**Commands:**
- `/play <game>`: Start a new game lobby.
- `/games`: List all available games.
- `/stop`: Stop the current game in the channel.
- `/help`: Show this message.

**How to play:**
Use `/play` to start a lobby. Other players can join using the 'Join' button. The host can then start the game.
"""
        embed = EmbedFactory.create_embed("❓ Help & Commands", desc)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GameCommands(bot))
