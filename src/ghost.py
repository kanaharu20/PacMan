import random

from src.mazegen import Direction, Maze
from src.mover import Mover

UNREACHABLE = 10 ** 9  # target まで行けないセルの距離（非常に遠い扱い）


class Ghost(Mover):
    def __init__(self, maze: Maze, cell: tuple[int, int], speed: float,
                 rng: random.Random) -> None:
        super().__init__(maze, cell, speed)
        self.target: tuple[int, int] = cell  # 毎フレーム外から設定する
        self.rng = rng

    # 逆走はせず、target までの歩数が一番少ない方向へ。同点なら乱数で選ぶ
    def _choose_direction(self) -> bool:
        options = [d for d in Direction
                   if self.maze.can_move(self.x, self.y, d)
                   and (self.direction is None
                        or d != self.direction.opposite)]
        if not options and self.direction is not None:  # dead end
            options = [self.direction.opposite]
        if not options:
            return False
        dist = self.maze.distances_from(self.target)
        costs = {d: dist.get((self.x + d.dx, self.y + d.dy), UNREACHABLE)
                 for d in options}
        best = min(costs.values())
        self.direction = self.rng.choice(
            [d for d in options if costs[d] == best])
        return True
