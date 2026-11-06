import random

from src.ghost import Ghost
from src.mazegen import Direction, Maze
from tests.test_collision import CORRIDOR, make_maze


def test_distances_follow_corridors() -> None:
    maze = make_maze(CORRIDOR)
    assert maze.distances_from((2, 0)) == {(2, 0): 0, (1, 0): 1}


def test_corner_cells_are_open() -> None:
    maze = Maze(21, 21, seed=42)
    corners = maze.corner_cells()
    assert corners == [(0, 0), (20, 0), (0, 20), (20, 20)]
    assert not any(maze.is_blocked(*cell) for cell in corners)


def test_reaches_a_still_target() -> None:
    maze = Maze(21, 21, seed=42)
    target = maze.center_cell()
    ghost = Ghost(maze, (0, 0), 5.0, random.Random(0))
    ghost.target = target
    for _ in range(60 * 60):
        ghost.update(1 / 60)
        if (ghost.x, ghost.y) == target:
            return
    raise AssertionError("ghost never reached the target")


def test_unreachable_target_does_not_crash() -> None:
    maze = Maze(21, 21, seed=42)
    ghost = Ghost(maze, (0, 0), 5.0, random.Random(0))
    ghost.target = (-5, -5)
    for _ in range(600):
        ghost.update(1 / 60)
    assert not maze.is_blocked(ghost.x, ghost.y)


def test_never_reverses_or_crosses_a_wall_in_random_play() -> None:
    maze = Maze(21, 21, seed=42)
    rng = random.Random(0)
    ghost = Ghost(maze, (0, 0), 5.4, rng)
    for _ in range(20000):
        if rng.random() < 0.01:
            ghost.target = (rng.randrange(21), rng.randrange(21))
        before = (ghost.x, ghost.y)
        prev = ghost.direction
        ghost.update(1 / 60)
        after = (ghost.x, ghost.y)
        if before != after:
            dx, dy = after[0] - before[0], after[1] - before[1]
            assert abs(dx) + abs(dy) == 1
            moved = next(d for d in Direction if (d.dx, d.dy) == (dx, dy))
            assert maze.can_move(*before, moved)
        if prev is not None and ghost.direction == prev.opposite:
            others = [d for d in Direction
                      if maze.can_move(ghost.x, ghost.y, d)
                      and d != prev.opposite]
            assert not others, "reversed although another way was open"
        assert not maze.is_blocked(ghost.x, ghost.y)
