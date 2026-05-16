import discord
import time
import asyncio
import random
from typing import List, Optional, Callable
from core.storage import Storage

class FastTypeGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.word = ""
        self.start_time = None
        self.winner = None

    async def start(self):
        # Using a fixed list of single words for now, could be loaded from words.json if updated
        words = ["DISCORD", "PYTHON", "PROGRAMMING", "CHALLENGE", "INTERACTIVE", "EXPERIENCE", "REACTION", "KEYBOARD", "SYSTEM", "FAST"]
        self.word = random.choice(words)
        
        # Apply anti-copy: Inject zero-width spaces between characters
        display_word = "\u200B".join(list(self.word))
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Fast Type",
            f"Type the following word as fast as you can!\n\n**{display_word}**",
            discord.Color.blue()
        )
        await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        def check(m):
            # Check for exact match with the original word (without ZWSP)
            return m.channel == self.channel and m.author in self.players and m.content.strip().upper() == self.word

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=10) # 10 seconds
            self.winner = msg.author
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{self.winner.mention} typed it in **{elapsed:.2f}s** and won! ⌨️")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, self.winner)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! No one typed the word in time. The word was **{self.word}**.")
            await self.on_end(None, None)
