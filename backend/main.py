from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import shutil
import re
from PIL import Image

app = FastAPI(title="Схемы ЭНЦ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = "storage"
DATA_DIR = "data"
FRONTEND_DIR = "../frontend" if os.path.exists("../frontend") else "frontend"
CONFIG_NETWORKS_FILE = os.path.join(DATA_DIR, "networks_registry.json")

DEFAULT_NETWORKS = {
    "drinking": {
        "id": "drinking",
        "title": "💧 ПВ",
        "image": "scheme.jpg",
        "dimensions": {"width": 14904, "height": 10528},
        "file": "drinking.json"
    },
    "tech_water": {
        "id": "tech_water",
        "title": "⚙️ ТВ пром",
        "image": "scheme_tv.jpg",
        "dimensions": {"width": 7445, "height": 5266},
        "file": "tech_water.json"
    },
    "tech_water_out": {
        "id": "tech_water_out",
        "title": "⚙️ ТВ внепром",
        "image": "scheme_tv_out.jpg",
        "dimensions": {"width": 7445, "height": 10528},
        "file": "tech_water_out.json"
    }
}

def load_networks():
    if os.path.exists(CONFIG_NETWORKS_FILE):
        try:
            with open(CONFIG_NETWORKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_NETWORKS.copy()

def save_networks(networks_dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_NETWORKS_FILE, "w", encoding="utf-8") as f:
        json.dump(networks_dict, f, ensure_ascii=False, indent=2)

NETWORKS = load_networks()

def init_storage():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    for net_id, cfg in NETWORKS.items():
        path = os.path.join(STORAGE_DIR, cfg["file"])
        if not os.path.exists(path):
            src = os.path.join(DATA_DIR, cfg["file"])
            if os.path.exists(src):
                shutil.copyfile(src, path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"nodes": [], "dimensions": cfg["dimensions"]}, f, ensure_ascii=False, indent=2)

init_storage()

def get_file_path(net_id: str):
    if net_id not in NETWORKS:
        raise HTTPException(status_code=404, detail="Схема не найдена")
    path = os.path.join(STORAGE_DIR, NETWORKS[net_id]["file"])
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"nodes": [], "dimensions": NETWORKS[net_id]["dimensions"]}, f, ensure_ascii=False, indent=2)
    return path

def read_data(net_id: str):
    path = get_file_path(net_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_data(net_id: str, data: dict):
    path = get_file_path(net_id)
    backup = path.replace(".json", ".backup.json")
    if os.path.exists(path):
        shutil.copyfile(path, backup)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    data_path = os.path.join(DATA_DIR, NETWORKS[net_id]["file"])
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class ValveNode(BaseModel):
    id: str
    name: str
    type: str
    x: float
    y: float
    status: Optional[str] = "open"
    description: Optional[str] = ""
    diameter: Optional[int] = 150

# Совместимость с двумя форматами API
@app.get("/api/networks")
@app.get("/api/schemes")
def get_networks():
    return list(NETWORKS.values())

@app.post("/api/schemes/upload")
async def upload_scheme(title: str = Form(...), file: UploadFile = File(...)):
    # Генерируем идентификатор
    raw_id = re.sub(r"[^\w\-]", "", title.lower().replace(" ", "_"), flags=re.UNICODE)
    scheme_id = raw_id if raw_id else f"scheme_{len(NETWORKS) + 1}"

    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    img_filename = f"scheme_{scheme_id}{ext}"
    target_img_path = os.path.join(FRONTEND_DIR, img_filename)

    # Сохраняем картинку подложки во frontend
    content = await file.read()
    with open(target_img_path, "wb") as f:
        f.write(content)

    # Измеряем точные размеры через Pillow
    try:
        with Image.open(target_img_path) as img:
            w, h = img.size
    except Exception:
        if os.path.exists(target_img_path):
            os.remove(target_img_path)
        raise HTTPException(status_code=400, detail="Неверный формат изображения")

    json_filename = f"{scheme_id}.json"
    NETWORKS[scheme_id] = {
        "id": scheme_id,
        "title": title,
        "image": img_filename,
        "dimensions": {"width": w, "height": h},
        "file": json_filename
    }

    # Инициализируем хранилище для новой схемы
    storage_path = os.path.join(STORAGE_DIR, json_filename)
    if not os.path.exists(storage_path):
        with open(storage_path, "w", encoding="utf-8") as f:
            json.dump({"nodes": [], "dimensions": {"width": w, "height": h}}, f, ensure_ascii=False, indent=2)

    save_networks(NETWORKS)
    return NETWORKS[scheme_id]

@app.get("/api/{net_id}/network")
def get_network(net_id: str):
    return read_data(net_id)

@app.post("/api/{net_id}/node")
def add_node(net_id: str, node: ValveNode):
    data = read_data(net_id)
    data.setdefault("nodes", []).append(node.dict())
    write_data(net_id, data)
    return {"status": "ok", "node": node}

@app.put("/api/{net_id}/node/{node_id}")
def update_node(net_id: str, node_id: str, updated_node: ValveNode):
    data = read_data(net_id)
    for i, n in enumerate(data.get("nodes", [])):
        if n["id"] == node_id:
            data["nodes"][i] = updated_node.dict()
            write_data(net_id, data)
            return {"status": "ok", "node": updated_node}
    raise HTTPException(status_code=404, detail="Объект не найден")

@app.delete("/api/{net_id}/node/{node_id}")
def delete_node(net_id: str, node_id: str):
    data = read_data(net_id)
    data["nodes"] = [n for n in data.get("nodes", []) if n["id"] != node_id]
    write_data(net_id, data)
    return {"status": "ok"}

@app.get("/api/{net_id}/export")
def export_database(net_id: str):
    path = get_file_path(net_id)
    return FileResponse(path, media_type="application/json", filename=f"{net_id}_valves_backup.json")

@app.post("/api/{net_id}/import")
async def import_database(net_id: str, file: UploadFile = File(...)):
    content = await file.read()
    data = json.loads(content.decode("utf-8"))
    write_data(net_id, data)
    return {"status": "ok", "count": len(data.get("nodes", []))}

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
