"""1 レベル分のゲームの規則と状態（得点・残機・制限時間・当たり判定）。"""

import random
from dataclasses import dataclass

from src.cheats import FAST_SPEED_RATE, Cheats
from src.ghost import Ghost
from src.mazegen import Direction, Maze
from src.player import PLAYER_SPEED, Player

LIVES = 3
GHOST_SPEEDS = (5.4, 5.1, 4.8, 4.5)  # プレイヤー (6.0) より少しずつ遅く
RESPAWN_DELAY = 2.0  # 当たってから全員が初期位置に戻って再開するまで（秒）
LEVEL_TIME = 90.0  # レベルの制限時間（秒）。0 になったら即ゲームオーバー
POINTS_PER_PACGUM = 10
POINTS_PER_SUPER_PACGUM = 50
FRIGHT_TIME = 7.0  # スーパーパックガムを食べてからゴーストが逃げる時間（秒）
POINTS_PER_GHOST = 200
GHOST_RESPAWN_DELAY = 3.0  # 食べられたゴーストが自分の隅で復活するまで（秒）

Cell = tuple[int, int]


@dataclass(frozen=True)
class Rules:
    """1 レベルの規則。設定ファイルの値で変えられる（既定値は上の定数）。"""

    level_time: float = LEVEL_TIME
    points_per_pacgum: int = POINTS_PER_PACGUM
    points_per_super_pacgum: int = POINTS_PER_SUPER_PACGUM
    points_per_ghost: int = POINTS_PER_GHOST


class Game:
    """1 レベル分のゲームの状態。描画や入力 (pygame) には依存しない。

    プレイヤーは中央、ゴースト 4 体は 4 隅から始まる。全部のガムを食べたら
    cleared、残機か制限時間がなくなったら game_over になる。
    """

    def __init__(self, maze: Maze, rng: random.Random,
                 rules: Rules = Rules(), score: int = 0,
                 lives: int = LIVES, cheats: Cheats | None = None) -> None:
        """迷路 maze の上にプレイヤー・ゴースト・ガムを置いてレベルを始める。

        score と lives は前のレベルから引き継ぐ値。cheats は Session と共有する
        （Cheats は書き換わるので、既定値を引数に書かず、ここで作る）。
        """
        self.maze = maze
        self.rules = rules
        self.cheats = cheats if cheats is not None else Cheats()
        self.player = Player(maze, maze.center_cell())
        self.ghosts = [Ghost(maze, cell, speed, rng)
                       for cell, speed in zip(maze.corner_cells(),
                                              GHOST_SPEEDS)]
        self.lives = lives
        self.score = score
        self.time_left = rules.level_time
        self.freeze = 0.0  # 残りの停止時間。0 より大きい間は誰も動かない
        self.game_over = False
        self.cleared = False
        self.pacgums, self.super_pacgums = self._place_pacgums()

    def _place_pacgums(self) -> tuple[set[Cell], set[Cell]]:
        """（通常のガム, スーパーパックガム）のセルの集合を返す。

        中央から行けるマス全部に置く。4 隅はスーパー、プレイヤーの開始マスには
        置かない。
        """
        start = self.maze.center_cell()
        reachable = set(self.maze.distances_from(start))
        supers = set(self.maze.corner_cells()) & reachable
        normal = reachable - supers - {start}
        return normal, supers - {start}

    def steer(self, direction: Direction) -> None:
        """プレイヤーを direction へ向ける。ミス直後の停止中と終了後は無視する。"""
        if self.freeze == 0.0 and not self.finished:
            self.player.steer(direction)

    @property
    def finished(self) -> bool:
        """レベルが終わった（クリアかゲームオーバー）なら True。"""
        return self.game_over or self.cleared

    def update(self, dt: float) -> None:
        """dt 秒ぶん進める（移動・ガムを食べる・時間・ゴーストとの当たり判定）。"""
        if self.finished:
            return
        if self.freeze > 0.0:
            self.freeze -= dt
            if self.freeze <= 0.0:
                self.freeze = 0.0
                self._reset_positions()
            return
        # 速度アップはいつでも入切できるので、毎回ここで速さを決める
        rate = FAST_SPEED_RATE if self.cheats.fast else 1.0
        self.player.speed = PLAYER_SPEED * rate
        self.player.update(dt)
        self._eat()
        if self.cleared:
            return
        # 時間は動いている間だけ減る（当たった後の停止中は止まる）
        self.time_left = max(0.0, self.time_left - dt)
        if self.time_left == 0.0:
            self.game_over = True
            return
        px, py = self.player.position
        for ghost in self.ghosts:
            ghost.target = round(px), round(py)
            ghost.update(dt, frozen=self.cheats.ghosts_frozen)
        # 全員が動き終わってから判定する
        self._check_ghost_collisions()

    def _eat(self) -> None:
        """プレイヤーの中心が一番近いマスのガムを食べて得点を足す。

        折り返し中でも正しく動く。スーパーパックガムならゴーストをいじけさせ、
        ガムがなくなったらクリアにする。
        """
        px, py = self.player.position
        cell = (round(px), round(py))
        if cell in self.pacgums:
            self.pacgums.remove(cell)
            self.score += self.rules.points_per_pacgum
        elif cell in self.super_pacgums:
            self.super_pacgums.remove(cell)
            self.score += self.rules.points_per_super_pacgum
            for ghost in self.ghosts:
                ghost.frighten(FRIGHT_TIME)
        if not self.pacgums and not self.super_pacgums:
            self.cleared = True

    def _check_ghost_collisions(self) -> None:
        """プレイヤーに触れているゴーストを調べる。

        いじけ中のゴーストは食べる。通常のゴーストに触れたらミス
        （同じ tick に何体と当たってもミスは 1 回だけ）。消えているゴーストは
        無視する。無敵のチート中はミスにならない（いじけ中のゴーストは
        食べられる）。
        """
        hit = False
        for ghost in self.ghosts:
            if ghost.eaten or not self.player.touches(ghost):
                continue
            if ghost.frightened:
                ghost.get_eaten(GHOST_RESPAWN_DELAY)
                self.score += self.rules.points_per_ghost
            else:
                hit = True
        if hit and not self.cheats.invincible:
            self._lose_life()

    def _lose_life(self) -> None:
        """残機を 1 減らす。0 ならゲームオーバー、残っていれば少し止めて再開する。"""
        self.lives -= 1
        if self.lives == 0:
            self.game_over = True
        else:
            self.freeze = RESPAWN_DELAY

    def _reset_positions(self) -> None:
        """ミスの後、プレイヤーを中央、ゴーストを自分の隅に戻す（ガムはそのまま）。"""
        self.player.place(self.maze.center_cell())
        for ghost in self.ghosts:
            ghost.place(ghost.home)
