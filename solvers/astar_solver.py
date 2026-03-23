"""A* Search solver implementation."""
import time
import heapq

from utils.heuristics import calculate_h_da

class AStarSolver:
    """A* solver for FreeCell."""

    def __init__(self, heuristic_func=calculate_h_da, weight=1, debug=False, debug_every=2000):
        self.heuristic = heuristic_func
        self.weight = weight
        self.debug = debug
        self.debug_every = max(1, int(debug_every))

    def _debug_log(self, message):
        if self.debug:
            print(f"[A*] {message}")

    def solve(self, initial_state):
        from game.freecell import FreeCell

        start_time = time.time()
        frontier = []
        counter = 0

        heuristic_cache = {}

        def h(state):
            cached = heuristic_cache.get(state)
            if cached is not None:
                return cached
            value = self.heuristic(state)
            heuristic_cache[state] = value
            return value

        g_cost = 0
        h_cost = h(initial_state)
        f_cost = g_cost + (self.weight * h_cost)

        heapq.heappush(frontier, (f_cost, counter, g_cost, initial_state))

        best_g = {initial_state: 0}
        came_from = {initial_state: (None, None)}
        expanded_nodes = 0
        generated_nodes = 1
        stale_pops = 0
        frontier_peak = 1

        self._debug_log(
            f"start weight={self.weight} h0={h_cost} f0={f_cost:.2f}"
        )

        while frontier:
            f, _, g, current_state = heapq.heappop(frontier)

            if g > best_g.get(current_state, float("inf")):
                stale_pops += 1
                continue

            expanded_nodes += 1

            if self.debug and expanded_nodes % self.debug_every == 0:
                progress = sum(current_state.foundations.values())
                self._debug_log(
                    f"expanded={expanded_nodes} frontier={len(frontier)} best_g={len(best_g)} "
                    f"stale={stale_pops} g={g} f={f:.2f} foundation_progress={progress}"
                )

            if current_state.is_goal_state():
                end_time = time.time()
                path = []
                curr = current_state
                while came_from[curr][0] is not None:
                    parent, move = came_from[curr]
                    path.append(move)
                    curr = parent
                path.reverse()

                self._debug_log(
                    f"solved expanded={expanded_nodes} generated={generated_nodes} "
                    f"stale={stale_pops} frontier_peak={frontier_peak} "
                    f"solution_len={len(path)} time={end_time - start_time:.3f}s"
                )

                return path, {
                    "time_taken": end_time - start_time,
                    "expanded_nodes": expanded_nodes,
                    "solution_length": len(path),
                    "max_memory_nodes": len(best_g) + len(frontier),
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "stale_pops": stale_pops,
                }

            targets = FreeCell.get_successors(current_state, foundation_only=True)

            for next_state, move in targets:
                new_g = g + 1
                if next_state not in best_g or new_g < best_g[next_state]:
                    best_g[next_state] = new_g
                    new_h = h(next_state)
                    new_f = new_g + (self.weight * new_h)
                    came_from[next_state] = (current_state, move)
                    counter += 1
                    heapq.heappush(frontier, (new_f, counter, new_g, next_state))
                    generated_nodes += 1

            if len(frontier) > frontier_peak:
                frontier_peak = len(frontier)

        elapsed = time.time() - start_time
        self._debug_log(
            f"failed expanded={expanded_nodes} generated={generated_nodes} "
            f"stale={stale_pops} frontier_peak={frontier_peak} time={elapsed:.3f}s"
        )
        return None, {
            "expanded_nodes": expanded_nodes,
            "time_taken": elapsed,
            "generated_nodes": generated_nodes,
            "frontier_peak": frontier_peak,
            "stale_pops": stale_pops,
        }