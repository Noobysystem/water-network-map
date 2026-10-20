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
import hashlib
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
        "icon": "💧",
        "image": "scheme.jpg",
        "dimensions": {"width": 14904, "height": 10528},
        "file": "drinking.json",
        "is_default": True
    },
    "tech_water": {
        "id": "tech_water",
        "title": "⚙️ ТВ пром",
        "icon": "⚙️",
        "image": "scheme_tv.jpg",
        "dimensions": {"width": 7445, "height": 5266},
        "file": "tech_water.json",
        "is_default": True
    },
    "tech_water_out": {
        "id": "tech_water_out",
        "title": "⚙️ ТВ внепром",
        "icon": "⚙️",
        "image": "scheme_tv_out.jpg",
        "dimensions": {"width": 7445, "height": 10528},
        "file": "tech_water_out.json",
        "is_default": True
    }
}

def load_networks():
    if os.path.exists(CONFIG_NETWORKS_FILE):
        try:
            with open(CONFIG_NETWORKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
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

@app.get("/api/networks")
@app.get("/api/schemes")
def get_networks():
    return list(NETWORKS.values())

@app.post("/api/schemes/upload")
async def upload_scheme(
    title: str = Form(...),
    icon: str = Form("💧"),
    file: UploadFile = File(...)
):
    # Генерируем уникальный английский ключ идентификатора
    hash_suffix = hashlib.md5(title.encode('utf-8')).hexdigest()[:6]
    ascii_clean = re.sub(r'[^a-zA-Z0-9_]', '', title.lower().replace(" ", "_"))
    scheme_id = f"sch_{ascii_clean}_{hash_suffix}" if ascii_clean else f"sch_{hash_suffix}"

    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    img_filename = f"{scheme_id}{ext}"
    
    # Сохраняем картинку непосредственно в директорию frontend
    target_img_path = os.path.join(FRONTEND_DIR, img_filename)

    content = await file.read()
    with open(target_img_path, "wb") as f:
        f.write(content)

    # Замеряем физические пиксели
    try:
        with Image.open(target_img_path) as img:
            w, h = img.size
    except Exception:
        if os.path.exists(target_img_path):
            os.remove(target_img_path)
        raise HTTPException(status_code=400, detail="Неверный формат изображения")

    json_filename = f"{scheme_id}.json"
    full_title = f"{icon} {title}".strip()

    entry = {
        "id": scheme_id,
        "title": full_title,
        "raw_title": title,
        "icon": icon,
        "image": img_filename,
        "dimensions": {"width": w, "height": h},
        "file": json_filename,
        "is_default": False
    }

    NETWORKS[scheme_id] = entry

    # Инициализируем файл для узлов
    storage_path = os.path.join(STORAGE_DIR, json_filename)
    if not os.path.exists(storage_path):
        with open(storage_path, "w", encoding="utf-8") as f:
            json.dump({"nodes": [], "dimensions": {"width": w, "height": h}}, f, ensure_ascii=False, indent=2)

    save_networks(NETWORKS)
    return entry

@app.delete("/api/schemes/{scheme_id}")
def delete_scheme(scheme_id: str):
    if scheme_id not in NETWORKS:
        raise HTTPException(status_code=404, detail="Схема не найдена")
    if NETWORKS[scheme_id].get("is_default"):
        raise HTTPException(status_code=400, detail="Базовые схемы удалять нельзя")

    cfg = NETWORKS.pop(scheme_id)
    save_networks(NETWORKS)

    # Удаляем картинку
    img_path = os.path.join(FRONTEND_DIR, cfg.get("image", ""))
    if os.path.exists(img_path):
        try: os.remove(img_path)
        except Exception: pass

    # Удаляем файлы узлов
    for folder in [STORAGE_DIR, DATA_DIR]:
        f_path = os.path.join(folder, cfg.get("file", ""))
        if os.path.exists(f_path):
            try: os.remove(f_path)
            except Exception: pass

    return {"status": "ok", "deleted": scheme_id}

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
