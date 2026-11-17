"""ゲーム画面（迷路・ガム・キャラクター・HUD）の描画。"""

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
# チートモード中に HUD の右に出す表示。プレイ領域の左端からの位置（固定の座標）
# 一番狭い迷路でもウィンドウに収まるように決めた（tests/test_cheats.py で確認）
CHEAT_HUD_X = 590
CHEAT_LABELS = ("CHEAT", "1 INVINCIBLE", "2 FREEZE", "3 FAST")
CHEAT_ITEMS_X = (0, 67, 181, 269)  # CHEAT_LABELS それぞれの位置
CHEAT_COLOR = (255, 80, 80)
CHEAT_ON_COLOR = (255, 220, 0)  # 入っている機能
CHEAT_OFF_COLOR = (110, 110, 110)  # 切れている機能


# 文字は mlx_string_put と同じ使い方だけにする:
# フォントは pygame の内蔵フォント 1 種類・1 サイズ、ASCII だけ、背景色なし、
# 文字の幅を測って中央寄せなどはしない（位置は固定の座標で決める）
FONT_SIZE = 24


class TextWriter:
    """画面に文字を書く。mlx_string_put と同じ使い方だけを提供する。"""

    def __init__(self) -> None:
        """pygame の内蔵フォントを 1 回だけ読み込む。"""
        self.font = pygame.font.Font(None, FONT_SIZE)  # 内蔵フォント

    def put_string(self, screen: pygame.Surface, x: int, y: int,
                   color: tuple[int, int, int], text: str) -> None:
        """screen の (x, y) を左上にして text を color で書く。

        mlx_string_put(mlx, win, x, y, color, text) の代わり。
        """
        screen.blit(self.font.render(text, False, color), (x, y))


def solid_image(width: int, height: int,
                color: tuple[int, int, int]) -> pygame.Surface:
    """width x height の、全部 color で塗った画像を作る。

    mlx_new_image + mlx_get_data_addr で全ピクセルに色を書くのと同じ。
    """
    image = pygame.Surface((width, height))
    image.fill(color)
    return image


def play_area_size(width: int, height: int) -> tuple[int, int]:
    """width x height マスの迷路のプレイ領域（HUD ＋ 迷路）のピクセル数。"""
    return (max(width * CELL + 2 * MARGIN, HUD_MIN_WIDTH),
            height * CELL + MAZE_TOP + MARGIN)


# ウィンドウはどの画面でも同じ大きさ。設定で選べる一番大きい迷路が入る大きさにする
WINDOW_SIZE = play_area_size(MAZE_WIDTH_MAX, MAZE_HEIGHT_MAX)


def play_area_origin(maze: Maze) -> tuple[int, int]:
    """プレイ領域の左上の座標。プレイ領域はウィンドウの真ん中に置く。"""
    width, height = play_area_size(maze.width, maze.height)
    return (WINDOW_SIZE[0] - width) // 2, (WINDOW_SIZE[1] - height) // 2


class Renderer:
    """1 つの迷路のゲーム画面を描く。迷路が変わったら作り直す。

    使う画像は最初に全部作っておき、毎フレームはそれを貼るだけにする。
    """

    def __init__(self, maze: Maze, text: TextWriter) -> None:
        """maze の描画位置を決め、壁・ガム・キャラクターの画像を作る。"""
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
        """session の今の状態を screen に描く。状態は読むだけで書き換えない。"""
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

    def _frightened_image(self, time_left: float) -> pygame.Surface:
        """いじけの残りが time_left 秒のゴーストの画像。

        いじけ中は青。終わる直前は青と白を交互に出して、もうすぐ戻ると知らせる。
        """
        if (time_left < FRIGHT_BLINK_TIME
                and int(time_left * FRIGHT_BLINKS_PER_SEC * 2) % 2 == 0):
            return self.fright_ending
        return self.frightened

    def _draw_hud(self, screen: pygame.Surface, session: Session) -> None:
        """上の帯に得点・レベル・残機・残り時間・状態（とチート）を書く。"""
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
        if session.cheats.enabled:
            self._draw_cheats(screen, session)

    def _draw_cheats(self, screen: pygame.Surface, session: Session) -> None:
        """HUD の右に CHEAT と各機能を書く。入っている機能は黄色、切れたら灰色。"""
        cheats = session.cheats
        colors = (CHEAT_COLOR, self._cheat_color(cheats.invincible),
                  self._cheat_color(cheats.ghosts_frozen),
                  self._cheat_color(cheats.fast))
        for x, text, color in zip(CHEAT_ITEMS_X, CHEAT_LABELS, colors):
            self.text.put_string(screen, self.origin_x + CHEAT_HUD_X + x,
                                 self.origin_y + 6, color, text)

    @staticmethod
    def _cheat_color(on: bool) -> tuple[int, int, int]:
        """チートの機能の文字の色。on なら入っている色、そうでなければ灰色。"""
        return CHEAT_ON_COLOR if on else CHEAT_OFF_COLOR

    def _draw_maze(self, screen: pygame.Surface) -> None:
        """迷路の壁と「42」のセルを描く。壁はセルの境目に細い画像を貼る。"""
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

    def _draw_centered(self, screen: pygame.Surface, image: pygame.Surface,
                       x: float, y: float) -> None:
        """image をセル (x, y) の中心に合わせて貼る。x, y は小数でもよい。"""
        cx, cy = self._cell_center(x, y)
        screen.blit(image, (round(cx - image.get_width() / 2),
                            round(cy - image.get_height() / 2)))

    def _cell_center(self, x: float, y: float) -> tuple[float, float]:
        """セル (x, y) の中心のピクセル座標。"""
        return (self.left + (x + 0.5) * CELL,
                self.top + (y + 0.5) * CELL)

    def _draw_mover(self, screen: pygame.Surface, image: pygame.Surface,
                    mover: Mover) -> None:
        """キャラクター mover を、今の位置（セルの途中も含む）に描く。"""
        self._draw_centered(screen, image, *mover.position)
