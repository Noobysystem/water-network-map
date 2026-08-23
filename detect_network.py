import cv2
import numpy as np
import json
import os
import easyocr
import re

IMAGE_PATH = "frontend/scheme.png"
OUTPUT_JSON = "data/network.json"

def detect_water_network():
    if not os.path.exists(IMAGE_PATH):
        print(f"Файл {IMAGE_PATH} не найден.")
        return

    print("1. Загрузка чертежа...")
    img = cv2.imread(IMAGE_PATH)
    height, width = img.shape[:2]
    print(f"Разрешение чертежа: {width} x {height}")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Строгая маска синего цвета трубопроводов и узлов
    lower_blue = np.array([95, 80, 80])
    upper_blue = np.array([130, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    print("2. Поиск узлов и гидрантов (фильтрация по контурам)...")
    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected_nodes = []
    idx = 1

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 40 <= area <= 1200:  # Истинный размер кружков колодцев и гидрантов
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            
            # Круглость контура (отсекаем прямые отрезки труб)
            if circularity > 0.6:
                (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                cx, cy = int(cx), int(cy)
                
                # В Leaflet CRS.Simple ось Y идет снизу вверх
                leaflet_y = height - cy
                node_type = "hydrant" if area > 250 else "well"

                detected_nodes.append({
                    "id": f"node_{idx}",
                    "name": f"{'ПГ' if node_type == 'hydrant' else 'к'}_{idx}",
                    "type": node_type,
                    "x": cx,
                    "y": leaflet_y,
                    "orig_y": cy
                })
                idx += 1

    print(f"Найдено реальных узлов: {len(detected_nodes)}")

    print("3. Распознавание подписей колодцев и арматуры...")
    reader = easyocr.Reader(['ru', 'en'], gpu=False)
    ocr_results = reader.readtext(gray, paragraph=False)

    for (bbox, text, prob) in ocr_results:
        clean_text = text.strip()
        if prob < 0.4:
            continue

        (tl, tr, br, bl) = bbox
        tx_center = int((tl[0] + br[0]) / 2)
        ty_center = int((tl[1] + br[1]) / 2)

        if re.search(r'^(к|k|K)\s*\d+', clean_text, re.IGNORECASE) or re.search(r'^(пг|п|г|pg)\s*\d+', clean_text, re.IGNORECASE):
            for node in detected_nodes:
                dist = np.hypot(node["x"] - tx_center, node["orig_y"] - ty_center)
                if dist < 60:
                    node["name"] = clean_text.replace(" ", "")
                    break

    for n in detected_nodes:
        n.pop("orig_y", None)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    payload = {
        "dimensions": {"width": width, "height": height},
        "nodes": detected_nodes, 
        "pipes": [], 
        "valves": []
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Готово! Сохранено {len(detected_nodes)} узлов.")

if __name__ == "__main__":
    detect_water_network()
