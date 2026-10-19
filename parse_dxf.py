import ezdxf
import json
import re
import os
import sys

# Настройки целевого разрешения картинки в приложении (для ПВ: 14904 x 10528)
TARGET_WIDTH = 14904
TARGET_HEIGHT = 10528

def clean_kompas_text(raw_text):
    """Очищает текст от управляющих кодов форматирования КОМПАС/AutoCAD (\H5.0;\W1.000; и т.д.)"""
    if not raw_text:
        return ""
    # Удаляем управляющие последовательности вида \H...; \W...; \Q...; \A...;
    cleaned = re.sub(r'\\[A-Za-z0-9\.,]+;', '', raw_text)
    # Удаляем фигурные скобки и переносы строк \P
    cleaned = cleaned.replace('\\P', ' ').replace('{', '').replace('}', '')
    return cleaned.strip()

def classify_text(text):
    """Определяет тип объекта по тексту подписи на чертеже"""
    t_upper = text.upper()
    
    # 1. Пожарные гидранты
    if re.match(r'^(ПГ|Г)\s*[-№]?\s*\d+', t_upper) or 'ГИДРАНТ' in t_upper:
        return "hydrant", text
        
    # 2. Водопроводные камеры / колодцы (ВК, К)
    if re.match(r'^(ВК|К)\s*[-№]?\s*\d+', t_upper):
        return "valve", text
        
    # 3. Номера задвижек (числа от 1 до 999, возможно с буквой: 157, 19б, 27в, 55с)
    # Исключаем диаметры и давления
    if re.match(r'^\d{1,3}[а-яА-Яa-zA-Z]?$', text):
        return "valve", text
        
    return None, text

def parse_dxf_to_json(dxf_path, output_json, img_w=TARGET_WIDTH, img_h=TARGET_HEIGHT):
    if not os.path.exists(dxf_path):
        print(f"Файл не найден: {dxf_path}")
        return

    print(f"Чтение чертежа: {dxf_path}...")
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Получаем габариты чертежа из заголовка DXF ($EXTMIN / $EXTMAX)
    extmin = doc.header.get('$EXTMIN', (0, 0, 0))
    extmax = doc.header.get('$EXTMAX', (850.925, 594.0, 0))
    
    min_x, min_y = extmin[0], extmin[1]
    max_x, max_y = extmax[0], extmax[1]
    
    dxf_width = max_x - min_x
    dxf_height = max_y - min_y
    print(f"Габариты чертежа DXF: {dxf_width:.2f} x {dxf_height:.2f} мм")

    def to_pixel_coords(x, y):
        """Переводит миллиметры чертежа в пиксели Leaflet"""
        px = ((x - min_x) / dxf_width) * img_w
        py = ((y - min_y) / dxf_height) * img_h
        return round(px, 1), round(py, 1)

    extracted_items = []

    # 1. Собираем все тексты из пространства модели (TEXT и MTEXT)
    for entity in msp.query('TEXT MTEXT'):
        raw = entity.dxf.text if entity.dxftype() == 'TEXT' else entity.text
        text = clean_kompas_text(raw)
        if text:
            pos = entity.dxf.insert
            extracted_items.append((text, pos.x, pos.y))

    # 2. Собираем тексты внутри блоков (INSERT), которые создал КОМПАС
    for insert in msp.query('INSERT'):
        block_name = insert.dxf.name
        if block_name not in doc.blocks:
            continue
        block = doc.blocks[block_name]
        ins_x, ins_y = insert.dxf.insert.x, insert.dxf.insert.y
        
        # Склеиваем многострочные подписи внутри одного блока (например, Т1 -> "ЦСП склад № 7")
        block_texts = []
        bx, by = None, None
        for e in block:
            if e.dxftype() in ('TEXT', 'MTEXT'):
                raw = e.dxf.text if e.dxftype() == 'TEXT' else e.text
                t = clean_kompas_text(raw)
                if t:
                    block_texts.append(t)
                    if bx is None:
                        bx = ins_x + e.dxf.insert.x
                        by = ins_y + e.dxf.insert.y
        if block_texts and bx is not None:
            full_text = " ".join(block_texts)
            extracted_items.append((full_text, bx, by))

    nodes = []
    buildings = []
    seen_coords = set()

    for idx, (text, x, y) in enumerate(extracted_items):
        px, py = to_pixel_coords(x, y)
        
        # Защита от полных дубликатов в одной точке
        coord_key = (text, round(px, -1), round(py, -1))
        if coord_key in seen_coords:
            continue
        seen_coords.add(coord_key)

        obj_type, clean_name = classify_text(text)
        
        if obj_type:
            nodes.append({
                "id": f"dxf_node_{idx}",
                "name": clean_name,
                "type": obj_type,
                "x": px,
                "y": py,
                "status": "open",
                "diameter": 150,
                "description": "Извлечено из чертежа КОМПАС"
            })
        else:
            buildings.append({
                "name": clean_name,
                "x": px,
                "y": py
            })

    result = {
        "nodes": nodes,
        "dimensions": {"width": img_w, "height": img_h}
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Дополнительно сохраняем список всех подписей (цеха, диаметры) для справки
    with open("data/dxf_all_labels.json", "w", encoding="utf-8") as f:
        json.dump(buildings, f, ensure_ascii=False, indent=2)

    print(f"Готово! Найдено задвижек/гидрантов/ВК: {len(nodes)}")
    print(f"Найдено прочих подписей (цеха, трубы): {len(buildings)}")
    print(f"База сохранена в: {output_json}")

if __name__ == "__main__":
    # Ищем первый попавшийся .dxf файл в папке или берем из аргумента
    dxf_files = [f for f in os.listdir(".") if f.lower().endswith(".dxf")]
    if len(sys.argv) > 1:
        target_dxf = sys.argv[1]
    elif dxf_files:
        target_dxf = dxf_files[0]
    else:
        print("Положите файл .dxf в папку water-network и запустите скрипт снова!")
        sys.exit(1)

    parse_dxf_to_json(target_dxf, "data/dxf_extracted_nodes.json")
