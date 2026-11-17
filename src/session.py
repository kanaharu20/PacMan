"""1 回のゲーム（レベル 1 から最後のレベルまで）の進行とチートの操作。"""

import random

from src.cheats import Cheats
from src.config import LIVES_MAX, Config, LevelConfig
from src.game import Game, Rules
from src.mazegen import Direction, Maze

LEVEL_CLEAR_DELAY = 2.0  # レベルをクリアしてから次のレベルが始まるまで（秒）


class Session:
    """1 回のゲームの進行。描画や入力 (pygame) には依存しない。

    レベルごとに新しい迷路と Game を作り、得点と残機だけ引き継ぐ。
    """

    def __init__(self, config: Config) -> None:
        """設定 config でレベル 1 を始める。"""
        self.config = config
        # ゴーストの動きの乱数。mazegenerator はグローバルの random を書き換えるので
        # 専用のものを使う（seed が 0 ならランダム）
        self.rng = random.Random(config.seed or None)
        self.level = 1  # 今のレベル（1 から数える）
        self.won = False
        self.clear_wait = 0.0  # クリアしてからの経過時間
        self.cheats = Cheats()  # 全レベルの Game に同じものを渡す
        self.game = self._start_level(score=0, lives=config.lives)

    @property
    def level_count(self) -> int:
        """全部のレベル数。"""
        return len(self.config.levels)

    @property
    def finished(self) -> bool:
        """全レベルをクリアしたか、ゲームオーバーになったら True。"""
        return self.won or self.game.game_over

    def steer(self, direction: Direction) -> None:
        """プレイヤーを direction へ向ける。"""
        self.game.steer(direction)

    def update(self, dt: float) -> None:
        """dt 秒ぶん進める。クリアしたら少し待ってから次のレベルへ進む。"""
        if self.finished:
            return
        if self.game.cleared:  # 少しだけ「CLEAR!」を見せてから次へ
            self.clear_wait += dt
            if self.clear_wait >= LEVEL_CLEAR_DELAY:
                self.next_level()
            return
        self.game.update(dt)

    def next_level(self) -> None:
        """次のレベルへ進む。最後のレベルなら勝ち。

        クリア後に自動で呼ばれる。チートのレベルスキップからも呼べる。
        """
        if self.finished:
            return
        if self.level == self.level_count:
            self.won = True
            return
        self.level += 1
        self.clear_wait = 0.0
        self.game = self._start_level(self.game.score, self.game.lives)

    # ---- チート（課題 VI.5）。チートモード中で、ゲームが続いている間だけ効く ----

    def toggle_cheat_mode(self) -> None:
        """チートモードを入切する。切ると入っていた機能も全部切れる。"""
        if self.cheats.enabled:
            self.cheats.disable()
        else:
            self.cheats.enabled = True

    def _can_cheat(self) -> bool:
        """チートモード中で、ゲームが続いているなら True。"""
        return self.cheats.enabled and not self.finished

    def toggle_invincible(self) -> None:
        """無敵（ゴーストに触れてもミスにならない）を入切する。"""
        if self._can_cheat():
            self.cheats.invincible = not self.cheats.invincible

    def toggle_ghost_freeze(self) -> None:
        """ゴースト停止を入切する。"""
        if self._can_cheat():
            self.cheats.ghosts_frozen = not self.cheats.ghosts_frozen

    def toggle_fast(self) -> None:
        """プレイヤーの速度アップを入切する。"""
        if self._can_cheat():
            self.cheats.fast = not self.cheats.fast

    def add_life(self) -> None:
        """残機を 1 つ増やす。HUD に 1 桁で出すので、設定の上限までにする。"""
        if self._can_cheat():
            self.game.lives = min(self.game.lives + 1, LIVES_MAX)

    def skip_level(self) -> None:
        """今のレベルをすぐクリアした扱いにして次へ（最後のレベルなら勝ち）。"""
        if self._can_cheat():
            self.next_level()

    def _start_level(self, score: int, lives: int) -> Game:
        """今のレベルの迷路と Game を作る。score と lives は引き継ぐ値。

        迷路はレベル 1 だけ設定のシードで作り、2 からはランダム（シード 0）。
        """
        level: LevelConfig = self.config.levels[self.level - 1]
        seed = self.config.seed if self.level == 1 else 0
        maze = Maze(level.width, level.height, seed=seed)
        rules = Rules(
            level_time=float(level.level_max_time),
            points_per_pacgum=self.config.points_per_pacgum,
            points_per_super_pacgum=self.config.points_per_super_pacgum,
            points_per_ghost=self.config.points_per_ghost,
        )
        return Game(maze, self.rng, rules, score=score, lives=lives,
                    cheats=self.cheats)
