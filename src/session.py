import random

from src.config import Config, LevelConfig
from src.game import Game, Rules
from src.mazegen import Direction, Maze

LEVEL_CLEAR_DELAY = 2.0  # レベルをクリアしてから次のレベルが始まるまで（秒）


# 1 回のゲーム（レベル 1 から最後まで）の進行。描画や入力 (pygame) には依存しない
# レベルごとに新しい迷路と Game を作り、得点と残機だけ引き継ぐ
class Session:
    def __init__(self, config: Config) -> None:
        self.config = config
        # ゴーストの動きの乱数。mazegenerator はグローバルの random を書き換えるので
        # 専用のものを使う（seed が 0 ならランダム）
        self.rng = random.Random(config.seed or None)
        self.level = 1  # 今のレベル（1 から数える）
        self.won = False
        self.clear_wait = 0.0  # クリアしてからの経過時間
        self.game = self._start_level(score=0, lives=config.lives)

    @property
    def level_count(self) -> int:
        return len(self.config.levels)

    # 全レベルをクリアしたか、ゲームオーバーになった
    @property
    def finished(self) -> bool:
        return self.won or self.game.game_over

    def steer(self, direction: Direction) -> None:
        self.game.steer(direction)

    def update(self, dt: float) -> None:
        if self.finished:
            return
        if self.game.cleared:  # 少しだけ「CLEAR!」を見せてから次へ
            self.clear_wait += dt
            if self.clear_wait >= LEVEL_CLEAR_DELAY:
                self.next_level()
            return
        self.game.update(dt)

    # 次のレベルへ進む。最後のレベルなら勝ち
    # （クリア後に自動で呼ばれる。チートのレベルスキップからも呼べる）
    def next_level(self) -> None:
        if self.finished:
            return
        if self.level == self.level_count:
            self.won = True
            return
        self.level += 1
        self.clear_wait = 0.0
        self.game = self._start_level(self.game.score, self.game.lives)

    # 迷路はレベル 1 だけ設定のシードで作り、2 からはランダム（シード 0）
    def _start_level(self, score: int, lives: int) -> Game:
        level: LevelConfig = self.config.levels[self.level - 1]
        seed = self.config.seed if self.level == 1 else 0
        maze = Maze(level.width, level.height, seed=seed)
        rules = Rules(
            level_time=float(level.level_max_time),
            points_per_pacgum=self.config.points_per_pacgum,
            points_per_super_pacgum=self.config.points_per_super_pacgum,
            points_per_ghost=self.config.points_per_ghost,
        )
        return Game(maze, self.rng, rules, score=score, lives=lives)
