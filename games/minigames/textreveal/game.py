import discord
import time
import asyncio
import random
from typing import List, Optional, Callable

class TextRevealGame:
    def __init__(self, bot, players: List[discord.Member], channel: discord.TextChannel, on_end: Callable):
        self.bot = bot
        self.players = players
        self.channel = channel
        self.on_end = on_end
        self.word = ""
        self.revealed = []
        self.start_time = None
        self.game_over = False

    async def start(self):
        words = ["PROGRAMMING", "DISCORD", "PYTHON", "DEVELOPER", "INTERFACE", "REACTION", "CHALLENGE"]
        self.word = random.choice(words)
        self.revealed = ["\_" for _ in self.word]
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Text Reveal",
            f"Guess the word as it reveals!\n\n**{' '.join(self.revealed)}**",
            discord.Color.blue()
        )
        msg = await self.channel.send(embed=embed)
        self.start_time = time.time()
        
        async def reveal_loop():
            indices = list(range(len(self.word)))
            random.shuffle(indices)
            for idx in indices:
                if self.game_over:
                    break
                await asyncio.sleep(3)
                self.revealed[idx] = self.word[idx]
                new_embed = EmbedFactory.create_embed(
                    "Text Reveal",
                    f"Guess the word as it reveals!\n\n**{' '.join(self.revealed)}**",
                    discord.Color.blue()
                )
                await msg.edit(embed=new_embed)

        reveal_task = asyncio.create_task(reveal_loop())

        def check(m):
            return m.channel == self.channel and m.author in self.players and m.content.strip().upper() == self.word

        try:
            guess_msg = await self.bot.wait_for('message', check=check, timeout=60)
            self.game_over = True
            elapsed = time.time() - self.start_time
            
            result_embed = EmbedFactory.success_embed(f"{guess_msg.author.mention} guessed it in **{elapsed:.2f}s**! The word was **{self.word}**.")
            await self.channel.send(embed=result_embed)
            await self.on_end(guess_msg, guess_msg.author)
        except asyncio.TimeoutError:
            self.game_over = True
            await self.channel.send(f"Time's up! The word was **{self.word}**.")
            await self.on_end(None, None)
        finally:
            reveal_task.cancel()
