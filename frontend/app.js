const API_URL = "/api";

let map;
let networkData = { nodes: [], pipes: [], valves: [], dimensions: { width: 4961, height: 3508 } };
let nodesLayer, pipesLayer;
let pipeBuffer = [];

async function initApp() {
    try {
        const res = await fetch(`${API_URL}/network`);
        if (res.ok) {
            networkData = await res.json();
        }
    } catch (e) {
        console.error("Ошибка загрузки API:", e);
    }

    const width = networkData.dimensions?.width || 4961;
    const height = networkData.dimensions?.height || 3508;
    const bounds = [[0, 0], [height, width]];

    map = L.map("map", {
        crs: L.CRS.Simple,
        minZoom: -4,
        maxZoom: 3,
        zoomSnap: 0.1
    });

    L.imageOverlay("scheme.png", bounds).addTo(map);
    map.fitBounds(bounds);

    nodesLayer = L.layerGroup().addTo(map);
    pipesLayer = L.layerGroup().addTo(map);

    setTimeout(() => {
        map.invalidateSize();
        map.fitBounds(bounds);
    }, 250);

    renderNetwork();

    map.on("click", handleMapClick);
}

function renderNetwork() {
    nodesLayer.clearLayers();
    pipesLayer.clearLayers();

    (networkData.pipes || []).forEach(pipe => {
        const polyline = L.polyline(pipe.path, {
            color: pipe.material === "пэ" ? "#0077ff" : "#00aa55",
            weight: 4
        }).addTo(pipesLayer);
        polyline.on("click", () => showInfo("Трубопровод", pipe));
    });

    (networkData.nodes || []).forEach(node => {
        const marker = L.circleMarker([node.y, node.x], {
            radius: node.type === "hydrant" ? 7 : 5,
            color: node.type === "hydrant" ? "#ff3333" : "#0066ff",
            fillColor: node.type === "hydrant" ? "#ff6666" : "#66b3ff",
            fillOpacity: 0.9,
            weight: 2
        }).addTo(nodesLayer);

        marker.bindTooltip(node.name, { permanent: false, direction: "top" });
        marker.on("click", (e) => {
            L.DomEvent.stopPropagation(e);
            handleNodeClick(node);
        });
    });

    document.getElementById("count-nodes").innerText = (networkData.nodes || []).length;
    document.getElementById("count-pipes").innerText = (networkData.pipes || []).length;
}

function handleNodeClick(node) {
    const mode = document.querySelector('input[name="mode"]:checked').value;
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
        <h3 style="margin-top:0">${type}: ${data.name || data.id}</h3>
        <pre style="white-space:pre-wrap;word-break:break-all;">${JSON.stringify(data, null, 2)}</pre>
    `;
}

async function handleMapClick(e) {
    const mode = document.querySelector('input[name="mode"]:checked').value;
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
        
        networkData.nodes.push(newNode);
        renderNetwork();
    }
}

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
    
    networkData.pipes.push(newPipe);
    renderNetwork();
}

initApp();
