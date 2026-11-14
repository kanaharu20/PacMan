import time

import pygame

from src.config import Config
from src.render import WINDOW_SIZE, TextWriter
from src.screens import Context, MainMenuScreen, Screen

TICK = 1 / 60  # ゲームの更新間隔（秒）。描画の速さに関係なく一定
MAX_LAG = 0.25  # 止まっていた後に一気に進まないよう、1 回に進める時間の上限


# ウィンドウとメインループ。今の画面にキー入力・時間・描画を任せるだけ
class App:
    def __init__(self, config: Config) -> None:
        pygame.init()  # mlx_init
        # どの画面でも同じ大きさのウィンドウを使う
        self.window = pygame.display.set_mode(WINDOW_SIZE)  # mlx_new_window
        pygame.display.set_caption("Pac-Man")
        ctx = Context(config, TextWriter())
        self.screen: Screen | None = MainMenuScreen(ctx)

    def run(self) -> None:
        try:
            self._loop()
        finally:
            pygame.quit()  # mlx_release

    def _loop(self) -> None:
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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # mlx_hook (ウィンドウを閉じる)
                self.screen = None
            elif event.type == pygame.KEYDOWN and self.screen is not None:
                self.screen = self.screen.handle_key(event.key)  # KeyPress
            if self.screen is None:
                return  # 終了した後のイベントは誰にも渡さない
