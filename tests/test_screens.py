import os
from collections.abc import Iterator

import pygame
import pytest

from src.app import TICK, App
from src.config import Config
from src.render import WINDOW_SIZE, TextWriter
from src.screens import (END_DELAY, Context, HighscoresScreen,
                         InstructionsScreen, MainMenuScreen, PauseScreen,
                         PlayScreen, ResultScreen, Screen)

ENTER = pygame.K_RETURN
DOWN = pygame.K_DOWN
UP = pygame.K_UP
ESC = pygame.K_ESCAPE


# 画面を出さずに pygame を動かす（フォントを使うには初期化が必要）
@pytest.fixture(autouse=True)
def headless() -> Iterator[None]:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def ctx() -> Context:
    return Context(Config(), TextWriter())


def press(screen: Screen, *keys: int) -> Screen | None:
    result: Screen | None = screen
    for key in keys:
        assert result is not None
        result = result.handle_key(key)
    return result


def test_menu_cursor_wraps_around(ctx: Context) -> None:
    menu = MainMenuScreen(ctx)
    assert menu.menu.selected == MainMenuScreen.START
    press(menu, UP)
    assert menu.menu.selected == MainMenuScreen.EXIT
    press(menu, DOWN)
    assert menu.menu.selected == MainMenuScreen.START


@pytest.mark.parametrize("downs, expected", [
    (0, PlayScreen), (1, HighscoresScreen), (2, InstructionsScreen)])
def test_menu_items_open_their_screen(ctx: Context, downs: int,
                                      expected: type) -> None:
    menu = MainMenuScreen(ctx)
    assert isinstance(press(menu, *[DOWN] * downs, ENTER), expected)


def test_exit_and_esc_quit_from_menu(ctx: Context) -> None:
    assert press(MainMenuScreen(ctx), UP, ENTER) is None  # EXIT
    assert press(MainMenuScreen(ctx), ESC) is None


@pytest.mark.parametrize("screen_type",
                         [HighscoresScreen, InstructionsScreen])
def test_info_screens_go_back_to_menu(ctx: Context,
                                      screen_type: type[Screen]) -> None:
    for key in (ENTER, ESC):
        assert isinstance(press(screen_type(ctx), key), MainMenuScreen)


def test_pause_and_resume_keep_the_same_game(ctx: Context) -> None:
    play = PlayScreen(ctx)
    pause = press(play, ESC)
    assert isinstance(pause, PauseScreen)
    assert press(pause, ESC) is play
    assert press(PauseScreen(ctx, play), pygame.K_p) is play
    assert press(PauseScreen(ctx, play), ENTER) is play  # RESUME


def test_game_does_not_move_while_paused(ctx: Context) -> None:
    play = PlayScreen(ctx)
    pause = press(play, ESC)
    assert pause is not None
    before = play.session.game.time_left
    for _ in range(60):
        assert pause.update(TICK) is pause
    assert play.session.game.time_left == before


def test_pause_to_main_menu(ctx: Context) -> None:
    pause = PauseScreen(ctx, PlayScreen(ctx))
    assert isinstance(press(pause, DOWN, ENTER), MainMenuScreen)


def test_start_game_makes_a_new_game_each_time(ctx: Context) -> None:
    first = press(MainMenuScreen(ctx), ENTER)
    second = press(MainMenuScreen(ctx), ENTER)
    assert isinstance(first, PlayScreen) and isinstance(second, PlayScreen)
    assert first.session is not second.session
    assert first.session.level == 1


def run_until_result(play: PlayScreen) -> Screen | None:
    screen: Screen | None = play
    for _ in range(int(END_DELAY / TICK) + 2):
        assert screen is not None
        screen = screen.update(TICK)
    return screen


def test_result_after_delay_when_lives_run_out(ctx: Context) -> None:
    play = PlayScreen(ctx)
    play.session.game.score = 120
    play.session.game.game_over = True
    result = run_until_result(play)
    assert isinstance(result, ResultScreen)
    assert not result.won and not result.time_up
    assert result.score == 120


def test_result_when_time_runs_out(ctx: Context) -> None:
    play = PlayScreen(ctx)
    play.session.game.time_left = 0.0
    play.session.game.game_over = True
    result = run_until_result(play)
    assert isinstance(result, ResultScreen) and result.time_up


def test_victory_after_the_last_level(ctx: Context) -> None:
    play = PlayScreen(ctx)
    while not play.session.won:  # チートのレベルスキップと同じ進め方
        play.session.next_level()
    result = run_until_result(play)
    assert isinstance(result, ResultScreen) and result.won
    assert isinstance(press(result, ENTER), MainMenuScreen)


def test_result_waits_before_switching(ctx: Context) -> None:
    play = PlayScreen(ctx)
    play.session.game.game_over = True
    assert play.update(END_DELAY / 2) is play
    assert press(play, ESC) is play  # 終わった後は一時停止しない


# 1 つのレベルをクリアしても結果の画面には行かず、次のレベルの迷路を描く
def test_next_level_draws_the_new_maze(ctx: Context) -> None:
    play = PlayScreen(ctx)
    surface = pygame.Surface(WINDOW_SIZE)
    play.draw(surface)
    play.session.next_level()
    assert play.update(TICK) is play
    play.draw(surface)
    assert play.session.level == 2
    assert play.renderer.maze is play.session.game.maze


def test_every_screen_draws(ctx: Context) -> None:
    surface = pygame.Surface(WINDOW_SIZE)
    play = PlayScreen(ctx)
    screens: list[Screen] = [
        MainMenuScreen(ctx), play, PauseScreen(ctx, play),
        ResultScreen(ctx, won=True, time_up=False, score=10),
        ResultScreen(ctx, won=False, time_up=True, score=0),
        InstructionsScreen(ctx), HighscoresScreen(ctx)]
    for screen in screens:
        screen.draw(surface)


# 本物のメインループに、キー入力を送ってきれいに終わるかを確かめる
# メニュー → ゲーム → 一時停止 → メインメニュー → EXIT
def test_app_loop_runs_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(Config())
    keys = [ENTER, ESC, DOWN, ENTER, UP, ENTER]
    # 2 つ目以降のキーが同じ回に届いても、EXIT の後で止まること
    batches = [[k] for k in keys[:-2]] + [keys[-2:] + [ENTER, ESC]]
    seen: list[str] = []

    def fake_get() -> list[pygame.event.Event]:
        if app.screen is not None:
            seen.append(type(app.screen).__name__)
        if not batches:
            raise AssertionError("loop did not exit")
        return [pygame.event.Event(pygame.KEYDOWN, key=k)
                for k in batches.pop(0)]

    monkeypatch.setattr(pygame.event, "get", fake_get)
    app.run()
    assert app.screen is None
    assert seen == ["MainMenuScreen", "PlayScreen", "PauseScreen",
                    "PauseScreen", "MainMenuScreen"]


def test_closing_the_window_quits(monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(Config())
    monkeypatch.setattr(pygame.event, "get",
                        lambda: [pygame.event.Event(pygame.QUIT),
                                 pygame.event.Event(pygame.KEYDOWN,
                                                    key=ENTER)])
    app.run()
    assert app.screen is None
