"""A* Search solver placeholder."""


class AStarSolver:
    """A* solver for FreeCell."""
    
    def __init__(self, heuristic=None):
        """Initialize A* solver."""
        self.heuristic = heuristic
    
    def solve(self, initial_state):
        """
        Solve FreeCell using A*.
        
        Args:
            initial_state (GameState): Starting game state
            
        Returns:
            tuple: (solution_path, metrics) or (None, metrics) if unsolvable
        """
        # Placeholder - to be implemented
        raise NotImplementedError("A* solver not yet implemented")
