"""Heuristic functions for FreeCell search algorithms."""


def _remaining_foundation_cost(state):
    """Return a lower bound on the remaining rank-based foundation cost."""
    remaining_cost = 0
    for top_rank in state.foundations.values():
        for rank in range(top_rank + 1, 14):
            remaining_cost += rank
    return remaining_cost


def calculate_h_da(state):
    """
    Deadlock-aware heuristic:
    h(n) = h0 (remaining rank-based foundation cost) + me (one-suit deadlock penalties).

    Args:
        state (GameState): Current board state

    Returns:
        int: Estimated remaining cost
    """
    # h0: Lower bound on the remaining action cost to finish the foundations.
    h0 = _remaining_foundation_cost(state)

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
    """Basic heuristic: remaining rank-based foundation cost."""
    return _remaining_foundation_cost(state)


def create_heuristic_function():
    """Compatibility helper returning the default heuristic function."""
    return calculate_h_da
