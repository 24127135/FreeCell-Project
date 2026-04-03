"""Breadth-First Search solver implementation for FreeCell."""

from collections import deque
import time


class BFSSolver:
    """BFS solver for FreeCell."""

    def __init__(
        self,
        debug=True,
        debug_every=1000,
        max_expansions=None,
        max_time_seconds=180,
    ):
        self.debug = debug
        self.debug_every = max(1, int(debug_every))
        self.max_expansions = max_expansions
        self.max_time_seconds = max_time_seconds

    def _debug_log(self, message):
        if self.debug:
            print(f"[BFS] {message}")

    def solve(
        self,
        initial_state,
        progress_callback=None,
        foundation_priority_mode=False,
        should_stop=None,
    ):
        """Solve FreeCell using BFS graph search."""
        from game.freecell import FreeCell

        start_time = time.time()

        frontier = deque([initial_state])
        visited = {initial_state}
        came_from = {initial_state: (None, None)}

        expanded_nodes = 0
        generated_nodes = 1
        frontier_peak = 1
        best_foundation_progress = sum(initial_state.foundations.values())

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
                    f"frontier_peak={frontier_peak} time={elapsed:.3f}s"
                )
                return None, {
                    "expanded_nodes": expanded_nodes,
                    "time_taken": elapsed,
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "terminated_by": "cancelled",
                    "best_foundation_progress": best_foundation_progress,
                }

            if self.max_time_seconds is not None and (time.time() - start_time) >= self.max_time_seconds:
                elapsed = time.time() - start_time
                self._debug_log(
                    f"stopped_by_time_limit expanded={expanded_nodes} generated={generated_nodes} "
                    f"frontier_peak={frontier_peak} time={elapsed:.3f}s"
                )
                return None, {
                    "expanded_nodes": expanded_nodes,
                    "time_taken": elapsed,
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "terminated_by": "time_limit",
                    "best_foundation_progress": best_foundation_progress,
                }

            current_state = frontier.popleft()
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

            if self.max_expansions is not None and expanded_nodes >= self.max_expansions:
                elapsed = time.time() - start_time
                self._debug_log(
                    f"stopped_by_expansion_limit expanded={expanded_nodes} generated={generated_nodes} "
                    f"frontier_peak={frontier_peak} time={elapsed:.3f}s"
                )
                return None, {
                    "expanded_nodes": expanded_nodes,
                    "time_taken": elapsed,
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "terminated_by": "expansion_limit",
                    "best_foundation_progress": best_foundation_progress,
                }

            if self.debug and expanded_nodes % self.debug_every == 0:
                self._debug_log(
                    f"expanded={expanded_nodes} frontier={len(frontier)} visited={len(visited)} "
                    f"foundation_progress={current_progress}"
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
                    f"frontier_peak={frontier_peak} solution_len={len(path)} "
                    f"time={end_time - start_time:.3f}s"
                )

                return path, {
                    "time_taken": end_time - start_time,
                    "expanded_nodes": expanded_nodes,
                    "solution_length": len(path),
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "best_foundation_progress": best_foundation_progress,
                }

            for next_state, move in FreeCell.get_successors(
                current_state,
                foundation_only=foundation_priority_mode,
            ):
                if next_state in visited:
                    continue

                visited.add(next_state)
                came_from[next_state] = (current_state, move)
                generated_nodes += 1

                # BFS can safely stop on first generated goal because states are expanded by depth.
                if next_state.is_goal_state():
                    next_progress = sum(next_state.foundations.values())
                    if next_progress > best_foundation_progress:
                        best_foundation_progress = next_progress
                        if progress_callback is not None:
                            progress_callback(
                                {
                                    "best_foundation_progress": best_foundation_progress,
                                    "expanded_nodes": expanded_nodes,
                                }
                            )

                    end_time = time.time()
                    path = []
                    curr = next_state
                    while came_from[curr][0] is not None:
                        parent, move_item = came_from[curr]
                        path.append(move_item)
                        curr = parent
                    path.reverse()

                    self._debug_log(
                        f"solved_early expanded={expanded_nodes} generated={generated_nodes} "
                        f"frontier_peak={frontier_peak} solution_len={len(path)} "
                        f"time={end_time - start_time:.3f}s"
                    )

                    return path, {
                        "time_taken": end_time - start_time,
                        "expanded_nodes": expanded_nodes,
                        "solution_length": len(path),
                        "generated_nodes": generated_nodes,
                        "frontier_peak": frontier_peak,
                        "best_foundation_progress": best_foundation_progress,
                    }

                frontier.append(next_state)

            if len(frontier) > frontier_peak:
                frontier_peak = len(frontier)

        elapsed = time.time() - start_time
        self._debug_log(
            f"failed expanded={expanded_nodes} generated={generated_nodes} "
            f"frontier_peak={frontier_peak} time={elapsed:.3f}s"
        )
        return None, {
            "expanded_nodes": expanded_nodes,
            "time_taken": elapsed,
            "generated_nodes": generated_nodes,
            "frontier_peak": frontier_peak,
            "best_foundation_progress": best_foundation_progress,
        }
