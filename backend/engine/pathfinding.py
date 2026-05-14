from heapq import heappop, heappush
from math import hypot


class AStarPathfinder:
    """A* over the layout road graph. RL chooses a slot; this chooses the route."""

    def __init__(self, layout):
        self.layout = layout
        self.nodes = {node["id"]: node for node in layout["roadGraph"]["nodes"]}
        self.graph = self._build_graph(layout["roadGraph"]["edges"])

    def _build_graph(self, edges):
        graph = {node_id: [] for node_id in self.nodes}
        for start, end in edges:
            distance = self._distance(start, end)
            graph[start].append((end, distance))
            graph[end].append((start, distance))
        return graph

    def path_to_slot(self, slot):
        node_path = self._a_star("ENTRY", slot["aisleNode"])
        coordinates = [{"x": self.nodes[node]["x"], "y": self.nodes[node]["y"]} for node in node_path]
        coordinates.append({"x": slot["x"], "y": slot["y"]})
        return coordinates

    def path_length(self, path):
        total = 0
        for index in range(1, len(path)):
            total += hypot(path[index]["x"] - path[index - 1]["x"], path[index]["y"] - path[index - 1]["y"])
        return total

    def _a_star(self, start, goal):
        open_set = [(0, start)]
        came_from = {}
        g_score = {node_id: float("inf") for node_id in self.nodes}
        g_score[start] = 0

        while open_set:
            _, current = heappop(open_set)
            if current == goal:
                return self._reconstruct_path(came_from, current)
            for neighbor, weight in self.graph[current]:
                tentative = g_score[current] + weight
                if tentative < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    priority = tentative + self._distance(neighbor, goal)
                    heappush(open_set, (priority, neighbor))
        return [start]

    def _reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return list(reversed(path))

    def _distance(self, start, end):
        first = self.nodes[start]
        second = self.nodes[end]
        return hypot(first["x"] - second["x"], first["y"] - second["y"])
