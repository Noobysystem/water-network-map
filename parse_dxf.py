import os
import json
import ezdxf

def parse_water_dxf(dxf_path):
    if not os.path.exists(dxf_path):
        print(f"Файл {dxf_path} не найден!")
        return
    
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    
    nodes = []
    pipes = []
    
    # Извлекаем узлы, задвижки, гидранты (вставки блоков или тексты/точки)
    for insert in msp.query('INSERT'):
        name = insert.dxf.name
        pos = insert.dxf.insert
        nodes.append({
            "id": f"node_{len(nodes)+1}",
            "name": name,
            "type": "valve",
            "status": "open",
            "x": float(pos.x),
            "y": float(pos.y)
        })
        
    # Извлекаем линии трубопроводов (LINE)
    for line in msp.query('LINE'):
        start = line.dxf.start
        end = line.dxf.end
        pipes.append({
            "coordinates": [[float(start.y), float(start.x)], [float(end.y), float(end.x)]],
            "diameter": 150
        })
        
    # Извлекаем полилинии (LWPOLYLINE)
    for pline in msp.query('LWPOLYLINE'):
        points = []
        for p in pline.get_points('xy'):
            points.append([float(p[1]), float(p[0])]) # Превращаем в формат Leaflet [lat, lng] / [y, x]
        if len(points) > 1:
            pipes.append({
                "coordinates": points,
                "diameter": 150
            })

    output_data = {
        "nodes": nodes,
        "pipes": pipes,
        "dimensions": {"width": 9946, "height": 7029}
    }
    
    os.makedirs("data", exist_ok=True)
    with open("data/dxf_vector_network.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"Успешно извлечено: труб - {len(pipes)}, узлов - {len(nodes)}")

if __name__ == "__main__":
    # Укажите ваш DXF файл схемы ПВ
    dxf_files = [f for f in os.listdir("frontend") if f.endswith(".dxf")]
    if dxf_files:
        parse_water_dxf(os.path.join("frontend", dxf_files[0]))
    else:
        print("DXF файл не найден в папке frontend. Положите его туда.")
