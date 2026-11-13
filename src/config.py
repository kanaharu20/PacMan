import json
import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

# 迷路の大きさ（マス数）の範囲。範囲外の値はこの範囲に丸める
# 下限: 迷路生成パッケージが中央に「42」を入れられる最小サイズ (14x10)。
#   これより小さいと「42」が入らず、ゴーストに捕まるまでの余裕も 2 秒を切る
# 上限: 1 マス 32px のウィンドウ (最大 1288x836px) が 1440x900 の画面にも収まる
MAZE_WIDTH_MIN, MAZE_WIDTH_MAX = 14, 40
MAZE_HEIGHT_MIN, MAZE_HEIGHT_MAX = 10, 25


class ConfigError(Exception):
    """設定ファイルが読めない・JSON として壊れている（続行できない）エラー"""


@dataclass
class Config:
    width: int = 21  # 迷路の横のマス数
    height: int = 21  # 迷路の縦のマス数


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
    known = set(vars(default))
    for key in data:
        if key not in known:
            log.warning("config: unknown key '%s' is ignored", key)
    return Config(
        width=_read_int(data, "width", default.width,
                        MAZE_WIDTH_MIN, MAZE_WIDTH_MAX),
        height=_read_int(data, "height", default.height,
                         MAZE_HEIGHT_MIN, MAZE_HEIGHT_MAX),
    )


def _read_int(data: dict[str, Any], key: str, default: int,
              low: int, high: int) -> int:
    if key not in data:
        log.warning("config: '%s' is missing, using default %d", key, default)
        return default
    value = data[key]
    # bool は int の子クラスなので、true / false を数として受け取らないよう除く
    if isinstance(value, bool) or not isinstance(value, int):
        log.warning("config: '%s' must be an integer (got %s), "
                    "using default %d", key, json.dumps(value), default)
        return default
    clamped = min(max(value, low), high)
    if clamped != value:
        log.warning("config: '%s' = %d is out of range [%d, %d], using %d",
                    key, value, low, high, clamped)
    return clamped
