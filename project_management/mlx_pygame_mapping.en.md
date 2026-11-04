# MLX ↔ pygame mapping

> 日本語版: [mlx_pygame_mapping.ja.md](mlx_pygame_mapping.ja.md)

## Purpose

The subject says we may only use functions that have an equivalent in MLX (MinilibX).
This project uses pygame (`pygame-ce`), so this table records **which pygame feature matches which MLX function**.
Before using a new pygame feature, check this table. If it is not listed, add it first.

- Source: [MinilibX Python Documentation](https://sarafreitas-dev.github.io/MinilibX-42-Pyhton-Documentation/) (a guide to the Python version of MLX, `mlx_CLXV v2.2`, Linux only)
- **This is not an official document.** It is not a 42 document, so check what is allowed with other groups and the staff, and record the answers in this file.

Legend: ✅ has an MLX equivalent / ⚠️ open to interpretation, needs checking / ❌ no MLX equivalent (do not use)

---

## 1. pygame features we use now

| pygame | MLX | Status | Used in | Notes |
|---|---|---|---|---|
| `pygame.init()` | `mlx_init()` | ✅ | `main.py` | |
| `pygame.quit()` | `mlx_release()` | ✅ | `main.py` | |
| `pygame.display.set_mode((w, h))` | `mlx_new_window(mlx, w, h, title)` | ✅ | `main.py` | |
| `pygame.display.set_caption(title)` | `title` argument of `mlx_new_window` | ✅ | `main.py` | |
| `pygame.display.flip()` | `mlx_do_sync()` | ✅ | `main.py` | MLX shows an image as soon as it is put; pygame needs flip |
| `pygame.event.get()` | the hooks called by `mlx_loop()` | ✅ | `main.py` | MLX uses callbacks; pygame lets you pull events |
| `pygame.KEYDOWN` event | `mlx_hook(win, 2, ...)` (KeyPress) | ✅ | `main.py` | `mlx_key_hook` fires on key **release**, so use `mlx_hook` for key press |
| `pygame.QUIT` event | `mlx_hook(win, 33, ...)` (window closed) | ✅ | `main.py` | |
| `pygame.Surface((w, h))` | `mlx_new_image(mlx, w, h)` | ✅ | `src/render.py` | |
| `fill(color)` on a whole new Surface | writing every pixel through `mlx_get_data_addr()` | ✅ | `src/render.py` (`solid_image`) | Only used when creating an image, to make a single-color image |
| `screen.fill(black)` on the whole screen | `mlx_clear_window()` | ✅ | `src/render.py` | |
| `screen.blit(image, (x, y))` | `mlx_put_image_to_window(mlx, win, img, x, y)` | ✅ | `src/render.py` | All drawing goes through this |
| Game loop (`while running:`) | `mlx_loop()` + `mlx_loop_hook()` | ✅ | `main.py` | |
| Timing: `time.perf_counter()` / `time.sleep()` | (MLX has no timer) | ✅ | `main.py` | Python standard library, so the graphics rule does not apply. We do not use `pygame.time.Clock` |

## 2. MLX functions and their pygame equivalents

| MLX | What it does | pygame | Status |
|---|---|---|---|
| `mlx_init()` | Connect to the display | `pygame.init()` | ✅ |
| `mlx_release(mlx)` | Disconnect and free | `pygame.quit()` | ✅ |
| `mlx_new_window(mlx, w, h, title)` | Open a window | `pygame.display.set_mode()` + `set_caption()` | ✅ |
| `mlx_clear_window(mlx, win)` | Fill the window with black | `screen.fill((0, 0, 0))` | ✅ |
| `mlx_destroy_window(mlx, win)` | Close a window | `pygame.display.quit()` | ✅ |
| `mlx_pixel_put(mlx, win, x, y, color)` | Draw one pixel (slow) | `screen.set_at((x, y), color)` | ✅ |
| `mlx_string_put(mlx, win, x, y, color, s)` | Draw text with the built-in font | `pygame.font.Font(None, size).render()` + `blit` | ⚠️ see section 4 |
| `mlx_new_image(mlx, w, h)` | Create an empty image | `pygame.Surface((w, h))` | ✅ |
| `mlx_get_data_addr(img)` | Write directly to an image's pixels | `Surface.fill()` (whole new image), `Surface.set_at()`, `pygame.PixelArray` | ✅ |
| `mlx_put_image_to_window(mlx, win, img, x, y)` | Put an image on the window | `screen.blit(img, (x, y))` | ✅ |
| `mlx_destroy_image(mlx, img)` | Free an image | (Python frees it when no reference is left) | ✅ |
| `mlx_xpm_file_to_image(mlx, file)` | Load an XPM image (recommended) | `pygame.image.load("x.xpm")` | ✅ |
| `mlx_png_file_to_image(mlx, file)` | Load a PNG image (said to be unreliable) | `pygame.image.load("x.png")` | ✅ |
| `mlx_loop(mlx)` | Start the event loop | `while running:` + `pygame.event.get()` | ✅ |
| `mlx_loop_exit(mlx)` | Leave the loop | `running = False` | ✅ |
| `mlx_loop_hook(mlx, f, param)` | Called every frame | the body of the loop | ✅ |
| `mlx_key_hook(win, f, param)` | Key **released** | `pygame.KEYUP` | ✅ |
| `mlx_mouse_hook(win, f, param)` | Mouse button pressed | `pygame.MOUSEBUTTONDOWN` | ✅ |
| `mlx_expose_hook(win, f, param)` | Window needs redrawing | `pygame.WINDOWEXPOSED` | ✅ (not needed: we redraw every frame) |
| `mlx_hook(win, event, mask, f, param)` | Any event (KeyPress=2, window closed=33, ...) | the matching `pygame.*` event | ✅ |
| `mlx_mouse_hide` / `mlx_mouse_show` | Hide / show the cursor | `pygame.mouse.set_visible()` | ✅ |
| `mlx_mouse_move(mlx, x, y)` | Move the cursor | `pygame.mouse.set_pos()` | ✅ |
| `mlx_mouse_get_pos(mlx)` | Get the cursor position | `pygame.mouse.get_pos()` | ✅ |
| `mlx_do_key_autorepeatoff` / `on` | Key repeat off / on | `pygame.key.set_repeat()` | ✅ |
| `mlx_get_screen_size(mlx)` | Monitor size | `pygame.display.get_desktop_sizes()` | ✅ |
| `mlx_do_sync(mlx)` / `mlx_sync(...)` | Show what was drawn | `pygame.display.flip()` | ✅ |

Colors: MLX uses `0xAARRGGBB` integers; pygame uses `(R, G, B)` tuples.

## 3. pygame features we do not use (no MLX equivalent)

| pygame | Why | What to do instead |
|---|---|---|
| `pygame.draw.*` (`line`, `rect`, `circle`, ...) | MLX has no shape drawing | Make a single-color image and `blit` it (`solid_image` in `src/render.py`), or load an image file |
| `pygame.mixer` / `pygame.mixer.music` | MLX has no sound | No sound |
| `pygame.transform.*` (scale, rotate, flip) | MLX cannot transform images | Prepare images at the right size and direction from the start |
| `pygame.time.Clock`, `pygame.time.get_ticks()` | MLX has no timer | Use Python's standard `time` |
| `pygame.key.get_pressed()` | MLX cannot ask which keys are held down | Track held keys yourself with `KEYDOWN` / `KEYUP` events |

## 4. Open questions (need checking)

| Topic | Problem | Current plan |
|---|---|---|
| Text (`pygame.font`) | MLX's `mlx_string_put` only has a fixed built-in font. Using any font such as a `.ttf` file may go beyond MLX | Only use `pygame.font.Font(None, size)` (pygame's default font), or draw text from images |
| Transparency (alpha) | MLX colors have an alpha byte, but the guide does not say whether `mlx_put_image_to_window` honors it | Check before using it. If possible, use images with a black background |
| Cutting a sprite sheet (`Surface.subsurface`) | MLX cannot cut out part of an image (copying pixels with `mlx_get_data_addr` does the same thing) | Safest: one image file per frame |
| `blit` from image to image (not to the screen) | MLX only puts images on the window. Copying pixels between images does the same thing | Not used now. Check if we need it |

## 5. Record of checks

| Date | Who / where | What was asked | Answer |
|---|---|---|---|
| | | | |
