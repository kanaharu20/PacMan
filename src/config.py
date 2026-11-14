import json
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# 迷路の大きさ（マス数）の範囲。範囲外の値はこの範囲に丸める
# 下限: 迷路生成パッケージが中央に「42」を入れられる最小サイズ (14x10)。
#   これより小さいと「42」が入らず、ゴーストに捕まるまでの余裕も 2 秒を切る
# 上限: 1 マス 32px のウィンドウ (最大 1288x836px) が 1440x900 の画面にも収まる
MAZE_WIDTH_MIN, MAZE_WIDTH_MAX = 14, 40
MAZE_HEIGHT_MIN, MAZE_HEIGHT_MAX = 10, 25
# そのほかの値の範囲
LIVES_MIN, LIVES_MAX = 1, 9  # HUD に 1 桁で出す
SEED_MIN, SEED_MAX = 0, 2 ** 31 - 1  # 0 はランダム（迷路生成パッケージの仕様）
TIME_MIN, TIME_MAX = 10, 999  # レベルの制限時間（秒）
POINTS_MIN, POINTS_MAX = 0, 1_000_000  # 得点は減らないので 0 以上
# レベル数。課題で 10 以上が必須なので、少ないときは既定の大きさで 10 まで足す
LEVELS_MIN, LEVELS_MAX = 10, 50


class ConfigError(Exception):
    """設定ファイルが読めない・JSON として壊れている（続行できない）エラー"""


@dataclass(frozen=True)
class LevelConfig:
    width: int = 21
    height: int = 21
    level_max_time: int = 90  # 秒


