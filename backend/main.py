from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="Water Network Interactive Map")

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

class Node(BaseModel):
    id: str
    name: str
    type: str
    x: float
    y: float

class Pipe(BaseModel):
    id: str
    from_node: str
    to_node: str
    diameter: int
    material: str
    path: List[List[float]]

@app.get("/api/network")
def get_network():
    return read_data()

@app.post("/api/node")
def add_node(node: Node):
    data = read_data()
    data.setdefault("nodes", []).append(node.dict())
    write_data(data)
    return {"status": "ok", "node": node}

@app.post("/api/pipe")
def add_pipe(pipe: Pipe):
    data = read_data()
    data.setdefault("pipes", []).append(pipe.dict())
    write_data(data)
    return {"status": "ok", "pipe": pipe}

# Монтируем отдачу статики (HTML, JS, Scheme.png)
if os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
elif os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
