import math

import pygame

from src.game import Game
from src.mazegen import Direction, Maze
from src.mover import Mover

# MLX には線や四角を描く関数がないので pygame.draw は使わない。
# 単色の画像（Surface）を最初に作っておき、毎フレームそれを貼る（blit）だけにする。
# 対応表: project_management/mlx_pygame_mapping.ja.md

CELL = 32
WALL = 2  # 壁の太さ
MARGIN = 4  # 外周の壁が画面端で切れないように
HUD_HEIGHT = 28  # 画面上部の HUD（得点・残機・残り時間）の帯
MAZE_TOP = HUD_HEIGHT + MARGIN
WALL_COLOR = (40, 80, 255)
BLOCKED_COLOR = (20, 30, 90)
PLAYER_COLOR = (255, 220, 0)
GHOST_COLORS = ((230, 60, 60), (60, 200, 90), (170, 90, 255),
                (240, 240, 240))
PACGUM_COLOR = (255, 190, 160)
PACGUM_SIZE = 4
SUPER_PACGUM_SIZE = 12
TEXT_COLOR = (255, 255, 255)
# 大きさはロジック側 (Mover.size) が決める。当たり判定と見た目を一致させるため
SPRITE_SIZE = round(Mover.size * CELL)

# 文字は mlx_string_put と同じ使い方だけにする:
# フォントは pygame の内蔵フォント 1 種類・1 サイズ、ASCII だけ、背景色なし、
# 文字の幅を測って中央寄せなどはしない（位置は固定の座標で決める）
FONT_SIZE = 24
HUD_ITEMS_X = (MARGIN, 200, 330, 470)  # SCORE, LIVES, TIME, 状態の表示位置


def solid_image(width: int, height: int,
                color: tuple[int, int, int]) -> pygame.Surface:
    # mlx_new_image + mlx_get_data_addr で全ピクセルに色を書くのと同じ
    image = pygame.Surface((width, height))
    image.fill(color)
    return image


def window_size(maze: Maze) -> tuple[int, int]:
    return (maze.width * CELL + 2 * MARGIN,
            maze.height * CELL + MAZE_TOP + MARGIN)


# セル (x, y) の中心のピクセル座標
def cell_center(x: float, y: float) -> tuple[float, float]:
    return MARGIN + (x + 0.5) * CELL, MAZE_TOP + (y + 0.5) * CELL


class Renderer:
    def __init__(self, maze: Maze) -> None:
        self.maze = maze
        self.h_wall = solid_image(CELL + WALL, WALL, WALL_COLOR)
        self.v_wall = solid_image(WALL, CELL + WALL, WALL_COLOR)
        self.blocked = solid_image(CELL, CELL, BLOCKED_COLOR)
        self.pacgum = solid_image(PACGUM_SIZE, PACGUM_SIZE, PACGUM_COLOR)
        self.super_pacgum = solid_image(SUPER_PACGUM_SIZE, SUPER_PACGUM_SIZE,
                                        PACGUM_COLOR)
        self.player = solid_image(SPRITE_SIZE, SPRITE_SIZE, PLAYER_COLOR)
        self.ghosts = [solid_image(SPRITE_SIZE, SPRITE_SIZE, color)
                       for color in GHOST_COLORS]
        self.font = pygame.font.Font(None, FONT_SIZE)  # 内蔵フォント

    def draw(self, screen: pygame.Surface, game: Game) -> None:
        screen.fill((0, 0, 0))  # mlx_clear_window
        self._draw_maze(screen)
        for x, y in game.pacgums:
            self._draw_centered(screen, self.pacgum, x, y)
        for x, y in game.super_pacgums:
            self._draw_centered(screen, self.super_pacgum, x, y)
        for i, ghost in enumerate(game.ghosts):
            image = self.ghosts[i % len(self.ghosts)]
            self._draw_mover(screen, image, ghost)
        self._draw_mover(screen, self.player, game.player)
        self._draw_hud(screen, game)

    # mlx_string_put(mlx, win, x, y, color, text) の代わり
    def put_string(self, screen: pygame.Surface, x: int, y: int,
                   color: tuple[int, int, int], text: str) -> None:
        screen.blit(self.font.render(text, False, color), (x, y))

    def _draw_hud(self, screen: pygame.Surface, game: Game) -> None:
        status = ""
        if game.cleared:
            status = "CLEAR!"
        elif game.game_over:
            status = "TIME UP" if game.time_left == 0.0 else "GAME OVER"
        texts = (f"SCORE {game.score}", f"LIVES {game.lives}",
                 # round で小数の誤差（89.0000001 → 90 表示）を防ぐ
                 f"TIME {math.ceil(round(game.time_left, 6))}", status)
        for x, text in zip(HUD_ITEMS_X, texts):
            self.put_string(screen, x, 6, TEXT_COLOR, text)

    def _draw_maze(self, screen: pygame.Surface) -> None:
        half = WALL // 2
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                left, top = MARGIN + x * CELL, MAZE_TOP + y * CELL
                if self.maze.is_blocked(x, y):
                    screen.blit(self.blocked, (left, top))
                walls = {
                    Direction.UP: (self.h_wall, left - half, top - half),
                    Direction.DOWN: (self.h_wall, left - half,
                                     top + CELL - half),
                    Direction.LEFT: (self.v_wall, left - half, top - half),
                    Direction.RIGHT: (self.v_wall, left + CELL - half,
                                      top - half),
                }
                for direction, (image, wx, wy) in walls.items():
                    if self.maze.has_wall(x, y, direction):
                        screen.blit(image, (wx, wy))

    # image を (x, y) の中心に合わせて貼る。x, y は小数でもよい
    def _draw_centered(self, screen: pygame.Surface, image: pygame.Surface,
                       x: float, y: float) -> None:
        cx, cy = cell_center(x, y)
        screen.blit(image, (round(cx - image.get_width() / 2),
                            round(cy - image.get_height() / 2)))

    def _draw_mover(self, screen: pygame.Surface, image: pygame.Surface,
                    mover: Mover) -> None:
        self._draw_centered(screen, image, *mover.position)
