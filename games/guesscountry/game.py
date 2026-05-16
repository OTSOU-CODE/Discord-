import discord
import time
import asyncio
import random
from typing import List, Optional, Callable
from core.storage import Storage

class GuessTheCountryGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.country_data = {}
        self.start_time = None

    async def start(self):
        countries = await Storage.load_json("data/countries.json")
        self.country_data = random.choice(countries)
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Guess The Country",
            f"**Clue:** {self.country_data['clue']}\n**Capital:** {self.country_data['capital']}\n**Continent:** {self.country_data['continent']}",
            discord.Color.blue()
        )
        await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        def check(m):
            return m.channel == self.channel and m.author in self.players and m.content.strip().lower() == self.country_data['name'].lower()

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=45)
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{msg.author.mention} guessed it in **{elapsed:.2f}s**! It's **{self.country_data['name']}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(msg, msg.author)
        except asyncio.TimeoutError:
            await self.channel.send(f"Time's up! The country was **{self.country_data['name']}**.")
            await self.on_end(None, None)
