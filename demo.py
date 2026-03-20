"""
Quick demo script showing FreeCell game state and move generation.
Useful for testing game logic without GUI.
"""

from game import Card, GameState, FreeCell


def demo_basic_cards():
    """Demonstrate Card class functionality."""
    print("\n" + "=" * 60)
    print("DEMO 1: Card Class")
    print("=" * 60)
    
    # Create some cards
    ah = Card(1, 'H')  # Ace of Hearts
    kh = Card(13, 'H')  # King of Hearts
    qd = Card(12, 'D')  # Queen of Diamonds
    jc = Card(11, 'C')  # Jack of Clubs
    
    print(f"\nCreated cards: {ah}, {kh}, {qd}, {jc}")
    print(f"Ace of Hearts color: {ah.get_color()}")
    print(f"Queen of Diamonds color: {qd.get_color()}")
    
    # Test stacking rules
    print(f"\nCan Queen of Diamonds stack on King of Hearts? {qd.can_stack_on(kh)}")
    print(f"Can Jack of Clubs stack on Queen of Diamonds? {jc.can_stack_on(qd)}")
    
    # Test alternating colors
    print(f"\nDo 7H and 6D have alternating colors? {Card(7, 'H').has_alternating_color(Card(6, 'D'))}")
    print(f"Do 7H and 6H have alternating colors? {Card(7, 'H').has_alternating_color(Card(6, 'H'))}")


def demo_game_state():
    """Demonstrate GameState class functionality."""
    print("\n" + "=" * 60)
    print("DEMO 2: Game State")
    print("=" * 60)
    
    # Create initial state
    state = GameState()
    
    # Add some cards
    state.add_to_cascade(Card(13, 'H'), 0)  # King of Hearts
    state.add_to_cascade(Card(12, 'D'), 0)  # Queen of Diamonds
    state.add_to_cascade(Card(11, 'C'), 0)  # Jack of Clubs
    state.add_to_cascade(Card(10, 'S'), 0)  # Ten of Spades
    
    # Add card to free cell
    state.add_to_free_cell(Card(1, 'C'), 0)  # Ace of Clubs
    
    print(state)
    print(f"\nEmpty free cells: {state.get_empty_free_cells_count()}")
    print(f"Empty cascades: {state.get_empty_cascades_count()}")


def demo_move_validation():
    """Demonstrate move validation."""
    print("\n" + "=" * 60)
    print("DEMO 3: Move Validation")
    print("=" * 60)
    
    # Create a state with two cascades
    state = GameState()
    state.add_to_cascade(Card(13, 'H'), 0)  # King of Hearts (red)
    state.add_to_cascade(Card(12, 'C'), 1)  # Queen of Clubs (black)
    
    print(state)
    
    # Test cascade-to-cascade move
    can_move = FreeCell.can_move_cascade_to_cascade(state, 0, 1)
    print(f"\nCan move King of Hearts from cascade 0 to cascade 1? {can_move}")
    print(f"Reason: King of Hearts can stack on Queen of Clubs = {Card(13, 'H').can_stack_on(Card(12, 'C'))}")
    
    # Test cascade-to-free-cell move
    can_move = FreeCell.can_move_cascade_to_freecell(state, 0)
    print(f"Can move King of Hearts to free cell? {can_move}")
    print(f"Reason: There are {state.get_empty_free_cells_count()} empty free cells")


def demo_successor_generation():
    """Demonstrate successor state generation."""
    print("\n" + "=" * 60)
    print("DEMO 4: Successor Generation")
    print("=" * 60)
    
    # Create a simple game state
    state = GameState()
    
    # Add Ace of each suit to cascade 0
    for suit in ['H', 'D', 'C', 'S']:
        state.add_to_cascade(Card(1, suit), 0)
    
    print("Initial State:")
    print(state)
    
    # Generate successors
    successors = FreeCell.get_successors(state)
    
    print(f"\nGenerated {len(successors)} successor states:")
    for i, (new_state, move) in enumerate(successors, 1):
        print(f"  {i}. {move}")
    
    print(f"\nExpected: Many moves possible since Aces can go to foundation...")


def demo_state_copy_and_hashing():
    """Demonstrate state copying and hashing."""
    print("\n" + "=" * 60)
    print("DEMO 5: State Copying and Hashing")
    print("=" * 60)
    
    # Create state
    state1 = GameState()
    state1.add_to_cascade(Card(7, 'H'), 0)
    
    # Copy state
    state2 = state1.copy()
    state2.add_to_cascade(Card(6, 'D'), 1)
    
    print(f"State 1 cascades: {len(state1.cascades[0])} cards, {len(state1.cascades[1])} cards")
    print(f"State 2 cascades: {len(state2.cascades[0])} cards, {len(state2.cascades[1])} cards")
    print(f"\nCopy works correctly: {state1 != state2}")
    
    # Test hashing for visited sets
    visited = {state1, state2}
    print(f"Can use states in sets: {len(visited)} unique states")
    
    state3 = GameState()
    state3.add_to_cascade(Card(7, 'H'), 0)
    print(f"state1 == state3: {state1 == state3}")
    print(f"Hash equal: {hash(state1) == hash(state3)}")


def main():
    """Run all demos."""
    print("\n\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  FreeCell Game Logic Demo".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    
    try:
        demo_basic_cards()
        demo_game_state()
        demo_move_validation()
        demo_successor_generation()
        demo_state_copy_and_hashing()
        
        print("\n" + "=" * 60)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
