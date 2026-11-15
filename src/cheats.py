from dataclasses import dataclass

FAST_SPEED_RATE = 1.5  # 速度アップ中のプレイヤーの速さ（通常の何倍か）


# 評価者がゲームの機能を試しやすくするためのチート（課題 VI.5）。
# Session が 1 つだけ持ち、全レベルの Game に同じものを渡す
# （次のレベルに進んでも続く。新しいゲームを始めたら元に戻る）
@dataclass
class Cheats:
    enabled: bool = False  # チートモードに入っているか
    invincible: bool = False  # ゴーストに触れてもミスにならない
    ghosts_frozen: bool = False  # ゴーストが動かない（タイマーは進む）
    fast: bool = False  # プレイヤーが速くなる

    # チートモードを切ると、入っていた機能も全部切って普通のゲームに戻す。
    # Game が同じものを持っているので、作り直さずに中身を書き換える
    def disable(self) -> None:
        self.enabled = False
        self.invincible = False
        self.ghosts_frozen = False
        self.fast = False
