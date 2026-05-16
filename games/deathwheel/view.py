import discord
import random
import asyncio
from typing import List, Optional, Callable

class DeathWheelView(discord.ui.View):
    def __init__(self, players: List[discord.Member], on_end: Callable):
        super().__init__(timeout=600)
        self.players = players
        self.on_end = on_end
        self.alive_players = players.copy()
        self.chosen_player: Optional[discord.Member] = None
        self.boxes = [] # List of bool (True = Safe, False = Trap)
        self.state = "spinning" # spinning, picking

    async def start_turn(self, channel: discord.TextChannel):
        self.state = "spinning"
        self.clear_items()
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Death Wheel",
            "🎡 The wheel is spinning to choose a victim...",
            discord.Color.blue()
        )
        msg = await channel.send(embed=embed)
        await asyncio.sleep(3)
        
        self.chosen_player = random.choice(self.alive_players)
        self.state = "picking"
        
        # Prepare boxes: number of boxes = number of alive players? 
        # Or just a fixed number, say 5 boxes, 1 is a trap.
        num_boxes = 5
        self.boxes = [True] * num_boxes
        trap_idx = random.randint(0, num_boxes - 1)
        self.boxes[trap_idx] = False
        
        for i in range(num_boxes):
            btn = discord.ui.Button(label=f"Box {i+1} 📦", style=discord.ButtonStyle.secondary, custom_id=f"box_{i}")
            btn.callback = self.make_box_callback(i)
            self.add_item(btn)
            
        pick_embed = EmbedFactory.create_embed(
            "Death Wheel - Your Turn!",
            f"🎯 {self.chosen_player.mention}, you have been chosen!\nPick a box. One is a **TRAP**, the others are **SAFE**.",
            discord.Color.orange()
        )
        await msg.edit(embed=pick_embed, view=self)

    def make_box_callback(self, box_idx: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.chosen_player:
                return await interaction.response.send_message("It's not your turn!", ephemeral=True)
            
            is_safe = self.boxes[box_idx]
            
            from core.embeds import EmbedFactory
            if is_safe:
                embed = EmbedFactory.success_embed(f"✨ {self.chosen_player.mention} picked Box {box_idx+1} and it was **SAFE**!")
                await interaction.response.edit_message(embed=embed, view=None)
                await asyncio.sleep(2)
                await self.start_turn(interaction.channel)
            else:
                self.alive_players.remove(self.chosen_player)
                embed = EmbedFactory.create_embed(
                    "BOOM! 💀",
                    f"💥 {self.chosen_player.mention} picked Box {box_idx+1} and it was a **TRAP**! They have been eliminated.",
                    discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=None)
                await asyncio.sleep(2)
                
                if len(self.alive_players) == 1:
                    winner = self.alive_players[0]
                    win_embed = EmbedFactory.success_embed(f"🏆 {winner.mention} is the lone survivor of the Death Wheel!")
                    await interaction.channel.send(embed=win_embed)
                    await self.on_end(None, winner)
                else:
                    await self.start_turn(interaction.channel)
        
        return callback
