PAC-MAN

START
    Open a terminal in this folder and run:  ./pac-man config.json
    macOS, first time only:  xattr -d com.apple.quarantine pac-man

CONTROLS
    Arrow keys / WASD           Move
    ESC / P                     Pause and resume
    UP / DOWN, ENTER / SPACE    Choose and select in menus
    ESC (main menu)             Quit

CHEAT MODE (press C during a game, then)
    1  Invincibility on/off     4  +1 life
    2  Ghost freeze on/off      5  Skip the level
    3  Fast player on/off

CONFIGURATION (edit config.json; lines starting with # are comments)
    lives                      Number of lives (1 to 9)
    seed                       Maze seed of level 1 (0 = random)
    points_per_pacgum          Points for a pacgum
    points_per_super_pacgum    Points for a super-pacgum
    points_per_ghost           Points for an eaten ghost
    highscore_filename         File where the 10 best scores are saved
    level_max_time             Time limit of a level, in seconds (10 to 999)
    levels                     Maze width (14 to 40) and height (10 to 25)
                               of each level, with an optional time limit
    An invalid value is replaced by a default and the game starts anyway.
