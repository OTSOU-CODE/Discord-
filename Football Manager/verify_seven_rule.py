from hezz_game import HezzGame, Card

def verify_seven():
    print("--- Verifying Seven Logic ---")
    game = HezzGame(["P1"])
    p1 = game.players[0]
    
    # Seven of Oros
    seven_oros = Card("Oros", 7)
    p1.hand = [seven_oros]
    
    # Scenario 1: Mismatch
    # Top Card: 5 of Copas. Active Suit: Copas. (Oros != Copas, 7 != 5)
    game.discard_pile = [Card("Copas", 5)]
    game.current_suit = "Copas"
    
    print(f"Scenario 1: Try playing {seven_oros} on 5 of Copas")
    if game.can_play(seven_oros):
        print("FAIL: Should NOT be playable on mismatch!")
    else:
        print("PASS: Correctly blocked mismatched 7.")
        
    # Scenario 2: Match Suit
    # Top Card: 5 of Oros.
    game.discard_pile = [Card("Oros", 5)]
    game.current_suit = "Oros"
    
    print(f"Scenario 2: Try playing {seven_oros} on 5 of Oros")
    if game.can_play(seven_oros):
         print("PASS: Playable on matching suit.")
    else:
         print("FAIL: Should be playable on matching suit!")

    # Scenario 3: Match Rank
    # Top Card: 7 of Espadas. (Oros != Espadas, but 7 == 7)
    game.discard_pile = [Card("Espadas", 7)]
    game.current_suit = "Espadas"
    
    print(f"Scenario 3: Try playing {seven_oros} on 7 of Espadas")
    if game.can_play(seven_oros):
         print("PASS: Playable on matching rank.")
    else:
         print("FAIL: Should be playable on matching rank!")

if __name__ == "__main__":
    verify_seven()
