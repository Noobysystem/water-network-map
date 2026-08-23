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

    print("1. Загрузка чертежа 15K...")
    img = cv2.imread(IMAGE_PATH)
    height, width = img.shape[:2]
    print(f"Разрешение: {width} x {height}")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Широкий диапазон синего цвета для любых оттенков чертежа
    lower_blue = np.array([80, 30, 30])
    upper_blue = np.array([140, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Морфологическое сглаживание для объединения разорванных кружков
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    cleaned_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)

    print("2. Поиск узловых точек и колодцев...")
    contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    detected_nodes = []
    idx = 1

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Диапазон площади кружков колодцев и арматуры на 15K разрешении
        if 80 <= area <= 60000:
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            
            # Если объект округлой формы
            if circularity > 0.35:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Проверка минимальной дистанции от уже найденных точек
                    too_close = False
                    for existing in detected_nodes:
                        if np.hypot(existing["x"] - cx, (height - existing["y"]) - cy) < 40:
                            too_close = True
                            break
                    if too_close:
                        continue

                    leaflet_y = height - cy
                    node_type = "hydrant" if area > 6000 else "well"

                    detected_nodes.append({
                        "id": f"node_{idx}",
                        "name": f"{'ПГ' if node_type == 'hydrant' else 'к'}_{idx}",
                        "type": node_type,
                        "x": cx,
                        "y": leaflet_y,
                        "orig_y": cy
                    })
                    idx += 1

    print(f"Найдено объектов сети: {len(detected_nodes)}")

    print("3. Распознавание подписей (OCR)...")
    reader = easyocr.Reader(['ru', 'en'], gpu=False)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ocr_results = reader.readtext(gray, paragraph=False)

    for (bbox, text, prob) in ocr_results:
        clean_text = text.strip()
        if prob < 0.3:
            continue

        (tl, tr, br, bl) = bbox
        tx_center = int((tl[0] + br[0]) / 2)
        ty_center = int((tl[1] + br[1]) / 2)

        if re.search(r'^(к|k|K|пг|pg)\s*\d+', clean_text, re.IGNORECASE):
            for node in detected_nodes:
                dist = np.hypot(node["x"] - tx_center, node["orig_y"] - ty_center)
                if dist < 220:
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

    print(f"Успешно сохранено {len(detected_nodes)} объектов в {OUTPUT_JSON}")

if __name__ == "__main__":
    detect_water_network()
