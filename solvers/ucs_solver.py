"""Uniform-Cost Search solver implementation for FreeCell."""

import heapq
import time

from .action_costs import get_action_cost


class UCSSolver:
    """UCS solver for FreeCell."""

    def __init__(
        self,
        debug=False,
        debug_every=1000,
        max_time_seconds=180,
    ):
        self.debug = debug
        self.debug_every = max(1, int(debug_every))
        self.max_time_seconds = max_time_seconds

    def _debug_log(self, message):
        if self.debug:
            print(f"[UCS] {message}")

    def solve(
        self,
        initial_state,
        progress_callback=None,
        foundation_priority_mode=False,
        should_stop=None,
    ):
        """Solve FreeCell using UCS graph search."""
        from game.freecell import FreeCell

        start_time = time.time()
        frontier = []
        counter = 0

        start_progress = sum(initial_state.foundations.values())
        heapq.heappush(frontier, (0, -start_progress, counter, 0, initial_state))

        best_g = {initial_state: 0}
        came_from = {initial_state: (None, None)}
        expanded_nodes = 0
        generated_nodes = 1
        stale_pops = 0
        frontier_peak = 1
        best_foundation_progress = start_progress

        if progress_callback is not None:
            progress_callback(
                {
                    "best_foundation_progress": best_foundation_progress,
                    "expanded_nodes": expanded_nodes,
                }
            )

        self._debug_log("start")

        while frontier:
            if should_stop is not None and should_stop():
                elapsed = time.time() - start_time
                self._debug_log(
                    f"stopped_by_cancel expanded={expanded_nodes} generated={generated_nodes} "
                    f"stale={stale_pops} frontier_peak={frontier_peak} time={elapsed:.3f}s"
                )
                return None, {
                    "expanded_nodes": expanded_nodes,
                    "time_taken": elapsed,
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "stale_pops": stale_pops,
                    "best_foundation_progress": best_foundation_progress,
                    "terminated_by": "cancelled",
                }

            if self.max_time_seconds is not None and (time.time() - start_time) >= self.max_time_seconds:
                elapsed = time.time() - start_time
                self._debug_log(
                    f"stopped_by_time_limit expanded={expanded_nodes} generated={generated_nodes} "
                    f"stale={stale_pops} frontier_peak={frontier_peak} time={elapsed:.3f}s"
                )
                return None, {
                    "expanded_nodes": expanded_nodes,
                    "time_taken": elapsed,
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "stale_pops": stale_pops,
                    "best_foundation_progress": best_foundation_progress,
                    "terminated_by": "time_limit",
                }

            cost, _, _, g, current_state = heapq.heappop(frontier)

            if g > best_g.get(current_state, float("inf")):
                stale_pops += 1
                continue

            expanded_nodes += 1
            current_progress = sum(current_state.foundations.values())
            if current_progress > best_foundation_progress:
                best_foundation_progress = current_progress
                if progress_callback is not None:
                    progress_callback(
                        {
                            "best_foundation_progress": best_foundation_progress,
                            "expanded_nodes": expanded_nodes,
                        }
                    )

            if self.debug and expanded_nodes % self.debug_every == 0:
                self._debug_log(
                    f"expanded={expanded_nodes} frontier={len(frontier)} best_g={len(best_g)} "
                    f"stale={stale_pops} g={g} cost={cost} "
                    f"foundation_progress_current={current_progress} "
                    f"foundation_progress_best={best_foundation_progress}"
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
                    "best_foundation_progress": best_foundation_progress,
                }

            for next_state, move in FreeCell.get_successors(
                current_state,
                foundation_only=foundation_priority_mode,
            ):
                new_g = g + get_action_cost(current_state, move)

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
            "best_foundation_progress": best_foundation_progress,
        }