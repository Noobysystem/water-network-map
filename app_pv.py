import os
import json
import re
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image

app = FastAPI(title="TMK Water Network App")

DATA_DIR = "data"
SCHEMES_DIR = os.path.join(DATA_DIR, "schemes")
SCHEMES_FILE = os.path.join(DATA_DIR, "schemes.json")
os.makedirs(SCHEMES_DIR, exist_ok=True)

# Инициализация схемы по умолчанию (ПВ)
if not os.path.exists(SCHEMES_FILE):
    pv_dir = os.path.join(SCHEMES_DIR, "pv")
    os.makedirs(pv_dir, exist_ok=True)
    initial_schemes = [
        {
            "id": "pv",
            "title": "ПВ",
            "image": "/data/schemes/pv/background.jpg",
            "width": 14904,
            "height": 10528,
            "dataFile": "/api/drinking/network"
        }
    ]
    with open(SCHEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(initial_schemes, f, ensure_ascii=False, indent=2)

VECTOR_FILE = os.path.join(DATA_DIR, "dxf_vector_network.json")

@app.get("/api/drinking/network")
def get_network():
    if os.path.exists(VECTOR_FILE):
        with open(VECTOR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nodes": [], "pipes": [], "dimensions": {"width": 14904, "height": 10528}}

@app.get("/api/schemes")
def get_schemes():
    if os.path.exists(SCHEMES_FILE):
        with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.post("/api/schemes/upload")
async def upload_scheme(title: str = Form(...), file: UploadFile = File(...)):
    scheme_id = re.sub(r'[^a-zA-Z0-9_]', '', title.lower().replace(" ", "_"))
    if not scheme_id:
        scheme_id = f"scheme_{len(get_schemes()) + 1}"

    target_dir = os.path.join(SCHEMES_DIR, scheme_id)
    os.makedirs(target_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    bg_name = f"background{ext}"
    bg_path = os.path.join(target_dir, bg_name)

    content = await file.read()
    with open(bg_path, "wb") as f:
        f.write(content)

    try:
        with Image.open(bg_path) as img:
            w, h = img.size
    except Exception:
        if os.path.exists(bg_path):
            os.remove(bg_path)
        raise HTTPException(status_code=400, detail="Неверный формат изображения")

    nodes_file = os.path.join(target_dir, "nodes.json")
    if not os.path.exists(nodes_file):
        with open(nodes_file, "w", encoding="utf-8") as f:
            json.dump({"nodes": [], "pipes": [], "dimensions": {"width": w, "height": h}}, f)

    schemes = get_schemes()
    new_entry = {
        "id": scheme_id,
        "title": title,
        "image": f"/data/schemes/{scheme_id}/{bg_name}",
        "width": w,
        "height": h,
        "dataFile": f"/api/schemes/{scheme_id}/network"
    }
    schemes.append(new_entry)

    with open(SCHEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(schemes, f, ensure_ascii=False, indent=2)

    return new_entry

@app.get("/api/schemes/{scheme_id}/network")
def get_scheme_network(scheme_id: str):
    nodes_file = os.path.join(SCHEMES_DIR, scheme_id, "nodes.json")
    if os.path.exists(nodes_file):
        with open(nodes_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nodes": [], "pipes": []}

app.mount("/data", StaticFiles(directory="data"), name="data")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
