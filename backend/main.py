from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import json
import os

app = FastAPI(title="Water Network Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "/data/network.json" if os.path.exists("/data") else "data/network.json"

def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        default_data = {"nodes": [], "valves": [], "pipes": []}
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: dict):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.get("/api/network")
def get_network():
    return load_data()

@app.post("/api/node")
def add_node(node: Dict[str, Any]):
    data = load_data()
    data["nodes"].append(node)
    save_data(data)
    return {"status": "ok", "node": node}

@app.post("/api/pipe")
def add_pipe(pipe: Dict[str, Any]):
    data = load_data()
    data["pipes"].append(pipe)
    save_data(data)
    return {"status": "ok", "pipe": pipe}

@app.delete("/api/node/{node_id}")
def delete_node(node_id: str):
    data = load_data()
    data["nodes"] = [n for n in data["nodes"] if n.get("id") != node_id]
    data["pipes"] = [p for p in data["pipes"] if p.get("from_node") != node_id and p.get("to_node") != node_id]
    save_data(data)
    return {"status": "ok"}
