import pygame

from src.mazegen import Direction, Maze
from src.player import Player
from src.render import draw, window_size

MAZE_SIZE = (21, 21)
SEED = 42
TICK = 1 / 60  # fixed logic step (seconds)

KEYS = {
    pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
}


def main() -> None:
    maze = Maze(*MAZE_SIZE, seed=SEED)
    player = Player(maze, maze.center_cell())

    pygame.init()
    screen = pygame.display.set_mode(window_size(maze))
    pygame.display.set_caption("Pac-Man (prototype)")
    clock = pygame.time.Clock()
    lag = 0.0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in KEYS:
                    player.steer(KEYS[event.key])
        lag += clock.tick(60) / 1000
        while lag >= TICK:
            player.update(TICK)
            lag -= TICK
        draw(screen, maze, player)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
