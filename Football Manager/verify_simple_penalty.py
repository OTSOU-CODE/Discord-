from hezz_game import HezzGame, Card

def verify_simple_penalty():
    print("--- Verifying Simple Penalty Logic ---")
    game = HezzGame(["P1", "P2"])
    
    p1 = game.players[0]
    p2 = game.players[1]
    
    # P1 has 2. P2 has no 2.
    p1.hand = [Card("Oros", 2)]
    p2.hand = [Card("Espadas", 5)]
    
    # Force top card to be matchable
    game.discard_pile = [Card("Oros", 4)]
    game.current_suit = "Oros"
    
    # 1. P1 Plays 2
    print(f"P1 Plays 2. Stack Before: {game.penalty_stack}")
    success, msg = game.play_card(p1, 0)
    print(f"P1 Result: {success}, {msg}")
    print(f"Stack After P1: {game.penalty_stack}")
    game.next_turn()
    
    # 2. P2 Turns
    print(f"P2 Turn. Stack: {game.penalty_stack}")
    # P2 cannot play 5 (Rank is 5, Suit is Espadas vs Oros or Rank 2)
    # Wait, can_play(Espadas 5)?
    # Stack > 0 -> Only Rank 2 allowed.
    print(f"P2 can play 5? {game.can_play(p2.hand[0])}")
    
    # P2 Draws
    old_len = len(p2.hand)
    print(f"P2 Draws. Hand Size Before: {old_len}")
    msg = game.draw_card_action(p2)
    print(f"Draw Msg: {msg}")
    new_len = len(p2.hand)
    print(f"P2 Hand Size After: {new_len}")
    print(f"Cards Drawn: {new_len - old_len}")
    
    if new_len - old_len == 2:
        print("PASS: Drawn 2 cards.")
    else:
        print("FAIL: Did not draw 2 cards.")

    print(f"Final Stack: {game.penalty_stack}")

if __name__ == "__main__":
    verify_simple_penalty()
