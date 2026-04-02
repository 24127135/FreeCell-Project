from game import Card, GameState
from gui.interface import FreeCell_GUI


SCENARIOS = {
    "testcase1": {
        "foundations": {"S": 9, "C": 10, "H": 10, "D": 10},
        "cascades": [
            [Card(10, "S"), Card(12, "H")],
            [Card(11, "C"), Card(13, "D")],
            [Card(11, "H"), Card(13, "S")],
            [Card(11, "D"), Card(13, "C")],
            [Card(11, "S"), Card(13, "H")],
            [Card(12, "C")],
            [Card(12, "D")],
            [Card(12, "S")],
        ],
    },
    "testcase2": {
        "foundations": {"H": 13, "C": 13, "S": 6, "D": 0},
        "cascades": [
            [Card(7, "S"), Card(8, "S"), Card(9, "S")],
            [Card(10, "S"), Card(11, "S"), Card(12, "S")],
            [Card(13, "S"), Card(1, "D"), Card(2, "D")],
            [Card(3, "D"), Card(4, "D"), Card(5, "D")],
            [Card(6, "D"), Card(7, "D")],
            [Card(8, "D"), Card(9, "D")],
            [Card(10, "D"), Card(11, "D")],
            [Card(12, "D"), Card(13, "D")],
        ],
    },
    "test_ucs": {
        "foundations": {"H": 13, "D": 13, "C": 13, "S": 9},
        "cascades": [
            [Card(10, "S"), Card(13, "S")],
            [Card(11, "S"), Card(12, "S")],
            [],
            [],
            [],
            [],
            [],
            [],
        ],
    },
}


def run_manual_scenario(name):
    if name not in SCENARIOS:
        valid = ", ".join(sorted(SCENARIOS.keys()))
        raise ValueError(f"Unknown scenario '{name}'. Valid options: {valid}")

    scenario = SCENARIOS[name]
    app = FreeCell_GUI()

    state = GameState(
        cascades=scenario["cascades"],
        free_cells=[None, None, None, None],
        foundations=scenario["foundations"],
    )

    app.state = state
    app.initial_state = state.copy()
    app.render()
    app.run()


if __name__ == "__main__":
    import sys

    scenario_name = sys.argv[1] if len(sys.argv) > 1 else "testcase1"
    run_manual_scenario(scenario_name)
