import discord
from discord import app_commands
from discord.ext import commands
from core.views import BaseLobbyView
from core.embeds import EmbedFactory
from .game import MafiaGame
import random
import asyncio
from typing import Dict, List

class RoleRevealView(discord.ui.View):
    def __init__(self, players_roles: dict, role_info: dict):
        super().__init__(timeout=60)
        self.players_roles = players_roles
        self.role_info = role_info

    @discord.ui.button(label="VIEW MY ROLE 🎭", style=discord.ButtonStyle.blurple)
    async def view_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_key = self.players_roles.get(interaction.user.id)
        if not role_key:
            return await interaction.response.send_message("You are not in this game!", ephemeral=True)
            
        info = self.role_info[role_key]
        embed = EmbedFactory.create_embed(
            f"YOUR ROLE: {role_key.upper()} {info['emoji']}",
            info['desc'],
            info['color']
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class NightActionView(discord.ui.View):
    def __init__(self, game: MafiaGame, action_type: str, player_id: int):
        super().__init__(timeout=300)
        self.game = game
        self.action_type = action_type
        self.player_id = player_id

    @discord.ui.select(placeholder="Choose a target...", options=[])
    async def select_target(self, interaction: discord.Interaction, select: discord.ui.Select):
        target_id = int(select.values[0])
        if self.action_type == "kill":
            self.game.record_kill(target_id)
        elif self.action_type == "protect":
            self.game.record_protect(target_id)
        elif self.action_type == "investigate":
            self.game.record_investigate(target_id)
        
        await self.game.record_action(self.player_id)
        
        member = self.game.channel.guild.get_member(target_id)
        name = member.display_name if member else f"Unknown User({target_id})"
        await interaction.response.send_message(f"✔️ **Action recorded!** You have chosen {name}.\nYour choice has been noted in the shadows. Now, wait for the dawn...", ephemeral=True)
        self.stop()

    async def update_options(self):
        options = []
        for pid in self.game.alive_players:
            if self.action_type == "kill" and pid == self.player_id:
                continue
            member = self.game.channel.guild.get_member(pid)
            name = member.display_name if member else f"User({pid})"
            options.append(discord.SelectOption(label=name, value=str(pid)))
        self.children[0].options = options

class NightActionPortalView(discord.ui.View):
    def __init__(self, game: MafiaGame, action_handler):
        super().__init__(timeout=300)
        self.game = game
        self.action_handler = action_handler

    async def create_action_view(self, interaction: discord.Interaction, role: str):
        action_type = None
        if role == "mafia": action_type = "kill"
        elif role == "doctor": action_type = "protect"
        elif role == "detective": action_type = "investigate"
        
        if not action_type:
            return await interaction.response.send_message("💤 You are a villager. You must sleep through the night.", ephemeral=True)
            
        view = NightActionView(self.game, action_type, interaction.user.id)
        await view.update_options()
        await interaction.response.send_message(f"🌙 **{role.capitalize()} Action**\nChoose your target for tonight!", view=view, ephemeral=True)

    @discord.ui.button(label="Mafia Action 🔪", style=discord.ButtonStyle.danger)
    async def mafia_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = self.game.players_roles.get(interaction.user.id)
        if role != "mafia":
            return await interaction.response.send_message("❌ You are not the Mafia!", ephemeral=True)
        await self.create_action_view(interaction, "mafia")

    @discord.ui.button(label="Doctor Action 🩺", style=discord.ButtonStyle.success)
    async def doctor_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = self.game.players_roles.get(interaction.user.id)
        if role != "doctor":
            return await interaction.response.send_message("❌ You are not the Doctor!", ephemeral=True)
        await self.create_action_view(interaction, "doctor")

    @discord.ui.button(label="Detective Action 🔍", style=discord.ButtonStyle.primary)
    async def detective_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = self.game.players_roles.get(interaction.user.id)
        if role != "detective":
            return await interaction.response.send_message("❌ You are not the Detective!", ephemeral=True)
        await self.create_action_view(interaction, "detective")

class MafiaCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Game state is now managed by self.bot.game_manager

    @app_commands.command(name="mafia_ping", description="Test the Mafia cog.")
    async def mafia_ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Mafia cog is online! 🕵️", ephemeral=True)

    @app_commands.command(name="mafia", description="Start a game of Mafia.")
    async def mafia(self, interaction: discord.Interaction):
        async def start_game(inter, players):
            # Players: 5-20 checked by lobby view
            await inter.response.edit_message(content="**MAFIA GAME STARTING!** Everyone, click the button below to see your role.", embed=None, view=None)
            
            game = MafiaGame(str(random.randint(1000, 9999)), interaction.user, inter.channel)
            role_info = await game.start_mafia(players)
            
            # Store the action handler in the game object so it can be called in subsequent nights
            game.action_handler = self.handle_night_actions
            
            # Register game in the manager
            await self.bot.game_manager.register_game(game)
            
            reveal_view = RoleRevealView(game.players_roles, role_info)
            msg = await inter.channel.send("🎭 **ROLE REVEAL PHASE**\nYour secret identity awaits... Click the button below to discover who you are in the shadows!", view=reveal_view)
            
            # Wait 15 seconds for people to see their roles before starting night
            await asyncio.sleep(15)
            await msg.delete()
            
            # Start night and trigger action portal in chat
            await game.start_night(self.handle_night_actions)
 
        lobby = BaseLobbyView(interaction.user, "Mafia", start_game, min_players=5, max_players=20)
        embed = EmbedFactory.game_lobby_embed(
            "Mafia", 
            interaction.user, 
            [interaction.user], 
            max_players=20,
            rules="1. 5-20 Players.\n2. Roles assigned instantly.\n3. 10 minute phases.\n4. View your role via the button in chat!"
        )
        await interaction.response.send_message(embed=embed, view=lobby)

    async def handle_night_actions(self, game: MafiaGame):
        # Use the Portal View to let special roles claim their action in the channel
        view = NightActionPortalView(game, self.handle_night_actions)
        await game.channel.send("🕵️ **Night Action Portal**\nSpecial roles, please click your respective button below to perform your secret actions!", view=view)

    @app_commands.command(name="vote", description="Vote for someone to be eliminated from the Mafia game.")
    @app_commands.guild_only()
    async def vote(self, interaction: discord.Interaction, target: discord.Member):
        game = self.bot.game_manager.get_game_in_channel(interaction.channel_id)
        
        if not game:
            return await interaction.response.send_message("There is no active Mafia game in this channel!", ephemeral=True)
        
        if game.phase != "voting":
            return await interaction.response.send_message("It is not currently voting time!", ephemeral=True)
        
        if interaction.user.id not in game.alive_players:
            return await interaction.response.send_message("You are already dead and cannot vote!", ephemeral=True)
        
        if target.id not in game.alive_players:
            return await interaction.response.send_message("That person is already dead or not in the game!", ephemeral=True)
            
        if target.id == interaction.user.id:
            return await interaction.response.send_message("You cannot vote for yourself!", ephemeral=True)
  
        await game.record_vote(interaction.user.id, target.id)
        await interaction.response.send_message(f"🗳️ Your vote for {target.display_name} has been recorded!", ephemeral=True)

 
    @app_commands.command(name="resolve_vote", description="Force resolve the voting phase (Admin/Host only).")
    @app_commands.guild_only()
    async def resolve_vote(self, interaction: discord.Interaction):
        game = self.bot.game_manager.get_game_in_channel(interaction.channel_id)
        
        if not game:
            return await interaction.response.send_message("There is no active Mafia game in this channel!", ephemeral=True)
            
        if game.phase != "voting":
            return await interaction.response.send_message("The game is not in the voting phase!", ephemeral=True)
            
        if interaction.user.id != game.host.id:
            return await interaction.response.send_message("Only the game host can force resolve votes!", ephemeral=True)
            
        await interaction.response.send_message("Resolving votes...")
        await game.resolve_voting()


async def setup(bot):
    await bot.add_cog(MafiaCommands(bot))
