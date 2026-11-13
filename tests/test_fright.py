import random

from src.game import (FRIGHT_TIME, GHOST_RESPAWN_DELAY, LIVES,
                      POINTS_PER_GHOST, Game)
from src.ghost import FRIGHT_SPEED_RATE, Ghost
from src.mazegen import Direction, Maze
from tests.test_game import OPEN_CORRIDOR
from tests.test_collision import make_maze

TICK = 1 / 60


def make_game() -> Game:
    return Game(Maze(21, 21, seed=42), random.Random(0))


def eat_super_pacgum(game: Game) -> None:
    corner = next(iter(game.super_pacgums))
    game.player.place(corner)
    game._eat()


def test_super_pacgum_frightens_all_ghosts() -> None:
    game = make_game()
    eat_super_pacgum(game)
    assert len(game.ghosts) == 4
    for ghost in game.ghosts:
        assert ghost.frightened
        assert ghost.speed == ghost.normal_speed * FRIGHT_SPEED_RATE


def test_frighten_reverses_a_moving_ghost() -> None:
    ghost = Ghost(make_maze(OPEN_CORRIDOR), (2, 0), 5.0, random.Random(0))
    ghost.direction = Direction.RIGHT
    ghost.progress = 0.3
    ghost.frighten(FRIGHT_TIME)
    assert ghost.direction == Direction.LEFT
    assert ghost.position == (2.3, 0.0)  # 位置は変わらず向きだけ反転


def test_frightened_ghost_runs_away() -> None:
    maze = make_maze(OPEN_CORRIDOR)
    ghost = Ghost(maze, (2, 0), 5.0, random.Random(0))
    ghost.target = (0, 0)
    ghost.frighten(FRIGHT_TIME)
    for _ in range(60):  # 半分の速さなので 1 秒で 2.5 マス進む
        ghost.update(TICK)
    assert ghost.direction == Direction.RIGHT  # target (左端) から離れる向き
    assert ghost.position[0] > 4.0


def test_flee_increases_distance_in_real_maze() -> None:
    maze = Maze(21, 21, seed=42)
    target = maze.center_cell()
    ghost = Ghost(maze, (0, 0), 5.0, random.Random(0))
    ghost.target = target
    # まずプレイヤーの近くまで来させる
    for _ in range(60 * 60):
        ghost.update(TICK)
        if (ghost.x, ghost.y) == target:
            break
    near = maze.distances_from(target)[(ghost.x, ghost.y)]
    ghost.frighten(FRIGHT_TIME)
    for _ in range(int(FRIGHT_TIME / TICK) - 1):
        ghost.update(TICK)
    assert ghost.frightened
    assert maze.distances_from(target)[(ghost.x, ghost.y)] > near


# プレイヤーをゴーストの位置に置いて 1 tick 進める。
# ゴーストは隅（スーパーパックガムの上）にいるので、ガムの得点やいじけの
# かけ直しが混ざらないよう、そのマスのガムは先に取り除いておく
def touch(game: Game, ghost: Ghost) -> None:
    cell = (ghost.x, ghost.y)
    game.pacgums.discard(cell)
    game.super_pacgums.discard(cell)
    game.player.place(cell)
    game.update(TICK)


def test_eat_frightened_ghost() -> None:
    game = make_game()
    eat_super_pacgum(game)
    score = game.score
    ghost = game.ghosts[0]
    touch(game, ghost)
    assert ghost.eaten
    assert not ghost.frightened
    assert game.score == score + POINTS_PER_GHOST
    assert game.lives == LIVES
    assert game.freeze == 0.0


def test_eaten_ghost_is_eaten_only_once() -> None:
    game = make_game()
    eat_super_pacgum(game)
    ghost = game.ghosts[0]
    touch(game, ghost)
    score = game.score
    for _ in range(30):  # 消えた場所に居続けても、もう得点もミスもない
        game.update(TICK)
    assert ghost.eaten
    assert game.score == score
    assert game.lives == LIVES


def test_eaten_ghost_respawns_at_home_after_delay() -> None:
    maze = Maze(21, 21, seed=42)
    ghost = Ghost(maze, (0, 0), 5.0, random.Random(0))
    ghost.place(maze.center_cell())  # 隅から離れた場所で食べられる
    ghost.frighten(FRIGHT_TIME)
    ghost.get_eaten(GHOST_RESPAWN_DELAY)
    for _ in range(int(GHOST_RESPAWN_DELAY / TICK) - 1):
        ghost.update(TICK)
    assert ghost.eaten
    for _ in range(2):
        ghost.update(TICK)
    assert not ghost.eaten
    assert not ghost.frightened
    assert (ghost.x, ghost.y) == ghost.home
    assert ghost.speed == ghost.normal_speed


def test_eaten_ghost_does_not_get_frightened() -> None:
    ghost = Ghost(Maze(21, 21, seed=42), (0, 0), 5.0, random.Random(0))
    ghost.get_eaten(GHOST_RESPAWN_DELAY)
    ghost.frighten(FRIGHT_TIME)
    assert ghost.eaten
    assert not ghost.frightened


def test_normal_ghost_still_costs_a_life() -> None:
    game = make_game()
    eat_super_pacgum(game)
    frightened, normal = game.ghosts[0], game.ghosts[1]
    normal.place(normal.home)  # place でいじけが解除される
    # いじけ中と通常のゴーストに同じ tick で触れる: 食べた上でミス
    frightened.place((normal.x, normal.y))
    frightened.frighten(FRIGHT_TIME)
    score = game.score
    touch(game, normal)
    assert frightened.eaten
    assert game.score == score + POINTS_PER_GHOST
    assert game.lives == LIVES - 1


def test_lost_life_brings_eaten_ghost_back() -> None:
    game = make_game()
    ghost = game.ghosts[0]
    ghost.get_eaten(GHOST_RESPAWN_DELAY)
    game._lose_life()
    for _ in range(int(game.freeze / TICK) + 2):
        game.update(TICK)
    assert not ghost.eaten
    assert (ghost.x, ghost.y) == ghost.home


def test_fright_wears_off() -> None:
    ghost = Ghost(Maze(21, 21, seed=42), (0, 0), 5.0, random.Random(0))
    ghost.frighten(FRIGHT_TIME)
    for _ in range(int(FRIGHT_TIME / TICK) + 2):
        ghost.update(TICK)
    assert not ghost.frightened
    assert ghost.speed == ghost.normal_speed


def test_place_clears_fright() -> None:
    ghost = Ghost(Maze(21, 21, seed=42), (0, 0), 5.0, random.Random(0))
    ghost.frighten(FRIGHT_TIME)
    ghost.place((0, 0))
    assert not ghost.frightened
    assert ghost.speed == ghost.normal_speed


def test_eating_again_restarts_the_timer() -> None:
    ghost = Ghost(Maze(21, 21, seed=42), (0, 0), 5.0, random.Random(0))
    ghost.frighten(FRIGHT_TIME)
    for _ in range(120):
        ghost.update(TICK)
    ghost.frighten(FRIGHT_TIME)
    assert ghost.fright == FRIGHT_TIME
