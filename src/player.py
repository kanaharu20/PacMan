from src.mazegen import Direction, Maze
from src.mover import Mover


class Player(Mover):
    def __init__(self, maze: Maze, cell: tuple[int, int],
                 speed: float = 6.0) -> None:
        super().__init__(maze, cell, speed)
        self.wanted: Direction | None = None  # buffered key input

    def steer(self, direction: Direction) -> None:
        self.wanted = direction
        if (self.direction is not None
                and direction == self.direction.opposite):
            self.reverse()

    def _choose_direction(self) -> bool:
        if (self.wanted is not None
                and self.maze.can_move(self.x, self.y, self.wanted)):
            self.direction = self.wanted
            return True
        if (self.direction is not None
                and self.maze.can_move(self.x, self.y, self.direction)):
            return True
        self.direction = None  # wall ahead: stop
        return False
