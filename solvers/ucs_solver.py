"""Uniform-Cost Search solver implementation."""

import heapq
import time


class UCSSolver:
    """UCS solver for FreeCell."""

    def __init__(self, debug=False, debug_every=1000):
        self.debug = debug
        self.debug_every = max(1, int(debug_every))

    def _debug_log(self, message):
        if self.debug:
            print(f"[UCS] {message}")

    def solve(self, initial_state):
        from game.freecell import FreeCell

        start_time = time.time()
        frontier = []
        counter = 0

        # Tie-break with higher foundation progress first when g is equal.
        start_progress = sum(initial_state.foundations.values())
        heapq.heappush(frontier, (0, -start_progress, counter, 0, initial_state))

        best_g = {initial_state: 0}
        came_from = {initial_state: (None, None)}
        expanded_nodes = 0
        generated_nodes = 1
        stale_pops = 0
        frontier_peak = 1

        self._debug_log("start")

        while frontier:
            cost, _, _, g, current_state = heapq.heappop(frontier)

            if g > best_g.get(current_state, float("inf")):
                stale_pops += 1
                continue

            expanded_nodes += 1

            if self.debug and expanded_nodes % self.debug_every == 0:
                progress = sum(current_state.foundations.values())
                self._debug_log(
                    f"expanded={expanded_nodes} frontier={len(frontier)} best_g={len(best_g)} "
                    f"stale={stale_pops} g={g} cost={cost} foundation_progress={progress}"
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
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "stale_pops": stale_pops,
                }

            for next_state, move in FreeCell.get_successors(current_state):
                new_g = g + 1

                if next_state not in best_g or new_g < best_g[next_state]:
                    best_g[next_state] = new_g
                    came_from[next_state] = (current_state, move)
                    counter += 1
                    progress = sum(next_state.foundations.values())
                    heapq.heappush(frontier, (new_g, -progress, counter, new_g, next_state))
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
