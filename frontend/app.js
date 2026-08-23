const API_URL = "http://localhost:8000/api";

const map = L.map("map", {
    crs: L.CRS.Simple,
    minZoom: -3,
    maxZoom: 2
});

const imgWidth = 7016; 
const imgHeight = 4960;
const bounds = [[0, 0], [imgHeight, imgWidth]];

const image = L.imageOverlay("scheme.png", bounds).addTo(map);
map.fitBounds(bounds);

let networkData = { nodes: [], pipes: [], valves: [] };
let pipeBuffer = [];

const nodesLayer = L.layerGroup().addTo(map);
const pipesLayer = L.layerGroup().addTo(map);

async function loadNetwork() {
    try {
        const res = await fetch(`${API_URL}/network`);
        networkData = await res.json();
        renderNetwork();
    } catch (e) {
        console.error("Ошибка загрузки данных:", e);
    }
}

function renderNetwork() {
    nodesLayer.clearLayers();
    pipesLayer.clearLayers();

    networkData.pipes.forEach(pipe => {
        const polyline = L.polyline(pipe.path, {
            color: pipe.material === "пэ" ? "#0077ff" : "#00aa55",
            weight: 4
        }).addTo(pipesLayer);
        
        polyline.on("click", () => showInfo("Трубопровод", pipe));
    });

    networkData.nodes.forEach(node => {
        const marker = L.circleMarker([node.y, node.x], {
            radius: node.type === "hydrant" ? 8 : 6,
            color: node.type === "hydrant" ? "#ff3333" : "#3388ff",
            fillOpacity: 0.8
        }).addTo(nodesLayer);

        marker.bindTooltip(node.name, { permanent: false });
        marker.on("click", (e) => {
            L.DomEvent.stopPropagation(e);
            handleNodeClick(node);
        });
    });

    document.getElementById("count-nodes").innerText = networkData.nodes.length;
    document.getElementById("count-pipes").innerText = networkData.pipes.length;
}

function handleNodeClick(node) {
    const mode = document.querySelector("input[name=\"mode\"]:checked").value;
    
    if (mode === "add_pipe") {
        pipeBuffer.push(node);
        if (pipeBuffer.length === 2) {
            createPipe(pipeBuffer[0], pipeBuffer[1]);
            pipeBuffer = [];
        }
    } else {
        showInfo(node.type === "hydrant" ? "Пожарный гидрант" : "Колодец", node);
    }
}

function showInfo(type, data) {
    const inspector = document.getElementById("inspector");
    inspector.innerHTML = `
        <h3>${type}: ${data.name || data.id}</h3>
        <pre>${JSON.stringify(data, null, 2)}</pre>
    `;
}

map.on("click", async (e) => {
    const mode = document.querySelector("input[name=\"mode\"]:checked").value;
    const y = Math.round(e.latlng.lat);
    const x = Math.round(e.latlng.lng);

    if (mode === "add_node" || mode === "add_hydrant") {
        const name = prompt(mode === "add_hydrant" ? "Номер гидранта (например, ПГ 101):" : "Номер колодца (например, к73):");
        if (!name) return;

        const newNode = {
            id: "node_" + Date.now(),
            name: name,
            type: mode === "add_hydrant" ? "hydrant" : "well",
            x: x,
            y: y
        };

        await fetch(`${API_URL}/node`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newNode)
        });
        loadNetwork();
    }
});

async function createPipe(nodeA, nodeB) {
    const diameter = prompt("Диаметр трубы (Ду):", "200");
    const material = prompt("Материал (чуг, ст, пэ):", "чуг");

    const newPipe = {
        id: "pipe_" + Date.now(),
        from_node: nodeA.id,
        to_node: nodeB.id,
        diameter: parseInt(diameter) || 200,
        material: material || "чуг",
        path: [[nodeA.y, nodeA.x], [nodeB.y, nodeB.x]]
    };

    await fetch(`${API_URL}/pipe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newPipe)
    });
    loadNetwork();
}

loadNetwork();
