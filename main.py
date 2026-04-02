"""
FreeCell Solver - Main Entry Point
Implements a playable FreeCell card game with AI solvers using various search algorithms.
"""

import sys

from game import Card, FreeCell, GameState
from gui import FreeCell_GUI
    
def main():
    gui = FreeCell_GUI()
    gui.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
