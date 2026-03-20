"""
FreeCell game rules and mechanics.
Validates moves and generates successor states.
"""

from .card import Card
from .state import GameState


class Move:
    """Represents a move in FreeCell."""
    
    MOVE_TYPES = ['CASCADE_TO_CASCADE', 'CASCADE_TO_FREECELL', 'FREECELL_TO_CASCADE',
                  'CASCADE_TO_FOUNDATION', 'FREECELL_TO_FOUNDATION']
    
    def __init__(self, move_type, from_location, to_location, card=None):
        """
        Initialize a Move.
        
        Args:
            move_type (str): Type of move
            from_location (int): Source location (cascade or free cell index)
            to_location (int): Destination location
            card (Card): The card being moved
        """
        self.move_type = move_type
        self.from_location = from_location
        self.to_location = to_location
        self.card = card
    
    def __str__(self):
        """Return readable move description."""
        locations = {
            'CASCADE_TO_CASCADE': f"Cascade {self.from_location} -> Cascade {self.to_location}",
            'CASCADE_TO_FREECELL': f"Cascade {self.from_location} -> Free Cell {self.to_location}",
            'FREECELL_TO_CASCADE': f"Free Cell {self.from_location} -> Cascade {self.to_location}",
            'CASCADE_TO_FOUNDATION': f"Cascade {self.from_location} -> Foundation {self.card.suit}",
            'FREECELL_TO_FOUNDATION': f"Free Cell {self.from_location} -> Foundation {self.card.suit}",
        }
        return f"Move {self.card}: {locations[self.move_type]}"
    
    def __repr__(self):
        return f"Move({self.move_type}, {self.from_location}, {self.to_location}, {self.card})"


