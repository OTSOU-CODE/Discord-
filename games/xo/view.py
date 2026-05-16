import discord
from typing import List, Optional, Callable

class XOView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member, on_win: Callable, on_draw: Callable):
        super().__init__(timeout=300)
        self.p1 = p1
        self.p2 = p2
        self.turn = p1
        self.board = [" " for _ in range(9)]
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
            
            symbol = "❌" if self.turn == self.p1 else "⭕"
            self.board[index] = symbol
            
            button = self.buttons[index]
            button.label = symbol
            button.style = discord.ButtonStyle.danger if symbol == "❌" else discord.ButtonStyle.primary
            button.disabled = True
            
            winner_symbol = self.check_winner()
            if winner_symbol:
                self.game_over = True
                self.disable_all()
                winner = self.p1 if winner_symbol == "❌" else self.p2
                await self.on_win(interaction, winner, self.board)
                return
            
            if " " not in self.board:
                self.game_over = True
                self.disable_all()
                await self.on_draw(interaction, self.board)
                return
            
            self.turn = self.p2 if self.turn == self.p1 else self.p1
            await self.update_board(interaction)

        return callback

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

    async def update_board(self, interaction: discord.Interaction):
        symbol = "❌" if self.turn == self.p1 else "⭕"
        from core.embeds import EmbedFactory
        embed = EmbedFactory.create_embed(
            "XO Game",
            f"**Turn:** {self.turn.mention} ({symbol})"
        )
        await interaction.response.edit_message(embed=embed, view=self)
