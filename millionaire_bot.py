import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import asyncio
import random
import os
import re

# ==================== CONFIGURATION ====================
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_TOCKEN")
COMMAND_PREFIX = "!"

# Constants
QUESTIONS_PER_LEVEL = 5
QUESTION_TIMER_SECONDS = 30

# ==================== GAME CLASS ====================
class MillionaireGame:
    def __init__(self, channel_id, host_id):
        self.channel_id = channel_id
        self.host_id = host_id
        self.current_question = 0
        self.questions = []
        self.all_levels = []
        self.active_players = set()
        self.answered_this_round = set()
        self.player_prizes = {}

        self.prize_ladder = [
            100, 200, 300, 400, 500,
            750, 1000, 1500, 2500, 5000,
            7500, 10000, 15000, 20000, 30000,
            50000, 75000, 100000, 150000, 250000,
            350000, 500000, 650000, 800000, 1000000
        ]

    def load_questions(self):
        try:
            # Build an absolute path to the Questions.json file to avoid pathing issues
            script_dir = os.path.dirname(os.path.abspath(__file__))
            questions_path = os.path.join(script_dir, "Questions.json")

            with open(questions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.all_levels = data

                level_map = {1: [], 2: [], 3: [], 4: [], 5: []}
    
                for block in data:
                    level_name = block.get("levelName", "")
                    # Use regex to find the first number for more robust level detection
                    match = re.search(r'\d+', level_name)
                    if match:
                        lvl = int(match.group(0))
                        if lvl in level_map:
                            level_map[lvl].extend(block.get("questions", []))
    
                self.questions = []
                for lvl in range(1, 6):
                    if level_map[lvl]:
                        num_to_pick = min(QUESTIONS_PER_LEVEL, len(level_map[lvl]))
                        self.questions.extend(random.sample(level_map[lvl], num_to_pick))
                
                # Ensure the number of questions does not exceed the prize ladder
                self.questions = self.questions[:len(self.prize_ladder)]
            return True

        except Exception as e:
            print("Error loading questions:", e)
            return False

    def get_current_question(self):
        if self.current_question < len(self.questions):
            return self.questions[self.current_question]
        return None

    def get_current_prize(self):
        return self.prize_ladder[self.current_question]

# ==================== VIEW CLASSES ====================
class JoinView(View):
    def __init__(self, game):
        super().__init__(timeout=300)
        self.game = game
        self.game_started = False

    async def update_embed(self, interaction):
        players = "\n".join([f"<@{p}>" for p in self.game.active_players]) or "None yet..."
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="Players Joined", value=players, inline=False)
        await interaction.message.edit(embed=embed)

    @discord.ui.button(label="Join Game", style=discord.ButtonStyle.green, emoji="✅")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in self.game.active_players:
            self.game.active_players.add(interaction.user.id)
            await interaction.response.defer()
            await self.update_embed(interaction)
            await interaction.followup.send("You have joined the game!", ephemeral=True)
        else:
            await interaction.response.send_message("You are already in the game.", ephemeral=True)

    @discord.ui.button(label="Start Game", style=discord.ButtonStyle.primary, emoji="🎮")
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.game.host_id:
            await interaction.response.send_message("Only the host can start the game.", ephemeral=True)
            return

        if not self.game.active_players:
            await interaction.response.send_message("No players have joined yet!", ephemeral=True)
            return

        self.game_started = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"🎮 Starting game with **{len(self.game.active_players)} players**!")
        self.stop()

