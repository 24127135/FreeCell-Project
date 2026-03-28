from game import Card, GameState
from gui.interface import FreeCell_GUI

def run_animated_test():
    app = FreeCell_GUI()
    foundations = {'H': 13, 'C': 13, 'S': 6, 'D': 0}
    cascades = [
        [Card(7, 'S'), Card(8, 'S'), Card(9, 'S')],
        [Card(10, 'S'), Card(11, 'S'), Card(12, 'S')],
        [Card(13, 'S'), Card(1, 'D'), Card(2, 'D')],
        [Card(3, 'D'), Card(4, 'D'), Card(5, 'D')],
        [Card(6, 'D'), Card(7, 'D')],
        [Card(8, 'D'), Card(9, 'D')],
        [Card(10, 'D'), Card(11, 'D')],
        [Card(12, 'D'), Card(13, 'D')]
    ]
    
    free_cells = [None, None, None, None]

    state_20 = GameState(cascades=cascades, free_cells=free_cells, foundations=foundations)

    app.state = state_20
    app.initial_state = state_20.copy()
    app.render()
    app.run()

if __name__ == "__main__":
    run_animated_test()