@dataclass
class Config:
    # width / height / level_max_time は、levels の中で省略したときの値。
    # levels がないときは、この大きさのレベルを LEVELS_MIN 個作る
    width: int = 21  # 迷路の横のマス数
    height: int = 21  # 迷路の縦のマス数
    level_max_time: int = 90  # レベルの制限時間（秒）
    lives: int = 3
    seed: int = 42  # レベル 1 の迷路のシード。レベル 2 からはランダム
    points_per_pacgum: int = 10
    points_per_super_pacgum: int = 50
    points_per_ghost: int = 200
    levels: list[LevelConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.levels:
            self.levels = [self.default_level()] * LEVELS_MIN

    def default_level(self) -> LevelConfig:
        return LevelConfig(self.width, self.height, self.level_max_time)


# 「#」で始まる行（前に空白があってもよい）をコメントとして消す。
# 行番号がずれないように、消した行は空行にしておく
def strip_comments(text: str) -> str:
    return "\n".join("" if line.lstrip().startswith("#") else line
                     for line in text.splitlines())


def load_config(path: str) -> Config:
    try:
        with open(path, encoding="utf-8") as file:
            text = file.read()
    except OSError as e:  # ない・ディレクトリ・権限がない など
        raise ConfigError(f"cannot read config file '{path}': "
                          f"{e.strerror}") from e
    except UnicodeDecodeError as e:
        raise ConfigError(f"config file '{path}' is not UTF-8 text") from e
    try:
        data = json.loads(strip_comments(text))
    except json.JSONDecodeError as e:
        raise ConfigError(f"config file '{path}' is not valid JSON: "
                          f"{e.msg} (line {e.lineno}, column {e.colno})"
                          ) from e
    if not isinstance(data, dict):
        raise ConfigError(f"config file '{path}' must contain a JSON object "
                          "({ ... }) at the top level")
    return parse_config(data)


# 値が足りない・おかしいときは既定値か範囲内の値に直して、ログを出して続ける
def parse_config(data: dict[str, Any]) -> Config:
    default = Config()
    _warn_unknown_keys(data, set(vars(default)), "")
    # levels があるときは、width / height / level_max_time は省略してよい
    # （levels の中で省略したレベルにだけ使う）ので、ないと言わない
    warn = "levels" not in data
    width = _read_int(data, "width", default.width,
                      MAZE_WIDTH_MIN, MAZE_WIDTH_MAX, warn_missing=warn)
    height = _read_int(data, "height", default.height,
                       MAZE_HEIGHT_MIN, MAZE_HEIGHT_MAX, warn_missing=warn)
    level_time = _read_int(data, "level_max_time", default.level_max_time,
                           TIME_MIN, TIME_MAX, warn_missing=warn)
    fallback = LevelConfig(width, height, level_time)
    return Config(
        width=width,
        height=height,
        level_max_time=level_time,
        lives=_read_int(data, "lives", default.lives, LIVES_MIN, LIVES_MAX),
        seed=_read_int(data, "seed", default.seed, SEED_MIN, SEED_MAX),
        points_per_pacgum=_read_points(data, "points_per_pacgum",
                                       default.points_per_pacgum),
        points_per_super_pacgum=_read_points(
            data, "points_per_super_pacgum", default.points_per_super_pacgum),
        points_per_ghost=_read_points(data, "points_per_ghost",
                                      default.points_per_ghost),
        levels=_read_levels(data, fallback),
    )


# levels: [{"width": 15, "height": 11, "level_max_time": 90}, ...]
# 各レベルで省略したキーは fallback（一番外の width / height / level_max_time）
def _read_levels(data: dict[str, Any],
                 fallback: LevelConfig) -> list[LevelConfig]:
    if "levels" not in data:
        log.warning("config: 'levels' is missing, using %d levels of %dx%d",
                    LEVELS_MIN, fallback.width, fallback.height)
        return [fallback] * LEVELS_MIN
    raw = data["levels"]
    if not isinstance(raw, list):
        log.warning("config: 'levels' must be a list (got %s), using %d "
                    "levels of %dx%d", json.dumps(raw), LEVELS_MIN,
                    fallback.width, fallback.height)
        return [fallback] * LEVELS_MIN
    if len(raw) > LEVELS_MAX:
        log.warning("config: 'levels' has %d levels, only the first %d are "
                    "used", len(raw), LEVELS_MAX)
        raw = raw[:LEVELS_MAX]
    levels = [_read_level(entry, i, fallback) for i, entry in enumerate(raw)]
    if len(levels) < LEVELS_MIN:
        log.warning("config: 'levels' has %d levels but at least %d are "
                    "needed, adding levels of %dx%d", len(levels), LEVELS_MIN,
                    fallback.width, fallback.height)
        levels += [fallback] * (LEVELS_MIN - len(levels))
    return levels


def _read_level(entry: Any, index: int, fallback: LevelConfig) -> LevelConfig:
    name = f"levels[{index}]"
    if not isinstance(entry, dict):
        log.warning("config: '%s' must be an object (got %s), using %dx%d",
                    name, json.dumps(entry), fallback.width, fallback.height)
        return fallback
    _warn_unknown_keys(entry, set(vars(fallback)), f"{name}.")
    return LevelConfig(
        width=_read_int(entry, "width", fallback.width, MAZE_WIDTH_MIN,
                        MAZE_WIDTH_MAX, warn_missing=False, prefix=name),
        height=_read_int(entry, "height", fallback.height, MAZE_HEIGHT_MIN,
                         MAZE_HEIGHT_MAX, warn_missing=False, prefix=name),
        level_max_time=_read_int(entry, "level_max_time",
                                 fallback.level_max_time, TIME_MIN, TIME_MAX,
                                 warn_missing=False, prefix=name),
    )


def _warn_unknown_keys(data: dict[str, Any], known: set[str],
                       prefix: str) -> None:
    for key in data:
        if key not in known:
            log.warning("config: unknown key '%s%s' is ignored", prefix, key)


def _read_points(data: dict[str, Any], key: str, default: int) -> int:
    return _read_int(data, key, default, POINTS_MIN, POINTS_MAX)


def _read_int(data: dict[str, Any], key: str, default: int,
              low: int, high: int, warn_missing: bool = True,
              prefix: str = "") -> int:
    name = f"{prefix}.{key}" if prefix else key
    if key not in data:
        if warn_missing:
            log.warning("config: '%s' is missing, using default %d",
                        name, default)
        return default
    value = data[key]
    # bool は int の子クラスなので、true / false を数として受け取らないよう除く
    if isinstance(value, bool) or not isinstance(value, int):
        log.warning("config: '%s' must be an integer (got %s), "
                    "using default %d", name, json.dumps(value), default)
        return default
    clamped = min(max(value, low), high)
    if clamped != value:
        log.warning("config: '%s' = %d is out of range [%d, %d], using %d",
                    name, value, low, high, clamped)
    return clamped
