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
        print(f"Ошибка: Файл {IMAGE_PATH} не найден.")
        return

    print("1. Загрузка изображения схемы...")
    img = cv2.imread(IMAGE_PATH)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Выделение синего цвета (трубы, узлы, гидранты)
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([135, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    print("2. Поиск узлов и колодцев (Hough Circles)...")
    # Поиск круглых узлов арматуры и колодцев
    circles = cv2.HoughCircles(
        blue_mask, 
        cv2.HOUGH_GRADIENT, 
        dp=1.2, 
        minDist=20, 
        param1=50, 
        param2=12, 
        minRadius=6, 
        maxRadius=22
    )

    detected_nodes = []
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for i, c in enumerate(circles[0, :]):
            cx, cy, r = int(c[0]), int(c[1]), int(c[2])
            node_type = "hydrant" if r >= 13 else "well"
            detected_nodes.append({
                "id": f"node_auto_{i+1}",
                "name": f"{'ПГ' if node_type == 'hydrant' else 'к'}_{i+1}",
                "type": node_type,
                "x": cx,
                "y": cy,
                "radius": r
            })

    print(f"Обнаружено узлов: {len(detected_nodes)}")

    print("3. Распознавание подписей (OCR)...")
    reader = easyocr.Reader(['ru', 'en'], gpu=False)
    # Считываем текст со схемы
    ocr_results = reader.readtext(gray, paragraph=False)

    print("4. Сопоставление текстовых меток с ближайшими узлами...")
    for (bbox, text, prob) in ocr_results:
        clean_text = text.strip()
        if prob < 0.4:
            continue

        # Координаты центра распознанного текста
        (tl, tr, br, bl) = bbox
        tx_center = int((tl[0] + br[0]) / 2)
        ty_center = int((tl[1] + br[1]) / 2)

        # Ищем совпадения по маскам: к12, ПГ 101, номер арматуры
        if re.search(r'^(к|k|K)\s*\d+', clean_text, re.IGNORECASE) or re.search(r'^(пг|п|г|pg)\s*\d+', clean_text, re.IGNORECASE):
            for node in detected_nodes:
                dist = np.hypot(node["x"] - tx_center, node["y"] - ty_center)
                if dist < 65:  # Текст находится рядом с узлом
                    node["name"] = clean_text.replace(" ", "")
                    break

    # Формируем итоговый JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    
    # Сохраняем существующие трубы, если были
    existing_data = {"nodes": [], "valves": [], "pipes": []}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except:
            pass

    existing_data["nodes"] = detected_nodes

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)

    print(f"Готово! Данные сохранены в {OUTPUT_JSON}")

if __name__ == "__main__":
    detect_water_network()
