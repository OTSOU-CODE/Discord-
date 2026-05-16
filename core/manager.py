import discord
from typing import Dict, Optional, List
from .game import BaseGame
from .logger import Logger
from .storage import Storage
import os

class GameManager:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.active_games: Dict[str, BaseGame] = {} # game_id -> game
        self.channel_games: Dict[int, str] = {} # channel_id -> game_id
        self.logger = Logger.setup_logger()

    def get_game_in_channel(self, channel_id: int) -> Optional[BaseGame]:
        game_id = self.channel_games.get(channel_id)
        if game_id:
            return self.active_games.get(game_id)
        return None

    async def register_game(self, game: BaseGame):
        if game.channel.id in self.channel_games:
            existing_game = self.get_game_in_channel(game.channel.id)
            if existing_game and existing_game.state == "active":
                raise Exception("A game is already active in this channel!")
        
        self.active_games[game.game_id] = game
        self.channel_games[game.channel.id] = game.game_id
        await game.save_game()

    async def unregister_game(self, game_id: str):
        game = self.active_games.get(game_id)
        if game:
            if game.channel.id in self.channel_games:
                del self.channel_games[game.channel.id]
            del self.active_games[game_id]
            
            storage_path = f"storage/active_games/{game_id}.json"
            if os.path.exists(storage_path):
                os.remove(storage_path)

    async def restore_games(self):
        self.logger.info("Restoring active games...")
        storage_dir = "storage/active_games"
        if not os.path.exists(storage_dir):
            return

        for filename in os.listdir(storage_dir):
            if filename.endswith(".json"):
                game_id = filename[:-5]
                try:
                    game = await BaseGame.load_game(game_id, self.bot)
                    if game:
                        self.active_games[game_id] = game
                        self.channel_games[game.channel.id] = game_id
                        self.logger.info(f"Restored game {game_id}")
                except Exception as e:
                    self.logger.error(f"Failed to restore game {game_id}: {e}")
