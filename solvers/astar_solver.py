"""A* Search solver implementation."""
import time
import heapq

from utils.heuristics import calculate_h_da

class AStarSolver:
    """A* solver for FreeCell."""

    def __init__(self, heuristic_func=calculate_h_da, weight=2.5):
        self.heuristic = heuristic_func
        self.weight = weight

    def solve(self, initial_state):
        from game.freecell import FreeCell

        start_time = time.time()
        frontier = []
        counter = 0

        g_cost = 0
        h_cost = self.heuristic(initial_state)
        f_cost = g_cost + (self.weight * h_cost)

        heapq.heappush(frontier, (f_cost, counter, g_cost, initial_state))

        best_g = {initial_state: 0}
        came_from = {initial_state: (None, None)}
        explored = set()
        expanded_nodes = 0

        while frontier:
            f, _, g, current_state = heapq.heappop(frontier)

            if current_state in explored:
                continue

            explored.add(current_state)
            expanded_nodes += 1

            if expanded_nodes % 1000 == 0:
                print(f"DEBUG: Đã duyệt {expanded_nodes} nodes... f={f:.2f}, g={g}")

            if current_state.is_goal_state():
                end_time = time.time()
                path = []
                curr = current_state
                while came_from[curr][0] is not None:
                    parent, move = came_from[curr]
                    path.append(move)
                    curr = parent
                path.reverse()

                return path, {
                    "time_taken": end_time - start_time,
                    "expanded_nodes": expanded_nodes,
                    "solution_length": len(path),
                    "max_memory_nodes": len(explored) + len(frontier)
                }

            successors = FreeCell.get_successors(current_state)
            foundation_moves = [s for s in successors if 'FOUNDATION' in s[1].move_type]

            targets = foundation_moves if foundation_moves else successors

            for next_state, move in targets:
                new_g = g + 1
                if next_state not in best_g or new_g < best_g[next_state]:
                    best_g[next_state] = new_g
                    new_h = self.heuristic(next_state)
                    new_f = new_g + (self.weight * new_h)
                    came_from[next_state] = (current_state, move)
                    counter += 1
                    heapq.heappush(frontier, (new_f, counter, new_g, next_state))

        return None, {"expanded_nodes": expanded_nodes, "time_taken": time.time() - start_time}