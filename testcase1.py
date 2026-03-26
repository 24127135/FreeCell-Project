from game import Card, GameState
from gui.interface import FreeCell_GUI

def run_animated_test():
    app = FreeCell_GUI()
    foundations = {'S': 9, 'C': 10, 'H': 10, 'D': 10}

    cascades = [
        [Card(10, 'S'), Card(12, 'H')],
        [Card(11, 'C'), Card(13, 'D')],
        [Card(11, 'H'), Card(13, 'S')],
        [Card(11, 'D'), Card(13, 'C')],
        [Card(11, 'S'), Card(13, 'H')],
        [Card(12, 'C')],
        [Card(12, 'D')],
        [Card(12, 'S')]
    ]
    free_cells = [None, None, None, None]

    state_13 = GameState(cascades=cascades, free_cells=free_cells, foundations=foundations)

    app.state = state_13
    app.initial_state = state_13.copy()
    app.render()
    app.run()

if __name__ == "__main__":
    run_animated_test()