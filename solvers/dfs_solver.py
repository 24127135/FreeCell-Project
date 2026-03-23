"""Depth-First Search solver implementation for FreeCell."""

import time


class DFSSolver:
    """DFS solver for FreeCell."""

    def __init__(
        self,
        debug=True,
        debug_every=1000,
        max_depth=200,
        max_expansions=None,
        max_time_seconds=None,
    ):
        self.debug = debug
        self.debug_every = max(1, int(debug_every))
        self.max_depth = max_depth
        self.max_expansions = max_expansions
        self.max_time_seconds = max_time_seconds

    def _debug_log(self, message):
        if self.debug:
            print(f"[DFS] {message}")

    def solve(self, initial_state):
        """Solve FreeCell using depth-limited DFS graph search."""
        from game.freecell import FreeCell

        start_time = time.time()

        stack = [(initial_state, 0)]
        came_from = {initial_state: (None, None)}
        best_depth = {initial_state: 0}

        expanded_nodes = 0
        generated_nodes = 1
        frontier_peak = 1
        pruned_by_depth = 0

        self._debug_log(f"start max_depth={self.max_depth}")

        while stack:
            if self.max_time_seconds is not None:
                elapsed = time.time() - start_time
                if elapsed >= self.max_time_seconds:
                    self._debug_log(
                        f"stopped_by_time_limit expanded={expanded_nodes} generated={generated_nodes} "
                        f"frontier_peak={frontier_peak} pruned_depth={pruned_by_depth} time={elapsed:.3f}s"
                    )
                    return None, {
                        "expanded_nodes": expanded_nodes,
                        "time_taken": elapsed,
                        "generated_nodes": generated_nodes,
                        "frontier_peak": frontier_peak,
                        "pruned_by_depth": pruned_by_depth,
                        "terminated_by": "time_limit",
                    }

            current_state, depth = stack.pop()
            expanded_nodes += 1

            if self.max_expansions is not None and expanded_nodes >= self.max_expansions:
                elapsed = time.time() - start_time
                self._debug_log(
                    f"stopped_by_expansion_limit expanded={expanded_nodes} generated={generated_nodes} "
                    f"frontier_peak={frontier_peak} pruned_depth={pruned_by_depth} time={elapsed:.3f}s"
                )
                return None, {
                    "expanded_nodes": expanded_nodes,
                    "time_taken": elapsed,
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "pruned_by_depth": pruned_by_depth,
                    "terminated_by": "expansion_limit",
                }

            if self.debug and expanded_nodes % self.debug_every == 0:
                progress = sum(current_state.foundations.values())
                self._debug_log(
                    f"expanded={expanded_nodes} stack={len(stack)} best_depth={len(best_depth)} "
                    f"depth={depth} foundation_progress={progress}"
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
                    f"pruned_depth={pruned_by_depth} time={end_time - start_time:.3f}s"
                )

                return path, {
                    "time_taken": end_time - start_time,
                    "expanded_nodes": expanded_nodes,
                    "solution_length": len(path),
                    "generated_nodes": generated_nodes,
                    "frontier_peak": frontier_peak,
                    "pruned_by_depth": pruned_by_depth,
                }

            if self.max_depth is not None and depth >= self.max_depth:
                pruned_by_depth += 1
                continue

            successors = FreeCell.get_successors(current_state)

            # Push in reverse so the first successor is explored first.
            for next_state, move in reversed(successors):
                next_depth = depth + 1

                prev_depth = best_depth.get(next_state)
                if prev_depth is not None and next_depth >= prev_depth:
                    continue

                best_depth[next_state] = next_depth
                came_from[next_state] = (current_state, move)
                stack.append((next_state, next_depth))
                generated_nodes += 1

            if len(stack) > frontier_peak:
                frontier_peak = len(stack)

        elapsed = time.time() - start_time
        self._debug_log(
            f"failed expanded={expanded_nodes} generated={generated_nodes} "
            f"frontier_peak={frontier_peak} pruned_depth={pruned_by_depth} time={elapsed:.3f}s"
        )
        return None, {
            "expanded_nodes": expanded_nodes,
            "time_taken": elapsed,
            "generated_nodes": generated_nodes,
            "frontier_peak": frontier_peak,
            "pruned_by_depth": pruned_by_depth,
        }
