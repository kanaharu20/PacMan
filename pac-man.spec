# PyInstaller の設定（課題 VII 章の packaging spec）。`make build` で使う。
# pac-man.py と、そこから import されるもの（src・pygame・迷路パッケージ）を
# 実行ファイル 1 個（dist/pac-man）にまとめる。

a = Analysis(['pac-man.py'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name='pac-man', console=True)
