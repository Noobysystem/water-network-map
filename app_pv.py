import webview
import json
import os
import sys

# Определение путей к ресурсам внутри .exe и снаружи
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    DATA_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR

DB_PATH = os.path.join(DATA_DIR, "pv_database.json")
INITIAL_DB = os.path.join(BASE_DIR, "data", "network.json")

class Api:
    def get_data(self):
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        elif os.path.exists(INITIAL_DB):
            with open(INITIAL_DB, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.save_data(data)
                return data
        return {"nodes": [], "dimensions": {"width": 14904, "height": 10528}}

    def save_node(self, node):
        data = self.get_data()
        nodes = data.get("nodes", [])
        updated = False
        for i, n in enumerate(nodes):
            if n["id"] == node["id"]:
                nodes[i] = node
                updated = True
                break
        if not updated:
            nodes.append(node)
        data["nodes"] = nodes
        self.save_data(data)
        return {"status": "ok"}

    def delete_node(self, node_id):
        data = self.get_data()
        data["nodes"] = [n for n in data.get("nodes", []) if n["id"] != node_id]
        self.save_data(data)
        return {"status": "ok"}

    def save_data(self, data):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    api = Api()
    html_path = os.path.join(BASE_DIR, "frontend", "index_pv.html")
    window = webview.create_window(
        title="Схема ПВ — Энергоцех",
        url=html_path,
        js_api=api,
        width=1280,
        height=850,
        min_size=(900, 600)
    )
    webview.start()

if __name__ == "__main__":
    main()