class QuestionView(View):
    def __init__(self, game, bot_instance: commands.Bot):
        super().__init__(timeout=QUESTION_TIMER_SECONDS)
        self.game = game
        self.bot = bot_instance
        self.correct_users = []
        self.wrong_users = []
        self.correct_answer = game.get_current_question()["correctAnswer"]
        self.options = game.get_current_question()["options"]

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        for i, option_text in enumerate(self.options):
            button = Button(label=option_text, style=discord.ButtonStyle.secondary, emoji=emojis[i])
            button.callback = self.create_callback(option_text)
            self.add_item(button)

    def create_callback(self, chosen_option):
        async def button_callback(interaction: discord.Interaction):
            user = interaction.user
            if user.id in self.game.active_players and user.id not in self.game.answered_this_round:
                self.game.answered_this_round.add(user.id)
                if chosen_option == self.correct_answer:
                    self.correct_users.append(user)
                else:
                    self.wrong_users.append(user)
                
                await interaction.response.send_message("Your answer has been locked in!", ephemeral=True)

                if len(self.game.answered_this_round) >= len(self.game.active_players):
                    self.stop()
            else:
                await interaction.response.send_message("You are not in this game or have already answered.", ephemeral=True)
        return button_callback

    async def on_timeout(self):
        game = self.game
        for player_id in list(game.active_players):
            if player_id not in game.answered_this_round:
                try:
                    user = await self.bot.fetch_user(player_id)
                    self.wrong_users.append(user)
                except discord.NotFound:
                    game.active_players.remove(player_id)
        
        for item in self.children:
            item.disabled = True

class ReplayView(View):
    def __init__(self, cog, original_ctx):
        super().__init__(timeout=60.0)
        self.cog = cog
        self.original_ctx = original_ctx

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.success, emoji="🔄")
    async def replay_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(f"🔄 Restarting game at the request of {interaction.user.mention}...")
        self.stop()
        await self.cog.start_game(self.original_ctx)

