# FreeCell Solver Project

## Overview

This repository contains a Python implementation of FreeCell with:
- Core game rules and state transitions
- A playable Tkinter interface
- Solver module stubs (BFS, DFS, UCS, A*)
- Experiment and heuristic scaffolding

## Repository Layout

```text
freecell/
  main.py
  demo.py
  game/
    card.py
    state.py
    freecell.py
  gui/
    interface.py
  solvers/
    bfs_solver.py
    dfs_solver.py
    ucs_solver.py
    astar_solver.py
  utils/
    heuristics.py
  experiments/
    analysis.py
```

## Implemented Components

### Game Engine
- Card model with rank, suit, color, and tableau stacking checks
- Game state model with cascades, free cells, and foundations
- Move validation and execution for all standard move types
- Successor generation for search algorithms
- Supermove capacity rules aligned with standard FreeCell conventions

### GUI
- Tkinter-based playable interface
- Drag-and-drop card movement
- Numbered deal support
- Undo and hint actions
- Automatic legal foundation moves

### Solver and Analysis Modules
- Solver classes are defined with consistent interfaces
- Heuristic and experiment modules are scaffolded for implementation

## Run

From the repository root:

```bash
.\.venv\Scripts\python.exe main.py
```

Run the built-in self-test:

```bash
.\.venv\Scripts\python.exe main.py --self-test
```

## Development Notes

- Main game API entry points are in `game/freecell.py`.
- GUI behavior is implemented in `gui/interface.py`.
- Solver stubs intentionally raise `NotImplementedError` until implemented.

## Status

Core gameplay and GUI are functional. Solver algorithms and experiment analysis remain to be implemented.
