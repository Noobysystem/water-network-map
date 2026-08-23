from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import shutil

app = FastAPI(title="Water Valves Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище вне зоны действия git
STORAGE_DIR = "storage"
DATA_FILE = os.path.join(STORAGE_DIR, "network.json")
BACKUP_FILE = os.path.join(STORAGE_DIR, "network.backup.json")
INIT_FILE = "data/network.json"

def get_data_path():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        if os.path.exists(INIT_FILE):
            shutil.copyfile(INIT_FILE, DATA_FILE)
        else:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"nodes": [], "dimensions": {"width": 14904, "height": 10528}}, f, ensure_ascii=False, indent=2)
    return DATA_FILE

def read_data():
    path = get_data_path()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_data(data):
    path = get_data_path()
    # Создаем резервную копию перед записью
    if os.path.exists(path):
        shutil.copyfile(path, BACKUP_FILE)
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

@app.get("/api/network")
def get_network():
    return read_data()

@app.post("/api/node")
def add_node(node: ValveNode):
    data = read_data()
    data.setdefault("nodes", []).append(node.dict())
    write_data(data)
    return {"status": "ok", "node": node}

@app.put("/api/node/{node_id}")
def update_node(node_id: str, updated_node: ValveNode):
    data = read_data()
    for i, n in enumerate(data.get("nodes", [])):
        if n["id"] == node_id:
            data["nodes"][i] = updated_node.dict()
            write_data(data)
            return {"status": "ok", "node": updated_node}
    raise HTTPException(status_code=404, detail="Объект не найден")

@app.delete("/api/node/{node_id}")
def delete_node(node_id: str):
    data = read_data()
    data["nodes"] = [n for n in data.get("nodes", []) if n["id"] != node_id]
    write_data(data)
    return {"status": "ok"}

# Скачивание файла базы данных
@app.get("/api/export")
def export_database():
    path = get_data_path()
    return FileResponse(path, media_type="application/json", filename="valves_backup.json")

# Загрузка резервной копии из браузера
@app.post("/api/import")
async def import_database(file: UploadFile = File(...)):
    content = await file.read()
    data = json.loads(content.decode("utf-8"))
    write_data(data)
    return {"status": "ok", "count": len(data.get("nodes", []))}

if os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
elif os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
