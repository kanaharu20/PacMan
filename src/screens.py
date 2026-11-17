from collections.abc import Callable
from dataclasses import dataclass

import pygame

from src.config import Config
from src.game import FRIGHT_TIME, GHOST_RESPAWN_DELAY
from src.highscore import MAX_ENTRIES, NAME_MAX, HighscoreTable, valid_name
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
BOTTOM_HINT_Y = 780  # 説明などの画面の一番下の案内の位置
# ハイスコアの列の位置。"10." が 22px、一番幅の広い名前 "WWWWWWWWWW" が 150px
RANK_X = TEXT_X
NAME_X = TEXT_X + 50
SCORE_X = TEXT_X + 220
NAME_INPUT_X = MENU_X + 170  # "ENTER YOUR NAME:" (160px) の右

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
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)  # 名前入力中は SPACE は文字
CHEAT_MODE_KEY = pygame.K_c
# チートモード中だけ効くキー（テンキーの数字も同じ）。Session のメソッドを呼ぶ
CHEAT_KEYS: dict[int, Callable[[Session], None]] = {
    pygame.K_1: Session.toggle_invincible,
    pygame.K_2: Session.toggle_ghost_freeze,
    pygame.K_3: Session.toggle_fast,
    pygame.K_4: Session.add_life,
    pygame.K_5: Session.skip_level,
    pygame.K_KP1: Session.toggle_invincible,
    pygame.K_KP2: Session.toggle_ghost_freeze,
    pygame.K_KP3: Session.toggle_fast,
    pygame.K_KP4: Session.add_life,
    pygame.K_KP5: Session.skip_level,
}
# 名前入力で使えるキーと文字。MLX のキーフックと同じく、キーの番号だけから
# 文字を決める（英字は大文字にする）。英数字とスペースだけ（課題 V.5）
NAME_KEYS: dict[int, str] = {
    **{pygame.K_a + i: chr(ord("A") + i) for i in range(26)},
    **{pygame.K_0 + i: str(i) for i in range(10)},
    **{key: str(i) for i, key in enumerate(
        (pygame.K_KP0, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP4,
         pygame.K_KP5, pygame.K_KP6, pygame.K_KP7, pygame.K_KP8,
         pygame.K_KP9))},
    pygame.K_SPACE: " ",
}


# 全部の画面で共有するもの。フォントは最初に 1 回だけ作る。
# ハイスコアは起動時に 1 回だけ読み込み、名前が入力されるたびに保存する
@dataclass
class Context:
    config: Config
    text: TextWriter
    highscores: HighscoreTable


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
        elif key == CHEAT_MODE_KEY:
            self.session.toggle_cheat_mode()
        elif key in CHEAT_KEYS:  # チートモードでなければ Session が無視する
            CHEAT_KEYS[key](self.session)
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


# ゲームオーバーと勝利の画面。勝っても負けても名前を入力してハイスコアに登録できる
# （課題 V.5 / VI.8）。ENTER で登録してハイスコアの画面へ、ESC で登録せずにメニューへ
class ResultScreen(Screen):
    def __init__(self, ctx: Context, won: bool, time_up: bool,
                 score: int) -> None:
        super().__init__(ctx)
        self.won = won
        self.time_up = time_up
        self.score = score
        self.name = ""

    def handle_key(self, key: int) -> Screen | None:
        if key == pygame.K_ESCAPE:
            return MainMenuScreen(self.ctx)
        if key in CONFIRM_KEYS:
            return self._register() if valid_name(self.name) else self
        if key == pygame.K_BACKSPACE:
            self.name = self.name[:-1]
        elif key in NAME_KEYS and len(self.name) < NAME_MAX:
            char = NAME_KEYS[key]
            if char != " " or self.name:  # 先頭の空白は入れない
                self.name += char
        return self

    # 一覧に追加して、上位 10 件に入ったらファイルに保存する
    def _register(self) -> Screen:
        table = self.ctx.highscores
        rank = table.add(self.name.rstrip(), self.score)
        if rank is None:
            note = f"Your score did not make the top {MAX_ENTRIES}."
        elif not table.save():
            note = "Could not save the highscores (see the terminal)."
        else:
            note = f"You are number {rank + 1}!"
        return HighscoresScreen(self.ctx, highlight=rank, note=note)

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
        name_y = MENU_TOP + 3 * LINE_HEIGHT
        self.ctx.text.put_string(surface, MENU_X, name_y, TEXT_COLOR,
                                 "ENTER YOUR NAME:")
        cursor = "_" if len(self.name) < NAME_MAX else ""
        self.ctx.text.put_string(surface, NAME_INPUT_X, name_y,
                                 SELECTED_COLOR, self.name + cursor)
        self.put_lines(surface, MENU_X, name_y + LINE_HEIGHT, [
            f"Letters, digits and spaces (up to {NAME_MAX})."
            "  BACKSPACE: delete",
            "ENTER: save   ESC: skip and go back to the main menu",
        ], HINT_COLOR)


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
            "  Cheat mode: C (see below)",
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
            "",
            "CHEAT MODE (for reviewers)",
            "  C: turn cheat mode on/off. It shows CHEAT at the top right.",
            "  1: invincible   2: freeze ghosts   3: fast player"
            "   (press again to turn off)",
            "  4: +1 life   5: skip the level",
        ]


# 上位 10 件の順位・名前・得点。名前を登録した直後は、その行を黄色にする
class HighscoresScreen(InfoScreen):
    title = "HIGHSCORES"

    def __init__(self, ctx: Context, highlight: int | None = None,
                 note: str = "") -> None:
        super().__init__(ctx)
        self.highlight = highlight
        self.note = note

    def lines(self) -> list[str]:
        if self.ctx.highscores.entries:
            return []
        return ["No highscores yet."]

    # 文字ごとに幅が違うフォントなので、列は固定の x 座標で揃える
    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        for i, entry in enumerate(self.ctx.highscores.entries):
            y = TEXT_TOP + i * LINE_HEIGHT
            color = SELECTED_COLOR if i == self.highlight else TEXT_COLOR
            for x, text in ((RANK_X, f"{i + 1}."), (NAME_X, entry.name),
                            (SCORE_X, str(entry.score))):
                self.ctx.text.put_string(surface, x, y, color, text)
        if self.note:
            self.ctx.text.put_string(
                surface, TEXT_X, TEXT_TOP + (MAX_ENTRIES + 1) * LINE_HEIGHT,
                SELECTED_COLOR, self.note)
