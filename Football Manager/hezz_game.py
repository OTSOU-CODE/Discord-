import random
import time
from card_renderer import CardRenderer

# Constants
SUITS = ['Bastos', 'Copas', 'Espadas', 'Oros']
# Spanish 40-card deck usually has 1-7, 10-12 (Knave, Horse, King)
# Mapping 8, 9, 10 to standard indices if needed, but let's stick to the labels 1-7, 10-12
RANKS = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"{self.rank} of {self.suit}"

    def __repr__(self):
        return self.__str__()

    def matches(self, other_card):
        return self.suit == other_card.suit or self.rank == other_card.rank

class Deck:
    def __init__(self):
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop() if self.cards else None

    def is_empty(self):
        return len(self.cards) == 0

class Player:
    def __init__(self, name, is_human=False):
        self.name = name
        self.hand = []
        self.is_human = is_human

    def add_card(self, card):
        self.hand.append(card)

    def remove_card(self, index):
        if 0 <= index < len(self.hand):
            return self.hand.pop(index)
        return None

    def has_won(self):
        return len(self.hand) == 0

    def __str__(self):
        return f"{self.name} ({len(self.hand)} cards)"

class HezzGame:
    def __init__(self, player_names):
        self.deck = Deck()
        self.discard_pile = []
        self.players = [Player(name, is_human=True) for name in player_names] # All human for CLI testing
        self.current_player_idx = 0
        self.direction = 1 # 1 for clockwise, -1 for counter-clockwise
        self.penalty_stack = 0 # For the "2" card rule
        self.current_suit = None # Can be changed by "7"
        self.renderer = CardRenderer() # Initialize renderer

        # Deal 4 cards to each player
        for _ in range(4):
            for player in self.players:
                self.deal_card(player)

        # Start the game with a card from the deck
        start_card = self.deck.draw()
        self.discard_pile.append(start_card)
        self.current_suit = start_card.suit
        print(f"Game Started! Center card: {start_card}")

        # If start card is special, we could apply rules, but for simplicity let's just set state
        if start_card.rank == 7:
            # Randomly pick suit or keep it? Let's keep it.
            pass
        
        # Generate initial images
        self.generate_center_card_image()
        for player in self.players:
            self.generate_player_hand_image(player)
            
    def generate_player_hand_image(self, player):
        """Generates an image of the player's hand and saves it."""
        filename = f"hand_{player.name}.webp"
        self.renderer.render_hand(player.hand, filename)
        return filename

    def generate_center_card_image(self):
        """Generates an image of the center card (top of discard pile)."""
        if not self.discard_pile:
            return None
        top_card = self.discard_pile[-1]
        filename = "center_card.webp"
        self.renderer.render_hand([top_card], filename)
        return filename

    def deal_card(self, player, count=1):
        for _ in range(count):
            if self.deck.is_empty():
                self.check_reshuffle()
                if self.deck.is_empty():
                    print("Deck is empty and cannot reshuffle!")
                    return
            card = self.deck.draw()
            if card:
                player.add_card(card)
        
        # Update player's hand image
        self.generate_player_hand_image(player)

    def check_reshuffle(self):
        if len(self.discard_pile) > 1:
            top_card = self.discard_pile.pop()
            new_cards = self.discard_pile[:]
            self.discard_pile = [top_card]
            self.deck.cards = new_cards
            self.deck.shuffle()
            print("Deck reshuffled from discard pile.")

    def next_turn(self):
        self.current_player_idx = (self.current_player_idx + self.direction) % len(self.players)

    def get_current_player(self):
        return self.players[self.current_player_idx]

    def can_play(self, card):
        # Must match active suit or active rank
        # However, if penalty_stack > 0, strict rules apply?
        # Rule: "2 triggers a take 2 penalty or matching response"
        # If penalty active, must play a 2.
        
        if self.penalty_stack > 0:
            return card.rank == 2
        
        # 7 is usually "Magic" / Wild in Hezz2?
        # Allowing 7 on any card to change suit makes gameplay smoother.
        if self.penalty_stack > 0:
            return card.rank == 2
        
        # 7 is usually "Magic" / Wild in Hezz2?
        # User requested 7 MUST MATCH suit/rank to be played.
        # So we remove the unconditional "return True" here and let it fall through to below logic.

        # Normal play
        # Match suit (current_suit might be different from top card's physical suit due to 7)
        if card.suit == self.current_suit:
            return True
        
        # Match rank (always allowed rank match, e.g. 5 on 5)
        top_card = self.discard_pile[-1]
        
        # Check against top card for Rank match
        # Note: If top card is 7 (Wild), its rank is 7. You can play a 7 on it (handled above).
        # You can also play matching suit (handled above).
        # Can you play a matching Rank? Yes.
        if card.rank == top_card.rank:
            return True
        
        return False

    def draw_card_action(self, player):
        """Handles drawing logic, including penalty stacks."""
        count = 1
        msg = f"{player.name} drew a card."
        
        if self.penalty_stack > 0:
            count = self.penalty_stack
            msg = f"{player.name} drew {count} cards (Penalty)!"
            self.penalty_stack = 0
            
        self.deal_card(player, count)
        return msg

    def play_card(self, player, card_index):
        card = player.hand[card_index]
        if not self.can_play(card):
            return False, "Card does not match current suit or rank."

        # Execute Play
        player.remove_card(card_index)
        self.discard_pile.append(card)
        self.current_suit = card.suit # Default, updates to new card's suit
        
        # Update Images
        self.generate_player_hand_image(player)
        self.generate_center_card_image()
        
        print(f"{player.name} played {card}")

        # Handle Special Cards
        msg = ""
        
        # 7: Change Suit
        if card.rank == 7:
            # In CLI, ask user. In code, needs input. 
            # For simplicity in logic engine, we set a flag or expect args.
            # I'll modify play_card to take optional 'declared_suit'
            pass  # Logic handled in loop or separate method
        
        # 2: Penalty
        if card.rank == 2:
            self.penalty_stack += 2
            msg = f"Penalty Stack increased to {self.penalty_stack}!"

        # 1: Skip
        if card.rank == 1:
            msg = "Next player Skipped!"
            self.next_turn() # Skip once immediately (logic will do next_turn again at end of turn)
            # Actually, standard flow: P1 plays. Loop ends. P2 starts.
            # If Skip: P1 plays. Skip logic increments idx. Loop ends. P3 starts.
        
        return True, msg

    def change_suit(self, new_suit):
        if new_suit in SUITS:
            self.current_suit = new_suit
            print(f"Suit changed to {new_suit}!")
            return True
        return False

    def run(self):
        print("Welcome to Hezz2 CLI!")
        print(f"Players: {[p.name for p in self.players]}")
        
        while True:
            current_player = self.get_current_player()
            top_card = self.discard_pile[-1]
            print(f("\n" + "="*30))
            print(f"Turn: {current_player.name}")
            print(f"Top Card: {top_card} | Active Suit: {self.current_suit}")
            if self.penalty_stack > 0:
                print(f"WARNING: PENALTY STACK: {self.penalty_stack} (Must play a 2 or draw)")
            
            print(f"Your Hand: {[(i, str(c)) for i, c in enumerate(current_player.hand)]}")
            
            # Simple AI/choice simulation
            valid_indices = [i for i, c in enumerate(current_player.hand) if self.can_play(c)]
            
            # Interaction
            if self.penalty_stack > 0 and not valid_indices:
                print(f"Cannot match 2! Drawing {self.penalty_stack} cards.")
                self.deal_card(current_player, self.penalty_stack)
                self.penalty_stack = 0
            else:
                action = input("Enter card index to play, or 'd' to draw: ").strip().lower()
                
                if action == 'd':
                    print(f"{current_player.name} draws a card.")
                    self.deal_card(current_player)
                    # Optional: Can play immediately? Standard Hezz: Yes if playable.
                    # For simplicity, turn ends.
                elif action.isdigit():
                    idx = int(action)
                    if 0 <= idx < len(current_player.hand):
                        success, msg = self.play_card(current_player, idx)
                        if success:
                            if msg: print(msg)
                            
                            # Handle 7 Suit Change
                            if self.discard_pile[-1].rank == 7:
                                print(f"Choose suit: {SUITS}")
                                while True:
                                    s_input = input("Suite (Bastos/Copas/Espadas/Oros): ").capitalize()
                                    if self.change_suit(s_input):
                                        break
                        else:
                            print(f"Invalid move: {msg}")
                            continue
                    else:
                        print("Invalid index.")
                        continue
                else:
                    print("Invalid input.")
                    continue

            # Check logic for next turn
            if current_player.has_won():
                print(f"\nWINNER! {current_player.name} has emptied their hand!")
                break
            
            self.next_turn()

if __name__ == "__main__":
    game = HezzGame(["Player 1", "Player 2", "Player 3"])
    game.run()
