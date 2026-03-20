"""
Card class for FreeCell solitaire game.
Represents a single playing card with rank and suit.
"""

class Card:
    """
    Represents a single playing card in FreeCell.
    
    Attributes:
        rank (int): Card rank from 1 (Ace) to 13 (King)
        suit (str): Card suit - 'H' (Hearts), 'D' (Diamonds), 'C' (Clubs), 'S' (Spades)
    """
    
    # Rank names for display
    RANK_NAMES = {1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
                  8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K'}
    
    # Suit colors - Red or Black
    SUIT_COLORS = {'H': 'Red', 'D': 'Red', 'C': 'Black', 'S': 'Black'}
    
    def __init__(self, rank, suit):
        """
        Initialize a Card.
        
        Args:
            rank (int): Card rank (1-13, where 1=Ace, 11=Jack, 12=Queen, 13=King)
            suit (str): Card suit ('H', 'D', 'C', 'S')
            
        Raises:
            ValueError: If rank or suit are invalid
        """
        if not (1 <= rank <= 13):
            raise ValueError(f"Invalid rank: {rank}. Rank must be 1-13.")
        if suit not in ['H', 'D', 'C', 'S']:
            raise ValueError(f"Invalid suit: {suit}. Suit must be H, D, C, or S.")
        
        self.rank = rank
        self.suit = suit
    
    def get_color(self):
        """
        Get the color of this card (Red or Black).
        
        Returns:
            str: 'Red' for Hearts/Diamonds, 'Black' for Clubs/Spades
        """
        return self.SUIT_COLORS[self.suit]
    
    def has_alternating_color(self, other_card):
        """
        Check if this card has alternating color with another card.
        Used in FreeCell cascade stacking rules.
        
        Args:
            other_card (Card): Card to compare with
            
        Returns:
            bool: True if colors are different
        """
        if other_card is None:
            return True
        return self.get_color() != other_card.get_color()
    
    def can_stack_on(self, other_card):
        """
        Check if this card can be stacked on another card according to FreeCell rules.
        This card must:
        - Have rank exactly 1 less than the other card
        - Have alternating color from the other card
        
        Args:
            other_card (Card): The card to stack this card on
            
        Returns:
            bool: True if this card can be stacked on the other card
        """
        if other_card is None:
            return False
        
        # Check rank sequence (this should be 1 less than other)
        if self.rank != other_card.rank - 1:
            return False
        
        # Check color alternation
        return self.has_alternating_color(other_card)
    
    def is_ace(self):
        """Check if this card is an Ace."""
        return self.rank == 1
    
    def is_king(self):
        """Check if this card is a King."""
        return self.rank == 13
    
    def __str__(self):
        """Return string representation like 'AH' or '7C'."""
        return f"{self.RANK_NAMES[self.rank]}{self.suit}"
    
    def __repr__(self):
        """Return representative string."""
        return f"Card({self.rank}, '{self.suit}')"
    
    def __eq__(self, other):
        """Check if two cards are equal."""
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit
    
    def __hash__(self):
        """Return hash of card for use in sets and dicts."""
        return hash((self.rank, self.suit))