class FreeCell:
    """FreeCell game rules engine."""
    
    @staticmethod
    def can_move_cascade_to_cascade(state, from_cascade, to_cascade):
        """
        Check if a card can be moved from one cascade to another.
        The top card of from_cascade must be able to stack on top of to_cascade's top card.
        
        Args:
            state (GameState): Current game state
            from_cascade (int): Source cascade index
            to_cascade (int): Destination cascade index
            
        Returns:
            bool: True if move is valid
        """
        # Can't move to itself
        if from_cascade == to_cascade:
            return False
        
        # Source cascade must not be empty
        from_top = state.get_top_card(from_cascade)
        if from_top is None:
            return False
        
        # Get destination top card
        to_top = state.get_top_card(to_cascade)
        
        # If destination is empty, can always move
        if to_top is None:
            return True
        
        # Otherwise, check stacking rules
        return from_top.can_stack_on(to_top)
    
    @staticmethod
    def can_move_cascade_to_freecell(state, cascade_index):
        """
        Check if top card of cascade can move to a free cell.
        Only the top card of a cascade can be moved to a free cell,
        and only if there's an empty free cell.
        
        Args:
            state (GameState): Current game state
            cascade_index (int): Cascade index
            
        Returns:
            bool: True if move is valid
        """
        # Cascade must not be empty
        if state.get_top_card(cascade_index) is None:
            return False
        
        # Must have an empty free cell
        return state.get_empty_free_cells_count() > 0
    
    @staticmethod
    def can_move_freecell_to_cascade(state, free_cell_index, cascade_index):
        """
        Check if card in free cell can move to cascade.
        
        Args:
            state (GameState): Current game state
            free_cell_index (int): Free cell index
            cascade_index (int): Cascade index
            
        Returns:
            bool: True if move is valid
        """
        # Free cell must have a card
        card = state.get_free_cell(free_cell_index)
        if card is None:
            return False
        
        # Get top card of destination cascade
        to_top = state.get_top_card(cascade_index)
        
        # If cascade is empty, can always move
        if to_top is None:
            return True
        
        # Otherwise, check stacking rules
        return card.can_stack_on(to_top)
    
    @staticmethod
    def can_move_cascade_to_foundation(state, cascade_index):
        """
        Check if top card of cascade can move to foundation.
        A card can move to foundation if:
        - It's an Ace (foundation is empty)
        - OR its suit foundation has the card with rank-1
        
        Args:
            state (GameState): Current game state
            cascade_index (int): Cascade index
            
        Returns:
            bool: True if move is valid
        """
        card = state.get_top_card(cascade_index)
        if card is None:
            return False
        
        current_rank = state.foundations[card.suit]
        # Card's rank must be exactly 1 more than current foundation rank
        return card.rank == current_rank + 1
    
    @staticmethod
    def can_move_freecell_to_foundation(state, free_cell_index):
        """
        Check if card in free cell can move to foundation.
        
        Args:
            state (GameState): Current game state
            free_cell_index (int): Free cell index
            
        Returns:
            bool: True if move is valid
        """
        card = state.get_free_cell(free_cell_index)
        if card is None:
            return False
        
        current_rank = state.foundations[card.suit]
        return card.rank == current_rank + 1
    
    @staticmethod
    def move_cascade_to_cascade(state, from_cascade, to_cascade):
        """
        Execute move from one cascade to another.
        
        Args:
            state (GameState): Current game state
            from_cascade (int): Source cascade
            to_cascade (int): Destination cascade
            
        Returns:
            GameState: New state after move
            
        Raises:
            ValueError: If move is invalid
        """
        if not FreeCell.can_move_cascade_to_cascade(state, from_cascade, to_cascade):
            raise ValueError(f"Cannot move from cascade {from_cascade} to {to_cascade}")
        
        new_state = state.copy()
        card = new_state.remove_card_from_cascade(from_cascade)
        new_state.add_to_cascade(card, to_cascade)
        return new_state
    
    @staticmethod
    def move_cascade_to_freecell(state, cascade_index, free_cell_index):
        """
        Execute move from cascade to free cell.
        
        Args:
            state (GameState): Current game state
            cascade_index (int): Source cascade
            free_cell_index (int): Destination free cell
            
        Returns:
            GameState: New state after move
            
        Raises:
            ValueError: If move is invalid
        """
        if not FreeCell.can_move_cascade_to_freecell(state, cascade_index):
            raise ValueError(f"Cannot move from cascade {cascade_index} to free cell")
        
        new_state = state.copy()
        card = new_state.remove_card_from_cascade(cascade_index)
        
        # Find first empty free cell if not specified
        if free_cell_index is None:
            for i in range(4):
                if new_state.is_free_cell_empty(i):
                    free_cell_index = i
                    break
        
        new_state.add_to_free_cell(card, free_cell_index)
        return new_state
    
    @staticmethod
    def move_freecell_to_cascade(state, free_cell_index, cascade_index):
        """
        Execute move from free cell to cascade.
        
        Args:
            state (GameState): Current game state
            free_cell_index (int): Source free cell
            cascade_index (int): Destination cascade
            
        Returns:
            GameState: New state after move
            
        Raises:
            ValueError: If move is invalid
        """
        if not FreeCell.can_move_freecell_to_cascade(state, free_cell_index, cascade_index):
            raise ValueError(f"Cannot move from free cell {free_cell_index} to cascade {cascade_index}")
        
        new_state = state.copy()
        card = new_state.remove_card_from_free_cell(free_cell_index)
        new_state.add_to_cascade(card, cascade_index)
        return new_state
    
    @staticmethod
    def move_cascade_to_foundation(state, cascade_index):
        """
        Execute move from cascade to foundation.
        
        Args:
            state (GameState): Current game state
            cascade_index (int): Source cascade
            
        Returns:
            GameState: New state after move
            
        Raises:
            ValueError: If move is invalid
        """
        if not FreeCell.can_move_cascade_to_foundation(state, cascade_index):
            raise ValueError(f"Cannot move from cascade {cascade_index} to foundation")
        
        new_state = state.copy()
        card = new_state.remove_card_from_cascade(cascade_index)
        new_state.add_to_foundation(card)
        return new_state
    
    @staticmethod
    def move_freecell_to_foundation(state, free_cell_index):
        """
        Execute move from free cell to foundation.
        
        Args:
            state (GameState): Current game state
            free_cell_index (int): Source free cell
            
        Returns:
            GameState: New state after move
            
        Raises:
            ValueError: If move is invalid
        """
        if not FreeCell.can_move_freecell_to_foundation(state, free_cell_index):
            raise ValueError(f"Cannot move from free cell {free_cell_index} to foundation")
        
        new_state = state.copy()
        card = new_state.remove_card_from_free_cell(free_cell_index)
        new_state.add_to_foundation(card)
        return new_state
    
    @staticmethod
    def get_successors(state):
        """
        Generate all valid successor states from current state.
        This is the key function used by search algorithms.
        
        Args:
            state (GameState): Current game state
            
        Returns:
            list: List of (new_state, move) tuples
        """
        successors = []
        
        # Try moves from cascades
        for cascade_idx in range(8):
            # Cascade to foundation (priority - frees up space)
            if FreeCell.can_move_cascade_to_foundation(state, cascade_idx):
                new_state = FreeCell.move_cascade_to_foundation(state, cascade_idx)
                card = state.get_top_card(cascade_idx)
                move = Move('CASCADE_TO_FOUNDATION', cascade_idx, None, card)
                successors.append((new_state, move))
            
            # Cascade to free cell
            if FreeCell.can_move_cascade_to_freecell(state, cascade_idx):
                for free_cell_idx in range(4):
                    if state.is_free_cell_empty(free_cell_idx):
                        new_state = FreeCell.move_cascade_to_freecell(state, cascade_idx, free_cell_idx)
                        card = state.get_top_card(cascade_idx)
                        move = Move('CASCADE_TO_FREECELL', cascade_idx, free_cell_idx, card)
                        successors.append((new_state, move))
                        break  # Only move to first available free cell
            
            # Cascade to cascade
            for to_cascade_idx in range(8):
                if FreeCell.can_move_cascade_to_cascade(state, cascade_idx, to_cascade_idx):
                    new_state = FreeCell.move_cascade_to_cascade(state, cascade_idx, to_cascade_idx)
                    card = state.get_top_card(cascade_idx)
                    move = Move('CASCADE_TO_CASCADE', cascade_idx, to_cascade_idx, card)
                    successors.append((new_state, move))
        
        # Try moves from free cells
        for free_cell_idx in range(4):
            card = state.get_free_cell(free_cell_idx)
            if card is None:
                continue
            
            # Free cell to foundation (priority)
            if FreeCell.can_move_freecell_to_foundation(state, free_cell_idx):
                new_state = FreeCell.move_freecell_to_foundation(state, free_cell_idx)
                move = Move('FREECELL_TO_FOUNDATION', free_cell_idx, None, card)
                successors.append((new_state, move))
            
            # Free cell to cascade
            for cascade_idx in range(8):
                if FreeCell.can_move_freecell_to_cascade(state, free_cell_idx, cascade_idx):
                    new_state = FreeCell.move_freecell_to_cascade(state, free_cell_idx, cascade_idx)
                    move = Move('FREECELL_TO_CASCADE', free_cell_idx, cascade_idx, card)
                    successors.append((new_state, move))
        
        return successors
