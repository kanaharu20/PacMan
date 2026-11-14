import logging
import os
import sys
import time

# pygame の起動メッセージ（"pygame-ce 2.5.8 (SDL ...)"）をターミナルに出さない。
# pygame を import する前に設定しないと効かないので、ここだけ import の途中に書く
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from src.config import Config, ConfigError, load_config  # noqa: E402
from src.mazegen import Direction, MazeError  # noqa: E402
from src.render import Renderer, window_size  # noqa: E402
from src.session import Session  # noqa: E402

TICK = 1 / 60  # ゲームの更新間隔（秒）。描画の速さに関係なく一定
USAGE = "usage: python3 pac-man.py <config.json>"

KEYS = {
    pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
}


def main() -> None:
    # 設定の補正などのメッセージを「WARNING: ...」の形でターミナルに出す
    logging.basicConfig(format="%(levelname)s: %(message)s")
    if len(sys.argv) != 2:
        sys.exit(USAGE)
    try:
        config = load_config(sys.argv[1])
    except ConfigError as e:
        sys.exit(f"Error: {e}")  # トレースバックは出さず、理由だけ出して終了
    # どこで何が起きてもトレースバックを出さない（最後の砦）
    try:
        run(config)
    except KeyboardInterrupt:  # Ctrl+C
        sys.exit(0)
    except MazeError as e:
        sys.exit(f"Error: {e}")
    except Exception as e:
        sys.exit(f"Error: unexpected {type(e).__name__}: {e}")


def run(config: Config) -> None:
    session = Session(config)
    pygame.init()  # mlx_init
    try:
        play(session)
    finally:
        pygame.quit()  # mlx_release（エラーで抜けたときも必ず呼ぶ）


def play(session: Session) -> None:
    # レベルごとに迷路の大きさが変わるので、変わったらウィンドウを作り直す
    game = session.game
    screen = pygame.display.set_mode(window_size(game.maze))  # mlx_new_window
    pygame.display.set_caption("Pac-Man (prototype)")
    renderer = Renderer(game.maze)
    # MLX にタイマーはないので、時間は Python 標準の time で測る
    last = time.perf_counter()
    lag = 0.0
    running = True
    while running:  # mlx_loop + mlx_loop_hook
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # mlx_hook (ウィンドウを閉じる)
                running = False
            elif event.type == pygame.KEYDOWN:  # mlx_hook (KeyPress)
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in KEYS:
                    session.steer(KEYS[event.key])
        now = time.perf_counter()
        lag += min(now - last, 0.25)  # 止まっていた後に一気に進まないように
        last = now
        while lag >= TICK:
            session.update(TICK)
            lag -= TICK
        if session.game is not game:  # 次のレベルに進んだ
            game = session.game
            screen = pygame.display.set_mode(window_size(game.maze))
            renderer = Renderer(game.maze)
        renderer.draw(screen, session)
        pygame.display.flip()  # mlx_do_sync
        time.sleep(max(0.0, TICK - (time.perf_counter() - now)))


if __name__ == "__main__":
    main()
