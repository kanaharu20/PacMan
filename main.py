import random
import time

import pygame

from src.ghost import Ghost
from src.mazegen import Direction, Maze
from src.player import Player
from src.render import Renderer, window_size

MAZE_SIZE = (21, 21)
SEED = 42
TICK = 1 / 60  # ゲームの更新間隔（秒）。描画の速さに関係なく一定
GHOST_SPEEDS = (5.4, 5.1, 4.8, 4.5)  # プレイヤー (6.0) より少しずつ遅く

KEYS = {
    pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
}


def main() -> None:
    maze = Maze(*MAZE_SIZE, seed=SEED)
    player = Player(maze, maze.center_cell())
    # mazegenerator がグローバルの random を書き換えるので専用の乱数を使う
    rng = random.Random(SEED)
    ghosts = [Ghost(maze, cell, speed, rng)
              for cell, speed in zip(maze.corner_cells(), GHOST_SPEEDS)]

    pygame.init()  # mlx_init
    screen = pygame.display.set_mode(window_size(maze))  # mlx_new_window
    pygame.display.set_caption("Pac-Man (prototype)")
    renderer = Renderer(maze)
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
                    player.steer(KEYS[event.key])
        now = time.perf_counter()
        lag += min(now - last, 0.25)  # 止まっていた後に一気に進まないように
        last = now
        while lag >= TICK:
            player.update(TICK)
            px, py = player.position
            for ghost in ghosts:
                ghost.target = round(px), round(py)
                ghost.update(TICK)
            lag -= TICK
        renderer.draw(screen, player, ghosts)
        pygame.display.flip()  # mlx_do_sync
        time.sleep(max(0.0, TICK - (time.perf_counter() - now)))
    pygame.quit()  # mlx_release


if __name__ == "__main__":
    main()
