import json
from pathlib import Path
from typing import Any

import pytest

from src.config import (LEVELS_MAX, LEVELS_MIN, Config, LevelConfig,
                        load_config, parse_config)
from src.mazegen import Maze, MazeError
from src.session import LEVEL_CLEAR_DELAY, Session

TICK = 1 / 60


# ---- 設定ファイル: levels とそのほかのキー ----

def test_levels_are_read_in_order(caplog: pytest.LogCaptureFixture) -> None:
    levels = [{"width": 15 + i, "height": 11, "level_max_time": 60 + i}
              for i in range(LEVELS_MIN)]
    config = parse_config({"levels": levels})
    assert config.levels == [LevelConfig(15 + i, 11, 60 + i)
                             for i in range(LEVELS_MIN)]
    assert "levels" not in caplog.text
    # levels があるときは、一番外の width / height がなくても警告しない
    assert "'width' is missing" not in caplog.text


def test_missing_level_keys_use_top_level_values() -> None:
    config = parse_config({"width": 17, "height": 13, "level_max_time": 70,
                           "levels": [{}, {"width": 25}] + [{}] * 8})
    assert config.levels[0] == LevelConfig(17, 13, 70)
    assert config.levels[1] == LevelConfig(25, 13, 70)


def test_missing_levels_means_ten_default_levels(
        caplog: pytest.LogCaptureFixture) -> None:
    config = parse_config({"width": 15, "height": 11})
    assert config.levels == [LevelConfig(15, 11, 90)] * LEVELS_MIN
    assert "'levels' is missing" in caplog.text


def test_too_few_levels_are_filled_up_to_ten(
        caplog: pytest.LogCaptureFixture) -> None:
    config = parse_config({"levels": [{"width": 30, "height": 20}]})
    assert len(config.levels) == LEVELS_MIN
    assert config.levels[0] == LevelConfig(30, 20, 90)
    assert config.levels[1:] == [LevelConfig()] * (LEVELS_MIN - 1)
    assert "at least 10 are needed" in caplog.text


def test_too_many_levels_are_cut(caplog: pytest.LogCaptureFixture) -> None:
    config = parse_config({"levels": [{}] * (LEVELS_MAX + 5)})
    assert len(config.levels) == LEVELS_MAX
    assert "only the first 50 are used" in caplog.text


@pytest.mark.parametrize("value", ["[]", "{}", '"abc"', "3", "null"])
def test_broken_levels_use_defaults(tmp_path: Path, value: str,
                                    caplog: pytest.LogCaptureFixture) -> None:
    path = tmp_path / "config.json"
    path.write_text(f'{{"levels": {value}}}', encoding="utf-8")
    config = load_config(str(path))
    assert config.levels == [LevelConfig()] * LEVELS_MIN
    assert "levels" in caplog.text


def test_broken_level_entries_are_fixed(
        caplog: pytest.LogCaptureFixture) -> None:
    levels: list[Any] = [5, {"width": "big", "height": 1000, "hight": 3}]
    config = parse_config({"levels": levels + [{}] * 8})
    assert config.levels[0] == LevelConfig()
    assert config.levels[1] == LevelConfig(21, 25, 90)
    assert "'levels[0]' must be an object" in caplog.text
    assert "'levels[1].width' must be an integer" in caplog.text
    assert "'levels[1].height' = 1000 is out of range" in caplog.text
    assert "unknown key 'levels[1].hight'" in caplog.text


@pytest.mark.parametrize("key, value, expected", [
    ("lives", 0, 1), ("lives", 100, 9), ("lives", "3", 3),
    ("seed", -1, 0), ("seed", 1.5, 42),
    ("level_max_time", 1, 10), ("level_max_time", 5000, 999),
    ("points_per_pacgum", -10, 0), ("points_per_ghost", True, 200),
])
def test_other_values_are_fixed(key: str, value: Any, expected: int,
                                caplog: pytest.LogCaptureFixture) -> None:
    config = parse_config({key: value})
    assert getattr(config, key) == expected
    assert f"'{key}'" in caplog.text


