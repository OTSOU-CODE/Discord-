import discord
import asyncio
import random
from typing import List, Dict, Optional, Callable

class ReplicaView(discord.ui.View):
    def __init__(self, prompt: str, players: List[discord.Member], on_end: Callable):
        super().__init__(timeout=600)
        self.prompt = prompt
        self.players = players
        self.on_end = on_end
        self.answers: Dict[int, str] = {}
        self.votes: Dict[int, int] = {} # voter -> player_id (who wrote the answer)
        self.state = "answering" # answering, voting

    @discord.ui.button(label="Submit Answer", style=discord.ButtonStyle.primary)
    async def submit_answer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            return await interaction.response.send_message("You are not in the game!", ephemeral=True)
        
        if self.state != "answering":
            return await interaction.response.send_message("Answering time is over!", ephemeral=True)

        class AnswerModal(discord.ui.Modal, title="Your Answer"):
            answer = discord.ui.TextInput(label="Answer", placeholder="Type your funny answer here...", max_length=100)
            
            def __init__(self, parent):
                super().__init__()
                self.parent = parent

            async def on_submit(self, inter: discord.Interaction):
                self.parent.answers[inter.user.id] = self.answer.value
                await inter.response.send_message("Answer submitted! ✅", ephemeral=True)
                
                if len(self.parent.answers) == len(self.parent.players):
                    await self.parent.start_voting(interaction.channel)

        await interaction.response.send_modal(AnswerModal(self))

    async def start_voting(self, channel: discord.TextChannel):
        self.state = "voting"
        self.children[0].disabled = True
        
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "Replica - Voting",
            f"**Prompt:** {self.prompt}\n\nVote for the funniest answer!",
            discord.Color.blue()
        )
        
        view = discord.ui.View()
        # Shuffle answers
        ans_list = list(self.answers.items())
        random.shuffle(ans_list)
        
        for uid, ans in ans_list:
            btn = discord.ui.Button(label=ans, style=discord.ButtonStyle.secondary)
            btn.callback = self.make_vote_callback(uid)
            view.add_item(btn)
            
        await channel.send(embed=embed, view=view)

    def make_vote_callback(self, player_id: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id in self.votes:
                return await interaction.response.send_message("You already voted!", ephemeral=True)
            
            if interaction.user.id == player_id:
                return await interaction.response.send_message("You can't vote for your own answer!", ephemeral=True)
            
            self.votes[interaction.user.id] = player_id
            await interaction.response.send_message("Vote recorded! ✅", ephemeral=True)
            
            if len(self.votes) == len(self.players):
                await self.show_results(interaction.channel)
        
        return callback

    async def show_results(self, channel: discord.TextChannel):
        scores = {pid: 0 for pid in self.answers.keys()}
        for voter_id, voted_id in self.votes.items():
            scores[voted_id] += 1
            
        results_text = f"**Prompt:** {self.prompt}\n\n"
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        for pid, score in sorted_scores:
            user = channel.guild.get_member(pid)
            results_text += f"{user.mention}: {self.answers[pid]} (**{score} votes**)\n"
            
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed("Replica Results", results_text, discord.Color.gold())
        await channel.send(embed=embed)
        await self.on_end(None, channel.guild.get_member(sorted_scores[0][0]))
