import discord
from discord.ext import commands
import os
import json
from .logger import Logger
from .storage import Storage
from .manager import GameManager
from games import GAMES_REGISTRY

class DiscordGameBot(commands.Bot):
    def __init__(self, config: dict):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=config.get("prefix", "!"),
            intents=intents,
            help_command=None
        )
        self.config = config
        self.logger = Logger.setup_logger()
        self.game_manager = GameManager(self)

    async def setup_hook(self):
        self.logger.info("Setting up bot extensions...")
        await self.game_manager.restore_games()
        
        # Load core commands
        try:
            await self.load_extension("core.commands")
            self.logger.info("Loaded core commands.")
        except Exception as e:
            self.logger.error(f"Failed to load core commands: {e}")
            
        # Load all registered games
        for game_key, info in GAMES_REGISTRY.items():
            try:
                await self.load_extension(info['cog_path'])
                self.logger.info(f"Loaded game extension: {info['name']}")
            except Exception as e:
                self.logger.error(f"Failed to load game {info['name']}: {e}")
                
        await self.sync_commands()

    async def sync_commands(self):
        try:
            self.logger.info("Syncing slash commands...")
            synced = await self.tree.sync()
            self.logger.info(f"Synced {len(synced)} global commands.")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Game(name="🎮 Games | /help"))
