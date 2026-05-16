import discord
import time
import asyncio
import random
from typing import List, Optional, Callable
from core.storage import Storage

class TextSplitGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.word = ""
        self.split_word = ""
        self.start_time = None

    async def start(self):
        words = ["HELLO", "WORLD", "DISCORD", "PYTHON", "GAMING", "SERVER", "MINIGAME", "CHALLENGE"]
        self.word = random.choice(words)
        
        # Split word randomly
        split_idx = random.randint(1, len(self.word) - 1)
        self.split_word = self.word[:split_idx] + " " + self.word[split_idx:]
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Text Split",
            f"Reconstruct the word from these parts:\n\n**{self.split_word}**",
            discord.Color.blue()
        )
        await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        def check(m):
            return m.channel == self.channel and m.author in self.players and m.content.strip().upper() == self.word

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{msg.author.mention} reconstructed it in **{elapsed:.2f}s**! The word was **{self.word}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, msg.author)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! The word was **{self.word}**.")
            await self.on_end(None, None)
