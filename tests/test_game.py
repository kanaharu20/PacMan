import random

from src.game import LIVES, RESPAWN_DELAY, Game
from src.ghost import Ghost
from src.mazegen import Direction, Maze
from src.player import Player
from tests.test_collision import CORRIDOR, make_maze

TICK = 1 / 60

# A 6x1 corridor without inner walls.
OPEN_CORRIDOR = [[1 | 4 | 8] + [1 | 4] * 4 + [1 | 4 | 2]]


def test_touches_only_when_sprites_meet() -> None:
    maze = make_maze(OPEN_CORRIDOR)
    a = Player(maze, (0, 0))
    b = Player(maze, (1, 0))
    b.direction = Direction.LEFT  # b is at x = 1 - progress
    b.progress = 1 - Player.size + 0.01
    assert a.touches(b)
    b.progress = 1 - Player.size - 0.01
    assert not a.touches(b)


def test_no_touch_through_a_wall() -> None:
    maze = make_maze(CORRIDOR)
    assert not Player(maze, (0, 0)).touches(Player(maze, (1, 0)))


def test_head_on_crossing_is_never_missed() -> None:
    maze = make_maze(OPEN_CORRIDOR)
    player = Player(maze, (1, 0))
    ghost = Ghost(maze, (4, 0), 5.4, random.Random(0))
    ghost.target = (0, 0)
    player.steer(Direction.RIGHT)
    for _ in range(60):
        player.update(TICK)
        ghost.update(TICK)
        if player.touches(ghost):
            return
    raise AssertionError("player and ghost passed through each other")


def hit(game: Game) -> None:
    ghost = game.ghosts[0]
    ghost.place((game.player.x, game.player.y))
    game.update(TICK)


def test_hit_freezes_then_resets_positions() -> None:
    maze = Maze(21, 21, seed=42)
    game = Game(maze, random.Random(0))
    hit(game)
    assert game.lives == LIVES - 1
    assert game.freeze == RESPAWN_DELAY
    frozen = [g.position for g in game.ghosts]
    for _ in range(int(RESPAWN_DELAY / TICK) - 1):
        game.update(TICK)
    assert [g.position for g in game.ghosts] == frozen
    for _ in range(5):
        game.update(TICK)
    assert game.freeze == 0.0
    assert (game.player.x, game.player.y) == maze.center_cell()
    corners = maze.corner_cells()
    assert [(g.x, g.y) for g in game.ghosts] == corners


def test_last_life_is_game_over() -> None:
    game = Game(Maze(21, 21, seed=42), random.Random(0))
    game.lives = 1
    hit(game)
    assert game.lives == 0
    assert game.game_over
    before = game.player.position
    game.steer(Direction.LEFT)
    for _ in range(60):
        game.update(TICK)
    assert game.player.position == before
