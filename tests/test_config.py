from pathlib import Path

import pytest

from src.config import (MAZE_HEIGHT_MAX, MAZE_HEIGHT_MIN, MAZE_WIDTH_MAX,
                        MAZE_WIDTH_MIN, Config, ConfigError, load_config)
from src.mazegen import Maze
from src.render import window_size


def write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "config.json"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_reads_width_and_height(tmp_path: Path) -> None:
    path = write(tmp_path, '{"width": 15, "height": 11}')
    assert load_config(path) == Config(width=15, height=11)


def test_hash_lines_are_comments(tmp_path: Path) -> None:
    path = write(tmp_path, """# top comment
{
    # the maze
    "width": 15,
  # indented comment
    "height": 11
}
""")
    assert load_config(path) == Config(width=15, height=11)


def test_project_config_file_loads() -> None:
    assert load_config("config.json") == Config()


def test_missing_keys_use_defaults(tmp_path: Path,
                                   caplog: pytest.LogCaptureFixture) -> None:
    assert load_config(write(tmp_path, "{}")) == Config()
    assert "'width' is missing" in caplog.text
    assert "'height' is missing" in caplog.text


@pytest.mark.parametrize("value", ['"21"', "21.5", "true", "null", "[21]"])
def test_wrong_type_uses_default(tmp_path: Path, value: str,
                                 caplog: pytest.LogCaptureFixture) -> None:
    path = write(tmp_path, f'{{"width": {value}, "height": 11}}')
    assert load_config(path) == Config(width=Config().width, height=11)
    assert "'width' must be an integer" in caplog.text


@pytest.mark.parametrize("width, height, expected", [
    (-3, 1000, Config(width=MAZE_WIDTH_MIN, height=MAZE_HEIGHT_MAX)),
    (1000, 0, Config(width=MAZE_WIDTH_MAX, height=MAZE_HEIGHT_MIN)),
    (MAZE_WIDTH_MIN - 1, MAZE_HEIGHT_MAX + 1,
     Config(width=MAZE_WIDTH_MIN, height=MAZE_HEIGHT_MAX)),
])
def test_out_of_range_is_clamped(tmp_path: Path, width: int, height: int,
                                 expected: Config,
                                 caplog: pytest.LogCaptureFixture) -> None:
    path = write(tmp_path, f'{{"width": {width}, "height": {height}}}')
    assert load_config(path) == expected
    assert "out of range" in caplog.text


# 範囲の両端ちょうどの値は直されずにそのまま使われる
@pytest.mark.parametrize("width, height", [
    (MAZE_WIDTH_MIN, MAZE_HEIGHT_MIN), (MAZE_WIDTH_MAX, MAZE_HEIGHT_MAX)])
def test_limits_are_inclusive(tmp_path: Path, width: int, height: int,
                              caplog: pytest.LogCaptureFixture) -> None:
    path = write(tmp_path, f'{{"width": {width}, "height": {height}}}')
    assert load_config(path) == Config(width=width, height=height)
    assert caplog.text == ""


def test_unknown_keys_are_ignored(tmp_path: Path,
                                  caplog: pytest.LogCaptureFixture) -> None:
    path = write(tmp_path, '{"width": 15, "height": 11, "widht": 3}')
    assert load_config(path) == Config(width=15, height=11)
    assert "unknown key 'widht'" in caplog.text


def test_missing_file_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cannot read config file"):
        load_config(str(tmp_path / "nope.json"))


def test_broken_json_reports_the_line(tmp_path: Path) -> None:
    # コメント行を消しても行番号がずれないこと（壊れているのは 3 行目のカンマ）
    path = write(tmp_path, '# comment\n{\n  "width": 15,\n}\n')
    with pytest.raises(ConfigError, match=r"not valid JSON.*line 3"):
        load_config(path)


def test_binary_file_is_a_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ConfigError, match="not UTF-8"):
        load_config(str(path))


@pytest.mark.parametrize("text", ["[1, 2]", "21", ""])
def test_top_level_must_be_an_object(tmp_path: Path, text: str) -> None:
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, text))


# 下限の根拠: 一番小さい迷路でも中央に「42」(四方が壁のセル) が入る
def test_smallest_maze_has_42() -> None:
    maze = Maze(MAZE_WIDTH_MIN, MAZE_HEIGHT_MIN, seed=42)
    assert any(maze.is_blocked(x, y)
               for y in range(maze.height) for x in range(maze.width))


# 上限の根拠: 一番大きい迷路のウィンドウが 1440x900 の画面に収まる
# （縦はメニューバーとタイトルバーの分、約 53px を引いておく）
def test_largest_window_fits_a_small_screen() -> None:
    width, height = window_size(Maze(MAZE_WIDTH_MAX, MAZE_HEIGHT_MAX))
    assert width <= 1440
    assert height <= 900 - 53
