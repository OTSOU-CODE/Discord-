import discord
import time
import asyncio
import random
from typing import List, Optional, Callable

class SortNumbersGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.numbers = []
        self.sorted_numbers_str = ""
        self.start_time = None

    async def start(self):
        # difficulty randomly 5 or 20
        count = random.choice([5, 20])
        self.numbers = [random.randint(0, 9) for _ in range(count)]
        self.sorted_numbers_str = ", ".join(map(str, sorted(self.numbers)))
        
        shuffled = self.numbers.copy()
        random.shuffle(shuffled)
        
        # Apply anti-copy (ZWSP) to the shuffled list for display
        display_shuffled = "\u200B".join(map(str, shuffled))
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Sort Numbers",
            f"Sort these single-digit numbers from smallest to largest. Separate with commas!\n\n**{display_shuffled}**",
            discord.Color.blue()
        )
        await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        def check(m):
            if m.channel != self.channel or m.author not in self.players:
                return False
            try:
                # User types numbers separated by commas
                user_numbers = [int(n.strip()) for n in m.content.split(",")]
                return user_numbers == sorted(self.numbers)
            except:
                return False

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=10) # 10 seconds
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{msg.author.mention} sorted them in **{elapsed:.2f}s**! Correct order: **{self.sorted_numbers_str}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, msg.author)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! The correct order was **{self.sorted_numbers_str}**.")
            await self.on_end(None, None)
