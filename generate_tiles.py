import os
import math
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

IMAGE_PATH = "frontend/scheme.png"
TILES_DIR = "frontend/tiles"
TILE_SIZE = 256

def generate_tiles():
    if not os.path.exists(IMAGE_PATH):
        print(f"Файл {IMAGE_PATH} не найден!")
        return

    print("Открываем чертеж высокого разрешения...")
    img = Image.open(IMAGE_PATH)
    w, h = img.size
    print(f"Размер: {w} x {h}")

    max_dim = max(w, h)
    max_zoom = int(math.ceil(math.log2(max_dim / TILE_SIZE)))
    print(f"Генерация уровней зума: 0..{max_zoom}")

    for z in range(max_zoom + 1):
        zoom_dir = os.path.join(TILES_DIR, str(z))
        os.makedirs(zoom_dir, exist_ok=True)

        scale = 2 ** (z - max_zoom)
        cur_w = max(1, int(round(w * scale)))
        cur_h = max(1, int(round(h * scale)))

        print(f"Уровень зума {z}/{max_zoom} ({cur_w}x{cur_h})...")
        resized = img.resize((cur_w, cur_h), Image.Resampling.BILINEAR)

        cols = int(math.ceil(cur_w / TILE_SIZE))
        rows = int(math.ceil(cur_h / TILE_SIZE))

        for x in range(cols):
            x_dir = os.path.join(zoom_dir, str(x))
            os.makedirs(x_dir, exist_ok=True)
            for y in range(rows):
                left = x * TILE_SIZE
                top = y * TILE_SIZE
                right = min(left + TILE_SIZE, cur_w)
                bottom = min(top + TILE_SIZE, cur_h)

                tile = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (255, 255, 255))
                cropped = resized.crop((left, top, right, bottom))
                tile.paste(cropped, (0, 0))

                tile_path = os.path.join(x_dir, f"{y}.jpg")
                tile.save(tile_path, "JPEG", quality=85)

    print("Готово! Тайлы успешно созданы в папке frontend/tiles")

if __name__ == "__main__":
    generate_tiles()
