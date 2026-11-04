import pygame

from src.mazegen import Direction, Maze
from src.player import Player

CELL = 32
MARGIN = 4  # 外周の壁線が画面端で切れないように
WALL_COLOR = (40, 80, 255)
BLOCKED_COLOR = (20, 30, 90)
PLAYER_COLOR = (255, 220, 0)
BACKGROUND = (0, 0, 0)


def draw_maze(screen: pygame.Surface, maze: Maze) -> None:
    for y in range(maze.height):
        for x in range(maze.width):
            left, top = MARGIN + x * CELL, MARGIN + y * CELL
            right, bottom = left + CELL, top + CELL
            if maze.is_blocked(x, y):
                pygame.draw.rect(screen, BLOCKED_COLOR,
                                 (left, top, CELL, CELL))
            sides = {
                Direction.UP: ((left, top), (right, top)),
                Direction.RIGHT: ((right, top), (right, bottom)),
                Direction.DOWN: ((left, bottom), (right, bottom)),
                Direction.LEFT: ((left, top), (left, bottom)),
            }
            for direction, (start, end) in sides.items():
                if maze.has_wall(x, y, direction):
                    pygame.draw.line(screen, WALL_COLOR, start, end, 2)


def draw_player(screen: pygame.Surface, player: Player) -> None:
    px, py = player.position
    size = CELL * 0.6
    cx = MARGIN + (px + 0.5) * CELL
    cy = MARGIN + (py + 0.5) * CELL
    pygame.draw.rect(screen, PLAYER_COLOR,
                     (cx - size / 2, cy - size / 2, size, size))


def window_size(maze: Maze) -> tuple[int, int]:
    return (maze.width * CELL + 2 * MARGIN,
            maze.height * CELL + 2 * MARGIN)


def draw(screen: pygame.Surface, maze: Maze, player: Player) -> None:
    screen.fill(BACKGROUND)
    draw_maze(screen, maze)
    draw_player(screen, player)
