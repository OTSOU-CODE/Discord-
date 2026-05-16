import discord
from typing import List, Optional, Callable, Any

class BaseLobbyView(discord.ui.View):
    def __init__(
        self,
        host: discord.Member,
        game_name: str,
        on_start: Callable,
        min_players: int = 1,
        max_players: Optional[int] = None
    ):
        super().__init__(timeout=600)
        self.host = host
        self.game_name = game_name
        self.on_start = on_start
        self.min_players = min_players
        self.max_players = max_players
        self.players: List[discord.Member] = [host]

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            return await interaction.response.send_message("You are already in the lobby!", ephemeral=True)
        
        if self.max_players and len(self.players) >= self.max_players:
            return await interaction.response.send_message("The lobby is full!", ephemeral=True)
            
        self.players.append(interaction.user)
        await self.update_lobby(interaction)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.host:
            return await interaction.response.send_message("The host cannot leave the lobby. Use Cancel to close it.", ephemeral=True)
            
        if interaction.user not in self.players:
            return await interaction.response.send_message("You are not in the lobby!", ephemeral=True)
            
        self.players.remove(interaction.user)
        await self.update_lobby(interaction)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.blurple)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("Only the host can start the game!", ephemeral=True)
            
        if len(self.players) < self.min_players:
            return await interaction.response.send_message(f"You need at least {self.min_players} players to start!", ephemeral=True)
            
        self.stop()
        await self.on_start(interaction, self.players)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("Only the host can cancel the lobby!", ephemeral=True)
            
        self.stop()
        await interaction.response.edit_message(content="Lobby cancelled.", embed=None, view=None)

    async def update_lobby(self, interaction: discord.Interaction):
        from .embeds import EmbedFactory
        embed = EmbedFactory.game_lobby_embed(
            self.game_name,
            self.host,
            self.players,
            self.max_players
        )
        await interaction.response.edit_message(embed=embed, view=self)
