import discord
import random
import asyncio
from typing import List, Dict, Optional, Any
from core.game import BaseGame
from core.embeds import EmbedFactory

class MafiaGame(BaseGame):
    def __init__(self, game_id: str, host: discord.Member, channel: discord.TextChannel):
        super().__init__(game_id, host, channel)
        self.players_roles: Dict[int, str] = {}
        self.alive_players: List[int] = []
        self.phase = "setup" # setup, night, day, voting
        self.night_actions: Dict[str, Any] = {"kill": None, "protect": None, "investigate": None}
        self.acted_players: set = set()
        self.votes: Dict[int, int] = {} # voter -> target
        self.phase_duration = 600 # 10 minutes
        self.phase_timer: Optional[asyncio.Task] = None

    async def _start_phase_timer(self, delay: int, callback):
        if self.phase_timer:
            self.phase_timer.cancel()
        
        async def timer_wrapper():
            try:
                await asyncio.sleep(delay)
                await callback()
            except asyncio.CancelledError:
                pass
        
        self.phase_timer = asyncio.create_task(timer_wrapper())

    async def start_mafia(self, players: List[discord.Member]) -> Dict[str, Any]:
        self.players = players
        self.alive_players = [p.id for p in self.players]
        
        # Role distribution
        num_players = len(players)
        num_mafia = max(1, num_players // 4)
        num_doctors = max(1, num_players // 8)
        num_detectives = max(1, num_players // 8)
        num_villagers = num_players - num_mafia - num_doctors - num_detectives
        
        roles = (["mafia"] * num_mafia) + (["doctor"] * num_doctors) + (["detective"] * num_detectives) + (["villager"] * num_villagers)
        random.shuffle(roles)
        
        role_info = {
            "mafia": {"color": discord.Color.red(), "emoji": "🔪", "desc": "You are Mafia. Goal: Kill everyone else."},
            "doctor": {"color": discord.Color.green(), "emoji": "🩺", "desc": "You are the Doctor. Goal: Protect one person each night."},
            "detective": {"color": discord.Color.blue(), "emoji": "🔍", "desc": "You are the Detective. Goal: Investigate one person each night."},
            "villager": {"color": discord.Color.light_gray(), "emoji": "🏘️", "desc": "You are a Villager. Goal: Find and vote out the Mafia."}
        }
        
        print("\n" + "="*40)
        print("🕵️  MAFIA GAME ROLE ASSIGNMENTS 🕵️")
        print("="*40)
        for i, player in enumerate(self.players):
            role_key = roles[i]
            self.players_roles[player.id] = role_key
            print(f"{player.display_name:<20} | {role_key.upper():<12} {role_info[role_key]['emoji']}")
        print("="*40 + "\n")
            
        return role_info

    async def start_night(self, action_callback=None):
        self.phase = "night"
        self.night_actions = {"kill": None, "protect": None, "investigate": None}
        self.acted_players = set()
        await self.channel.send("🌙 **Night falls.**\nEveryone, please close your eyes. The town is silent... Special roles, check the chat to perform your actions!")
        
        # Trigger action requests if a callback is provided
        if action_callback:
            await action_callback(self)
        
        # We wait for actions or timeout (1 minute)
        await self._start_phase_timer(60, self.start_day)

    def record_kill(self, target_id: int):
        self.night_actions["kill"] = target_id

    def record_protect(self, target_id: int):
        self.night_actions["protect"] = target_id

    def record_investigate(self, target_id: int):
        self.night_actions["investigate"] = target_id

    async def record_action(self, player_id: int):
        self.acted_players.add(player_id)
        if await self.check_all_acted():
            if self.phase_timer:
                self.phase_timer.cancel()
                self.phase_timer = None
            await self.channel.send("✨ **All special roles have acted! The sun is rising early...**")
            await self.start_day()

    async def check_all_acted(self) -> bool:
        special_roles = {"mafia", "doctor", "detective"}
        special_players = [pid for pid in self.alive_players if self.players_roles.get(pid) in special_roles]
        if not special_players:
            return False
        return all(pid in self.acted_players for pid in special_players)

    async def reveal_investigation(self):
        target_id = self.night_actions["investigate"]
        if not target_id:
            return
            
        detective_id = next((pid for pid, role in self.players_roles.items() if role == "detective"), None)
        if not detective_id or detective_id not in self.alive_players:
            return
            
        detective = self.channel.guild.get_member(detective_id)
        target = self.channel.guild.get_member(target_id)
        
        if detective and target:
            is_mafia = self.players_roles.get(target_id) == "mafia"
            result = "is Mafia! 🔪" if is_mafia else "is NOT Mafia. 🏘️"
            try:
                await detective.send(f"🔍 **Investigation Result:** {target.display_name} {result}")
            except discord.Forbidden:
                await self.channel.send(f"⚠️ Could not DM the Detective with their result!")

    async def record_vote(self, voter_id: int, target_id: int):
        self.votes[voter_id] = target_id
        if await self.check_all_voted():
            if self.phase_timer:
                self.phase_timer.cancel()
                self.phase_timer = None
            await self.channel.send("🗳️ Everyone has voted! The results are being tallied...")
            await self.resolve_voting()

    async def check_all_voted(self) -> bool:
        return len(self.votes) >= len(self.alive_players)


    async def resolve_voting(self):
        if self.phase != "voting":
            return
        
        if self.phase_timer:
            self.phase_timer.cancel()
            self.phase_timer = None
            
        if not self.votes:
            await self.channel.send("🌅 **Morning comes.** No one was voted out due to lack of votes.")
            await self.start_night(self.action_handler)
            return
        
        # Count votes
        counts = {}
        for target in self.votes.values():
            counts[target] = counts.get(target, 0) + 1
        
        max_votes = max(counts.values())
        candidates = [target for target, count in counts.items() if count == max_votes]
        
        if len(candidates) > 1:
            await self.channel.send("🌅 **Morning comes.** The town is divided and no one was voted out.")
        else:
            voted_out = candidates[0]
            if voted_out in self.alive_players:
                self.alive_players.remove(voted_out)
            
            role = self.players_roles.get(voted_out, "unknown")
            user = self.channel.guild.get_member(voted_out)
            mention = user.mention if user else f"User({voted_out})"
            
            embed = discord.Embed(
                title="🌅 The Town's Verdict",
                description=f"After a heated debate, the town has spoken.\n\n**{mention}** was voted out!",
                color=discord.Color.orange()
            )
            embed.add_field(name="Role Revealed", value=f"They were a **{role.capitalize()}** { '🔪' if role == 'mafia' else '🏘️' }")
            embed.set_footer(text="The town grows smaller, but the truth comes closer.")
            
            await self.channel.send(embed=embed)
        
        if await self.check_win_condition():
            return
        
        await self.start_night(self.action_handler)
 
    async def start_day(self):
        self.phase = "day"
        killed = self.night_actions["kill"]
        protected = self.night_actions["protect"]
        
        # Reveal investigation results to the detective first
        await self.reveal_investigation()
        
        if killed and killed != protected:
            if killed in self.alive_players:
                self.alive_players.remove(killed)
            user = self.channel.guild.get_member(killed)
            mention = user.mention if user else f"User({killed})"
            
            embed = discord.Embed(
                title="🌅 A Grim Morning",
                description=f"The town wakes up to a tragedy...\n\n**{mention}** was killed during the night.",
                color=discord.Color.dark_red()
            )
            embed.set_footer(text="The shadows claim another soul.")
            await self.channel.send(embed=embed)
        else:
            await self.channel.send("🌅 **Morning comes.** The sun rises over a quiet town. No one was killed tonight.")
        
        if await self.check_win_condition():
            return
        
        await self.channel.send(f"🗣️ **Day Time.**\nDiscuss and find the Mafia! You have **1 minute** to debate before voting begins.")
        
        # Wait for discussion duration (1 minute)
        await self._start_phase_timer(60, self.start_voting)

    async def start_voting(self):
        self.phase = "voting"
        self.votes = {}
        await self.channel.send("⏳ Discussion time is over! The town must now cast their votes. Who is the traitor?\nUse `/mafia vote` to cast your vote.")
        
        # Wait for voting duration (60 seconds)
        await self._start_phase_timer(60, self.resolve_voting)


    async def check_win_condition(self) -> bool:
        mafia_alive = [p for p in self.alive_players if self.players_roles[p] == "mafia"]
        town_alive = [p for p in self.alive_players if self.players_roles[p] != "mafia"]
        
        if not mafia_alive:
            await self.channel.send("🏆 **TOWN WINS!** All mafia have been eliminated.")
            return True
        if len(mafia_alive) >= len(town_alive):
            await self.channel.send("🩸 **MAFIA WINS!** They have taken over the town.")
            return True
        return False
