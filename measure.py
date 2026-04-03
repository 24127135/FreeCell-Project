import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import tracemalloc
import time

from game import Card, GameState, FreeCell

from solvers.astar_solver import AStarSolver
from solvers.bfs_solver import BFSSolver
from solvers.dfs_solver import DFSSolver
from solvers.ucs_solver import UCSSolver


TEST_TIME_LIMIT_SECONDS = 180


def _rows(*cards):
    row = []
    for card in cards:
        if card is None:
            row.append(None)
            continue
        rank, suit = card
        row.append(Card(rank, suit))
    return row


def _state_from_rows(rows, foundations=None, free_cells=None):
    if foundations is None:
        foundations = {"S": 0, "C": 0, "H": 0, "D": 0}
    if free_cells is None:
        free_cells = [None] * 4

    cascades = [[] for _ in range(8)]
    for row in reversed(rows):
        for column_index, card in enumerate(row):
            if card is None:
                continue
            cascades[column_index].append(card)

    return GameState(cascades=cascades, free_cells=free_cells, foundations=foundations)


def _state_from_columns(columns, foundations=None, free_cells=None):
    if foundations is None:
        foundations = {"S": 0, "C": 0, "H": 0, "D": 0}
    if free_cells is None:
        free_cells = [None] * 4

    cascades = []
    for column in columns:
        cascades.append([Card(rank, suit) for rank, suit in column])
    return GameState(cascades=cascades, free_cells=free_cells, foundations=foundations)


def _state_from_deal(deal_number):
    return FreeCell.create_initial_state(deal_number=deal_number)


def _state_game1_foundation_progress():
    base = FreeCell.create_initial_state(deal_number=1)
    cascades = []
    for cascade in base.cascades:
        cascades.append([card for card in cascade if card.rank > 6])
    foundations = {"S": 6, "C": 6, "H": 6, "D": 6}
    return GameState(cascades=cascades, free_cells=[None] * 4, foundations=foundations)


def _state_game1_late_16():
    foundations = {"C": 9, "D": 9, "S": 9, "H": 9}
    columns = [
        [(10, "S"), (11, "H"), (12, "S"), (13, "H")],
        [(10, "D"), (11, "S"), (12, "D"), (13, "S")],
        [(10, "C"), (11, "D"), (12, "C"), (13, "D")],
        [(10, "H"), (11, "C"), (12, "H"), (13, "C")],
        [],
        [],
        [],
        [],
    ]
    return _state_from_columns(columns, foundations=foundations, free_cells=[None] * 4)


def _state_game1_late_12():
    foundations = {"C": 10, "D": 10, "S": 10, "H": 10}
    columns = [
        [(11, "S"), (12, "H"), (13, "S")],
        [(11, "D"), (12, "S"), (13, "D")],
        [(11, "C"), (12, "D"), (13, "C")],
        [(11, "H"), (12, "C"), (13, "H")],
        [],
        [],
        [],
        [],
    ]
    return _state_from_columns(columns, foundations=foundations, free_cells=[None] * 4)


def _state_game1_late_10():
    # Layout provided as "10 cards remaining" contains 8 cascade cards; foundations follow provided values.
    foundations = {"C": 11, "D": 11, "S": 11, "H": 11}
    columns = [
        [(12, "S"), (13, "H")],
        [(12, "D"), (13, "S")],
        [(12, "C"), (13, "D")],
        [(12, "H"), (13, "C")],
        [],
        [],
        [],
        [],
    ]
    return _state_from_columns(columns, foundations=foundations, free_cells=[None] * 4)


def _pop_card_once(cascades, rank, suit):
    for cascade in cascades:
        for index, card in enumerate(cascade):
            if card.rank == rank and card.suit == suit:
                return cascade.pop(index)
    raise ValueError(f"Card {rank}{suit} not found when building scenario")


def _state_game1941_freecell_clog():
    base = FreeCell.create_initial_state(deal_number=1941)
    cascades = []
    for cascade in base.cascades:
        cascades.append(
            [card for card in cascade if not (card.suit in {"C", "D"} and card.rank <= 5)]
        )

    free_cells = [
        _pop_card_once(cascades, 13, "H"),
        _pop_card_once(cascades, 12, "S"),
        _pop_card_once(cascades, 11, "D"),
        _pop_card_once(cascades, 10, "S"),
    ]
    foundations = {"S": 0, "C": 5, "H": 0, "D": 5}
    return GameState(cascades=cascades, free_cells=free_cells, foundations=foundations)


