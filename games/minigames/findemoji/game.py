import discord
import time
import asyncio
import random
from typing import List, Optional, Callable

class FindEmojiGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.target = ""
        self.spam = ""
        self.start_time = None

    async def start(self):
        # Pairs of identical-looking emojis
        emoji_pairs = [
            ("🙂", "🙃"), ("😀", "😃"), ("😆", "😅"), ("😊", "😋"),
            ("😎", "🕶️"), ("🥺", "🥺"), # Some can be identical if we just want volume
            ("🍎", "🍎"), ("🍒", "🍒")
        ]
        # Better yet, just use a large list and one slightly different or just a specific one
        base_emojis = ["😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣"]
        self.target = random.choice(base_emojis)
        
        # We need IDENTICAL emojis as per user request to make it hard
        # But if they are literally identical, any would work.
        # User said: "identical to each other so the use must find it hard"
        # I'll use 49 identical ones and 1 slightly different or just 50 identical ones and user must type it.
        # Actually, "find the emoji" usually implies one is different.
        # Let's use 49 'O' and 1 '0' logic but with emojis.
        
        filler = "😀"
        self.target = "😃"
        
        length = 50
        target_pos = random.randint(0, length - 1)
        
        # Apply anti-copy (ZWSP) to the spam as well
        spam_list = [filler if i != target_pos else self.target for i in range(length)]
        self.spam = "\u200B".join(spam_list)
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Find The Emoji",
            f"Find the emoji that is different (or find the target) in this spam:\n\n{self.spam}\n\n**Type the emoji!**",
            discord.Color.blue()
        )
        await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        def check(m):
            return m.channel == self.channel and m.author in self.players and m.content.strip() == self.target

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=10) # 10 seconds
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{msg.author.mention} found it in **{elapsed:.2f}s**! The emoji was **{self.target}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, msg.author)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! The emoji was **{self.target}**.")
            await self.on_end(None, None)
