# FreeCell Solver Project

## Overview

A Python implementation of FreeCell solitaire with AI solvers using multiple search algorithms:
- Breadth-First Search (BFS)
- Depth-First Search (DFS)
- Uniform-Cost Search (UCS)
- A* Search

## Project Structure

```
freecell/
├── main.py                 # Entry point - initializes and tests all modules
├── __init__.py            # Package initialization
│
├── game/                   # Game logic and rules
│   ├── __init__.py
│   ├── card.py            # Card class (rank, suit, color, comparison)
│   ├── state.py           # GameState class (cascades, free cells, foundations)
│   └── freecell.py        # FreeCell rules engine & move validation
│
├── solvers/               # Search algorithm implementations
│   ├── __init__.py
│   ├── bfs_solver.py      # Breadth-First Search
│   ├── dfs_solver.py      # Depth-First Search
│   ├── ucs_solver.py      # Uniform-Cost Search
│   └── astar_solver.py    # A* Search
│
├── gui/                   # Graphical User Interface
│   ├── __init__.py
│   └── interface.py       # Tkinter-based GUI
│
├── utils/                 # Helper modules
│   ├── __init__.py
│   └── heuristics.py      # Heuristic functions for A*
│
└── experiments/           # Performance analysis
    ├── __init__.py
    └── analysis.py        # Metrics collection and visualization
```

## Completed Components

### ✅ Game Module (100% Complete)

#### Card Class (`game/card.py`)
- Represents cards with rank (1-13) and suit (H/D/C/S)
- Color detection (Red/Black)
- Alternating color checking
- Stacking rules validation
- Hashable for use in sets/dicts
- String representation (e.g., "7H", "KD")

#### GameState Class (`game/state.py`)
- Represents complete board configuration
- 8 cascade piles (lists of cards)
- 4 free cells (single cards each)
- 4 foundation piles (tracks highest rank per suit)
- Deep copy support for search algorithms
- State comparison and hashing
- Pretty-print board display

#### FreeCell Rules (`game/freecell.py`)
- Move class for representing moves
- Complete move validation:
  - Cascade to cascade
  - Cascade to free cell
  - Free cell to cascade
  - Cascade to foundation
  - Free cell to foundation
- State execution (creates new states from moves)
- **Successor generation** - critical function for search algorithms
- Returns all valid next states from current state

### ✅ Solver Modules (Framework Ready)
- `bfs_solver.py` - BFS implementation placeholder
- `dfs_solver.py` - DFS implementation placeholder
- `ucs_solver.py` - UCS implementation placeholder
- `astar_solver.py` - A* implementation placeholder

All solvers have the same interface: `solve(initial_state)` → `(solution_path, metrics)`

### ✅ Supporting Modules
- **GUI Module** - Tkinter framework placeholder
- **Utils Module** - Heuristics placeholder
- **Experiments Module** - Performance analysis placeholder

### ✅ Entry Point (`main.py`)
- Verifies all modules import correctly
- Tests Card, GameState, and FreeCell functionality
- Confirms game state generation works

## How to Run

```bash
cd c:\Users\truon\Dev\OS\freecell
py main.py
```

Expected output:
```
============================================================
FreeCell Solver - Main Entry Point
============================================================

Project successfully initialized!
All modules imported successfully.

[...test output showing Card creation, StateState creation, successor generation...]

============================================================
All tests passed! Project is ready for development.
============================================================
```

## Key Features Implemented

### Card Class Features
- ✓ Rank validation (1-13)
- ✓ Suit validation (H/D/C/S)
- ✓ Color mapping (Red: H/D, Black: C/S)
- ✓ Alternating color detection
- ✓ Stack compatibility checking
- ✓ Hashable for visited state tracking

### GameState Class Features
- ✓ 8 cascades, 4 free cells, 4 foundations
- ✓ Deep copy for state branching
- ✓ State equality comparison
- ✓ State hashing for visited sets
- ✓ Goal state detection
- ✓ Pretty-print display

### FreeCell Rules Engine Features
- ✓ All 5 move types supported
- ✓ Complete move validation
- ✓ Safe state execution (creates new states)
- ✓ **Successor generation** (crucial for search algorithms)
- ✓ Foundation priority moves

## Next Steps (According to Project Timeline)

### Week 1 (Remaining Tasks)
1. **BFS/DFS Solvers** - Implement search algorithms with visited tracking
2. **Solution Reconstruction** - Build move sequences from search trees
3. **UCS/A* Solvers** - Implement advanced algorithms
4. **Heuristics** - Design heuristic functions for A*

### Week 2
1. **GUI Implementation** - Create Tkinter interface with card display
2. **GUI Integration** - Connect GUI with solver modules
3. **Performance Metrics** - Measure search time, memory, expanded nodes
4. **Testing & Debugging** - Comprehensive testing of all algorithms
5. **Report Writing** - Document system architecture and results

## Development Notes

### For Search Algorithm Developers
The `FreeCell.get_successors(state)` function returns a list of `(new_state, move)` tuples representing all valid moves from the current state. This is your main interface to the game logic.

Example usage:
```python
from game import GameState, FreeCell

state = GameState()  # Initial state
successors = FreeCell.get_successors(state)

for next_state, move in successors:
    print(f"Moving {move.card}: {move.move_type}")
    next_state_copy = next_state.copy()  # Safe to modify
```

### For GUI Developers
The GameState class includes a `__str__()` method that pretty-prints the board. Use this for debugging and UI display.

```python
print(state)  # Displays cascades, free cells, foundations
```

### State Hashing
Both Card and GameState are hashable, so you can use them directly in sets and dicts:
```python
visited = {state}  # Works!
visited.add(another_state)
```

## Technology Stack
- **Language**: Python 3
- **GUI**: Tkinter (standard library)
- **Visualization**: Matplotlib
- **Data Structures**: heapq, collections.deque

## Testing Status
✅ All core components tested and working
✅ Move validation tested
✅ Successor generation working
✅ State hashing working
✅ Deep copy working

Ready for solver implementation!