# ==================== GAME COG ====================
class GameCog(commands.Cog, name="Game"):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @commands.command(name="millionaire")
    async def start_game(self, ctx):
        if ctx.channel.id in self.active_games:
            await ctx.send("❌ A game is already running here!")
            return

        game = MillionaireGame(ctx.channel.id, ctx.author.id)

        if not game.load_questions():
            await ctx.send("❌ Could not load Questions.json!")
            return

        self.active_games[ctx.channel.id] = game

        embed = discord.Embed(
            title="💰 WHO WANTS TO BE A MILLIONAIRE?",
            description=f"Host: {ctx.author.mention}\nClick **✅** to join!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Players Joined", value="None yet...", inline=False)
        embed.set_footer(text="Host must click 🎮 to start the game.")

        join_view = JoinView(game)
        message = await ctx.send(embed=embed, view=join_view)
        
        await join_view.wait()

        if not join_view.game_started:
            await message.edit(content="Game timed out and did not start.", embed=None, view=None)
            del self.active_games[ctx.channel.id]
            return

        await asyncio.sleep(2)
        await self.send_question(ctx)

    async def send_question(self, ctx):
        game = self.active_games.get(ctx.channel.id)
        if not game:
            return

        if len(game.active_players) == 0:
            await self.end_game(ctx, False)
            return

        q = game.get_current_question()
        if not q:
            await self.end_game(ctx, True)
            return

        game.answered_this_round.clear()

        number = game.current_question + 1

        embed = discord.Embed(
            title=f"📘 Question {number}/25 – Prize: ${game.get_current_prize():,}",
            description=q["questionText"],
            color=discord.Color.blue()
        )

        players = "\n".join([f"<@{p}>" for p in game.active_players])
        embed.add_field(name=f"🎮 Active Players ({len(game.active_players)})", value=players, inline=False)
        embed.set_footer(text=f"You have {QUESTION_TIMER_SECONDS} seconds to answer!")

        question_view = QuestionView(game, self.bot)
        question_message = await ctx.send(embed=embed, view=question_view)

        await question_view.wait()

        for item in question_view.children:
            item.disabled = True
        await question_message.edit(view=question_view)

        correct_users = question_view.correct_users
        wrong_users = question_view.wrong_users

        for user in wrong_users:
            if user.id in game.active_players:
                prize = game.prize_ladder[game.current_question - 1] if game.current_question > 0 else 0
                game.player_prizes[user.id] = prize
                game.active_players.remove(user.id)

        result = discord.Embed(title="📊 Results", color=discord.Color.gold())
        result.add_field(name="Correct Answer", value=f"**{q['correctAnswer']}**", inline=False)
        
        correct_mentions = "\n".join([u.mention for u in correct_users])
        if correct_mentions:
            result.add_field(name="✅ Correct Players", value=correct_mentions, inline=True)
        else:
            result.add_field(name="✅ Correct Players", value="None", inline=True)

        wrong_mentions = "\n".join([u.mention for u in wrong_users])
        if wrong_mentions:
            result.add_field(name="❌ Eliminated", value=wrong_mentions, inline=True)
        else:
            result.add_field(name="❌ Eliminated", value="None", inline=True)

        await ctx.send(embed=result)

        if len(game.active_players) == 0:
            await self.end_game(ctx, False)
        else:
            game.current_question += 1
            await asyncio.sleep(2)
            await self.send_question(ctx)

    async def end_game(self, ctx, won: bool):
        game = self.active_games.get(ctx.channel.id)
        if not game:
            return

        if won:
            embed = discord.Embed(
                title="🎉 YOU WIN!",
                description="You reached **$1,000,000**!",
                color=discord.Color.green()
            )
            winners = "\n".join([f"<@{uid}>" for uid in game.active_players])
            embed.add_field(name="Millionaires", value=winners)
        else:
            embed = discord.Embed(
                title="💀 All Players Eliminated!",
                description="Final player winnings:",
                color=discord.Color.red()
            )

            prize_list = "\n".join(
                [f"💰 <@{pid}> — **${amount:,}**" for pid, amount in game.player_prizes.items()]
            ) if game.player_prizes else "No prize data."

            embed.add_field(name="Final Results", value=prize_list, inline=False)

        replay_view = ReplayView(self, ctx)
        await ctx.send(embed=embed, view=replay_view)
        del self.active_games[ctx.channel.id]

    @commands.command(name="stopgame")
    async def stop_game(self, ctx):
        if ctx.channel.id in self.active_games:
            del self.active_games[ctx.channel.id]
            await ctx.send("🛑 Game stopped.")
        else:
            await ctx.send("No game running here.")

    @commands.command(name="givehost", help="Transfers game host ownership to another member. Usage: !givehost @member")
    async def give_host(self, ctx, new_host: discord.Member = None):
        """Transfers host ownership to another member."""
        game = self.active_games.get(ctx.channel.id)
        if not game:
            await ctx.send("There is no game currently running in this channel.")
            return

        if ctx.author.id != game.host_id:
            await ctx.send("Only the current host can transfer ownership.")
            return

        if new_host is None:
            await ctx.send("Please mention a member to transfer host ownership to. Usage: `!givehost @member`")
            return

        if new_host.bot:
            await ctx.send("You cannot give host ownership to a bot.")
            return

        game.host_id = new_host.id
        await ctx.send(f"👑 Host ownership has been transferred to {new_host.mention}.")

# ==================== BOT SETUP ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"✅ Bot is online as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Command prefix: {COMMAND_PREFIX}")
    print(f"Connected to {len(bot.guilds)} server(s)")
    print("=" * 50)
    print(f"Use command: {COMMAND_PREFIX}millionaire")
    print("=" * 50)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    else:
        print(f"Error: {error}")
        await ctx.send(f"❌ An error occurred: {error}")

# ==================== MAIN ====================
async def main():
    async with bot:
        await bot.add_cog(GameCog(bot))
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Check if token is set
    if not TOKEN:
        print("=" * 50)
        print("❌ ERROR: Bot token not found!")
        print("=" * 50)
        print("Make sure you have a .env file with one of these:")
        print("  TOKEN=your_bot_token_here")
        print("  BOT_TOKEN=your_bot_token_here")
        print("  DISCORD_TOKEN=your_bot_token_here")
        print("=" * 50)
        exit(1)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested")
    except Exception as e:
        print(f"❌ Fatal error: {e}")