def test_config_without_levels_has_ten_levels() -> None:
    assert Config(width=15, height=11).levels == [LevelConfig(15, 11)] * 10


# ---- Session: レベルの進行 ----

def small_config(**kwargs: Any) -> Config:
    levels = [LevelConfig(15, 11, 90)] * LEVELS_MIN
    return Config(levels=levels, **kwargs)


def clear_level(session: Session) -> None:
    game = session.game
    game.pacgums = set()
    game.super_pacgums = {next(iter(game.super_pacgums))}
    game.ghosts = []
    game.player.place(next(iter(game.super_pacgums)))
    session.update(TICK)
    assert game.cleared
    for _ in range(int(LEVEL_CLEAR_DELAY / TICK) + 2):
        session.update(TICK)


def test_level_one_uses_the_seed_and_later_levels_are_random() -> None:
    first = Session(small_config()).game.maze.grid
    assert Session(small_config()).game.maze.grid == first
    assert first == Maze(15, 11, seed=42).grid
    session = Session(small_config())
    clear_level(session)
    assert session.level == 2
    second = session.game.maze.grid
    other = Session(small_config())
    clear_level(other)
    assert other.game.maze.grid != second  # 2 からは毎回ちがう迷路


def test_score_and_lives_carry_over() -> None:
    session = Session(small_config(lives=5, points_per_super_pacgum=77))
    session.game.lives = 4
    clear_level(session)
    assert session.level == 2
    assert session.game.score == 77
    assert session.game.lives == 4


def test_next_level_waits_after_a_clear() -> None:
    session = Session(small_config())
    game = session.game
    game.pacgums, game.super_pacgums = set(), set()
    game.ghosts = []
    session.update(TICK)
    assert game.cleared and session.level == 1
    for _ in range(int(LEVEL_CLEAR_DELAY / TICK) - 5):
        session.update(TICK)
    assert session.level == 1  # まだ「CLEAR!」を見せている
    for _ in range(10):
        session.update(TICK)
    assert session.level == 2


def test_each_level_uses_its_size_and_time() -> None:
    levels = [LevelConfig(15 + 2 * i, 11, 30 + i) for i in range(LEVELS_MIN)]
    session = Session(Config(levels=levels))
    for i in range(LEVELS_MIN):
        assert session.level == i + 1
        assert session.game.maze.width == 15 + 2 * i
        assert session.game.time_left == 30 + i
        session.next_level()


def test_clearing_the_last_level_wins() -> None:
    session = Session(small_config())
    for _ in range(LEVELS_MIN - 1):
        session.next_level()
    assert session.level == LEVELS_MIN and not session.won
    clear_level(session)
    assert session.won and session.finished
    assert session.level == LEVELS_MIN


def test_game_over_ends_the_session() -> None:
    session = Session(small_config())
    session.game.time_left = TICK / 2
    session.update(TICK)
    assert session.finished and not session.won
    level = session.level
    session.next_level()  # 終わった後はレベルスキップも効かない
    assert session.level == level


def test_points_from_config_are_used() -> None:
    session = Session(small_config(points_per_pacgum=3))
    game = session.game
    game.ghosts = []
    game.player.place(next(iter(game.pacgums)))
    session.update(TICK)
    assert game.score == 3


# ---- 迷路生成の失敗 ----

def test_maze_generator_errors_become_maze_error() -> None:
    with pytest.raises(MazeError, match="maze generator failed"):
        Maze(0, 0)


def test_shipped_config_is_valid_json_without_comments() -> None:
    lines = Path("config.json").read_text(encoding="utf-8").splitlines()
    data = json.loads("\n".join(line for line in lines
                                if not line.lstrip().startswith("#")))
    assert len(data["levels"]) == LEVELS_MIN
