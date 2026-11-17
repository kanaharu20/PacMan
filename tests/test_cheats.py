import os
from collections.abc import Iterator
from pathlib import Path

import pygame
import pytest

from src.app import TICK
from src.cheats import FAST_SPEED_RATE
from src.config import (LIVES_MAX, MAZE_HEIGHT_MIN, MAZE_WIDTH_MIN, Config,
                        LevelConfig)
from src.game import FRIGHT_TIME, GHOST_RESPAWN_DELAY, Game
from src.ghost import Ghost
from src.highscore import HighscoreTable
from src.player import PLAYER_SPEED
from src.render import (CHEAT_HUD_X, CHEAT_ITEMS_X, CHEAT_LABELS, FONT_SIZE,
                        HUD_ITEMS_X, WINDOW_SIZE, TextWriter, play_area_size)
from src.screens import END_DELAY, Context, PlayScreen, ResultScreen, Screen
from src.session import Session


@pytest.fixture(autouse=True)
def headless() -> Iterator[None]:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    yield
    pygame.quit()


def cheating_session() -> Session:
    session = Session(Config())
    session.toggle_cheat_mode()
    return session


# プレイヤーをゴーストの位置に置いて 1 tick 進める（そのマスのガムは先に消す）
def touch(game: Game, ghost: Ghost) -> None:
    cell = (ghost.x, ghost.y)
    game.pacgums.discard(cell)
    game.super_pacgums.discard(cell)
    game.player.place(cell)
    game.update(TICK)


# ---- Session（ゲームの中身）----

def test_cheats_do_nothing_until_cheat_mode_is_on() -> None:
    session = Session(Config())
    session.toggle_invincible()
    session.toggle_ghost_freeze()
    session.toggle_fast()
    session.add_life()
    session.skip_level()
    cheats = session.cheats
    assert not (cheats.invincible or cheats.ghosts_frozen or cheats.fast)
    assert session.game.lives == Config().lives
    assert session.level == 1


def test_turning_cheat_mode_off_turns_everything_off() -> None:
    session = cheating_session()
    session.toggle_invincible()
    session.toggle_ghost_freeze()
    session.toggle_fast()
    session.toggle_cheat_mode()
    cheats = session.cheats
    assert not cheats.enabled
    assert not (cheats.invincible or cheats.ghosts_frozen or cheats.fast)


def test_toggles_turn_off_when_pressed_again() -> None:
    session = cheating_session()
    session.toggle_invincible()
    assert session.cheats.invincible
    session.toggle_invincible()
    assert not session.cheats.invincible


def test_invincible_player_loses_no_life() -> None:
    session = cheating_session()
    session.toggle_invincible()
    game = session.game
    touch(game, game.ghosts[0])
    assert game.lives == Config().lives
    assert game.freeze == 0.0


def test_invincible_player_can_still_eat_ghosts() -> None:
    session = cheating_session()
    session.toggle_invincible()
    game = session.game
    ghost = game.ghosts[0]
    ghost.frighten(FRIGHT_TIME)
    score = game.score
    touch(game, ghost)
    assert ghost.eaten
    assert game.score == score + Config().points_per_ghost


def test_frozen_ghosts_do_not_move() -> None:
    session = cheating_session()
    session.toggle_ghost_freeze()
    game = session.game
    before = [ghost.position for ghost in game.ghosts]
    for _ in range(120):
        game.update(TICK)
    assert [ghost.position for ghost in game.ghosts] == before


# 止まっている間も、食べられたゴーストは復活し、逃げる状態は終わる
def test_frozen_ghost_timers_keep_running() -> None:
    session = cheating_session()
    session.toggle_ghost_freeze()
    game = session.game
    eaten, scared = game.ghosts[0], game.ghosts[1]
    eaten.get_eaten(GHOST_RESPAWN_DELAY)
    scared.frighten(FRIGHT_TIME)
    for _ in range(int(FRIGHT_TIME / TICK) + 2):
        game.update(TICK)
    assert not eaten.eaten
    assert (eaten.x, eaten.y) == eaten.home
    assert not scared.frightened


def test_fast_player_and_back_to_normal() -> None:
    session = cheating_session()
    game = session.game
    session.toggle_fast()
    game.update(TICK)
    assert game.player.speed == PLAYER_SPEED * FAST_SPEED_RATE
    session.toggle_fast()
    game.update(TICK)
    assert game.player.speed == PLAYER_SPEED


# 速くしても 1 tick に進むのは半マス未満（ガムや当たり判定を飛ばさない）
def test_fast_player_moves_less_than_half_a_cell_per_tick() -> None:
    assert PLAYER_SPEED * FAST_SPEED_RATE * TICK < 0.5


