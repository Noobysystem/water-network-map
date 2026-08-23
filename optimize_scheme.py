from PIL import Image
import os

Image.MAX_IMAGE_PIXELS = None

INPUT = "frontend/scheme.png"
OUTPUT = "frontend/scheme.jpg"

if os.path.exists(INPUT):
    print("Оптимизация схемы для стабильной работы на смартфонах...")
    img = Image.open(INPUT)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # Масштабируем до 5000px по ширине (идеальный баланс четкости и памяти для Safari iOS)
    orig_w, orig_h = img.size
    target_w = 5000
    target_h = int(orig_h * (target_w / orig_w))
    
    resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    resized.save(OUTPUT, "JPEG", quality=90, optimize=True)
    print(f"Готово! Создан {OUTPUT} ({target_w}x{target_h})")
