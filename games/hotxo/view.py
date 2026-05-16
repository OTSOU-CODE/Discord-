import discord
import random
from typing import List, Optional, Callable, Dict

class HotXOView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member, on_win: Callable, on_draw: Callable):
        super().__init__(timeout=300)
        self.p1 = p1
        self.p2 = p2
        self.turn = p1
        self.board = [" " for _ in range(9)]
        # Track history of moves for each player: player_id -> list of board indices
        self.move_history: Dict[int, List[int]] = {p1.id: [], p2.id: []}
        self.buttons: List[discord.ui.Button] = []
        self.on_win = on_win
        self.on_draw = on_draw
        self.game_over = False

        for i in range(9):
            button = discord.ui.Button(label="\u200b", style=discord.ButtonStyle.secondary, row=i // 3)
            button.callback = self.make_callback(i)
            self.buttons.append(button)
            self.add_item(button)

    def make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if self.game_over:
                return
            
            if interaction.user != self.turn:
                return await interaction.response.send_message("It's not your turn!", ephemeral=True)
            
            if self.board[index] != " ":
                return await interaction.response.send_message("This spot is already taken!", ephemeral=True)
            
            symbol = "❌" if self.turn == self.p1 else "⭕"
            self.board[index] = symbol
            
            # Record move
            self.move_history[self.turn.id].append(index)
            
            msg = ""
            # Every fourth move, the first is inflamed and deleted
            if len(self.move_history[self.turn.id]) > 3:
                old_move = self.move_history[self.turn.id].pop(0)
                self.board[old_move] = " "
                msg = f"🔥 Your oldest mark at position {old_move+1} was inflamed and deleted!"
            
            self.update_all_buttons()
            
            winner_symbol = self.check_winner()
            if winner_symbol:
                self.game_over = True
                self.disable_all()
                winner = self.p1 if winner_symbol == "❌" else self.p2
                await self.on_win(interaction, winner, msg)
                return
            
            self.turn = self.p2 if self.turn == self.p1 else self.p1
            await self.update_board_status(interaction, msg)

        return callback

    def update_all_buttons(self):
        for i in range(9):
            symbol = self.board[i]
            btn = self.buttons[i]
            
            # Check if this is the oldest mark of the current player (about to be deleted)
            # Actually user said "every fourth move the first is inflamed", 
            # so I'll just show current board state.
            
            if symbol == " ":
                btn.label = "\u200b"
                btn.style = discord.ButtonStyle.secondary
                btn.disabled = False
            else:
                btn.label = symbol
                btn.style = discord.ButtonStyle.danger if symbol == "❌" else discord.ButtonStyle.primary
                btn.disabled = True

    def check_winner(self) -> Optional[str]:
        b = self.board
        lines = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for l in lines:
            if b[l[0]] == b[l[1]] == b[l[2]] != " ":
                return b[l[0]]
        return None

    def disable_all(self):
        for b in self.buttons:
            b.disabled = True

    async def update_board_status(self, interaction: discord.Interaction, status: str):
        symbol = "❌" if self.turn == self.p1 else "⭕"
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "HotXO Game",
            f"{status}\n\n**Turn:** {self.turn.mention} ({symbol})"
        )
        await interaction.response.edit_message(embed=embed, view=self)