def test_extra_lives_stop_at_the_limit() -> None:
    session = cheating_session()
    for _ in range(20):
        session.add_life()
    assert session.game.lives == LIVES_MAX


def test_skip_level_keeps_score_and_lives() -> None:
    session = cheating_session()
    session.game.score = 500
    session.game.lives = 2
    session.skip_level()
    assert session.level == 2
    assert session.game.score == 500
    assert session.game.lives == 2


def test_skip_on_the_last_level_wins() -> None:
    session = cheating_session()
    for _ in range(session.level_count):
        session.skip_level()
    assert session.won
    assert session.level == session.level_count


def test_cheats_carry_over_to_the_next_level() -> None:
    session = cheating_session()
    session.toggle_invincible()
    session.skip_level()
    assert session.game.cheats is session.cheats
    assert session.game.cheats.invincible


def test_no_cheats_after_game_over() -> None:
    session = cheating_session()
    session.game.lives = 0
    session.game.game_over = True
    session.add_life()
    assert session.game.lives == 0


def test_new_game_starts_without_cheats() -> None:
    cheating_session()
    assert not Session(Config()).cheats.enabled


# ---- ゲーム画面のキー ----

@pytest.fixture
def play(tmp_path: Path) -> PlayScreen:
    table = HighscoreTable(str(tmp_path / "highscores.json"))
    return PlayScreen(Context(Config(), TextWriter(), table))


def press(screen: PlayScreen, *keys: int) -> None:
    for key in keys:
        assert screen.handle_key(key) is screen


def test_c_key_turns_cheat_mode_on_and_off(play: PlayScreen) -> None:
    press(play, pygame.K_c)
    assert play.session.cheats.enabled
    press(play, pygame.K_c)
    assert not play.session.cheats.enabled


def test_number_keys_do_nothing_without_cheat_mode(play: PlayScreen) -> None:
    press(play, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)
    cheats = play.session.cheats
    assert not (cheats.invincible or cheats.ghosts_frozen or cheats.fast)
    assert play.session.level == 1


def test_number_keys_use_cheats(play: PlayScreen) -> None:
    press(play, pygame.K_c, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_5)
    cheats = play.session.cheats
    assert cheats.invincible and cheats.ghosts_frozen and cheats.fast
    assert play.session.level == 2


# 残機追加を連打しても上限で止まり、HUD も描ける（review_lessons のストレステスト）
def test_pressing_extra_life_many_times(play: PlayScreen) -> None:
    press(play, pygame.K_c, *[pygame.K_4] * 20)
    assert play.session.game.lives == LIVES_MAX
    play.draw(pygame.Surface(WINDOW_SIZE))


def test_skipping_every_level_shows_the_victory_screen(
        play: PlayScreen) -> None:
    press(play, pygame.K_c, *[pygame.K_5] * play.session.level_count)
    screen: Screen | None = play
    for _ in range(int(END_DELAY / TICK) + 2):
        assert screen is not None
        screen = screen.update(TICK)
    assert isinstance(screen, ResultScreen)
    assert screen.won


# ---- HUD の表示位置（ゲームのコードでは文字の幅を測らないので、ここで確かめる）----

def test_cheat_hud_fits_and_does_not_overlap() -> None:
    font = pygame.font.Font(None, FONT_SIZE)
    widths = [font.size(label)[0] for label in CHEAT_LABELS]
    # 項目どうしが重ならない
    for i in range(len(CHEAT_LABELS) - 1):
        assert CHEAT_ITEMS_X[i] + widths[i] < CHEAT_ITEMS_X[i + 1]
    # 左の HUD の一番長い状態表示とも重ならない
    longest_status = max(font.size(text)[0] for text in
                         ("YOU WIN!", "CLEAR!", "TIME UP", "GAME OVER"))
    assert HUD_ITEMS_X[-1] + longest_status < CHEAT_HUD_X
    # 一番狭い迷路（プレイ領域が一番右に寄る）でもウィンドウに収まる
    area_width = play_area_size(MAZE_WIDTH_MIN, MAZE_HEIGHT_MIN)[0]
    origin_x = (WINDOW_SIZE[0] - area_width) // 2
    right = origin_x + CHEAT_HUD_X + CHEAT_ITEMS_X[-1] + widths[-1]
    assert right <= WINDOW_SIZE[0]


def test_hud_draws_with_cheats_on_smallest_maze(tmp_path: Path) -> None:
    config = Config(levels=[LevelConfig(MAZE_WIDTH_MIN, MAZE_HEIGHT_MIN)])
    table = HighscoreTable(str(tmp_path / "highscores.json"))
    play = PlayScreen(Context(config, TextWriter(), table))
    press(play, pygame.K_c, pygame.K_1)
    play.draw(pygame.Surface(WINDOW_SIZE))
