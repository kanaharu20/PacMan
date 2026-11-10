import pygame

from src.ghost import Ghost
from src.mazegen import Direction, Maze
from src.mover import Mover
from src.player import Player

# MLX には線や四角を描く関数がないので pygame.draw は使わない。
# 単色の画像（Surface）を最初に作っておき、毎フレームそれを貼る（blit）だけにする。
# 対応表: project_management/mlx_pygame_mapping.ja.md

CELL = 32
WALL = 2  # 壁の太さ
MARGIN = 4  # 外周の壁が画面端で切れないように
WALL_COLOR = (40, 80, 255)
BLOCKED_COLOR = (20, 30, 90)
PLAYER_COLOR = (255, 220, 0)
GHOST_COLORS = ((230, 60, 60), (60, 200, 90), (170, 90, 255),
                (240, 240, 240))
# 大きさはロジック側 (Mover.size) が決める。当たり判定と見た目を一致させるため
SPRITE_SIZE = round(Mover.size * CELL)


def solid_image(width: int, height: int,
                color: tuple[int, int, int]) -> pygame.Surface:
    # mlx_new_image + mlx_get_data_addr で全ピクセルに色を書くのと同じ
    image = pygame.Surface((width, height))
    image.fill(color)
    return image


def window_size(maze: Maze) -> tuple[int, int]:
    return (maze.width * CELL + 2 * MARGIN,
            maze.height * CELL + 2 * MARGIN)


class Renderer:
    def __init__(self, maze: Maze) -> None:
        self.maze = maze
        self.h_wall = solid_image(CELL + WALL, WALL, WALL_COLOR)
        self.v_wall = solid_image(WALL, CELL + WALL, WALL_COLOR)
        self.blocked = solid_image(CELL, CELL, BLOCKED_COLOR)
        self.player = solid_image(SPRITE_SIZE, SPRITE_SIZE, PLAYER_COLOR)
        self.ghosts = [solid_image(SPRITE_SIZE, SPRITE_SIZE, color)
                       for color in GHOST_COLORS]

    def draw(self, screen: pygame.Surface, player: Player,
             ghosts: list[Ghost]) -> None:
        screen.fill((0, 0, 0))  # mlx_clear_window
        self._draw_maze(screen)
        for i, ghost in enumerate(ghosts):
            image = self.ghosts[i % len(self.ghosts)]
            self._draw_mover(screen, image, ghost)
        self._draw_mover(screen, self.player, player)

    def _draw_maze(self, screen: pygame.Surface) -> None:
        half = WALL // 2
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                left, top = MARGIN + x * CELL, MARGIN + y * CELL
                if self.maze.is_blocked(x, y):
                    screen.blit(self.blocked, (left, top))
                walls = {
                    Direction.UP: (self.h_wall, left - half, top - half),
                    Direction.DOWN: (self.h_wall, left - half,
                                     top + CELL - half),
                    Direction.LEFT: (self.v_wall, left - half, top - half),
                    Direction.RIGHT: (self.v_wall, left + CELL - half,
                                      top - half),
                }
                for direction, (image, wx, wy) in walls.items():
                    if self.maze.has_wall(x, y, direction):
                        screen.blit(image, (wx, wy))

    def _draw_mover(self, screen: pygame.Surface, image: pygame.Surface,
                    mover: Mover) -> None:
        px, py = mover.position
        cx = MARGIN + (px + 0.5) * CELL
        cy = MARGIN + (py + 0.5) * CELL
        screen.blit(image, (round(cx - SPRITE_SIZE / 2),
                            round(cy - SPRITE_SIZE / 2)))
