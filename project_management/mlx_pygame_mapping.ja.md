# MLX と pygame の対応表

> English version: [mlx_pygame_mapping.en.md](mlx_pygame_mapping.en.md)

## この資料の目的

課題では「MLX（MinilibX）と同等の関数だけ使ってよい」という制約がある。
このプロジェクトは pygame（`pygame-ce`）を使うので、**pygame のどの機能が MLX のどの関数に当たるか**を表にしておく。
新しく pygame の機能を使うときは、まずこの表を見て、なければ追記してから使う。

- 出典：[MinilibX Python Documentation](https://sarafreitas-dev.github.io/MinilibX-42-Pyhton-Documentation/)（MLX の Python 版 `mlx_CLXV v2.2` の解説、Linux 専用）
- **非公式の資料**。42 の公式資料ではないので、「使ってよい範囲」は周りのグループやスタッフにも確認し、結果をこの資料に追記する。

記号：✅ MLX に同等品がある ／ ⚠️ 解釈が分かれる・要確認 ／ ❌ MLX に同等品がない（使わない）

---

## 1. いま使っている pygame の機能

| pygame | MLX | 判定 | 使っている場所 | メモ |
|---|---|---|---|---|
| `pygame.init()` | `mlx_init()` | ✅ | `pac-man.py` | |
| `pygame.quit()` | `mlx_release()` | ✅ | `pac-man.py` | |
| `pygame.display.set_mode((w, h))` | `mlx_new_window(mlx, w, h, title)` | ✅ | `pac-man.py` | |
| `pygame.display.set_caption(title)` | `mlx_new_window` の `title` 引数 | ✅ | `pac-man.py` | |
| `pygame.display.flip()` | `mlx_do_sync()` | ✅ | `pac-man.py` | MLX は貼った時点で表示されるが、pygame は flip が必要 |
| `pygame.event.get()` | `mlx_loop()` が呼ぶ各フック | ✅ | `pac-man.py` | MLX はコールバック方式、pygame はイベントを取り出す方式 |
| `pygame.KEYDOWN` イベント | `mlx_hook(win, 2, ...)`（KeyPress） | ✅ | `pac-man.py` | `mlx_key_hook` は**キーを離したとき**なので、押した瞬間は `mlx_hook` を使う |
| `pygame.QUIT` イベント | `mlx_hook(win, 33, ...)`（ウィンドウを閉じる） | ✅ | `pac-man.py` | |
| `pygame.Surface((w, h))` | `mlx_new_image(mlx, w, h)` | ✅ | `src/render.py` | |
| 新しい Surface 全体への `fill(color)` | `mlx_get_data_addr()` で全ピクセルに書き込む | ✅ | `src/render.py`（`solid_image`） | 画像を作る段階で使う。単色の画像を作るだけ |
| 画面全体への `screen.fill(黒)` | `mlx_clear_window()` | ✅ | `src/render.py` | |
| `screen.blit(image, (x, y))` | `mlx_put_image_to_window(mlx, win, img, x, y)` | ✅ | `src/render.py` | 描画は基本これだけで行う |
| ゲームループ（`while running:`） | `mlx_loop()` ＋ `mlx_loop_hook()` | ✅ | `pac-man.py` | |
| 時間の計測：`time.perf_counter()` / `time.sleep()` | （MLX にはタイマーがない） | ✅ | `pac-man.py` | Python 標準ライブラリなのでグラフィックの制約の対象外。`pygame.time.Clock` は使わない |

## 2. MLX の関数と、対応する pygame の機能

| MLX | 内容 | pygame | 判定 |
|---|---|---|---|
| `mlx_init()` | ディスプレイに接続 | `pygame.init()` | ✅ |
| `mlx_release(mlx)` | 接続を切って解放 | `pygame.quit()` | ✅ |
| `mlx_new_window(mlx, w, h, title)` | ウィンドウを開く | `pygame.display.set_mode()` ＋ `set_caption()` | ✅ |
| `mlx_clear_window(mlx, win)` | ウィンドウを黒で塗る | `screen.fill((0, 0, 0))` | ✅ |
| `mlx_destroy_window(mlx, win)` | ウィンドウを閉じる | `pygame.display.quit()` | ✅ |
| `mlx_pixel_put(mlx, win, x, y, color)` | 1 ピクセル描く（遅い） | `screen.set_at((x, y), color)` | ✅ |
| `mlx_string_put(mlx, win, x, y, color, s)` | 内蔵フォントで文字を描く | `pygame.font.Font(None, size).render()` ＋ `blit` | ⚠️ 下の 4 章 |
| `mlx_new_image(mlx, w, h)` | 空の画像を作る | `pygame.Surface((w, h))` | ✅ |
| `mlx_get_data_addr(img)` | 画像のピクセルデータに直接書き込む | `Surface.fill()`（新しい画像全体）、`Surface.set_at()`、`pygame.PixelArray` | ✅ |
| `mlx_put_image_to_window(mlx, win, img, x, y)` | 画像をウィンドウに貼る | `screen.blit(img, (x, y))` | ✅ |
| `mlx_destroy_image(mlx, img)` | 画像を解放 | （Python では参照を消せば解放される） | ✅ |
| `mlx_xpm_file_to_image(mlx, file)` | XPM 画像を読む（推奨） | `pygame.image.load("x.xpm")` | ✅ |
| `mlx_png_file_to_image(mlx, file)` | PNG 画像を読む（不安定とのこと） | `pygame.image.load("x.png")` | ✅ |
| `mlx_loop(mlx)` | イベントループ開始 | `while running:` ＋ `pygame.event.get()` | ✅ |
| `mlx_loop_exit(mlx)` | ループを抜ける | `running = False` | ✅ |
| `mlx_loop_hook(mlx, f, param)` | 毎フレーム呼ばれる処理 | ループの中身 | ✅ |
| `mlx_key_hook(win, f, param)` | キーを**離した**とき | `pygame.KEYUP` | ✅ |
| `mlx_mouse_hook(win, f, param)` | マウスボタンを押したとき | `pygame.MOUSEBUTTONDOWN` | ✅ |
| `mlx_expose_hook(win, f, param)` | 再描画が必要なとき | `pygame.WINDOWEXPOSED` | ✅（毎フレーム描き直すので不要） |
| `mlx_hook(win, event, mask, f, param)` | 任意のイベント（KeyPress=2、閉じる=33 など） | 対応する `pygame.*` イベント | ✅ |
| `mlx_mouse_hide` / `mlx_mouse_show` | カーソルを隠す / 出す | `pygame.mouse.set_visible()` | ✅ |
| `mlx_mouse_move(mlx, x, y)` | カーソルを動かす | `pygame.mouse.set_pos()` | ✅ |
| `mlx_mouse_get_pos(mlx)` | カーソル位置を取る | `pygame.mouse.get_pos()` | ✅ |
| `mlx_do_key_autorepeatoff` / `on` | キーリピートのオフ / オン | `pygame.key.set_repeat()` | ✅ |
| `mlx_get_screen_size(mlx)` | モニターの大きさ | `pygame.display.get_desktop_sizes()` | ✅ |
| `mlx_do_sync(mlx)` / `mlx_sync(...)` | 描画を反映する | `pygame.display.flip()` | ✅ |

色について：MLX は `0xAARRGGBB` の整数、pygame は `(R, G, B)` のタプルで指定する。

## 3. 使わない pygame の機能（MLX に同等品がない）

| pygame | 理由 | 代わりにどうするか |
|---|---|---|
| `pygame.draw.*`（`line`、`rect`、`circle` など） | MLX に図形を描く関数がない | 単色の画像を作って `blit` する（`src/render.py` の `solid_image`）、または画像ファイルを読む |
| `pygame.mixer` / `pygame.mixer.music` | MLX に音の機能がない | サウンドは使わない |
| `pygame.transform.*`（拡大・縮小・回転・反転） | MLX に画像を変形する関数がない | 必要な大きさ・向きの画像を最初から用意する |
| `pygame.time.Clock`、`pygame.time.get_ticks()` | MLX にタイマーがない | Python 標準の `time` を使う |
| `pygame.key.get_pressed()` | MLX にはキーの状態を問い合わせる関数がない | `KEYDOWN` / `KEYUP` イベントで押されているキーを自分で記録する |

## 4. 判断が分かれるもの（要確認）

| 項目 | 問題 | 今の方針 |
|---|---|---|
| 文字の表示（`pygame.font`） | MLX の `mlx_string_put` は内蔵の固定フォントだけ。`.ttf` などの好きなフォントを使うのは MLX を超えているかもしれない | `pygame.font.Font(None, size)`（pygame の既定フォント）だけ使う。または文字を画像で用意する |
| 画像の透明部分（アルファ） | MLX の色にはアルファがあるが、`mlx_put_image_to_window` で透明が効くかは資料からは不明 | 使う前に確認する。使わなくて済むなら黒背景の画像にする |
| スプライトシートの切り出し（`Surface.subsurface`） | MLX には画像の一部を切り出す関数がない（`mlx_get_data_addr` でピクセルを写せば同じことはできる） | 1 コマずつ別の画像ファイルにしておくのが一番安全 |
| 画像同士の `blit`（画面ではなく画像に画像を貼る） | MLX は「画像をウィンドウに貼る」だけ。画像同士はピクセルを写せば同じことはできる | 今は使っていない。必要になったら確認する |

## 5. 確認の記録

| 日付 | 誰に / どこで | 確認した内容 | 結果 |
|---|---|---|---|
| | | | |
