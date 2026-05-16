import discord
import time
import asyncio
import random
import io
from typing import List, Optional, Callable
from core.storage import Storage
from PIL import Image, ImageDraw

class GuessTheColorGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.color_name = ""
        self.hex_code = ""
        self.start_time = None

    async def start(self):
        colors = await Storage.load_json("data/colors.json")
        choice = random.choice(colors)
        self.color_name = choice["name"]
        self.hex_code = choice["hex"]
        
        # Generate color image using Pillow
        img = Image.new('RGB', (200, 200), color=self.hex_code)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        file = discord.File(img_byte_arr, filename="color.png")
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Guess The Color",
            "What is the name of this color?",
            discord.Color(int(self.hex_code.replace("#", "0x"), 16))
        )
        embed.set_image(url="attachment://color.png")
        
        await self.channel.send(file=file, embed=embed)
        self.start_time = time.time()
        
        def check(m):
            return m.channel == self.channel and m.author in self.players and m.content.strip().lower() == self.color_name.lower()

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=10) # 10 seconds
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{msg.author.mention} guessed it in **{elapsed:.2f}s**! It's **{self.color_name}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, msg.author)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! The color was **{self.color_name}**.")
            await self.on_end(None, None)
