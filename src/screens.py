from dataclasses import dataclass

import pygame

from src.config import Config
from src.game import FRIGHT_TIME, GHOST_RESPAWN_DELAY
from src.mazegen import Direction
from src.render import Renderer, TextWriter, solid_image
from src.session import Session

# 画面は「キー入力を受け取る・時間を進める・描く」の 3 つを持つ。
# handle_key と update は次に表示する画面を返す（そのままなら self、終了なら None）

END_DELAY = 2.0  # ゲームが終わってから結果の画面に移るまで（秒）

# 文字の位置は固定の座標（文字の幅を測って中央寄せはしない。MLX の決まり）
TITLE_POS = (560, 220)
MENU_X = 560
MENU_TOP = 300
LINE_HEIGHT = 36
CURSOR_OFFSET = 24  # 選んでいる項目の左に出す ">" の位置
TEXT_X = 360  # 説明などの長い文の左端
TEXT_TOP = 150
SMALL_LINE_HEIGHT = 30
BOTTOM_HINT_Y = 720  # 説明などの画面の一番下の案内の位置

TITLE_COLOR = (255, 220, 0)
TEXT_COLOR = (255, 255, 255)
SELECTED_COLOR = (255, 220, 0)
HINT_COLOR = (150, 150, 150)
PANEL_COLOR = (20, 20, 60)
PANEL_RECT = (480, 260, 330, 190)  # 一時停止の枠 (x, y, 幅, 高さ)

UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
SELECT_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
PAUSE_KEYS = (pygame.K_ESCAPE, pygame.K_p)
STEER_KEYS = {
    pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
}


# 全部の画面で共有するもの。フォントは最初に 1 回だけ作る
@dataclass
class Context:
    config: Config
    text: TextWriter


class Screen:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def handle_key(self, key: int) -> "Screen | None":
        raise NotImplementedError

    def update(self, dt: float) -> "Screen | None":
        return self

    def draw(self, surface: pygame.Surface) -> None:
        raise NotImplementedError

    def put_lines(self, surface: pygame.Surface, x: int, y: int,
                  lines: list[str], color: tuple[int, int, int],
                  line_height: int = SMALL_LINE_HEIGHT) -> None:
        for i, line in enumerate(lines):
            self.ctx.text.put_string(surface, x, y + i * line_height,
                                     color, line)


# 上下キーで選んで Enter で決める項目のリスト。端まで行ったら反対の端に戻る
class Menu:
    def __init__(self, items: list[str]) -> None:
        self.items = items
        self.index = 0

    @property
    def selected(self) -> str:
        return self.items[self.index]

    # 上下キーなら選択を動かして True。それ以外のキーは False
    def move(self, key: int) -> bool:
        if key in UP_KEYS:
            self.index = (self.index - 1) % len(self.items)
        elif key in DOWN_KEYS:
            self.index = (self.index + 1) % len(self.items)
        else:
            return False
        return True

    def draw(self, ctx: Context, surface: pygame.Surface,
             x: int, y: int) -> None:
        for i, item in enumerate(self.items):
            line_y = y + i * LINE_HEIGHT
            if i == self.index:
                ctx.text.put_string(surface, x - CURSOR_OFFSET, line_y,
                                    SELECTED_COLOR, ">")
                ctx.text.put_string(surface, x, line_y, SELECTED_COLOR, item)
            else:
                ctx.text.put_string(surface, x, line_y, TEXT_COLOR, item)


class MainMenuScreen(Screen):
    START = "START GAME"
    HIGHSCORES = "HIGHSCORES"
    INSTRUCTIONS = "INSTRUCTIONS"
    EXIT = "EXIT"

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.menu = Menu([self.START, self.HIGHSCORES, self.INSTRUCTIONS,
                          self.EXIT])

    def handle_key(self, key: int) -> Screen | None:
        if self.menu.move(key):
            return self
        if key == pygame.K_ESCAPE:
            return None
        if key not in SELECT_KEYS:
            return self
        choice = self.menu.selected
        if choice == self.START:
            return PlayScreen(self.ctx)
        if choice == self.HIGHSCORES:
            return HighscoresScreen(self.ctx)
        if choice == self.INSTRUCTIONS:
            return InstructionsScreen(self.ctx)
        return None  # EXIT

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))
        self.ctx.text.put_string(surface, *TITLE_POS, TITLE_COLOR, "PAC-MAN")
        self.menu.draw(self.ctx, surface, MENU_X, MENU_TOP)
        self.ctx.text.put_string(surface, MENU_X - CURSOR_OFFSET,
                                 MENU_TOP + 5 * LINE_HEIGHT, HINT_COLOR,
                                 "UP/DOWN: choose   ENTER: select")


class PlayScreen(Screen):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        # 「START GAME」のたびにレベル 1 から始める（前のゲームは使い回さない）
        self.session = Session(ctx.config)
        self.renderer = Renderer(self.session.game.maze, ctx.text)
        self.end_wait = 0.0  # 終わってからの経過時間。結果を少し見せてから移る

    def handle_key(self, key: int) -> Screen | None:
        if key in PAUSE_KEYS and not self.session.finished:
            return PauseScreen(self.ctx, self)
        if key in STEER_KEYS:
            self.session.steer(STEER_KEYS[key])
        return self

    def update(self, dt: float) -> Screen | None:
        if not self.session.finished:
            self.session.update(dt)
            return self
        self.end_wait += dt
        if self.end_wait < END_DELAY:
            return self
        game = self.session.game
        return ResultScreen(self.ctx, won=self.session.won,
                            time_up=game.time_left == 0.0, score=game.score)

    def draw(self, surface: pygame.Surface) -> None:
        # 次のレベルに進んだら迷路が変わるので、その迷路用の画像を作り直す
        # （ウィンドウの大きさは変えない）
        if self.renderer.maze is not self.session.game.maze:
            self.renderer = Renderer(self.session.game.maze, self.ctx.text)
        self.renderer.draw(surface, self.session)


