"""
FreeCell game rules and mechanics.
Validates moves, generates deals, and generates successor states.
"""

import random

from .card import Card
from .state import GameState


class Move:
    """Represents a move in FreeCell."""
    
    MOVE_TYPES = [
        'CASCADE_TO_CASCADE',
        'SEQUENCE_CASCADE_TO_CASCADE',
        'CASCADE_TO_FREECELL',
        'FREECELL_TO_CASCADE',
        'CASCADE_TO_FOUNDATION',
        'FREECELL_TO_FOUNDATION',
    ]
    
    def __init__(self, move_type, from_location, to_location, card=None, count=1):
        """
        Initialize a Move.
        
        Args:
            move_type (str): Type of move
            from_location (int): Source location (cascade or free cell index)
            to_location (int): Destination location
            card (Card): The card being moved
            count (int): Number of cards being moved (for sequence moves)
        """
        self.move_type = move_type
        self.from_location = from_location
        self.to_location = to_location
        self.card = card
        self.count = count
    
    def __str__(self):
        """Return readable move description."""
        locations = {
            'CASCADE_TO_CASCADE': f"Cascade {self.from_location} -> Cascade {self.to_location}",
            'SEQUENCE_CASCADE_TO_CASCADE': (
                f"Cascade {self.from_location} -> Cascade {self.to_location}"
            ),
            'CASCADE_TO_FREECELL': f"Cascade {self.from_location} -> Free Cell {self.to_location}",
            'FREECELL_TO_CASCADE': f"Free Cell {self.from_location} -> Cascade {self.to_location}",
            'CASCADE_TO_FOUNDATION': f"Cascade {self.from_location} -> Foundation {self.card.suit}",
            'FREECELL_TO_FOUNDATION': f"Free Cell {self.from_location} -> Foundation {self.card.suit}",
        }
        if self.move_type == 'SEQUENCE_CASCADE_TO_CASCADE':
            return f"Move {self.count} cards (start {self.card}): {locations[self.move_type]}"
        return f"Move {self.card}: {locations[self.move_type]}"
    
    def __repr__(self):
        return (
            f"Move({self.move_type}, {self.from_location}, {self.to_location}, "
            f"{self.card}, count={self.count})"
        )


