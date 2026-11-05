from collections import deque
from enum import Enum

from mazegenerator import MazeGenerator


# maze[y][x] の下位4bitが壁 (N=1, E=2, S=4, W=8)。ビットが立っていたら壁あり
class Direction(Enum):
    # 方向と壁のビットパターンを定義
    UP = (0, -1, 1)
    RIGHT = (1, 0, 2)
    DOWN = (0, 1, 4)
    LEFT = (-1, 0, 8)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def wall(self) -> int:
        return self.value[2]

    @property
    def opposite(self) -> "Direction":
        return {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }[self]


BLOCKED = 15  # all four walls: the isolated "42" cells


class Maze:
    def __init__(self, width: int, height: int, seed: int = 0) -> None:
        generator = MazeGenerator(size=(width, height), perfect=False,
                                  seed=seed)
        self.grid: list[list[int]] = [row[:] for row in generator.maze]
        self.width = width
        self.height = height

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def has_wall(self, x: int, y: int, direction: Direction) -> bool:
        return bool(self.grid[y][x] & direction.wall)

    def can_move(self, x: int, y: int, direction: Direction) -> bool:
        if not self.in_bounds(x, y) or self.has_wall(x, y, direction):
            return False
        return self.in_bounds(x + direction.dx, y + direction.dy)

    def is_blocked(self, x: int, y: int) -> bool:
        return self.grid[y][x] == BLOCKED

    def center_cell(self) -> tuple[int, int]:
        start = (self.width // 2, self.height // 2)
        seen = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            if not self.is_blocked(x, y):
                return x, y
            for d in Direction:
                nxt = (x + d.dx, y + d.dy)
                if self.in_bounds(*nxt) and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return start
