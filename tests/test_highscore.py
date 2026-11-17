import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pygame
import pytest

from src.config import Config, parse_config
from src.highscore import (MAX_ENTRIES, NAME_MAX, Entry, HighscoreTable,
                           valid_name, valid_score)
from src.render import WINDOW_SIZE, TextWriter
from src.screens import (Context, HighscoresScreen, MainMenuScreen,
                         ResultScreen, Screen)


def table_at(tmp_path: Path) -> HighscoreTable:
    return HighscoreTable(str(tmp_path / "highscores.json"))


def write_file(tmp_path: Path, data: Any) -> str:
    path = tmp_path / "highscores.json"
    path.write_text(data if isinstance(data, str) else json.dumps(data),
                    encoding="utf-8")
    return str(path)


# ---- 名前と得点の決まり ----

@pytest.mark.parametrize("name", ["A", "ABC 123", "x" * NAME_MAX, "a b"])
def test_valid_names(name: str) -> None:
    assert valid_name(name)


@pytest.mark.parametrize("name", ["", " ", "   ", "x" * (NAME_MAX + 1),
                                  "AB-C", "ÉLODIE", "名前", "A\tB", "a_b"])
def test_invalid_names(name: str) -> None:
    assert not valid_name(name)


@pytest.mark.parametrize("score, ok", [
    (0, True), (1200, True), (-1, False), (1.5, False), (True, False),
    ("100", False), (None, False)])
def test_valid_scores(score: Any, ok: bool) -> None:
    assert valid_score(score) == ok


# ---- 一覧（上位 10 件） ----

def test_entries_are_sorted_by_score(tmp_path: Path) -> None:
    table = table_at(tmp_path)
    table.add("LOW", 10)
    table.add("HIGH", 300)
    table.add("MID", 100)
    assert [e.name for e in table.entries] == ["HIGH", "MID", "LOW"]


def test_on_a_tie_the_older_entry_stays_above(tmp_path: Path) -> None:
    table = table_at(tmp_path)
    table.add("FIRST", 100)
    assert table.add("SECOND", 100) == 1
    assert [e.name for e in table.entries] == ["FIRST", "SECOND"]


def test_only_the_top_ten_are_kept(tmp_path: Path) -> None:
    table = table_at(tmp_path)
    for i in range(MAX_ENTRIES):
        table.add(f"P{i}", 100 + i)
    assert table.add("LOW", 50) is None  # 入らない
    assert table.add("TOP", 1000) == 0  # 入って、一番下が押し出される
    assert len(table.entries) == MAX_ENTRIES
    assert table.entries[0] == Entry("TOP", 1000)
    assert Entry("P0", 100) not in table.entries


# ---- ファイルの読み書き ----

def test_save_and_load_round_trip(tmp_path: Path) -> None:
    table = table_at(tmp_path)
    table.add("ALICE", 500)
    table.add("BOB 2", 700)
    assert table.save()
    loaded = HighscoreTable.load(table.path)
    assert loaded.entries == [Entry("BOB 2", 700), Entry("ALICE", 500)]


def test_missing_file_is_an_empty_list_without_warning(
        tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    table = HighscoreTable.load(str(tmp_path / "nope.json"))
    assert table.entries == []
    assert caplog.text == ""


@pytest.mark.parametrize("text", ["{broken", "[1, 2]", '{"highscores": 3}',
                                  "", '"text"'])
def test_broken_file_is_an_empty_list(tmp_path: Path, text: str,
                                      caplog: pytest.LogCaptureFixture
                                      ) -> None:
    table = HighscoreTable.load(write_file(tmp_path, text))
    assert table.entries == []
    assert "highscores:" in caplog.text


def test_binary_file_is_an_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "highscores.json"
    path.write_bytes(b"\xff\xfe\x00")
    assert HighscoreTable.load(str(path)).entries == []


def test_a_folder_instead_of_a_file_does_not_crash(tmp_path: Path) -> None:
    folder = tmp_path / "scores"
    folder.mkdir()
    table = HighscoreTable.load(str(folder))
    assert table.entries == []
    table.add("ABC", 10)
    assert not table.save()


# 読み込むときも名前と得点を確認して、おかしな行だけ捨てる
def test_broken_entries_are_skipped(tmp_path: Path,
                                    caplog: pytest.LogCaptureFixture) -> None:
    rows: list[Any] = [
        {"name": "GOOD", "score": 100},
        {"name": "TOOLONGNAME1", "score": 1},
        {"name": "BAD!", "score": 1},
        {"name": "NEG", "score": -5},
        {"name": "FLOAT", "score": 1.5},
        {"name": "BOOL", "score": True},
        {"name": 42, "score": 1},
        {"score": 1},
        "not an object",
        {"name": "OK 2", "score": 0},
    ]
    table = HighscoreTable.load(write_file(tmp_path, {"highscores": rows}))
    assert table.entries == [Entry("GOOD", 100), Entry("OK 2", 0)]
    assert "skipped 8 broken entries" in caplog.text


def test_file_with_too_many_or_unsorted_rows_is_fixed(tmp_path: Path) -> None:
    rows = [{"name": f"P{i}", "score": i} for i in range(15)]
    table = HighscoreTable.load(write_file(tmp_path, {"highscores": rows}))
    assert len(table.entries) == MAX_ENTRIES
    assert [e.score for e in table.entries] == list(range(14, 4, -1))


def test_save_creates_missing_folders(tmp_path: Path) -> None:
    table = HighscoreTable(str(tmp_path / "a" / "b" / "scores.json"))
    table.add("ABC", 10)
    assert table.save()
    assert HighscoreTable.load(table.path).entries == [Entry("ABC", 10)]


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0,
                    reason="needs file permissions (and not root)")
