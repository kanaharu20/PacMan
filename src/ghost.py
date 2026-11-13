import random

from src.mazegen import Direction, Maze
from src.mover import Mover

UNREACHABLE = 10 ** 9  # target まで行けないセルの距離（非常に遠い扱い）
FRIGHT_SPEED_RATE = 0.5  # いじけ中は通常の半分の速さで逃げる


class Ghost(Mover):
    def __init__(self, maze: Maze, cell: tuple[int, int], speed: float,
                 rng: random.Random) -> None:
        # Mover.__init__ の中で place が呼ばれるので、place が使う値を先に用意する
        self.normal_speed = speed
        self.fright = 0.0  # いじけの残り時間（秒）。0 より大きい間は逃げる
        self.respawn = 0.0  # 食べられてから復活までの残り時間（秒）
        super().__init__(maze, cell, speed)
        self.home = cell  # 自分の隅。食べられたらここで復活する
        self.target: tuple[int, int] = cell  # 毎フレーム外から設定する
        self.rng = rng

    # 初期位置に置くときは、いじけも食べられた状態も解除して通常状態に戻す
    def place(self, cell: tuple[int, int]) -> None:
        super().place(cell)
        self.respawn = 0.0
        self._calm_down()

    @property
    def frightened(self) -> bool:
        return self.fright > 0.0

    # 食べられて迷路から消えている間は True。動かず、当たり判定もない
    @property
    def eaten(self) -> bool:
        return self.respawn > 0.0

    # スーパーパックガムが食べられたとき。向きを反転して、遅くなって逃げ始める
    # 食べられて消えているゴーストはいじけない（復活したら通常状態）
    def frighten(self, duration: float) -> None:
        if self.eaten:
            return
        if not self.frightened:
            self.reverse()
        self.fright = duration
        self.speed = self.normal_speed * FRIGHT_SPEED_RATE

    # プレイヤーに食べられたとき。delay 秒後に自分の隅で復活する
    def get_eaten(self, delay: float) -> None:
        self._calm_down()
        self.respawn = delay

    def update(self, dt: float) -> None:
        if self.eaten:
            self.respawn -= dt
            if self.respawn <= 0.0:
                self.place(self.home)
            return
        if self.frightened:
            self.fright -= dt
            if self.fright <= 0.0:
                self._calm_down()
        super().update(dt)

    def _calm_down(self) -> None:
        self.fright = 0.0
        self.speed = self.normal_speed

    # 逆走はせず、通常時は target までの歩数が一番少ない方向へ、
    # いじけ中は一番多い方向へ（target から逃げる）。同点なら乱数で選ぶ
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
        if self.frightened:
            # 歩数の符号を反転すれば「一番遠い」も min で選べる。
            # target から行けないセルは一番安全なので、一番小さい値にする
            costs = {d: -dist.get((self.x + d.dx, self.y + d.dy), UNREACHABLE)
                     for d in options}
        else:
            costs = {d: dist.get((self.x + d.dx, self.y + d.dy), UNREACHABLE)
                     for d in options}
        best = min(costs.values())
        self.direction = self.rng.choice(
            [d for d in options if costs[d] == best])
        return True
