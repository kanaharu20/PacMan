from src.mazegen import Direction, Maze


# 位置 = 整数セル (x, y) + 次のセルへの進み具合 progress (0〜1)。
# 曲がる・壁で止まる判定はセルの中心 (progress == 0) でだけ行うので、壁にめり込まない
class Player:
    def __init__(self, maze: Maze, cell: tuple[int, int],
                 speed: float = 6.0) -> None:
        self.maze = maze
        self.x, self.y = cell
        self.speed = speed
        self.direction: Direction | None = None
        self.wanted: Direction | None = None  # buffered key input
        self.progress = 0.0

    @property
    def position(self) -> tuple[float, float]:
        if self.direction is None:
            return float(self.x), float(self.y)
        return (self.x + self.direction.dx * self.progress,
                self.y + self.direction.dy * self.progress)

    def steer(self, direction: Direction) -> None:
        self.wanted = direction
        # Reversing is always legal: we came from that cell.
        if (self.direction is not None and self.progress > 0
                and direction == self.direction.opposite):
            self.x += self.direction.dx
            self.y += self.direction.dy
            self.progress = 1.0 - self.progress
            self.direction = direction

    def update(self, dt: float) -> None:
        remaining = self.speed * dt
        while remaining > 0:
            if self.progress == 0.0 and not self._choose_direction():
                return
            assert self.direction is not None
            to_center = 1.0 - self.progress
            if remaining < to_center:
                self.progress += remaining
                return
            remaining -= to_center  # arrived on the next cell center
            self.x += self.direction.dx
            self.y += self.direction.dy
            self.progress = 0.0

    def _choose_direction(self) -> bool:
        if (self.wanted is not None
                and self.maze.can_move(self.x, self.y, self.wanted)):
            self.direction = self.wanted
            return True
        if (self.direction is not None
                and self.maze.can_move(self.x, self.y, self.direction)):
            return True
        self.direction = None  # wall ahead: stop
        return False