SCENARIOS = {
    "1-start": {
        "label": "Game #1 (Start: 52 Cards)",
        "state_builder": lambda: _state_from_deal(1),
    },
    "1-mid": {
        "label": "Game #1 (Mid-Game: 28 Cards Remaining)",
        "state_builder": _state_game1_foundation_progress,
    },
    "1-late16": {
        "label": "Game #1 (Late-Game: 16 Cards Remaining)",
        "state_builder": _state_game1_late_16,
    },
    "1-late12": {
        "label": "Game #1 (Late-Game: 12 Cards Remaining)",
        "state_builder": _state_game1_late_12,
    },
    "1-late10": {
        "label": "Game #1 (Late-Game: 10 Cards Remaining)",
        "state_builder": _state_game1_late_10,
    },
}

FIXED_TEST_SET_ORDER = ["1-start", "1-mid", "1-late16", "1-late12", "1-late10"]

# --- MAIN GUI CLASS ---
class AlgorithmTesterUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FreeCell Algorithm Tester")
        self.root.geometry("700x580")
        
        self.filename = "results_ui.txt"
        self.saved_results = {}
        self.fixed_testcases = SCENARIOS
        self.case_label_to_key = {data["label"]: case_key for case_key, data in SCENARIOS.items()}
        self.case_keys = FIXED_TEST_SET_ORDER
        self._timer_after_id = None
        self._timer_started_at = None
        self._timer_prefix = "Elapsed"
        self.timer_var = tk.StringVar(value="Elapsed: 00:00")
        
        self._initialize_file()
        self.setup_ui()

    def _initialize_file(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write("UI TESTER RESULTS REPORT\n")
            f.write("="*40 + "\n\n")

    def setup_ui(self):
        # 1. Configuration Frame
        frame_config = tk.LabelFrame(self.root, text="1. Problem Configuration", padx=10, pady=10)
        frame_config.pack(fill="x", padx=10, pady=5)

        frame_tc = tk.Frame(frame_config)
        frame_tc.pack(fill="x", pady=(0, 5))
        tk.Label(frame_tc, text="Select Test Case:").pack(side="left")
        default_label = self.fixed_testcases[self.case_keys[0]]["label"]
        self.testcase_var = tk.StringVar(value=default_label)
        self.testcase_combo = ttk.Combobox(
            frame_tc,
            textvariable=self.testcase_var,
            values=[self.fixed_testcases[key]["label"] for key in self.case_keys],
            state="readonly",
            width=38,
        )
        self.testcase_combo.pack(side="left", padx=10)
        self.testcase_var.trace_add("write", lambda *_: self._refresh_case_preview())

        frame_opts = tk.Frame(frame_config)
        frame_opts.pack(fill="x")
        self.foundation_priority_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frame_opts, 
            text="Enable Foundation Priority Mode", 
            variable=self.foundation_priority_var,
            onvalue=True,
            offvalue=False
        ).pack(side="left")

        # 2. Algorithm Control Frame 
        frame_mid = tk.LabelFrame(self.root, text="2. Run Algorithms", padx=10, pady=10)
        frame_mid.pack(fill="x", padx=10, pady=5)

        self.btn_astar = tk.Button(frame_mid, text="Run A*", width=12, command=lambda: self.start_thread("A* Search", AStarSolver(debug=False, max_time_seconds=TEST_TIME_LIMIT_SECONDS)))
        self.btn_astar.pack(side="left", padx=5)

        self.btn_bfs = tk.Button(frame_mid, text="Run BFS", width=12, command=lambda: self.start_thread("BFS", BFSSolver(debug=False, max_expansions=2000000, max_time_seconds=TEST_TIME_LIMIT_SECONDS)))
        self.btn_bfs.pack(side="left", padx=5)

        self.btn_dfs = tk.Button(frame_mid, text="Run DFS", width=12, command=lambda: self.start_thread("DFS", DFSSolver(debug=False, max_depth=800, max_time_seconds=TEST_TIME_LIMIT_SECONDS)))
        self.btn_dfs.pack(side="left", padx=5)

        self.btn_ucs = tk.Button(frame_mid, text="Run UCS", width=12, command=lambda: self.start_thread("UCS", UCSSolver(debug=False, max_time_seconds=TEST_TIME_LIMIT_SECONDS)))
        self.btn_ucs.pack(side="left", padx=5)

        self.btn_batch = tk.Button(
            frame_mid,
            text="Run Fixed Set",
            width=14,
            command=self.start_batch_thread,
            bg="#ffe9b3",
        )
        self.btn_batch.pack(side="left", padx=5)

        timer_row = tk.Frame(frame_mid)
        timer_row.pack(fill="x", pady=(8, 0))
        tk.Label(
            timer_row,
            textvariable=self.timer_var,
            font=("Consolas", 10, "bold"),
            anchor="w",
            fg="#1d3557",
        ).pack(side="left")

        # 2b. Current Shuffle Preview
        frame_preview = tk.LabelFrame(self.root, text="2b. Current Shuffle Preview", padx=10, pady=10)
        frame_preview.pack(fill="x", padx=10, pady=5)

        self.preview_text = scrolledtext.ScrolledText(frame_preview, wrap=tk.WORD, font=("Consolas", 10), height=10)
        self.preview_text.pack(fill="both", expand=True)
        self.preview_text.configure(state=tk.DISABLED)
        self._refresh_case_preview()

        # 3. Log Display Frame
        frame_bot = tk.LabelFrame(self.root, text="3. Measurement Results", padx=10, pady=10)
        frame_bot.pack(fill="both", expand=True, padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(frame_bot, wrap=tk.WORD, font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True)

    def log(self, message):
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)

    def _start_run_timer(self, prefix="Elapsed"):
        self._stop_run_timer()
        self._timer_prefix = prefix
        self._timer_started_at = time.time()
        self._tick_run_timer()

    def _tick_run_timer(self):
        if self._timer_started_at is None:
            return
        elapsed = int(time.time() - self._timer_started_at)
        minutes, seconds = divmod(elapsed, 60)
        self.timer_var.set(f"{self._timer_prefix}: {minutes:02d}:{seconds:02d}")
        self._timer_after_id = self.root.after(250, self._tick_run_timer)

    def _stop_run_timer(self):
        if self._timer_after_id is not None:
            try:
                self.root.after_cancel(self._timer_after_id)
            except Exception:
                pass
            self._timer_after_id = None
        self._timer_started_at = None

    def toggle_buttons(self, state):
        for btn in [self.btn_astar, self.btn_bfs, self.btn_dfs, self.btn_ucs, self.btn_batch]:
            btn.config(state=state)

    def _current_case_key(self):
        return self.case_label_to_key.get(self.testcase_var.get(), self.case_keys[0])

    def _get_case_label(self, case_key):
        return self.fixed_testcases.get(case_key, SCENARIOS[self.case_keys[0]])["label"]

    def _get_case_state(self, case_key):
        data = self.fixed_testcases.get(case_key, SCENARIOS[self.case_keys[0]])
        if "state_builder" in data:
            return data["label"], data["state_builder"]()
        return data["label"], _state_from_rows(
            data["rows"],
            foundations=data.get("foundations"),
            free_cells=data.get("free_cells"),
        )

    def _refresh_case_preview(self):
        case_key = self._current_case_key()
        case_name, state = self._get_case_state(case_key)

        free_cell_tokens = [str(card) if card is not None else "--" for card in state.free_cells]
        foundations_text = (
            f"Foundations: C:{state.foundations.get('C', 0)} "
            f"D:{state.foundations.get('D', 0)} "
            f"H:{state.foundations.get('H', 0)} "
            f"S:{state.foundations.get('S', 0)}"
        )

        lines = [
            case_name,
            "",
            foundations_text,
            f"FreeCells: {', '.join(free_cell_tokens)}",
            "",
            "Current layout (top to bottom rows):",
        ]

        max_height = max((len(cascade) for cascade in state.cascades), default=0)
        for row_index in range(max_height):
            row_cards = []
            for column_index in range(8):
                cascade = state.cascades[column_index]
                card_idx = len(cascade) - 1 - row_index
                if card_idx >= 0:
                    row_cards.append(str(cascade[card_idx]))
                else:
                    row_cards.append("--")
            lines.append(f"Row {row_index + 1}: {'  '.join(row_cards)}")

        preview = "\n".join(lines)
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert(tk.END, preview)
        self.preview_text.configure(state=tk.DISABLED)

    def start_thread(self, name, solver):
        self.toggle_buttons(tk.DISABLED) 
        self._start_run_timer(prefix=f"{name} elapsed")
        case_key = self._current_case_key()
        case_name = self._get_case_label(case_key)
        priority_status = "ON" if self.foundation_priority_var.get() else "OFF"
        
        self.log(f"\n[RUNNING] {name} - Test case {case_name} (Priority: {priority_status})... Please wait.")
        
        thread = threading.Thread(target=self.run_algorithm, args=(name, solver, case_key, self.foundation_priority_var.get(), False))
        thread.daemon = True
        thread.start()

    def start_batch_thread(self):
        self.toggle_buttons(tk.DISABLED)
        self._start_run_timer(prefix="Batch elapsed")
        priority_val = self.foundation_priority_var.get()
        priority_status = "ON" if priority_val else "OFF"
        self.log(
            f"\n[RUNNING] Fixed test set ({', '.join(self._get_case_label(key) for key in FIXED_TEST_SET_ORDER)}) "
            f"with priority {priority_status}."
        )

        thread = threading.Thread(target=self.run_fixed_test_set, args=(priority_val,))
        thread.daemon = True
        thread.start()

    def run_fixed_test_set(self, priority_val):
        solver_builders = [
            ("A* Search", lambda: AStarSolver(debug=False, max_time_seconds=TEST_TIME_LIMIT_SECONDS)),
            ("BFS", lambda: BFSSolver(debug=False, max_expansions=600000, max_time_seconds=TEST_TIME_LIMIT_SECONDS)),
            ("DFS", lambda: DFSSolver(debug=False, max_depth=800, max_time_seconds=TEST_TIME_LIMIT_SECONDS)),
            ("UCS", lambda: UCSSolver(debug=False, max_time_seconds=TEST_TIME_LIMIT_SECONDS)),
        ]

        total_jobs = len(FIXED_TEST_SET_ORDER) * len(solver_builders)
        done_jobs = 0

        try:
            for case_key in FIXED_TEST_SET_ORDER:
                case_name = self._get_case_label(case_key)
                for solver_name, builder in solver_builders:
                    done_jobs += 1
                    self.root.after(
                        0,
                        self.log,
                        f"[BATCH] ({done_jobs}/{total_jobs}) Running {solver_name} on {case_name}...",
                    )
                    self.run_algorithm(solver_name, builder(), case_key, priority_val, True)

            self.root.after(0, self.log, "[DONE] Fixed test set run completed.")
        except Exception as exc:
            self.root.after(0, self.log, f"[ERROR] Batch run stopped: {exc}")
        finally:
            self.root.after(0, self._stop_run_timer)
            self.root.after(0, self.toggle_buttons, tk.NORMAL)

    def run_algorithm(self, name, solver, case_key, priority_val, keep_buttons_disabled=False):
        case_name, state = self._get_case_state(case_key)

        tracemalloc.start()
        try:
            path, stats = solver.solve(state, progress_callback=None, foundation_priority_mode=priority_val)
            _current_mem, peak_mem = tracemalloc.get_traced_memory()
        except Exception as exc:
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            self.root.after(0, self.log, f"[ERROR] {name} crashed on {case_name}: {exc}")
            if not keep_buttons_disabled:
                self.root.after(0, self._stop_run_timer)
                self.root.after(0, self.toggle_buttons, tk.NORMAL)
            return
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()

        # Process metrics
        peak_mb = peak_mem / (1024 * 1024)
        search_time = stats.get('time_taken', 0.0)
        expanded_nodes = stats.get('expanded_nodes', 0)
        termination_reason = stats.get('terminated_by', None)
        
        if path is not None:
            solution_length = str(len(path))
            status_msg = "SUCCESS"
        else:
            if termination_reason == "time_limit":
                solution_length = "N/A (Timeout)"
                status_msg = "FAILED (Timeout)"
            elif termination_reason == "expansion_limit":
                solution_length = "N/A (Node Limit)"
                status_msg = "FAILED (Hit Limit)"
            else:
                solution_length = "N/A (No Solution)"
                status_msg = "FAILED"

        # Format result text
        result_text = (
            f"--- {name} [{status_msg}] ---\n"
            f"  * Search time: {search_time:.4f} seconds\n"
            f"  * Memory usage (peak memory): {peak_mb:.4f} MB\n"
            f"  * Expanded nodes: {expanded_nodes}\n"
            f"  * Solution length: {solution_length}\n"
            f"{'-'*40}"
        )

        config_key = (case_key, priority_val, name)
        self.saved_results[config_key] = result_text
        self._rewrite_file()

        self.root.after(0, self.log, f"[Test case {case_name} | {'Priority ON' if priority_val else 'Priority OFF'}]\n{result_text}")
        if not keep_buttons_disabled:
            self.root.after(0, self._stop_run_timer)
            self.root.after(0, self.toggle_buttons, tk.NORMAL)

    def _rewrite_file(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write("UI TESTER RESULTS REPORT\n")
            f.write("="*40 + "\n\n")

            grouped = {}
            for (case_val, priority_val, solver_name), res_text in self.saved_results.items():
                case_str = self._get_case_label(case_val)
                key = (case_str, bool(priority_val))
                grouped.setdefault(key, []).append((solver_name, res_text))

            for (case_str, priority_val), rows in sorted(
                grouped.items(), key=lambda item: (item[0][0], not item[0][1])
            ):
                priority_str = "Priority ON" if priority_val else "Priority OFF"
                f.write(f"[Test case {case_str} | {priority_str}]\n")
                for _solver_name, res_text in sorted(rows, key=lambda item: item[0]):
                    f.write(res_text + "\n")
                f.write("\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = AlgorithmTesterUI(root)
    root.mainloop()