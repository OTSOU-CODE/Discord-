import discord
import asyncio
import random
import time
from typing import List, Dict, Optional, Callable

class ChairsView(discord.ui.View):
    def __init__(self, players: List[discord.Member], on_end: Callable):
        super().__init__(timeout=600)
        self.players = players
        self.on_end = on_end
        self.alive_players = players.copy()
        self.seated_players = []
        self.state = "waiting" # waiting, music, stop
        self.round_num = 1

    async def start_round(self, channel: discord.TextChannel):
        self.clear_items()
        self.seated_players = []
        self.state = "music"
        
        # Add a single dummy button during music
        wait_btn = discord.ui.Button(label="WAIT...", style=discord.ButtonStyle.secondary, disabled=True)
        self.add_item(wait_btn)
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            f"Musical Chairs - Round {self.round_num}",
            f"🎵 Music is playing... Get ready!\n\n**Players Alive:** {len(self.alive_players)}\n**Chairs Available:** {len(self.alive_players) - 1}",
            discord.Color.blue()
        )
        msg = await channel.send(embed=embed, view=self)
        
        await asyncio.sleep(random.uniform(3, 8))
        
        self.state = "stop"
        self.clear_items()
        
        num_chairs = len(self.alive_players) - 1
        for i in range(num_chairs):
            chair_btn = discord.ui.Button(label=f"CHAIR {i+1} 🪑", style=discord.ButtonStyle.success, custom_id=f"chair_{i}")
            chair_btn.callback = self.make_sit_callback(i)
            self.add_item(chair_btn)
        
        stop_embed = EmbedFactory.create_embed(
            f"Musical Chairs - Round {self.round_num}",
            "🛑 **THE MUSIC STOPPED! CLICK A CHAIR!**",
            discord.Color.red()
        )
        await msg.edit(embed=stop_embed, view=self)

    def make_sit_callback(self, chair_idx: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user not in self.alive_players:
                return await interaction.response.send_message("You are not in this game!", ephemeral=True)
            
            if interaction.user in self.seated_players:
                return await interaction.response.send_message("You already found a chair!", ephemeral=True)
            
            if self.state != "stop":
                return
            
            # Check if this specific chair is already taken
            # (In this simple implementation, any chair button works until all chairs are full)
            # But the user asked for "more than one sit button", so I'll let each button be a chair.
            # To be more realistic, I'll disable the button once clicked.
            
            # Find the button in self.children and disable it
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == f"chair_{chair_idx}":
                    if item.disabled:
                        return await interaction.response.send_message("This chair is already taken!", ephemeral=True)
                    item.disabled = True
                    item.label = "TAKEN 🪑"
                    item.style = discord.ButtonStyle.secondary
                    break
            
            self.seated_players.append(interaction.user)
            await interaction.response.send_message("You found a chair! ✅", ephemeral=True)
            await interaction.edit_original_response(view=self) # Update board to show disabled chair
            
            num_chairs = len(self.alive_players) - 1
            if len(self.seated_players) == num_chairs:
                await self.end_round(interaction.channel)
        
        return callback

    async def end_round(self, channel: discord.TextChannel):
        # The player who didn't sit
        remaining = [p for p in self.alive_players if p not in self.seated_players]
        if not remaining:
             # Should not happen but for safety
             return
        
        eliminated = remaining[0]
        self.alive_players.remove(eliminated)
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Round Ended",
            f"😢 {eliminated.mention} couldn't find a chair and was eliminated!",
            discord.Color.orange()
        )
        await channel.send(embed=embed)
        
        if len(self.alive_players) == 1:
            winner = self.alive_players[0]
            win_embed = EmbedFactory.success_embed(f"🏆 {winner.mention} is the last one standing and wins Musical Chairs!")
            await channel.send(embed=win_embed)
            await self.on_end(None, winner)
        else:
            self.round_num += 1
            await asyncio.sleep(3)
            await self.start_round(channel)
