"""Uniform-Cost Search solver implementation."""
import time
import heapq

class UCSSolver:
    """UCS solver for FreeCell."""
    def __init__(self):
        pass

    def solve(self, initial_state):
        from game.freecell import FreeCell

        start_time = time.time()
        frontier = []
        counter = 0

        heapq.heappush(frontier, (0, counter, 0, initial_state))

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

            if expanded_nodes % 5000 == 0:
                print(f"UCS DEBUG: Đã duyệt {expanded_nodes} nodes... g={g}")
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
                    "solution_length": len(path)
                }

            for next_state, move in FreeCell.get_successors(current_state):
                new_g = g + 1

                if next_state not in best_g or new_g < best_g[next_state]:
                    best_g[next_state] = new_g
                    came_from[next_state] = (current_state, move)
                    counter += 1
                    heapq.heappush(frontier, (new_g, counter, new_g, next_state))

        return None, {"expanded_nodes": expanded_nodes, "time_taken": time.time() - start_time}