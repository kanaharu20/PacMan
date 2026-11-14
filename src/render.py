import math

import pygame

from src.config import MAZE_HEIGHT_MAX, MAZE_WIDTH_MAX
from src.mazegen import Direction, Maze
from src.mover import Mover
from src.session import Session

# MLX には線や四角を描く関数がないので pygame.draw は使わない。
# 単色の画像（Surface）を最初に作っておき、毎フレームそれを貼る（blit）だけにする。
# 対応表: project_management/mlx_pygame_mapping.ja.md

CELL = 32
WALL = 2  # 壁の太さ
MARGIN = 4  # 外周の壁が画面端で切れないように
HUD_HEIGHT = 28  # 画面上部の HUD（得点・レベル・残機・残り時間）の帯
MAZE_TOP = HUD_HEIGHT + MARGIN
WALL_COLOR = (40, 80, 255)
BLOCKED_COLOR = (20, 30, 90)
PLAYER_COLOR = (255, 220, 0)
GHOST_COLORS = ((230, 60, 60), (60, 200, 90), (170, 90, 255),
                (240, 240, 240))
FRIGHTENED_COLOR = (40, 40, 220)  # いじけ中のゴースト
FRIGHT_ENDING_COLOR = (230, 230, 255)  # いじけが終わりそうなときに点滅する色
FRIGHT_BLINK_TIME = 2.0  # いじけの残りがこの秒数を切ったら点滅する
FRIGHT_BLINKS_PER_SEC = 4
PACGUM_COLOR = (255, 190, 160)
PACGUM_SIZE = 4
SUPER_PACGUM_SIZE = 12
TEXT_COLOR = (255, 255, 255)
# 大きさはロジック側 (Mover.size) が決める。当たり判定と見た目を一致させるため
SPRITE_SIZE = round(Mover.size * CELL)

# SCORE, LEVEL, LIVES, TIME, 状態の表示位置。一番長くなる文字の幅（"SCORE 999999"
# 120px、"LEVEL 50/50" 95px、"LIVES 9" 59px、"TIME 999" 72px）に余白を足して決めた
HUD_ITEMS_X = (MARGIN, 140, 255, 335, 430)
# HUD の文字が全部入る幅。迷路がこれより狭いときは、プレイ領域をこの幅にして
# 迷路を左右の真ん中に置く（"GAME OVER" が約 98px なので 430 + 98 に余白を足す）
HUD_MIN_WIDTH = 580


# 文字は mlx_string_put と同じ使い方だけにする:
# フォントは pygame の内蔵フォント 1 種類・1 サイズ、ASCII だけ、背景色なし、
# 文字の幅を測って中央寄せなどはしない（位置は固定の座標で決める）
FONT_SIZE = 24


class TextWriter:
    def __init__(self) -> None:
        self.font = pygame.font.Font(None, FONT_SIZE)  # 内蔵フォント

    # mlx_string_put(mlx, win, x, y, color, text) の代わり
    def put_string(self, screen: pygame.Surface, x: int, y: int,
                   color: tuple[int, int, int], text: str) -> None:
        screen.blit(self.font.render(text, False, color), (x, y))


def solid_image(width: int, height: int,
                color: tuple[int, int, int]) -> pygame.Surface:
    # mlx_new_image + mlx_get_data_addr で全ピクセルに色を書くのと同じ
    image = pygame.Surface((width, height))
    image.fill(color)
    return image


# プレイ領域（HUD ＋ 迷路）の大きさ。迷路の大きさで決まる
def play_area_size(width: int, height: int) -> tuple[int, int]:
    return (max(width * CELL + 2 * MARGIN, HUD_MIN_WIDTH),
            height * CELL + MAZE_TOP + MARGIN)


# ウィンドウはどの画面でも同じ大きさ。設定で選べる一番大きい迷路が入る大きさにする
WINDOW_SIZE = play_area_size(MAZE_WIDTH_MAX, MAZE_HEIGHT_MAX)


# プレイ領域の左上の座標。ウィンドウの真ん中に置く
def play_area_origin(maze: Maze) -> tuple[int, int]:
    width, height = play_area_size(maze.width, maze.height)
    return (WINDOW_SIZE[0] - width) // 2, (WINDOW_SIZE[1] - height) // 2


