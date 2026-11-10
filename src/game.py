import random

from src.ghost import Ghost
from src.mazegen import Direction, Maze
from src.player import Player

LIVES = 3
GHOST_SPEEDS = (5.4, 5.1, 4.8, 4.5)  # プレイヤー (6.0) より少しずつ遅く
RESPAWN_DELAY = 2.0  # 当たってから全員が初期位置に戻って再開するまで（秒）


# 1 レベル分のゲームの状態。描画や入力 (pygame) には依存しない
class Game:
    def __init__(self, maze: Maze, rng: random.Random) -> None:
        self.maze = maze
        self.player = Player(maze, maze.center_cell())
        self.ghosts = [Ghost(maze, cell, speed, rng)
                       for cell, speed in zip(maze.corner_cells(),
                                              GHOST_SPEEDS)]
        self.lives = LIVES
        self.freeze = 0.0  # 残りの停止時間。0 より大きい間は誰も動かない
        self.game_over = False

    def steer(self, direction: Direction) -> None:
        if self.freeze == 0.0 and not self.game_over:
            self.player.steer(direction)

    def update(self, dt: float) -> None:
        if self.game_over:
            return
        if self.freeze > 0.0:
            self.freeze -= dt
            if self.freeze <= 0.0:
                self.freeze = 0.0
                self._reset_positions()
            return
        self.player.update(dt)
        px, py = self.player.position
        for ghost in self.ghosts:
            ghost.target = round(px), round(py)
            ghost.update(dt)
        # 全員が動き終わってから判定する。同じ tick に何体と当たっても 1 回だけ
        if any(self.player.touches(ghost) for ghost in self.ghosts):
            self._lose_life()

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
