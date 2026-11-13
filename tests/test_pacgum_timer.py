import random

from src.game import (LEVEL_TIME, POINTS_PER_PACGUM, POINTS_PER_SUPER_PACGUM,
                      Game)
from src.mazegen import Maze

TICK = 1 / 60


def make_game() -> Game:
    game = Game(Maze(21, 21, seed=42), random.Random(0))
    game.ghosts = []  # ゴーストに当たらないようにする
    return game


def test_pacgum_placement() -> None:
    game = make_game()
    maze = game.maze
    start = maze.center_cell()
    assert game.super_pacgums == set(maze.corner_cells())
    assert start not in game.pacgums
    assert not game.pacgums & game.super_pacgums
    assert all(not maze.is_blocked(x, y) for x, y in game.pacgums)
    # 中央から行けるマスには全部どちらかのガムがある
    reachable = set(maze.distances_from(start)) - {start}
    assert game.pacgums | game.super_pacgums == reachable


def test_eat_pacgum_and_super_pacgum() -> None:
    game = make_game()
    cell = next(iter(game.pacgums))
    game.player.place(cell)
    game.update(TICK)
    assert cell not in game.pacgums
    assert game.score == POINTS_PER_PACGUM

    corner = next(iter(game.super_pacgums))
    game.player.place(corner)
    game.update(TICK)
    assert corner not in game.super_pacgums
    assert game.score == POINTS_PER_PACGUM + POINTS_PER_SUPER_PACGUM


def test_eating_everything_clears_the_level() -> None:
    game = make_game()
    cell = next(iter(game.pacgums))
    game.pacgums = {cell}
    game.super_pacgums = set()
    game.player.place(cell)
    game.update(TICK)
    assert game.cleared and not game.game_over
    time_left = game.time_left
    game.update(TICK)
    assert game.time_left == time_left  # クリア後は時間が止まる


def test_timer_counts_down() -> None:
    game = make_game()
    for _ in range(60):
        game.update(TICK)
    assert abs(game.time_left - (LEVEL_TIME - 1.0)) < 1e-6


def test_time_up_is_game_over() -> None:
    game = make_game()
    game.time_left = TICK / 2
    game.update(TICK)
    assert game.time_left == 0.0
    assert game.game_over
    assert game.lives > 0  # 残機が残っていてもゲームオーバー


def test_timer_stops_while_frozen_after_a_hit() -> None:
    game = Game(Maze(21, 21, seed=42), random.Random(0))
    ghost = game.ghosts[0]
    ghost.place((game.player.x, game.player.y))
    game.update(TICK)
    time_left = game.time_left
    game.update(TICK)
    assert game.freeze > 0.0
    assert game.time_left == time_left
