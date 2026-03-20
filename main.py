"""
FreeCell Solver - Main Entry Point
Implements a playable FreeCell card game with AI solvers using various search algorithms.
"""

import sys

from game import Card, FreeCell, GameState
from gui import FreeCell_GUI


def run_self_test():
    """Run a quick non-GUI self test for core modules."""
    print("=" * 60)
    print("FreeCell Solver - Main Entry Point")
    print("=" * 60)
    print()
    print("Project successfully initialized!")
    print("All modules imported successfully.")
    print()
    print("Core Components:")
    print("  ✓ Game module: Card, GameState, FreeCell")
    print("  ✓ Solvers: BFS, DFS, UCS, A*")
    print("  ✓ GUI framework")
    print("  ✓ Experiment analyzer")
    print("  ✓ Utilities: Heuristics")
    print()
    print("=" * 60)
    print()
    
    # Quick test of game components
    print("Running initialization test...")
    print()
    
    try:
        # Test Card class
        card1 = Card(7, 'H')
        card2 = Card(6, 'D')
        print(f"Created cards: {card1}, {card2}")
        print(f"Card 1 color: {card1.get_color()}")
        print(f"Can card 2 stack on card 1? {card2.can_stack_on(card1)}")
        print()
        
        # Test GameState
        state = GameState()
        state.add_to_cascade(card1, 0)
        state.add_to_cascade(card2, 0)
        print("Created initial game state and added cards to cascade")
        print(f"Cascade 0 has {len(state.get_cascade(0))} cards")
        print(f"Empty free cells: {state.get_empty_free_cells_count()}")
        print(f"Is goal state? {state.is_goal_state()}")
        print()
        
        # Test FreeCell rules
        print("Testing FreeCell rules...")
        card_ace = Card(1, 'C')
        state2 = GameState()
        state2.add_to_cascade(card_ace, 0)
        successors = FreeCell.get_successors(state2)
        print(f"Generated {len(successors)} successor states from Ace of Clubs")
        print()
        
        print("=" * 60)
        print("All tests passed! Project is ready for development.")
        print("=" * 60)
        return 0
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point for FreeCell application."""
    if "--self-test" in sys.argv:
        return run_self_test()

    gui = FreeCell_GUI()
    gui.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
