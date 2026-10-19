import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="TMK Water Network Vector App")

os.makedirs("data", exist_ok=True)
DB_FILE = "data/drinking_network.json"
VECTOR_FILE = "data/dxf_vector_network.json"

@app.get("/api/drinking/network")
def get_network():
    # Если есть векторный файл из DXF, отдаем его вместе с узлами
    if os.path.exists(VECTOR_FILE):
        with open(VECTOR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nodes": [], "pipes": [], "dimensions": {"width": 9946, "height": 7029}}

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
