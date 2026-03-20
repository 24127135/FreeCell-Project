"""
GameState class representing the complete FreeCell board configuration.
Includes cascades, free cells, and foundation piles.
"""

from copy import deepcopy


class GameState:
    """
    Represents the complete state of a FreeCell game board.
    
    Attributes:
        cascades (list): List of 8 cascade piles, each containing a list of cards
        free_cells (list): List of 4 free cells, each containing either a Card or None
        foundations (dict): Dictionary mapping suit to highest rank in foundation (0 if empty)
    """
    
    def __init__(self, cascades=None, free_cells=None, foundations=None):
        """
        Initialize a GameState.
        
        Args:
            cascades (list): List of 8 cascade piles. Each pile is a list of cards.
            free_cells (list): List of 4 free cells. Each cell contains Card or None.
            foundations (dict): Mapping of suit ('H', 'D', 'C', 'S') to highest rank (0=empty)
        """
        # Initialize with empty state
        if cascades is None:
            self.cascades = [[] for _ in range(8)]
        else:
            self.cascades = [list(cascade) for cascade in cascades]
        
        if free_cells is None:
            self.free_cells = [None, None, None, None]
        else:
            self.free_cells = list(free_cells)
        
        if foundations is None:
            self.foundations = {'H': 0, 'D': 0, 'C': 0, 'S': 0}
        else:
            self.foundations = dict(foundations)
    
    def copy(self):
        """
        Create a deep copy of this game state.
        Used by search algorithms to generate new states without modifying originals.
        
        Returns:
            GameState: A deep copy of this state
        """
        return GameState(
            cascades=deepcopy(self.cascades),
            free_cells=deepcopy(self.free_cells),
            foundations=dict(self.foundations)
        )
    
    def get_cascade(self, index):
        """Get the cascade pile at the given index."""
        if not (0 <= index < 8):
            raise IndexError(f"Cascade index must be 0-7, got {index}")
        return self.cascades[index]
    
    def get_free_cell(self, index):
        """Get the free cell at the given index."""
        if not (0 <= index < 4):
            raise IndexError(f"Free cell index must be 0-3, got {index}")
        return self.free_cells[index]
    
    def is_free_cell_empty(self, index):
        """Check if a free cell is empty."""
        return self.free_cells[index] is None
    
    def get_empty_free_cells_count(self):
        """Return the number of empty free cells."""
        return sum(1 for cell in self.free_cells if cell is None)
    
    def get_empty_cascades_count(self):
        """Return the number of empty cascade piles."""
        return sum(1 for cascade in self.cascades if len(cascade) == 0)
    
    def get_top_card(self, cascade_index):
        """
        Get the top card of a cascade pile.
        
        Args:
            cascade_index (int): Index of the cascade (0-7)
            
        Returns:
            Card or None: The top card, or None if cascade is empty
        """
        cascade = self.cascades[cascade_index]
        if len(cascade) == 0:
            return None
        return cascade[-1]
    
    def add_to_cascade(self, card, cascade_index):
        """
        Add a card to the top of a cascade pile.
        
        Args:
            card (Card): Card to add
            cascade_index (int): Index of the cascade
        """
        self.cascades[cascade_index].append(card)
    
    def add_to_free_cell(self, card, free_cell_index):
        """
        Add a card to an empty free cell.
        
        Args:
            card (Card): Card to add
            free_cell_index (int): Index of the free cell
            
        Raises:
            ValueError: If free cell is not empty
        """
        if self.free_cells[free_cell_index] is not None:
            raise ValueError(f"Free cell {free_cell_index} is not empty")
        self.free_cells[free_cell_index] = card
    
    def add_to_foundation(self, card):
        """
        Add a card to its foundation pile.
        
        Args:
            card (Card): Card to add to foundation
            
        Raises:
            ValueError: If card cannot be added to its foundation
        """
        current_rank = self.foundations[card.suit]
        if card.rank != current_rank + 1:
            raise ValueError(f"Card {card} cannot be added to {card.suit} foundation (current rank: {current_rank})")
        self.foundations[card.suit] = card.rank
    
    def remove_card_from_cascade(self, cascade_index):
        """
        Remove and return the top card from a cascade.
        
        Args:
            cascade_index (int): Index of the cascade
            
        Returns:
            Card: The removed card
            
        Raises:
            ValueError: If cascade is empty
        """
        cascade = self.cascades[cascade_index]
        if len(cascade) == 0:
            raise ValueError(f"Cannot remove from empty cascade {cascade_index}")
        return cascade.pop()
    
    def remove_card_from_free_cell(self, free_cell_index):
        """
        Remove and return the card from a free cell.
        
        Args:
            free_cell_index (int): Index of the free cell
            
        Returns:
            Card: The removed card
            
        Raises:
            ValueError: If free cell is empty
        """
        card = self.free_cells[free_cell_index]
        if card is None:
            raise ValueError(f"Cannot remove from empty free cell {free_cell_index}")
        self.free_cells[free_cell_index] = None
        return card
    
    def is_goal_state(self):
        """
        Check if this is the goal state (all cards in foundations).
        
        Returns:
            bool: True if all foundations are complete (each at rank 13)
        """
        return all(rank == 13 for rank in self.foundations.values())
    
    def __eq__(self, other):
        """Check if two game states are equal."""
        if not isinstance(other, GameState):
            return False
        
        # Compare cascades
        if len(self.cascades) != len(other.cascades):
            return False
        for c1, c2 in zip(self.cascades, other.cascades):
            if c1 != c2:
                return False
        
        # Compare free cells
        if self.free_cells != other.free_cells:
            return False
        
        # Compare foundations
        if self.foundations != other.foundations:
            return False
        
        return True
    
    def __hash__(self):
        """Return hash of game state for use in sets and dicts."""
        cascades_tuple = tuple(tuple(cascade) for cascade in self.cascades)
        free_cells_tuple = tuple(self.free_cells)
        foundations_tuple = tuple(sorted(self.foundations.items()))
        return hash((cascades_tuple, free_cells_tuple, foundations_tuple))
    
    def __str__(self):
        """Return string representation of the board."""
        lines = []
        lines.append("=" * 50)
        lines.append("FREECELL BOARD STATE")
        lines.append("=" * 50)
        
        # Free cells
        lines.append("Free Cells:")
        free_cells_str = [str(cell) if cell is not None else "---" for cell in self.free_cells]
        lines.append("  " + "  ".join(free_cells_str))
        
        # Foundations
        lines.append("\nFoundations:")
        for suit in ['H', 'D', 'C', 'S']:
            rank = self.foundations[suit]
            suit_name = {'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs', 'S': 'Spades'}[suit]
            lines.append(f"  {suit_name}: {rank}")
        
        # Cascades
        lines.append("\nCascades:")
        for i, cascade in enumerate(self.cascades):
            if len(cascade) == 0:
                lines.append(f"  [{i}] (empty)")
            else:
                cards_str = " -> ".join(str(card) for card in cascade)
                lines.append(f"  [{i}] {cards_str}")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    def __repr__(self):
        """Return representative string."""
        return f"GameState(cascades={self.cascades}, free_cells={self.free_cells}, foundations={self.foundations})"
