import discord
import time
import asyncio
import random
from typing import List, Optional, Callable

class MergeTextGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.word = ""
        self.fragments = []
        self.start_time = None

    async def start(self):
        words = ["PROGRAMMING", "DEVELOPER", "CHALLENGE", "INTERACTIVE", "EXPERIENCE", "KNOWLEDGE", "REACTION"]
        self.word = random.choice(words)
        
        # Split into 3 fragments
        chunk_size = len(self.word) // 3
        self.fragments = [self.word[:chunk_size], self.word[chunk_size:chunk_size*2], self.word[chunk_size*2:]]
        random.shuffle(self.fragments)
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Merge Text",
            f"Merge these fragments into the correct word:\n\n**{', '.join(self.fragments)}**",
            discord.Color.blue()
        )
        await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        def check(m):
            return m.channel == self.channel and m.author in self.players and m.content.strip().upper() == self.word

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{msg.author.mention} merged it in **{elapsed:.2f}s**! The word was **{self.word}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, msg.author)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! The word was **{self.word}**.")
            await self.on_end(None, None)