# 一時停止中は止まったゲームの上に枠とメニューを重ねる。ゲームは同じものを持ち続ける
class PauseScreen(Screen):
    RESUME = "RESUME"
    MAIN_MENU = "MAIN MENU"

    def __init__(self, ctx: Context, play: PlayScreen) -> None:
        super().__init__(ctx)
        self.play = play
        self.menu = Menu([self.RESUME, self.MAIN_MENU])
        x, y, width, height = PANEL_RECT
        self.panel = solid_image(width, height, PANEL_COLOR)
        self.panel_pos = (x, y)

    def handle_key(self, key: int) -> Screen | None:
        if key in PAUSE_KEYS:
            return self.play
        if self.menu.move(key) or key not in SELECT_KEYS:
            return self
        if self.menu.selected == self.RESUME:
            return self.play
        return MainMenuScreen(self.ctx)

    def draw(self, surface: pygame.Surface) -> None:
        self.play.draw(surface)
        surface.blit(self.panel, self.panel_pos)
        x, y = self.panel_pos
        self.ctx.text.put_string(surface, x + 40, y + 24, TITLE_COLOR,
                                 "PAUSED")
        self.menu.draw(self.ctx, surface, x + 64, y + 70)
        self.ctx.text.put_string(surface, x + 40, y + 150, HINT_COLOR,
                                 "ESC / P: resume")


# ゲームオーバーと勝利の画面。名前の入力はハイスコアを作るときに追加する
class ResultScreen(Screen):
    def __init__(self, ctx: Context, won: bool, time_up: bool,
                 score: int) -> None:
        super().__init__(ctx)
        self.won = won
        self.time_up = time_up
        self.score = score

    def handle_key(self, key: int) -> Screen | None:
        if key in SELECT_KEYS or key == pygame.K_ESCAPE:
            return MainMenuScreen(self.ctx)
        return self

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))
        if self.won:
            title, message = "CONGRATULATIONS!", "You cleared every level!"
        elif self.time_up:
            title, message = "TIME UP", "The time limit ran out."
        else:
            title, message = "GAME OVER", "You lost all your lives."
        self.ctx.text.put_string(surface, *TITLE_POS, TITLE_COLOR, title)
        self.put_lines(surface, MENU_X, MENU_TOP,
                       [message, f"FINAL SCORE  {self.score}"], TEXT_COLOR,
                       LINE_HEIGHT)
        self.ctx.text.put_string(surface, MENU_X, MENU_TOP + 3 * LINE_HEIGHT,
                                 HINT_COLOR, "ENTER: back to main menu")


# メインメニューから開く、文を表示するだけの画面
class InfoScreen(Screen):
    title = ""

    def lines(self) -> list[str]:
        raise NotImplementedError

    def handle_key(self, key: int) -> Screen | None:
        if key in SELECT_KEYS or key == pygame.K_ESCAPE:
            return MainMenuScreen(self.ctx)
        return self

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))
        self.ctx.text.put_string(surface, TEXT_X, TEXT_TOP - 50, TITLE_COLOR,
                                 self.title)
        self.put_lines(surface, TEXT_X, TEXT_TOP, self.lines(), TEXT_COLOR)
        self.ctx.text.put_string(surface, TEXT_X, BOTTOM_HINT_Y, HINT_COLOR,
                                 "ENTER / ESC: back to main menu")


class InstructionsScreen(InfoScreen):
    title = "INSTRUCTIONS"

    # 数字は設定とゲームの定数から作る（値を変えても説明がずれないように）
    def lines(self) -> list[str]:
        config = self.ctx.config
        return [
            # 文字ごとに幅が違うフォントなので、空白で列を揃えない
            "CONTROLS",
            "  Move: arrow keys or WASD",
            "  Pause: ESC or P",
            "  Menus: UP/DOWN to choose, ENTER to select",
            "",
            "RULES",
            "  Eat every pacgum in the maze to clear the level.",
            f"  Clear all {len(config.levels)} levels to win."
            " Score and lives carry over.",
            f"  Pacgum: {config.points_per_pacgum} points."
            "  Super pacgum (corners):"
            f" {config.points_per_super_pacgum} points.",
            f"  After a super pacgum, ghosts run away for {FRIGHT_TIME:g}"
            " seconds.",
            f"  Eat a running ghost for {config.points_per_ghost} points."
            f" It comes back in {GHOST_RESPAWN_DELAY:g} seconds.",
            "  Touching a normal ghost costs a life."
            f" You have {config.lives}.",
            "  Each level has a time limit (TIME at the top).",
            "  The game is over when time runs out or no lives are left.",
        ]


class HighscoresScreen(InfoScreen):
    title = "HIGHSCORES"

    def lines(self) -> list[str]:
        return ["No highscores yet."]  # ハイスコアの保存を作るときに中身を入れる
