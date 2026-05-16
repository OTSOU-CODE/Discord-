import discord
import time
import asyncio
import random
import string
from typing import List, Optional, Callable

class FindLetterGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.target = ""
        self.spam = ""
        self.start_time = None

    async def start(self):
        # Pairs of identical-looking characters
        pairs = [("O", "0"), ("I", "l"), ("1", "l"), ("5", "S"), ("8", "B"), ("2", "Z")]
        pair = random.choice(pairs)
        filler = pair[0]
        self.target = pair[1]
        
        length = 50
        target_pos = random.randint(0, length - 1)
        
        # Apply anti-copy (ZWSP)
        spam_list = [filler if i != target_pos else self.target for i in range(length)]
        self.spam = "\u200B".join(spam_list)
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Find Letter",
            f"Find the character that is different in this spam:\n\n`{self.spam}`\n\n**Type the character!**",
            discord.Color.blue()
        )
        await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        def check(m):
            return m.channel == self.channel and m.author in self.players and m.content.strip().upper() == self.target.upper()

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=10) # 10 seconds
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{msg.author.mention} found it in **{elapsed:.2f}s**! The character was **{self.target}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, msg.author)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! The character was **{self.target}**.")
            await self.on_end(None, None)
