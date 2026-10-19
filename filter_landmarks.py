import json
import re

with open("data/dxf_all_labels.json", "r", encoding="utf-8") as f:
    raw_labels = json.load(f)

clean_landmarks = []
seen = set()

for item in raw_labels:
    name = item["name"].strip()
    if len(name) < 3:
        continue
    if re.match(r'^(чуг|ст|пэ|пол|ду|dy|d|l=|к\d+|в\d+)\b', name.lower()):
        continue
    if re.match(r'^\d+([.,]\d+)?$', name):
        continue
        
    key = (name.lower(), round(item["x"], -2), round(item["y"], -2))
    if key not in seen:
        seen.add(key)
        clean_landmarks.append({
            "name": name,
            "x": item["x"],
            "y": item["y"]
        })

with open("frontend/landmarks_pv.json", "w", encoding="utf-8") as f:
    json.dump(clean_landmarks, f, ensure_ascii=False, indent=2)

print(f"Отфильтровано чистых названий цехов и объектов: {len(clean_landmarks)}")