class FreeCell:
    """FreeCell game rules engine."""

    MICROSOFT_CLASSIC_MAX_DEAL = 32000

    @staticmethod
    def _microsoft_rand(seed):
        """Return next MSVC rand seed and value using classic LCG parameters."""
        next_seed = (214013 * seed + 2531011) & 0xFFFFFFFF
        return next_seed, (next_seed >> 16) & 0x7FFF

    @staticmethod
    def _create_microsoft_deck(deal_number):
        """Create a Microsoft-compatible shuffled deck for a numbered deal."""
        # Classic FreeCell uses suit-major order C, D, H, S then A..K.
        deck = [Card(rank, suit) for suit in ["C", "D", "H", "S"] for rank in range(1, 14)]
        seed = int(deal_number) & 0xFFFFFFFF

        for i in range(len(deck) - 1, 0, -1):
            seed, value = FreeCell._microsoft_rand(seed)
            j = value % (i + 1)
            deck[i], deck[j] = deck[j], deck[i]

        return deck

    @staticmethod
    def create_initial_state(deal_number=None):
        """
        Create a standard FreeCell initial state (4x7, 4x6 cascades).

        Args:
            deal_number (int|None): Optional numbered deal seed.
                - 1..32000 uses classic Microsoft deal generation
                - Other values fall back to Python's seeded shuffle

        Returns:
            GameState: Freshly dealt board
        """
        deck = [Card(rank, suit) for suit in ["H", "D", "C", "S"] for rank in range(1, 14)]
        if deal_number is None:
            random.shuffle(deck)
        else:
            deal_number = int(deal_number)
            if 1 <= deal_number <= FreeCell.MICROSOFT_CLASSIC_MAX_DEAL:
                deck = FreeCell._create_microsoft_deck(deal_number)
            else:
                rng = random.Random(deal_number)
                rng.shuffle(deck)

        cascades = [[] for _ in range(8)]
        # Deal cards left-to-right in rounds, as in classic FreeCell.
        for index, card in enumerate(deck):
            pile = index % 8
            cascades[pile].append(card)

        return GameState(cascades=cascades)

    @staticmethod
    def is_valid_tableau_sequence(cards):
        """
        Check if cards form a descending alternating-color tableau sequence.

        Args:
            cards (list[Card]): Cards in cascade order (bottom to top)

        Returns:
            bool: True if sequence is a valid movable tableau run
        """
        if not cards:
            return False

        for i in range(1, len(cards)):
            if not cards[i].can_stack_on(cards[i - 1]):
                return False
        return True

    @staticmethod
    def get_movable_sequence_length(state, cascade_index):
        """
        Return max valid descending alternating run length from top of cascade.

        Args:
            state (GameState): Current game state
            cascade_index (int): Source cascade index

        Returns:
            int: Length of valid top run that could be moved as a sequence
        """
        cascade = state.get_cascade(cascade_index)
        if not cascade:
            return 0

        length = 1
        for i in range(len(cascade) - 1, 0, -1):
            top = cascade[i]
            below = cascade[i - 1]
            if top.can_stack_on(below):
                length += 1
            else:
                break
        return length

    @staticmethod
    def get_max_movable_cards(state, from_cascade, to_cascade):
        """
                Compute maximum transferable sequence size for a cascade move.

                Rule-aligned with FreeCell supermoves as commonly documented:
                - To a non-empty cascade:
                    C = 2^M * (N + 1)
                - To an empty cascade:
                    C / 2

                Where:
                - N is the number of empty free cells
                - M is the number of empty cascades (excluding source cascade)

        Args:
            state (GameState): Current game state
            from_cascade (int): Source cascade index
            to_cascade (int): Destination cascade index

        Returns:
            int: Maximum number of cards that can be moved legally
        """
        empty_free_cells = state.get_empty_free_cells_count()

        empty_cascades_excluding_source = 0
        for idx, cascade in enumerate(state.cascades):
            if idx == from_cascade:
                continue
            if len(cascade) == 0:
                empty_cascades_excluding_source += 1

        to_is_empty = len(state.get_cascade(to_cascade)) == 0

        # C = 2^M * (N + 1), with M as empty cascades excluding source.
        c_to_non_empty = (empty_free_cells + 1) * (2 ** empty_cascades_excluding_source)

        if to_is_empty:
            # Moving to an empty cascade reduces capacity to C/2.
            return max(1, c_to_non_empty // 2)

        return c_to_non_empty
    
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
    def can_move_sequence_cascade_to_cascade(state, from_cascade, to_cascade, count):
        """
        Check if a sequence can be moved between cascades using supermove limits.

        Args:
            state (GameState): Current game state
            from_cascade (int): Source cascade index
            to_cascade (int): Destination cascade index
            count (int): Number of cards to move

        Returns:
            bool: True if sequence move is valid
        """
        if from_cascade == to_cascade:
            return False
        if count <= 0:
            return False

        source = state.get_cascade(from_cascade)
        if len(source) < count:
            return False

        sequence = source[-count:]
        if not FreeCell.is_valid_tableau_sequence(sequence):
            return False

        max_cards = FreeCell.get_max_movable_cards(state, from_cascade, to_cascade)
        if count > max_cards:
            return False

        destination_top = state.get_top_card(to_cascade)
        moving_base = sequence[0]
        if destination_top is None:
            return True
        return moving_base.can_stack_on(destination_top)
    
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
    def move_sequence_cascade_to_cascade(state, from_cascade, to_cascade, count):
        """
        Execute a sequence move from one cascade to another.

        Args:
            state (GameState): Current game state
            from_cascade (int): Source cascade index
            to_cascade (int): Destination cascade index
            count (int): Number of cards to move

        Returns:
            GameState: New state after move

        Raises:
            ValueError: If move is invalid
        """
        if not FreeCell.can_move_sequence_cascade_to_cascade(state, from_cascade, to_cascade, count):
            raise ValueError(
                f"Cannot move sequence of {count} card(s) from cascade {from_cascade} to {to_cascade}"
            )

        new_state = state.copy()
        cards = new_state.remove_sequence_from_cascade(from_cascade, count)
        new_state.add_sequence_to_cascade(cards, to_cascade)
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
    def get_successors(state, foundation_only=False):
        """
        Generate all valid successor states from current state.
        This is the key function used by search algorithms.
        
        Args:
            state (GameState): Current game state
            foundation_only (bool): If True, return only foundation moves when
                at least one exists. If none exist, return full successors.
            
        Returns:
            list: List of (new_state, move) tuples
        """
        successors = []
        foundation_successors = []

        # Generate foundation moves first so solvers can optionally short-circuit.
        for cascade_idx in range(8):
            if FreeCell.can_move_cascade_to_foundation(state, cascade_idx):
                new_state = FreeCell.move_cascade_to_foundation(state, cascade_idx)
                card = state.get_top_card(cascade_idx)
                move = Move('CASCADE_TO_FOUNDATION', cascade_idx, None, card)
                foundation_successors.append((new_state, move))

        for free_cell_idx in range(4):
            card = state.get_free_cell(free_cell_idx)
            if card is None:
                continue
            if FreeCell.can_move_freecell_to_foundation(state, free_cell_idx):
                new_state = FreeCell.move_freecell_to_foundation(state, free_cell_idx)
                move = Move('FREECELL_TO_FOUNDATION', free_cell_idx, None, card)
                foundation_successors.append((new_state, move))

        if foundation_only and foundation_successors:
            return foundation_successors

        successors.extend(foundation_successors)
        
        # Try moves from cascades
        for cascade_idx in range(8):
            # Cascade to free cell
            if FreeCell.can_move_cascade_to_freecell(state, cascade_idx):
                for free_cell_idx in range(4):
                    if state.is_free_cell_empty(free_cell_idx):
                        new_state = FreeCell.move_cascade_to_freecell(state, cascade_idx, free_cell_idx)
                        card = state.get_top_card(cascade_idx)
                        move = Move('CASCADE_TO_FREECELL', cascade_idx, free_cell_idx, card)
                        successors.append((new_state, move))
                        break  # Only move to first available free cell
            
            # Cascade to cascade (single-card and supermove sequence support)
            for to_cascade_idx in range(8):
                max_sequence = min(
                    FreeCell.get_movable_sequence_length(state, cascade_idx),
                    FreeCell.get_max_movable_cards(state, cascade_idx, to_cascade_idx),
                )

                for count in range(1, max_sequence + 1):
                    if FreeCell.can_move_sequence_cascade_to_cascade(
                        state, cascade_idx, to_cascade_idx, count
                    ):
                        if count == 1:
                            new_state = FreeCell.move_cascade_to_cascade(state, cascade_idx, to_cascade_idx)
                            card = state.get_top_card(cascade_idx)
                            move = Move('CASCADE_TO_CASCADE', cascade_idx, to_cascade_idx, card, count=1)
                        else:
                            new_state = FreeCell.move_sequence_cascade_to_cascade(
                                state, cascade_idx, to_cascade_idx, count
                            )
                            card = state.cascades[cascade_idx][-count]
                            move = Move(
                                'SEQUENCE_CASCADE_TO_CASCADE',
                                cascade_idx,
                                to_cascade_idx,
                                card,
                                count=count,
                            )

                        successors.append((new_state, move))
        
        # Try moves from free cells
        for free_cell_idx in range(4):
            card = state.get_free_cell(free_cell_idx)
            if card is None:
                continue

            # Free cell to cascade
            for cascade_idx in range(8):
                if FreeCell.can_move_freecell_to_cascade(state, free_cell_idx, cascade_idx):
                    new_state = FreeCell.move_freecell_to_cascade(state, free_cell_idx, cascade_idx)
                    move = Move('FREECELL_TO_CASCADE', free_cell_idx, cascade_idx, card)
                    successors.append((new_state, move))
        
        return successors
