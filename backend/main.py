from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import shutil

app = FastAPI(title="Схемы ЭНЦ - Информационная система")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = "storage"
NETWORKS_CONFIG = {
    "drinking": {
        "id": "drinking",
        "title": "💧 Питьевой водопровод (ХПВ)",
        "image": "scheme.jpg",
        "dimensions": {"width": 14904, "height": 10528},
        "file": "drinking.json"
    },
    "tech_water": {
        "id": "tech_water",
        "title": "⚙️ Технический водопровод (ТВ)",
        "image": "scheme_tv.jpg",
        "dimensions": {"width": 7445, "height": 5266},
        "file": "tech_water.json"
    }
}

def migrate_legacy_storage():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    old_file = os.path.join(STORAGE_DIR, "network.json")
    drinking_file = os.path.join(STORAGE_DIR, "drinking.json")
    
    if os.path.exists(old_file) and not os.path.exists(drinking_file):
        shutil.copyfile(old_file, drinking_file)
    elif not os.path.exists(drinking_file):
        init_file = "data/network.json"
        if os.path.exists(init_file):
            shutil.copyfile(init_file, drinking_file)
        else:
            with open(drinking_file, "w", encoding="utf-8") as f:
                json.dump({"nodes": [], "dimensions": NETWORKS_CONFIG["drinking"]["dimensions"]}, f, ensure_ascii=False, indent=2)

migrate_legacy_storage()

def get_network_path(net_id: str):
    if net_id not in NETWORKS_CONFIG:
        raise HTTPException(status_code=404, detail="Схема не найдена")
    
    os.makedirs(STORAGE_DIR, exist_ok=True)
    filename = NETWORKS_CONFIG[net_id]["file"]
    filepath = os.path.join(STORAGE_DIR, filename)

    if not os.path.exists(filepath):
        dims = NETWORKS_CONFIG[net_id]["dimensions"]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"nodes": [], "dimensions": dims}, f, ensure_ascii=False, indent=2)
            
    return filepath

def read_network_data(net_id: str):
    path = get_network_path(net_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_network_data(net_id: str, data: dict):
    path = get_network_path(net_id)
    backup = path.replace(".json", ".backup.json")
    if os.path.exists(path):
        shutil.copyfile(path, backup)
    with open(path, "w", encoding="utf-8") as f:
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
def list_networks():
    return list(NETWORKS_CONFIG.values())

@app.get("/api/{net_id}/network")
def get_network(net_id: str):
    return read_network_data(net_id)

@app.post("/api/{net_id}/node")
def add_node(net_id: str, node: ValveNode):
    data = read_network_data(net_id)
    data.setdefault("nodes", []).append(node.dict())
    write_network_data(net_id, data)
    return {"status": "ok", "node": node}

@app.put("/api/{net_id}/node/{node_id}")
def update_node(net_id: str, node_id: str, updated_node: ValveNode):
    data = read_network_data(net_id)
    for i, n in enumerate(data.get("nodes", [])):
        if n["id"] == node_id:
            data["nodes"][i] = updated_node.dict()
            write_network_data(net_id, data)
            return {"status": "ok", "node": updated_node}
    raise HTTPException(status_code=404, detail="Объект не найден")

@app.delete("/api/{net_id}/node/{node_id}")
def delete_node(net_id: str, node_id: str):
    data = read_network_data(net_id)
    data["nodes"] = [n for n in data.get("nodes", []) if n["id"] != node_id]
    write_network_data(net_id, data)
    return {"status": "ok"}

@app.get("/api/{net_id}/export")
def export_database(net_id: str):
    path = get_network_path(net_id)
    return FileResponse(path, media_type="application/json", filename=f"{net_id}_valves_backup.json")

@app.post("/api/{net_id}/import")
async def import_database(net_id: str, file: UploadFile = File(...)):
    content = await file.read()
    data = json.loads(content.decode("utf-8"))
    write_network_data(net_id, data)
    return {"status": "ok", "count": len(data.get("nodes", []))}

if os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
elif os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
