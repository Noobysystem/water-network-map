import cv2
import numpy as np
import json
import os
import easyocr
import re

IMAGE_PATH = "frontend/scheme.png"
OUTPUT_JSON = "data/network.json"
IMG_HEIGHT = 3508

def detect_water_network():
    if not os.path.exists(IMAGE_PATH):
        print(f"Файл {IMAGE_PATH} не найден.")
        return

    print("1. Обработка изображения...")
    img = cv2.imread(IMAGE_PATH)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Маска синего цвета
    lower_blue = np.array([90, 40, 40])
    upper_blue = np.array([140, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    print("2. Детекция кругов (колодцы и арматура)...")
    circles = cv2.HoughCircles(
        blue_mask, 
        cv2.HOUGH_GRADIENT, 
        dp=1.2, 
        minDist=25, 
        param1=40, 
        param2=13, 
        minRadius=5, 
        maxRadius=25
    )

    detected_nodes = []
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for i, c in enumerate(circles[0, :]):
            cx, cy, r = int(c[0]), int(c[1]), int(c[2])
            # Leaflet CRS.Simple инвертирует ось Y
            leaflet_y = IMG_HEIGHT - cy
            node_type = "hydrant" if r >= 13 else "well"
            detected_nodes.append({
                "id": f"node_auto_{i+1}",
                "name": f"{'ПГ' if node_type == 'hydrant' else 'к'}_{i+1}",
                "type": node_type,
                "x": cx,
                "y": leaflet_y,
                "orig_y": cy,
                "radius": r
            })

    print(f"Найдено узлов: {len(detected_nodes)}")

    print("3. Считывание текста с чертежа (EasyOCR)...")
    reader = easyocr.Reader(['ru', 'en'], gpu=False)
    ocr_results = reader.readtext(gray, paragraph=False)

    print("4. Привязка подписей...")
    for (bbox, text, prob) in ocr_results:
        clean_text = text.strip()
        if prob < 0.35:
            continue

        (tl, tr, br, bl) = bbox
        tx_center = int((tl[0] + br[0]) / 2)
        ty_center = int((tl[1] + br[1]) / 2)

        # Проверяем метки номеров колодцев и гидрантов
        if re.search(r'^(к|k|K)\s*\d+', clean_text, re.IGNORECASE) or re.search(r'^(пг|п|г|pg)\s*\d+', clean_text, re.IGNORECASE):
            for node in detected_nodes:
                dist = np.hypot(node["x"] - tx_center, node["orig_y"] - ty_center)
                if dist < 70:
                    node["name"] = clean_text.replace(" ", "")
                    break

    # Очистка служебных полей
    for n in detected_nodes:
        n.pop("orig_y", None)
        n.pop("radius", None)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    payload = {"nodes": detected_nodes, "pipes": [], "valves": []}

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Готово! Сохранено {len(detected_nodes)} узлов в {OUTPUT_JSON}")

if __name__ == "__main__":
    detect_water_network()
