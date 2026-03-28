import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import tracemalloc

from game import Card, GameState
from gui.interface import FreeCell_GUI

from solvers.astar_solver import AStarSolver
from solvers.bfs_solver import BFSSolver
from solvers.dfs_solver import DFSSolver
from solvers.ucs_solver import UCSSolver

def get_11_cards_state():
    foundations = {'S': 11, 'C': 10, 'H': 10, 'D': 10}

    cascades = [
        [Card(12, 'S'), Card(13, 'H')],
        [Card(11, 'C'), Card(12, 'D')],
        [Card(11, 'H'), Card(13, 'S')],
        [Card(11, 'D'), Card(12, 'C')],
        [Card(12, 'H'), Card(13, 'D')],
        [Card(13, 'C')],
        [],
        []
    ]
    return GameState(cascades=cascades, free_cells=[None]*4, foundations=foundations)

def get_10_cards_state():
    foundations = {'S': 11, 'C': 11, 'H': 10, 'D': 10}

    cascades = [
        [Card(12, 'S'), Card(13, 'H')],
        [Card(12, 'C'), Card(13, 'D')],
        [Card(11, 'H'), Card(13, 'S')],
        [Card(11, 'D'), Card(13, 'C')],
        [Card(12, 'H')],
        [Card(12, 'D')],
        [],
        []
    ]
    return GameState(cascades=cascades, free_cells=[None]*4, foundations=foundations)

# --- MAIN GUI CLASS ---
class AlgorithmTesterUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FreeCell Algorithm Tester")
        self.root.geometry("700x580")
        
        self.filename = "results_ui.txt"
        self.saved_results = {} 
        
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
        self.testcase_var = tk.StringVar(value="11")
        tk.Radiobutton(frame_tc, text="11 Cards", variable=self.testcase_var, value="11").pack(side="left", padx=10)
        tk.Radiobutton(frame_tc, text="10 Cards", variable=self.testcase_var, value="10").pack(side="left", padx=10)

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

        self.btn_astar = tk.Button(frame_mid, text="Run A*", width=12, command=lambda: self.start_thread("A* Search", AStarSolver(debug=False)))
        self.btn_astar.pack(side="left", padx=5)

        self.btn_bfs = tk.Button(frame_mid, text="Run BFS", width=12, command=lambda: self.start_thread("BFS", BFSSolver(debug=False, max_expansions=2000000, max_time_seconds=600)))
        self.btn_bfs.pack(side="left", padx=5)

        self.btn_dfs = tk.Button(frame_mid, text="Run DFS", width=12, command=lambda: self.start_thread("DFS", DFSSolver(debug=False, max_depth=800, max_time_seconds=600)))
        self.btn_dfs.pack(side="left", padx=5)

        self.btn_ucs = tk.Button(frame_mid, text="Run UCS", width=12, command=lambda: self.start_thread("UCS", UCSSolver(debug=False)))
        self.btn_ucs.pack(side="left", padx=5)

        frame_game = tk.Frame(self.root)
        frame_game.pack(fill="x", padx=10, pady=5)
        tk.Button(frame_game, text="Open FreeCell Game GUI", command=self.open_game_gui, bg="lightblue").pack(side="right")

        # 3. Log Display Frame
        frame_bot = tk.LabelFrame(self.root, text="3. Measurement Results", padx=10, pady=10)
        frame_bot.pack(fill="both", expand=True, padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(frame_bot, wrap=tk.WORD, font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True)

    def log(self, message):
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)

    def toggle_buttons(self, state):
        for btn in [self.btn_astar, self.btn_bfs, self.btn_dfs, self.btn_ucs]:
            btn.config(state=state)

    def open_game_gui(self):
        state = get_11_cards_state() if self.testcase_var.get() == "11" else get_10_cards_state()
        app = FreeCell_GUI()
        app.state = state.copy()
        app.initial_state = state.copy()
        app.foundation_priority_var.set(self.foundation_priority_var.get())
        app.render()
        app.run()

    def start_thread(self, name, solver):
        self.toggle_buttons(tk.DISABLED) 
        case_name = "11 cards" if self.testcase_var.get() == "11" else "10 cards"
        priority_status = "ON" if self.foundation_priority_var.get() else "OFF"
        
        self.log(f"\n[RUNNING] {name} - Test case {case_name} (Priority: {priority_status})... Please wait.")
        
        thread = threading.Thread(target=self.run_algorithm, args=(name, solver, self.testcase_var.get(), self.foundation_priority_var.get()))
        thread.daemon = True
        thread.start()

    def run_algorithm(self, name, solver, case_val, priority_val):
        state = get_11_cards_state() if case_val == "11" else get_10_cards_state()
        
        # Start tracing memory
        tracemalloc.start()
        
        path, stats = solver.solve(state, progress_callback=None, foundation_priority_mode=priority_val)
        
        # Stop tracing memory
        current_mem, peak_mem = tracemalloc.get_traced_memory()
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

        config_key = (case_val, priority_val, name)
        self.saved_results[config_key] = result_text
        self._rewrite_file()

        self.root.after(0, self.log, result_text)
        self.root.after(0, self.toggle_buttons, tk.NORMAL)

    def _rewrite_file(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write("UI TESTER RESULTS REPORT\n")
            f.write("="*40 + "\n\n")
            
            for key, res_text in self.saved_results.items():
                case_val, priority_val, _ = key
                case_str = "11 cards" if case_val == "11" else "10 cards"
                priority_str = "Priority ON" if priority_val else "Priority OFF"
                
                f.write(f"[Test case {case_str} | {priority_str}]\n")
                f.write(res_text + "\n\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = AlgorithmTesterUI(root)
    root.mainloop()