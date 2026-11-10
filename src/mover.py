from src.mazegen import Direction, Maze


# 位置 = 整数セル (x, y) + 次のセルへの進み具合 progress (0〜1)。
# 曲がる・壁で止まる判定はセルの中心 (progress == 0) でだけ行うので、壁にめり込まない
# 中心でどの方向に進むかは子クラスが _choose_direction で決める
class Mover:
    # 画像と当たり判定の一辺（セル単位）。1 以上だと壁越しに当たるので 1 未満にする
    size = 0.6

    def __init__(self, maze: Maze, cell: tuple[int, int],
                 speed: float) -> None:
        self.maze = maze
        self.speed = speed
        self.place(cell)

    # cell の中心に止まった状態で置く（開始時と復活時）
    def place(self, cell: tuple[int, int]) -> None:
        self.x, self.y = cell
        self.direction: Direction | None = None
        self.progress = 0.0

    @property
    def position(self) -> tuple[float, float]:
        if self.direction is None:
            return float(self.x), float(self.y)
        return (self.x + self.direction.dx * self.progress,
                self.y + self.direction.dy * self.progress)

    # 画像（一辺 size の正方形）どうしが触れたら True。辺が接しただけでも当たり
    def touches(self, other: "Mover") -> bool:
        ax, ay = self.position
        bx, by = other.position
        reach = (self.size + other.size) / 2
        return abs(ax - bx) <= reach and abs(ay - by) <= reach

    def reverse(self) -> None:
        # Reversing is always legal: we came from that cell.
        if self.direction is None or self.progress == 0.0:
            return
        self.x += self.direction.dx
        self.y += self.direction.dy
        self.progress = 1.0 - self.progress
        self.direction = self.direction.opposite

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

    # セルの中心で呼ばれる。進むなら self.direction を決めて True、止まるなら False
    def _choose_direction(self) -> bool:
        raise NotImplementedError
