import os
import discord
import logging
from discord.ext import commands
from dotenv import load_dotenv
from hezz_game import HezzGame

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Logging Setup
if not os.path.exists("LOG"):
    os.makedirs("LOG")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("LOG/game.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- UI THEME COLORS ---
class Theme:
    PRIMARY = 0xC19A6B  # Desert Sand / Gold-ish
    SECONDARY = 0x8D0909 # Deep Red (Moroccan Style)
    ACCENT = 0x006233    # Emerald Green (Moroccan Flag Green)
    
    # Suits
    OROS = 0xFFD700    # Gold
    COPAS = 0xDC143C   # Crimson
    ESPADAS = 0x4169E1 # Royal Blue
    BASTOS = 0x228B22  # Forest Green

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Game State Management
# Mapping channel_id -> Game Instance
games = {}

import re

def sanitize_name(name):
    # Keep alpha-numeric, spaces, underscores, dashes
    # Remove anything else
    safe = re.sub(r'[^\w\s-]', '', name).strip()
    if not safe:
        return "UnknownPlayer"
    return safe

class LobbyView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.players = [] # List of unique (user_id, name)
    
    @discord.ui.button(label="Join Game", style=discord.ButtonStyle.green, custom_id="join_game")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        if any(p[0] == user.id for p in self.players):
            await interaction.response.send_message("You are already in the lobby!", ephemeral=True)
            return
        
        if len(self.players) >= 4:
            await interaction.response.send_message("Lobby is full! (Max 4 players)", ephemeral=True)
            return

        self.players.append((user.id, user.display_name))
        
        # Embed for Join
        embed = discord.Embed(
            title="✨ Lobby Update", 
            description=f"**{user.display_name}** has joined the game!", 
            color=discord.Color(Theme.ACCENT) # Green for join
        )
        embed.add_field(name="Current Players", value=f"{len(self.players)}/4", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)
        logger.info(f"Player joined lobby: {user.display_name} (ID: {user.id})")
    
    @discord.ui.button(label="Start Game", style=discord.ButtonStyle.blurple, custom_id="start_game")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Only the lobby creator can start the game.", ephemeral=True)
            return
        
        if len(self.players) < 2: # Min 2 players
            await interaction.response.send_message("Need at least 2 players to start!", ephemeral=True)
            return

        await interaction.response.send_message("Starting game...", ephemeral=True)
        self.stop()
        
        # Initialize Game with SAFE names
        channel_id = interaction.channel_id
        
        game_player_names = []
        user_map = {} # SafeName -> UserID
        
        # Track used names to handle duplicates/collisions after sanitization
        # e.g. "User!!!" and "User???" both become "User"
        used_safe_names = set()
        
        for uid, dname in self.players:
            safe = sanitize_name(dname)
            if not safe: safe = f"Player{uid}"
            
            # Uniquify if needed
            original_safe = safe
            counter = 1
            while safe in used_safe_names:
                safe = f"{original_safe}{counter}"
                counter += 1
            
            used_safe_names.add(safe)
            game_player_names.append(safe)
            user_map[safe] = uid
        
        game_instance = HezzGame(game_player_names)
        games[channel_id] = {
            'game': game_instance,
            'user_map': user_map,
            'channel': interaction.channel,
            'last_turn_msg': None # Track last turn message to delete it
        }
        
        logger.info(f"Game Started in Channel {channel_id} with players: {game_player_names}")
        await start_game_flow(channel_id)

async def start_game_flow(channel_id):
    session = games.get(channel_id)
    if not session:
        return

    game = session['game']
    channel = session['channel']
    user_map = session['user_map']

    # Game already initializes and deals in __init__
    # Images are already generated: "hand_Name.webp" and "center_card.webp"

    # Send Center Card to Channel
    try:
        center_file = discord.File("center_card.webp", filename="center_card.webp")
        embed = discord.Embed(
            title="🎮 Game Started! 🚀", 
            description=f"Top Card: **{game.discard_pile[-1]}**", 
            color=discord.Color(Theme.PRIMARY) # Theme Gold
        )
        embed.set_image(url="attachment://center_card.webp")
        embed.set_footer(text="Let the Hezz begin!")
        await channel.send(file=center_file, embed=embed)
    except Exception as e:
        await channel.send(f"⚠️ Error sending center card: {e}")

    # Prompt first player
    await prompt_next_player(channel_id)

async def prompt_next_player(channel_id):
    session = games.get(channel_id)
    game = session['game']
    channel = session['channel']
    
    current_player = game.get_current_player()
    
    # Send a public embed with "Play Turn" button
    embed = discord.Embed(
        title=f"⏳ {current_player.name}'s Turn", 
        description="👉 It is your turn! Check your hand and play a card.",
        color=discord.Color(Theme.SECONDARY) # Red for "Action Needed"
    )
    view = TurnView(game, current_player, session['user_map'])
    
    # Add context: Show the current top card in thumbnail
    # We need to re-send the file or use a previously sent one? 
    # Discord attachments are tricky. Safest is to attach it again or just rely on the previous message.
    # However, for "Modern" look, re-attaching a small thumbnail is nice.
    try:
        center_file = discord.File("center_card.webp", filename="center_card_thumb.webp")
        embed.set_thumbnail(url="attachment://center_card_thumb.webp")
        embed.set_footer(text=f"Current Top Card: {game.discard_pile[-1]}")
        
        # CLEANUP: Delete previous turn message to reduce clutter
        if session.get('last_turn_msg'):
            try:
                await session['last_turn_msg'].delete()
            except: 
                pass # Already deleted or permission error
                
        msg = await channel.send(file=center_file, embed=embed, view=view)
        session['last_turn_msg'] = msg
        
    except:
        # CLEANUP (Fallback)
        if session.get('last_turn_msg'):
            try: await session['last_turn_msg'].delete()
            except: pass
            
        msg = await channel.send(embed=embed, view=view)
        session['last_turn_msg'] = msg

class TurnView(discord.ui.View):
    def __init__(self, game, current_player, user_map):
        super().__init__(timeout=None)
        self.game = game
        self.current_player = current_player
        self.user_map = user_map
        self.user_id = user_map.get(current_player.name)

    @discord.ui.button(label="Check Hand / Actions 🃏", style=discord.ButtonStyle.blurple, custom_id="play_turn")
    async def play_turn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # We allow ANYONE to click this now
        # But only the current player gets the CONTROLS
        
        # Determine who clicked
        clicker_name = interaction.user.display_name
        # Find player object by mapping (reverse lookup needed or iterate players)
        # We stored simple map: Name -> ID. We need ID -> Name/Player
        # Actually, self.game.players has Player objects. We can match by Name if Discord Name used.
        # But easier: We check ID vs Current Player ID.
        
        is_current_player = (interaction.user.id == self.user_id)
        
        # Defer ephemeral
        await interaction.response.defer(ephemeral=True)
        
        # Logic:
        # If Current Player -> Show Hand + Controls
        # If Other Player -> Show Hand + "Wait your turn"
        
        try:
            # We need to find the "Clicking Player" to get their hand image
            # Warning: "hand_Name.webp" depends on sanitized name. 
            # Ideally we'd have a lookup. 
            # For now, let's try to assume map works or just check current player.
            
            # If current player, easy:
            if is_current_player:
                hand_file = discord.File(f"hand_{self.current_player.name}.webp", filename="hand.webp")
                view = GameControls(self.game, self.current_player, self.user_map)
                await interaction.followup.send(
                    content=f"**Your Hand** (It IS your turn!):\nSelect an action below:", 
                    file=hand_file, 
                    view=view,
                    ephemeral=True
                )
            else:
                # Non-active player: Show THEIR hand, but no controls
                # Find the player object for the clicker
                clicker_player = None
                for p in self.game.players:
                    if self.user_map.get(p.name) == interaction.user.id:
                        clicker_player = p
                        break
                
                if clicker_player:
                    hand_file = discord.File(f"hand_{clicker_player.name}.webp", filename="hand.webp")
                    await interaction.followup.send(
                        content=f"� **Your Hand** (Waiting for {self.current_player.name}...):", 
                        file=hand_file, 
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        content="You are not in this game!",
                        ephemeral=True
                    )
                
        except Exception as e:
            await interaction.followup.send(f"Error loading view: {e}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error loading hand: {e}", ephemeral=True)



class GameControls(discord.ui.View):
    def __init__(self, game, current_player, user_map):
        super().__init__(timeout=180)
        self.game = game
        self.current_player = current_player
        self.user_map = user_map
        self.user_id = user_map.get(current_player.name)

        # Add Play Card Select Menu
        self.add_item(CardSelect(game, current_player))

    @discord.ui.button(label="Draw Card", style=discord.ButtonStyle.primary, custom_id="draw_card")
    async def draw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Already verified user in TurnView, but logic is safe to keep
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        
        # Defer updates to the ephemeral view
        await interaction.response.defer(ephemeral=True)
            
        # Execute Draw with smart logic (Penalty handling)
        msg = self.game.draw_card_action(self.current_player)
        
        # Public Announce via Embed
        embed = discord.Embed(
            description=f"📥 **{self.current_player.name}** drew a card from the deck.", 
            color=discord.Color(Theme.PRIMARY)
        )
        await interaction.channel.send(embed=embed)
        
        # Update Private View (show new hand or just confirm)
        # using edit_original_response since we deferred
        try:
            hand_file = discord.File(f"hand_{self.current_player.name}.webp", filename="hand.webp")
            await interaction.edit_original_response(content=f"{msg} Turn ended.", attachments=[hand_file], view=None)
        except:
             await interaction.edit_original_response(content=f"{msg} Turn ended.", view=None)

        # End turn
        self.game.next_turn()
        # self.stop()
        await prompt_next_player(interaction.channel_id)

class CardSelect(discord.ui.Select):
    def __init__(self, game, player):
        self.game = game
        self.player = player
        
        options = []
        for i, card in enumerate(player.hand):
            label = str(card)
            is_valid = game.can_play(card)
            emoji = "✅" if is_valid else "❌"
            
            options.append(discord.SelectOption(
                label=f"{label} {emoji}", 
                value=str(i),
                description="Click to play" if is_valid else "Cannot play this card"
            ))
            
            if len(options) >= 25: break 

        super().__init__(placeholder="Select a card to play...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        session = games.get(interaction.channel_id)
        if not session or session['user_map'][self.player.name] != interaction.user.id:
             await interaction.response.send_message("Not your turn!", ephemeral=True)
             return

        # Defer for safety
        await interaction.response.defer(ephemeral=True)

        idx = int(self.values[0])
        success, msg = self.game.play_card(self.player, idx)
        
        if success:
            top_card = self.game.discard_pile[-1]
            logger.info(f"Turn: {self.player.name} played {top_card}. Msg: {msg}")
            
            # Embed for Play
            color = discord.Color(Theme.PRIMARY)
            emoji_suit = ""
            if top_card.suit == "Oros": 
                color = discord.Color(Theme.OROS)
                emoji_suit = "🟡" # Gold/Coin
            elif top_card.suit == "Copas": 
                color = discord.Color(Theme.COPAS)
                emoji_suit = "🎗️" # Ribbon/Copas
            elif top_card.suit == "Espadas": 
                color = discord.Color(Theme.ESPADAS)
                emoji_suit = "⚔️" # Swords
            elif top_card.suit == "Bastos": 
                color = discord.Color(Theme.BASTOS)
                emoji_suit = "🌵" # Cactus/Clubs
            
            embed = discord.Embed(title=f"{emoji_suit} {self.player.name} played a card!", description=f"Placed **{top_card}**", color=color)
            if msg: embed.add_field(name="Effect", value=msg)
            embed.set_thumbnail(url="attachment://center_card.webp") # We can refer to the attachment we are about to send? 
            # Actually discord.File logic: we must send file with the message.
            
            # Update Center Image
            center_file = discord.File("center_card.webp", filename="center_card.webp")
            embed.set_image(url="attachment://center_card.webp")
            
            await interaction.channel.send(file=center_file, embed=embed)
            # await interaction.channel.send(f"{self.player.name} played {top_card}! {msg if msg else ''}")
            
            # Update Center Image
            # center_file = discord.File("center_card.webp", filename="center_card.webp")
            # await interaction.channel.send(file=center_file)
            
            # Close/Update Ephemeral View using edit_original_response
            try:
                 await interaction.edit_original_response(content=f"You played {top_card}. Turn ended.", view=None, attachments=[])
            except: pass

            # Send Ephemeral Hand Update? 
            # Actually, `edit_original_response` replaces the view/message. We can just end it.
            # But let's verify if we need to send new hand?
            # User might want to see new hand if they draw, but here they played. Turn ends.
            
            # Check Win
            if self.player.has_won():
                logger.info(f"Game Over. Winner: {self.player.name}")
                embed = discord.Embed(title="🎉🏆 GAME OVER 🏆🎉", description=f"👑 **{self.player.name}** WINS THE GAME! 👑", color=discord.Color(Theme.OROS))
                await interaction.channel.send(embed=embed)
                del games[interaction.channel_id]
                self.view.stop()
                return
            
            # Check Special - 7 changed suit?
            if top_card.rank == 7:
                 # Show "Choose Suit" view EPHEMERALLY to this player
                 # by editing the original interaction response
                 session = games.get(interaction.channel_id)
                 
                 # NOTE: We do NOT close the view or stop it yet, effectively "chaining" the UI
                 await interaction.edit_original_response(
                     content=f"**You played a 7! Choose a new suit:**", 
                     view=SuitSelectView(self.game, self.player, session['user_map']),
                     attachments=[] 
                 )
                 # Return without next_turn, suit selection handles it
                 return 

            # Proceed
            self.game.next_turn()
            self.view.stop()
            await prompt_next_player(interaction.channel_id)
            
        else:
             # Defer response for error? We deferred already.
             await interaction.edit_original_response(content=f"Invalid move: {msg}", view=self.view) # Reshow view?

class SuitSelectView(discord.ui.View):
    def __init__(self, game, player, user_map):
        super().__init__()
        self.game = game
        self.player = player
        self.user_map = user_map
        self.user_id = user_map.get(player.name)
    
    async def check_user(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the player who played 7 can choose!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Bastos", style=discord.ButtonStyle.primary)
    async def bastos(self, interaction: discord.Interaction, button):
        if not await self.check_user(interaction): return
        self.game.change_suit("Bastos")
        await self.finalize(interaction, "Bastos")

    @discord.ui.button(label="Copas", style=discord.ButtonStyle.danger)
    async def copas(self, interaction: discord.Interaction, button):
        if not await self.check_user(interaction): return
        self.game.change_suit("Copas")
        await self.finalize(interaction, "Copas")

    @discord.ui.button(label="Espadas", style=discord.ButtonStyle.secondary)
    async def espadas(self, interaction: discord.Interaction, button):
        if not await self.check_user(interaction): return
        self.game.change_suit("Espadas")
        await self.finalize(interaction, "Espadas")

    @discord.ui.button(label="Oros", style=discord.ButtonStyle.success)
    async def oros(self, interaction: discord.Interaction, button):
        if not await self.check_user(interaction): return
        self.game.change_suit("Oros")
        await self.finalize(interaction, "Oros")

    async def finalize(self, interaction, suit):
        # 1. Announce Publicly
        logger.info(f"Suit changed to {suit}")
        
        color = discord.Color(Theme.PRIMARY)
        if suit == "Oros": color = discord.Color(Theme.OROS)
        elif suit == "Copas": color = discord.Color(Theme.COPAS)
        elif suit == "Espadas": color = discord.Color(Theme.ESPADAS)
        elif suit == "Bastos": color = discord.Color(Theme.BASTOS)

        embed = discord.Embed(title="Suit Changed 🎨", description=f"Active suit is now **{suit}**", color=color)
        await interaction.channel.send(embed=embed)
        
        # 2. Update Private (Ephemeral) Message to close it
        # Try/Except because depending on flow, interaction might be different or timed out (though unlikely with buttons)
        try:
             await interaction.response.edit_message(content=f"You chose {suit}. Turn ended.", view=None)
        except:
             pass

        # 3. Next Turn
        self.game.next_turn()
        self.stop()
        await prompt_next_player(interaction.channel_id)


@bot.command()
async def carta(ctx):
    """Starts a new Hezz Game Lobby"""
    view = LobbyView(ctx)
    await ctx.send("Starting **Carta-Maroc** (Hezz2)! Click below to join.", view=view)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(TOKEN)
