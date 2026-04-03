"""Shared action-cost model for cost-based FreeCell solvers."""

# Cost table provided for search experiments.
ACTION_COSTS = {
    "MOVE_TO_FOUNDATION": 0.8,
    "CASCADE_TO_CASCADE": 1.0,
    "CASCADE_TO_FREECELL": 1.2,
    "FREECELL_TO_CASCADE": 0.9,
    "EMPTY_CASCADE_FILL": 1.1,
}


def get_action_cost(state, move):
    """Return cost of applying ``move`` from ``state`` under the configured table."""
    move_type = move.move_type

    if move_type in {"CASCADE_TO_FOUNDATION", "FREECELL_TO_FOUNDATION"}:
        return ACTION_COSTS["MOVE_TO_FOUNDATION"]

    if move_type == "CASCADE_TO_FREECELL":
        return ACTION_COSTS["CASCADE_TO_FREECELL"]

    if move_type == "FREECELL_TO_CASCADE":
        destination_empty = len(state.get_cascade(move.to_location)) == 0
        if destination_empty:
            return ACTION_COSTS["EMPTY_CASCADE_FILL"]
        return ACTION_COSTS["FREECELL_TO_CASCADE"]

    if move_type in {"CASCADE_TO_CASCADE", "SEQUENCE_CASCADE_TO_CASCADE"}:
        destination_empty = len(state.get_cascade(move.to_location)) == 0
        if destination_empty:
            return ACTION_COSTS["EMPTY_CASCADE_FILL"]
        return ACTION_COSTS["CASCADE_TO_CASCADE"]

    # Safe fallback in case new move types are added later.
    return ACTION_COSTS["CASCADE_TO_CASCADE"]
