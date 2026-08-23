from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import shutil

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

NETWORKS = {
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
    }
}

def init_storage():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    drinking_storage = os.path.join(STORAGE_DIR, "drinking.json")
    
    source_json = os.path.join(DATA_DIR, "network.json")
    if (not os.path.exists(drinking_storage) or os.path.getsize(drinking_storage) < 50) and os.path.exists(source_json):
        shutil.copyfile(source_json, drinking_storage)
    elif not os.path.exists(drinking_storage):
        with open(drinking_storage, "w", encoding="utf-8") as f:
            json.dump({"nodes": [], "dimensions": NETWORKS["drinking"]["dimensions"]}, f, ensure_ascii=False, indent=2)

    tech_storage = os.path.join(STORAGE_DIR, "tech_water.json")
    tech_source = os.path.join(DATA_DIR, "tech_water.json")
    if (not os.path.exists(tech_storage) or os.path.getsize(tech_storage) < 50) and os.path.exists(tech_source):
        shutil.copyfile(tech_source, tech_storage)
    elif not os.path.exists(tech_storage):
        with open(tech_storage, "w", encoding="utf-8") as f:
            json.dump({"nodes": [], "dimensions": NETWORKS["tech_water"]["dimensions"]}, f, ensure_ascii=False, indent=2)

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
def get_networks():
    return list(NETWORKS.values())

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

if os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
elif os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