class Renderer:
    def __init__(self, maze: Maze, text: TextWriter) -> None:
        self.maze = maze
        self.text = text
        # HUD と迷路は、ウィンドウの真ん中に置いたプレイ領域の中に描く
        self.origin_x, self.origin_y = play_area_origin(maze)
        area_width = play_area_size(maze.width, maze.height)[0]
        # 迷路の左上。迷路がプレイ領域より狭いときは左右の真ん中に寄せる
        self.left = self.origin_x + (area_width - maze.width * CELL) // 2
        self.top = self.origin_y + MAZE_TOP
        self.h_wall = solid_image(CELL + WALL, WALL, WALL_COLOR)
        self.v_wall = solid_image(WALL, CELL + WALL, WALL_COLOR)
        self.blocked = solid_image(CELL, CELL, BLOCKED_COLOR)
        self.pacgum = solid_image(PACGUM_SIZE, PACGUM_SIZE, PACGUM_COLOR)
        self.super_pacgum = solid_image(SUPER_PACGUM_SIZE, SUPER_PACGUM_SIZE,
                                        PACGUM_COLOR)
        self.player = solid_image(SPRITE_SIZE, SPRITE_SIZE, PLAYER_COLOR)
        self.ghosts = [solid_image(SPRITE_SIZE, SPRITE_SIZE, color)
                       for color in GHOST_COLORS]
        self.frightened = solid_image(SPRITE_SIZE, SPRITE_SIZE,
                                      FRIGHTENED_COLOR)
        self.fright_ending = solid_image(SPRITE_SIZE, SPRITE_SIZE,
                                         FRIGHT_ENDING_COLOR)

    def draw(self, screen: pygame.Surface, session: Session) -> None:
        game = session.game
        screen.fill((0, 0, 0))  # mlx_clear_window
        self._draw_maze(screen)
        for x, y in game.pacgums:
            self._draw_centered(screen, self.pacgum, x, y)
        for x, y in game.super_pacgums:
            self._draw_centered(screen, self.super_pacgum, x, y)
        for i, ghost in enumerate(game.ghosts):
            if ghost.eaten:  # 食べられて復活待ちの間は描かない
                continue
            image = self.ghosts[i % len(self.ghosts)]
            if ghost.frightened:
                image = self._frightened_image(ghost.fright)
            self._draw_mover(screen, image, ghost)
        self._draw_mover(screen, self.player, game.player)
        self._draw_hud(screen, session)

    # いじけ中は青。終わる直前は青と白を交互に出して、もうすぐ戻ると知らせる
    def _frightened_image(self, time_left: float) -> pygame.Surface:
        if (time_left < FRIGHT_BLINK_TIME
                and int(time_left * FRIGHT_BLINKS_PER_SEC * 2) % 2 == 0):
            return self.fright_ending
        return self.frightened

    def _draw_hud(self, screen: pygame.Surface, session: Session) -> None:
        game = session.game
        status = ""
        if session.won:
            status = "YOU WIN!"
        elif game.cleared:
            status = "CLEAR!"
        elif game.game_over:
            status = "TIME UP" if game.time_left == 0.0 else "GAME OVER"
        texts = (f"SCORE {game.score}",
                 f"LEVEL {session.level}/{session.level_count}",
                 f"LIVES {game.lives}",
                 # round で小数の誤差（89.0000001 → 90 表示）を防ぐ
                 f"TIME {math.ceil(round(game.time_left, 6))}", status)
        for x, text in zip(HUD_ITEMS_X, texts):
            self.text.put_string(screen, self.origin_x + x,
                                 self.origin_y + 6, TEXT_COLOR, text)

    def _draw_maze(self, screen: pygame.Surface) -> None:
        half = WALL // 2
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                left, top = self.left + x * CELL, self.top + y * CELL
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
        cx, cy = self._cell_center(x, y)
        screen.blit(image, (round(cx - image.get_width() / 2),
                            round(cy - image.get_height() / 2)))

    # セル (x, y) の中心のピクセル座標
    def _cell_center(self, x: float, y: float) -> tuple[float, float]:
        return (self.left + (x + 0.5) * CELL,
                self.top + (y + 0.5) * CELL)

    def _draw_mover(self, screen: pygame.Surface, image: pygame.Surface,
                    mover: Mover) -> None:
        self._draw_centered(screen, image, *mover.position)
