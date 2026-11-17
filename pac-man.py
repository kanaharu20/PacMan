"""Pac-Man の起動スクリプト。

使い方: python3 pac-man.py <config.json>
引数の確認・設定の読み込み・ゲームの起動を行い、どんなエラーでも
トレースバックを出さずにメッセージだけ出して終了する。
"""

import logging
import os
import sys

# pygame の起動メッセージ（"pygame-ce 2.5.8 (SDL ...)"）をターミナルに出さない。
# pygame を import する前に設定しないと効かないので、ここだけ import の途中に書く
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from src.app import App  # noqa: E402
from src.config import ConfigError, load_config  # noqa: E402
from src.mazegen import MazeError  # noqa: E402

USAGE = "usage: python3 pac-man.py <config.json>"


def main() -> None:
    """引数の設定ファイルを読んでゲームを起動する。

    引数が 1 つでない・設定が読めない・迷路が作れない・想定外の例外が
    起きたときは、理由を 1 行出して終了する。
    """
    # 設定の補正などのメッセージを「WARNING: ...」の形でターミナルに出す
    logging.basicConfig(format="%(levelname)s: %(message)s")
    if len(sys.argv) != 2:
        sys.exit(USAGE)
    try:
        config = load_config(sys.argv[1])
    except ConfigError as e:
        sys.exit(f"Error: {e}")  # トレースバックは出さず、理由だけ出して終了
    # どこで何が起きてもトレースバックを出さない（最後の砦）
    # App.run は抜けるときに必ず pygame.quit を呼ぶ
    try:
        App(config).run()
    except KeyboardInterrupt:  # Ctrl+C
        sys.exit(0)
    except MazeError as e:
        sys.exit(f"Error: {e}")
    except Exception as e:
        sys.exit(f"Error: unexpected {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
