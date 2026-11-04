import random

from src.mazegen import Direction, Maze
from src.player import Player


def make_maze(grid: list[list[int]]) -> Maze:
    maze = Maze(3, 3, seed=1)
    maze.grid = grid
    maze.height, maze.width = len(grid), len(grid[0])
    return maze


# A 3x1 corridor:  [ 0 | 1   2 ]   wall between cell 0 and cell 1.
CORRIDOR = [[1 | 4 | 8 | 2, 1 | 4 | 8, 1 | 4 | 2]]


def test_stops_at_wall() -> None:
    player = Player(make_maze(CORRIDOR), (1, 0), speed=1.0)
    player.steer(Direction.RIGHT)
    player.update(10.0)
    assert player.position == (2.0, 0.0)
    assert player.direction is None


def test_cannot_go_through_wall() -> None:
    player = Player(make_maze(CORRIDOR), (1, 0), speed=1.0)
    player.steer(Direction.LEFT)
    player.update(10.0)
    assert player.position == (1.0, 0.0)


def test_reverse_mid_cell() -> None:
    player = Player(make_maze(CORRIDOR), (1, 0), speed=1.0)
    player.steer(Direction.RIGHT)
    player.update(0.5)
    assert player.position == (1.5, 0.0)
    player.steer(Direction.LEFT)
    player.update(10.0)
    assert player.position == (1.0, 0.0)


def test_never_crosses_a_wall_in_random_play() -> None:
    maze = Maze(21, 21, seed=42)
    player = Player(maze, maze.center_cell(), speed=6.0)
    rng = random.Random(0)
    for _ in range(20000):
        if rng.random() < 0.05:
            player.steer(rng.choice(list(Direction)))
        before = (player.x, player.y)
        player.update(1 / 60)
        after = (player.x, player.y)
        if before != after:
            dx, dy = after[0] - before[0], after[1] - before[1]
            assert abs(dx) + abs(dy) == 1
            moved = next(d for d in Direction if (d.dx, d.dy) == (dx, dy))
            assert maze.can_move(*before, moved)
        assert not maze.is_blocked(player.x, player.y)
