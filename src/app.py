"""ウィンドウとメインループ（固定時間ステップでゲームを進める）。"""

import time

import pygame

from src.config import Config
from src.highscore import HighscoreTable
from src.render import WINDOW_SIZE, TextWriter
from src.screens import Context, MainMenuScreen, Screen

TICK = 1 / 60  # ゲームの更新間隔（秒）。描画の速さに関係なく一定
MAX_LAG = 0.25  # 止まっていた後に一気に進まないよう、1 回に進める時間の上限


class App:
    """ウィンドウとメインループ。今の画面にキー入力・時間・描画を任せるだけ。"""

    def __init__(self, config: Config) -> None:
        """pygame を初期化し、ウィンドウを開いてメインメニューを用意する。"""
        pygame.init()  # mlx_init
        # どの画面でも同じ大きさのウィンドウを使う
        self.window = pygame.display.set_mode(WINDOW_SIZE)  # mlx_new_window
        pygame.display.set_caption("Pac-Man")
        # ハイスコアはゲームの開始時に読み込む（課題 V.5）
        highscores = HighscoreTable.load(config.highscore_filename)
        ctx = Context(config, TextWriter(), highscores)
        self.screen: Screen | None = MainMenuScreen(ctx)

    def run(self) -> None:
        """画面がなくなる（終了する）までループし、最後に必ず pygame を閉じる。"""
        try:
            self._loop()
        finally:
            pygame.quit()  # mlx_release

    def _loop(self) -> None:
        """入力 → TICK 秒ずつ更新 → 描画、をくり返す。

        経過時間を lag にためて TICK ごとに update を呼ぶので、描画の速さが
        変わってもゲームの速さは変わらない。
        """
        # MLX にタイマーはないので、時間は Python 標準の time で測る
        last = time.perf_counter()
        lag = 0.0
        while self.screen is not None:  # mlx_loop + mlx_loop_hook
            self._handle_events()
            now = time.perf_counter()
            lag += min(now - last, MAX_LAG)
            last = now
            while lag >= TICK and self.screen is not None:
                self.screen = self.screen.update(TICK)
                lag -= TICK
            if self.screen is None:
                return
            self.screen.draw(self.window)
            pygame.display.flip()  # mlx_do_sync
            time.sleep(max(0.0, TICK - (time.perf_counter() - now)))

    def _handle_events(self) -> None:
        """たまったイベントを処理する。キーは今の画面に渡し、閉じたら終了する。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # mlx_hook (ウィンドウを閉じる)
                self.screen = None
            elif event.type == pygame.KEYDOWN and self.screen is not None:
                self.screen = self.screen.handle_key(event.key)  # KeyPress
            if self.screen is None:
                return  # 終了した後のイベントは誰にも渡さない
