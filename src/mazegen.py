"""割り当てられた迷路生成パッケージ (mazegenerator) を包むアダプタ。

パッケージは変更せずに使い、その出力をゲームが使いやすい Maze に変換する。
"""

from collections import deque
from enum import Enum

from mazegenerator import MazeGenerator


class Direction(Enum):
    """上下左右の 4 方向。値は (dx, dy, 壁のビット)。

    maze[y][x] の下位 4 bit が壁 (N=1, E=2, S=4, W=8)。ビットが立っていたら
    その方向に壁がある。
    """

    UP = (0, -1, 1)
    RIGHT = (1, 0, 2)
    DOWN = (0, 1, 4)
    LEFT = (-1, 0, 8)

    @property
    def dx(self) -> int:
        """この方向に 1 マス進んだときの x の変化。"""
        return self.value[0]

    @property
    def dy(self) -> int:
        """この方向に 1 マス進んだときの y の変化（下が +）。"""
        return self.value[1]

    @property
    def wall(self) -> int:
        """この方向の壁を表すビット。"""
        return self.value[2]

    @property
    def opposite(self) -> "Direction":
        """反対の方向。"""
        return {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }[self]


BLOCKED = 15  # all four walls: the isolated "42" cells


class MazeError(Exception):
    """迷路生成パッケージが失敗した・おかしな迷路を返した（続行できない）エラー。"""


class Maze:
    """セルとセルの間に壁がある形式の迷路。grid[y][x] が壁のビット。"""

    def __init__(self, width: int, height: int, seed: int = 0) -> None:
        """mazegenerator で width x height の迷路を作る。

        perfect=False（行き止まりを減らした Pac-Man 向けの迷路）で作る。
        seed が 0 ならランダム。生成に失敗したり、大きさや値がおかしい迷路が
        返ってきたりしたら MazeError を投げる。
        """
        # 他のグループのパッケージなので、何が起きても MazeError にまとめる
        try:
            generator = MazeGenerator(size=(width, height), perfect=False,
                                      seed=seed)
            grid = [list(row) for row in generator.maze]
        except Exception as e:
            raise MazeError(f"maze generator failed for a {width}x{height} "
                            f"maze: {e}") from e
        if (len(grid) != height or any(len(row) != width for row in grid)
                or not all(isinstance(v, int) for row in grid for v in row)):
            raise MazeError(f"maze generator returned a broken maze for "
                            f"{width}x{height}")
        self.grid: list[list[int]] = grid
        self.width = width
        self.height = height

    def in_bounds(self, x: int, y: int) -> bool:
        """(x, y) が迷路の中のセルなら True。"""
        return 0 <= x < self.width and 0 <= y < self.height

    def has_wall(self, x: int, y: int, direction: Direction) -> bool:
        """セル (x, y) の direction 側に壁があれば True。"""
        return bool(self.grid[y][x] & direction.wall)

    def can_move(self, x: int, y: int, direction: Direction) -> bool:
        """セル (x, y) から direction の隣のセルへ移れるなら True。

        壁があるときと、隣が迷路の外になるときは False。
        """
        if not self.in_bounds(x, y) or self.has_wall(x, y, direction):
            return False
        return self.in_bounds(x + direction.dx, y + direction.dy)

    def is_blocked(self, x: int, y: int) -> bool:
        """四方が壁のセル（中央の「42」の模様）なら True。"""
        return self.grid[y][x] == BLOCKED

    def center_cell(self) -> tuple[int, int]:
        """プレイヤーの開始セル。中央に一番近い「42」でないセル。"""
        return self.nearest_open((self.width // 2, self.height // 2))

    def corner_cells(self) -> list[tuple[int, int]]:
        """4 隅のセル（左上・右上・左下・右下の順）。

        スーパーパックガムとゴーストを置く場所。隅が「42」のセルなら、
        一番近い「42」でないセルにする。
        """
        right, bottom = self.width - 1, self.height - 1
        corners = [(0, 0), (right, 0), (0, bottom), (right, bottom)]
        return [self.nearest_open(cell) for cell in corners]

    def nearest_open(self, start: tuple[int, int]) -> tuple[int, int]:
        """壁は無視して、start から一番近い「42」でないセルを探す。

        見つからなければ start をそのまま返す。
        """
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

    def distances_from(self,
                       start: tuple[int, int]) -> dict[tuple[int, int], int]:
        """start から通路をたどったときの、各セルまでの歩数（幅優先探索）。

        start から行けないセルは辞書に入らない。
        """
        dist = {start: 0}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for d in Direction:
                nxt = (x + d.dx, y + d.dy)
                if self.can_move(x, y, d) and nxt not in dist:
                    dist[nxt] = dist[(x, y)] + 1
                    queue.append(nxt)
        return dist
