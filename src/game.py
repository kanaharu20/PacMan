import random

from src.ghost import Ghost
from src.mazegen import Direction, Maze
from src.player import Player

LIVES = 3
GHOST_SPEEDS = (5.4, 5.1, 4.8, 4.5)  # プレイヤー (6.0) より少しずつ遅く
RESPAWN_DELAY = 2.0  # 当たってから全員が初期位置に戻って再開するまで（秒）
LEVEL_TIME = 90.0  # レベルの制限時間（秒）。0 になったら即ゲームオーバー
POINTS_PER_PACGUM = 10
POINTS_PER_SUPER_PACGUM = 50

Cell = tuple[int, int]


# 1 レベル分のゲームの状態。描画や入力 (pygame) には依存しない
class Game:
    def __init__(self, maze: Maze, rng: random.Random) -> None:
        self.maze = maze
        self.player = Player(maze, maze.center_cell())
        self.ghosts = [Ghost(maze, cell, speed, rng)
                       for cell, speed in zip(maze.corner_cells(),
                                              GHOST_SPEEDS)]
        self.lives = LIVES
        self.score = 0
        self.time_left = LEVEL_TIME
        self.freeze = 0.0  # 残りの停止時間。0 より大きい間は誰も動かない
        self.game_over = False
        self.cleared = False
        self.pacgums, self.super_pacgums = self._place_pacgums()

    # 中央から行けるマス全部に置く。4 隅はスーパー、プレイヤーの開始マスには置かない
    def _place_pacgums(self) -> tuple[set[Cell], set[Cell]]:
        start = self.maze.center_cell()
        reachable = set(self.maze.distances_from(start))
        supers = set(self.maze.corner_cells()) & reachable
        normal = reachable - supers - {start}
        return normal, supers - {start}

    def steer(self, direction: Direction) -> None:
        if self.freeze == 0.0 and not self.finished:
            self.player.steer(direction)

    @property
    def finished(self) -> bool:
        return self.game_over or self.cleared

    def update(self, dt: float) -> None:
        if self.finished:
            return
        if self.freeze > 0.0:
            self.freeze -= dt
            if self.freeze <= 0.0:
                self.freeze = 0.0
                self._reset_positions()
            return
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
            ghost.update(dt)
        # 全員が動き終わってから判定する。同じ tick に何体と当たっても 1 回だけ
        if any(self.player.touches(ghost) for ghost in self.ghosts):
            self._lose_life()

    # プレイヤーの中心が一番近いマスのガムを食べる（折り返し中でも正しく動く）
    def _eat(self) -> None:
        px, py = self.player.position
        cell = (round(px), round(py))
        if cell in self.pacgums:
            self.pacgums.remove(cell)
            self.score += POINTS_PER_PACGUM
        elif cell in self.super_pacgums:
            self.super_pacgums.remove(cell)
            self.score += POINTS_PER_SUPER_PACGUM
        if not self.pacgums and not self.super_pacgums:
            self.cleared = True

    def _lose_life(self) -> None:
        self.lives -= 1
        if self.lives == 0:
            self.game_over = True
        else:
            self.freeze = RESPAWN_DELAY

    def _reset_positions(self) -> None:
        self.player.place(self.maze.center_cell())
        for ghost, cell in zip(self.ghosts, self.maze.corner_cells()):
            ghost.place(cell)