def test_read_only_folder_does_not_crash(
        tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    folder = tmp_path / "locked"
    folder.mkdir()
    folder.chmod(0o500)
    try:
        table = HighscoreTable(str(folder / "scores.json"))
        table.add("ABC", 10)
        assert not table.save()
        assert "cannot save" in caplog.text
    finally:
        folder.chmod(0o700)


def test_failed_save_keeps_the_old_file(tmp_path: Path) -> None:
    table = table_at(tmp_path)
    table.add("OLD", 10)
    assert table.save()
    before = Path(table.path).read_text(encoding="utf-8")
    table.path = str(tmp_path)  # フォルダには書けない
    assert not table.save()
    assert (tmp_path / "highscores.json").read_text(encoding="utf-8") \
        == before
    assert not list(tmp_path.glob("*.tmp"))  # 一時ファイルが残らない


# ---- 設定ファイルの highscore_filename ----

def test_highscore_filename_is_read() -> None:
    assert parse_config({"highscore_filename": "x/scores.json"}
                        ).highscore_filename == "x/scores.json"


@pytest.mark.parametrize("value", ["", "   ", 3, None, ["a"]])
def test_bad_highscore_filename_uses_default(
        value: Any, caplog: pytest.LogCaptureFixture) -> None:
    config = parse_config({"highscore_filename": value})
    assert config.highscore_filename == Config().highscore_filename
    assert "'highscore_filename'" in caplog.text


# ---- 名前の入力画面とハイスコアの画面 ----

@pytest.fixture
def ctx(tmp_path: Path) -> Iterator[Context]:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    yield Context(Config(), TextWriter(), table_at(tmp_path))
    pygame.quit()


def type_keys(screen: Screen, *keys: int) -> Screen | None:
    result: Screen | None = screen
    for key in keys:
        assert result is not None
        result = result.handle_key(key)
    return result


def result_screen(ctx: Context, score: int = 1234) -> ResultScreen:
    return ResultScreen(ctx, won=False, time_up=False, score=score)


def test_typing_a_name(ctx: Context) -> None:
    screen = result_screen(ctx)
    type_keys(screen, pygame.K_SPACE, pygame.K_a, pygame.K_b, pygame.K_SPACE,
              pygame.K_7, pygame.K_KP3, pygame.K_MINUS)
    assert screen.name == "AB 73"  # 先頭の空白と記号は入らない
    type_keys(screen, pygame.K_BACKSPACE)
    assert screen.name == "AB 7"


def test_name_stops_at_ten_letters(ctx: Context) -> None:
    screen = result_screen(ctx)
    type_keys(screen, *[pygame.K_x] * (NAME_MAX + 5))
    assert screen.name == "X" * NAME_MAX


def test_enter_saves_and_shows_the_list(ctx: Context) -> None:
    screen = result_screen(ctx, score=500)
    shown = type_keys(screen, pygame.K_k, pygame.K_o, pygame.K_SPACE,
                      pygame.K_RETURN)
    assert isinstance(shown, HighscoresScreen)
    assert shown.highlight == 0
    assert ctx.highscores.entries == [Entry("KO", 500)]  # 末尾の空白は消す
    saved = HighscoreTable.load(ctx.highscores.path)
    assert saved.entries == [Entry("KO", 500)]
    assert isinstance(type_keys(shown, pygame.K_RETURN), MainMenuScreen)


def test_empty_name_cannot_be_saved(ctx: Context) -> None:
    screen = result_screen(ctx)
    assert type_keys(screen, pygame.K_RETURN) is screen
    assert ctx.highscores.entries == []


def test_esc_skips_without_saving(ctx: Context) -> None:
    screen = result_screen(ctx)
    shown = type_keys(screen, pygame.K_a, pygame.K_ESCAPE)
    assert isinstance(shown, MainMenuScreen)
    assert ctx.highscores.entries == []
    assert not Path(ctx.highscores.path).exists()


def test_score_outside_the_top_ten_is_not_saved(ctx: Context) -> None:
    for i in range(MAX_ENTRIES):
        ctx.highscores.add(f"P{i}", 1000)
    shown = type_keys(result_screen(ctx, score=1), pygame.K_a,
                      pygame.K_RETURN)
    assert isinstance(shown, HighscoresScreen)
    assert shown.highlight is None
    assert "did not make the top" in shown.note
    assert not Path(ctx.highscores.path).exists()


def test_screens_draw_full_and_empty_lists(ctx: Context) -> None:
    surface = pygame.Surface(WINDOW_SIZE)
    HighscoresScreen(ctx).draw(surface)
    for i in range(MAX_ENTRIES):
        ctx.highscores.add("W" * NAME_MAX, 1_000_000 - i)
    HighscoresScreen(ctx, highlight=3, note="note").draw(surface)
    screen = result_screen(ctx)
    type_keys(screen, *[pygame.K_w] * NAME_MAX)
    screen.draw(surface)


def test_app_loads_highscores_at_start(tmp_path: Path) -> None:
    from src.app import App
    path = write_file(tmp_path, {"highscores": [{"name": "ME", "score": 9}]})
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    app = App(Config(highscore_filename=path))
    try:
        assert app.screen is not None
        assert app.screen.ctx.highscores.entries == [Entry("ME", 9)]
    finally:
        pygame.quit()
