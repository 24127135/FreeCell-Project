from game import Card, GameState
from gui.interface import FreeCell_GUI


def run_animated_test_harder():
    app = FreeCell_GUI()

    foundations = {'H': 13, 'D': 13, 'C': 13, 'S': 9}

    cascades = [
        [Card(10, 'S'), Card(13, 'S')],
        [Card(11, 'S'), Card(12, 'S')],
        [], [], [], [], [], []
    ]
    free_cells = [None, None, None, None]

    harder_state = GameState(cascades=cascades, free_cells=free_cells, foundations=foundations)

    app.state = harder_state
    app.initial_state = harder_state.copy()
    app.render()
    app.run()


if __name__ == "__main__":
    run_animated_test_harder()