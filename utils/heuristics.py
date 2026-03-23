"""Heuristic functions for FreeCell search algorithms."""


def calculate_h_da(state):
    """
    Deadlock-aware heuristic:
    h(n) = h0 (cards not yet in foundation) + me (one-suit deadlock penalties).

    Args:
        state (GameState): Current board state

    Returns:
        int: Estimated remaining cost
    """
    # h0: Number of cards not yet moved to foundations.
    h0 = 52 - sum(state.foundations.values())

    # me: One-suit deadlock penalties.
    # O(n) per cascade by scanning top->bottom and tracking max seen rank per suit.
    me = 0
    for cascade in state.cascades:
        max_rank_above = {"H": 0, "D": 0, "C": 0, "S": 0}
        for card in reversed(cascade):
            suit = card.suit
            if max_rank_above[suit] > card.rank:
                me += 1
            if card.rank > max_rank_above[suit]:
                max_rank_above[suit] = card.rank

    return h0 + me


def calculate_h0_basic(state):
    """Basic heuristic: cards not yet in foundations."""
    return 52 - sum(state.foundations.values())


def create_heuristic_function():
    """Compatibility helper returning the default heuristic function."""
    return calculate_h_da
