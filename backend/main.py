from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="Water Valves & Hydrants Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "data/network.json"

def read_data():
    if not os.path.exists(DATA_FILE):
        return {"nodes": [], "pipes": [], "valves": [], "dimensions": {"width": 14904, "height": 10528}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def write_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class ValveNode(BaseModel):
    id: str
    name: str
    type: str  # "valve" или "hydrant"
    x: float
    y: float
    status: Optional[str] = "open"  # "open", "closed", "no_cheeks", "jammed_closed", "hard_turn"
    description: Optional[str] = ""  # Текстовые примечания и дефекты
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

if os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
elif os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
