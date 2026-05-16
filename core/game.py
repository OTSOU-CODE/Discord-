import uuid
import asyncio
import os
from typing import List, Optional, Dict, Any
import discord
from .storage import Storage

class BaseGame:
    def __init__(self, game_id: str, host: discord.Member, channel: discord.TextChannel):
        self.game_id = game_id or str(uuid.uuid4())
        self.host = host
        self.players: List[discord.Member] = [host]
        self.channel = channel
        self.state = "lobby"
        self.game_data: Dict[str, Any] = {}

    async def create_lobby(self):
        self.state = "lobby"
        await self.save_game()

    async def join_player(self, player: discord.Member):
        if player not in self.players:
            self.players.append(player)
            await self.save_game()

    async def leave_player(self, player: discord.Member):
        if player in self.players and player != self.host:
            self.players.remove(player)
            await self.save_game()

    async def start_game(self):
        self.state = "active"
        await self.save_game()

    async def end_game(self, reason: str = "finished"):
        self.state = reason
        await self.save_game()
        # Clean up storage
        storage_path = f"storage/active_games/{self.game_id}.json"
        if os.path.exists(storage_path):
            os.remove(storage_path)

    async def save_game(self):
        data = {
            "game_id": self.game_id,
            "host_id": self.host.id,
            "player_ids": [p.id for p in self.players],
            "channel_id": self.channel.id,
            "state": self.state,
            "game_data": self.game_data
        }
        await Storage.save_json(f"storage/active_games/{self.game_id}.json", data)

    @classmethod
    async def load_game(cls, game_id: str, bot: discord.Client):
        data = await Storage.load_json(f"storage/active_games/{game_id}.json")
        if not data:
            return None
        
        channel = bot.get_channel(data["channel_id"])
        host = bot.get_user(data["host_id"])
        if not channel or not host:
            return None
            
        game = cls(data["game_id"], host, channel)
        game.state = data["state"]
        game.game_data = data["game_data"]
        # Note: we might need to fetch players here if they aren't in cache
        game.players = [bot.get_user(pid) for pid in data["player_ids"]]
        return game
