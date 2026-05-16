import discord
import time
import asyncio
import random
import string
from typing import List, Optional, Callable

class CorrectLetterGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.different_char = ""
        self.spam = ""
        self.start_time = None

    async def start(self):
        char1, char2 = random.sample(string.ascii_uppercase, 2)
        
        length = 50
        target_pos = random.randint(0, length - 1)
        self.different_char = char2
        self.spam = "".join([char1 if i != target_pos else char2 for i in range(length)])
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Correct Letter",
            f"One character is different from the others. Type it!\n\n`{self.spam}`",
            discord.Color.blue()
        )
        await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        def check(m):
            return m.channel == self.channel and m.author in self.players and m.content.strip().upper() == self.different_char

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{msg.author.mention} identified it in **{elapsed:.2f}s**! The different character was **{self.different_char}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, msg.author)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! The different character was **{self.different_char}**.")
            await self.on_end(None, None)
