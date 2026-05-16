import discord
import random
import asyncio
from typing import List, Dict, Optional, Callable

class HideSeekView(discord.ui.View):
    def __init__(self, players: List[discord.Member], on_end: Callable):
        super().__init__(timeout=600)
        self.players = players
        self.on_end = on_end
        self.hiding_places = ["Tree", "Box", "Closet", "Bed", "Curtain"]
        self.alive_hiders: List[discord.Member] = []
        self.hider_locations: Dict[int, str] = {}
        self.seeker: Optional[discord.Member] = None
        self.state = "hiding" # hiding, seeking

    async def start_round(self, channel: discord.TextChannel):
        self.state = "hiding"
        self.hider_locations = {}
        self.clear_items()
        
        # Randomly assign seeker
        self.seeker = random.choice(self.players)
        self.alive_hiders = [p for p in self.players if p != self.seeker]
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Hide and Seek",
            f"🕵️ **{self.seeker.mention} is the seeker!**\nEveryone else, click the button to choose your hiding spot!",
            discord.Color.blue()
        )
        
        hide_btn = discord.ui.Button(label="CHOOSE SPOT 🚪", style=discord.ButtonStyle.success)
        hide_btn.callback = self.hide_callback
        self.add_item(hide_btn)
        
        self.msg = await channel.send(embed=embed, view=self)

    async def hide_callback(self, interaction: discord.Interaction):
        if interaction.user == self.seeker:
            return await interaction.response.send_message("You are the seeker! Wait for hiders.", ephemeral=True)
        
        if self.state != "hiding":
            return await interaction.response.send_message("Hiding time is over!", ephemeral=True)
            
        view = discord.ui.View()
        select = discord.ui.Select(placeholder="Choose a hiding place", options=[
            discord.SelectOption(label=p) for p in self.hiding_places
        ])
        
        async def select_callback(inter: discord.Interaction):
            self.hider_locations[inter.user.id] = select.values[0]
            await inter.response.edit_message(content=f"You are hidden in the **{select.values[0]}**! 🤫", view=None)
            
            if len(self.hider_locations) == len(self.alive_hiders):
                await self.start_seeking(interaction.channel)

        select.callback = select_callback
        view.add_item(select)
        await interaction.response.send_message("Choose your hiding place:", view=view, ephemeral=True)

    async def start_seeking(self, channel: discord.TextChannel):
        self.state = "seeking"
        self.clear_items()
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Hide and Seek - Seeking Time!",
            f"🕵️ **{self.seeker.mention} is now seeking!**\nSeeker, pick a spot to check.",
            discord.Color.orange()
        )
        
        for place in self.hiding_places:
            btn = discord.ui.Button(label=f"Check {place}", style=discord.ButtonStyle.secondary)
            btn.callback = self.make_search_callback(place)
            self.add_item(btn)
            
        await self.msg.edit(embed=embed, view=self)

    def make_search_callback(self, place: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.seeker:
                return await interaction.response.send_message("Only the seeker can search!", ephemeral=True)
            
            found_ids = [hid for hid, loc in self.hider_locations.items() if loc == place]
            found_members = [interaction.guild.get_member(uid) for uid in found_ids]
            
            from core.embeds import EmbedFactory
            if found_members:
                mentions = ", ".join([m.mention for m in found_members])
                # These players are kicked (removed from players list)
                for m in found_members:
                    self.players.remove(m)
                
                res_embed = EmbedFactory.create_embed(
                    "GOTCHA! 🔎",
                    f"🔎 {self.seeker.mention} searched the **{place}** and found: {mentions}!\nThey have been eliminated.",
                    discord.Color.red()
                )
            else:
                res_embed = EmbedFactory.create_embed(
                    "Empty Spot 🔎",
                    f"🔎 {self.seeker.mention} searched the **{place}** but it was empty.",
                    discord.Color.blue()
                )
            
            await interaction.response.send_message(embed=res_embed)
            
            # Check win condition
            if len(self.players) <= 2: # One seeker, one hider left (or just seeker)
                 # Actually user said "Remaining players wins if one spot or player is remaining"
                 # I'll interpret as: if only one hider remains, they win? Or if seeker finds everyone, seeker wins.
                 # Let's say if seeker finds everyone, seeker wins. If hider(s) remain after all spots checked? 
                 # User said "Remaining players wins if one spot or player is remaining".
                 # I'll just end when only 1 player or 1 spot is left as requested.
                 
                 winner = self.players[0] if len(self.players) == 1 else None # Should be at least seeker
                 win_text = f"🏆 Game over! "
                 if len(self.players) > 1:
                     win_text += "Hiders survived!"
                 else:
                     win_text += f"{self.seeker.mention} found everyone!"
                 
                 win_embed = EmbedFactory.success_embed(win_text)
                 await interaction.channel.send(embed=win_embed)
                 await self.on_end(None, winner)
            else:
                # Next round? User said "Each round a seeker is randomly assigned"
                # So we reset and start again with remaining players
                await asyncio.sleep(3)
                await self.start_round(interaction.channel)
        
        return callback
