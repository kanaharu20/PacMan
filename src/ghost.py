"""ゴースト（プレイヤーを追い、いじけ中は逃げるキャラクター）。"""

import random

from src.mazegen import Direction, Maze
from src.mover import Mover

UNREACHABLE = 10 ** 9  # target まで行けないセルの距離（非常に遠い扱い）
FRIGHT_SPEED_RATE = 0.5  # いじけ中は通常の半分の速さで逃げる


class Ghost(Mover):
    """自分の隅から出発し、target（プレイヤーのいるセル）を追うゴースト。

    状態は 3 つ: 通常（追う）、いじけ（fright > 0 の間、遅くなって逃げる）、
    食べられた（respawn > 0 の間、迷路から消えて隅での復活を待つ）。
    """

    def __init__(self, maze: Maze, cell: tuple[int, int], speed: float,
                 rng: random.Random) -> None:
        """隅のセル cell に置く。分かれ道で同点のときは rng で方向を選ぶ。"""
        # Mover.__init__ の中で place が呼ばれるので、place が使う値を先に用意する
        self.normal_speed = speed
        self.fright = 0.0  # いじけの残り時間（秒）。0 より大きい間は逃げる
        self.respawn = 0.0  # 食べられてから復活までの残り時間（秒）
        super().__init__(maze, cell, speed)
        self.home = cell  # 自分の隅。食べられたらここで復活する
        self.target: tuple[int, int] = cell  # 毎フレーム外から設定する
        self.rng = rng

    def place(self, cell: tuple[int, int]) -> None:
        """cell に置き、いじけも食べられた状態も解除して通常状態に戻す。"""
        super().place(cell)
        self.respawn = 0.0
        self._calm_down()

    @property
    def frightened(self) -> bool:
        """いじけ中（プレイヤーから逃げていて、食べられる）なら True。"""
        return self.fright > 0.0

    @property
    def eaten(self) -> bool:
        """食べられて迷路から消えている間は True。動かず、当たり判定もない。"""
        return self.respawn > 0.0

    def frighten(self, duration: float) -> None:
        """スーパーパックガムが食べられたときに呼び、duration 秒いじけさせる。

        向きを反転して、遅くなって逃げ始める。いじけ中にもう一度呼ばれたら
        反転せず、残り時間を duration に戻す。食べられて消えているゴーストは
        いじけない（いじけ中に復活したときは、Game が残りの時間で呼び直す）。
        """
        if self.eaten:
            return
        if not self.frightened:
            self.reverse()
        self.fright = duration
        self.speed = self.normal_speed * FRIGHT_SPEED_RATE

    def get_eaten(self, delay: float) -> None:
        """プレイヤーに食べられたときに呼ぶ。delay 秒後に自分の隅で復活する。"""
        self._calm_down()
        self.respawn = delay

    def update(self, dt: float, frozen: bool = False) -> None:
        """dt 秒ぶん、タイマーを進めて動く。

        frozen（チートのゴースト停止）のときは動かないが、タイマーは進める。
        止まっている間も、逃げる状態は終わり、食べられたゴーストは隅で復活する。
        """
        if self.eaten:
            self.respawn -= dt
            if self.respawn <= 0.0:
                self.place(self.home)
            return
        if self.frightened:
            self.fright -= dt
            if self.fright <= 0.0:
                self._calm_down()
        if not frozen:
            super().update(dt)

    def _calm_down(self) -> None:
        """いじけを終わらせ、通常の速さに戻す。"""
        self.fright = 0.0
        self.speed = self.normal_speed

    def _choose_direction(self) -> bool:
        """分かれ道で、target までの歩数を見て進む方向を決める。

        逆走はせず（行き止まりだけは引き返す）、通常時は歩数が一番少ない方向へ、
        いじけ中は一番多い方向へ（target から逃げる）。同点なら乱数で選ぶ。
        """
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
