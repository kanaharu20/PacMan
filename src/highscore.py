import contextlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

MAX_ENTRIES = 10  # 上位 10 件だけ残す（課題 V.5）
NAME_MAX = 10  # 名前は最大 10 文字
NAME_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                 "abcdefghijklmnopqrstuvwxyz0123456789 ")  # 英数字とスペースだけ


@dataclass(frozen=True)
class Entry:
    name: str
    score: int


# 名前の決まり: 1〜10 文字、英数字とスペースだけ、空白だけはだめ
def valid_name(name: str) -> bool:
    return (0 < len(name) <= NAME_MAX and set(name) <= NAME_CHARS
            and name.strip() != "")


# 得点の決まり: 0 以上の整数（JSON の true / false は数として受け取らない）
def valid_score(score: Any) -> bool:
    return (isinstance(score, int) and not isinstance(score, bool)
            and score >= 0)


# ハイスコアの一覧（得点の高い順、最大 10 件）とその保存先。
# ファイルは JSON: {"highscores": [{"name": "ABC", "score": 1200}, ...]}
# 読めない・壊れているときは警告を出して空の一覧から始め、ゲームは止めない
class HighscoreTable:
    def __init__(self, path: str, entries: list[Entry] | None = None) -> None:
        self.path = path
        self.entries: list[Entry] = []
        for entry in entries or []:
            self.add(entry.name, entry.score)

    @classmethod
    def load(cls, path: str) -> "HighscoreTable":
        table = cls(path)
        if not os.path.exists(path):  # 初めて遊ぶときはファイルがない
            return table
        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            log.warning("highscores: cannot read '%s' (%s), starting with an "
                        "empty list", path, e)
            return table
        raw = data.get("highscores") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            log.warning("highscores: '%s' has no \"highscores\" list, "
                        "starting with an empty list", path)
            return table
        skipped = 0
        for item in raw:
            name = item.get("name") if isinstance(item, dict) else None
            score = item.get("score") if isinstance(item, dict) else None
            if (isinstance(name, str) and valid_name(name)
                    and isinstance(score, int) and valid_score(score)):
                table.add(name, score)
            else:
                skipped += 1
        if skipped:
            log.warning("highscores: skipped %d broken entries in '%s'",
                        skipped, path)
        return table

    # 上位 10 件に入るなら追加して順位（0 から数える）を返す。入らなければ None
    # 同点なら先に登録した人が上
    def add(self, name: str, score: int) -> int | None:
        rank = sum(1 for entry in self.entries if entry.score >= score)
        if rank >= MAX_ENTRIES:
            return None
        self.entries.insert(rank, Entry(name, score))
        del self.entries[MAX_ENTRIES:]
        return rank

    # 保存できたら True。できなくても（場所がない・書き込めないなど）落とさない。
    # 一時ファイルに書いてから置き換えるので、途中で失敗しても前のファイルは残る
    def save(self) -> bool:
        data = {"highscores": [{"name": e.name, "score": e.score}
                               for e in self.entries]}
        folder = os.path.dirname(os.path.abspath(self.path))
        try:
            os.makedirs(folder, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    json.dump(data, file, indent=2)
                os.replace(tmp, self.path)
            except BaseException:
                with contextlib.suppress(OSError):  # 一時ファイルの後片付け
                    os.unlink(tmp)
                raise
        except OSError as e:
            log.warning("highscores: cannot save to '%s' (%s)", self.path, e)
            return False
        return True
