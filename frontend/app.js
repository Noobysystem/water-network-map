const API_URL = "/api";

let map;
let networkData = { nodes: [], pipes: [], valves: [], dimensions: { width: 14904, height: 10528 } };
let nodesLayer, pipesLayer;
let pipeBuffer = [];
let selectedNode = null;

async function initApp() {
    try {
        const res = await fetch(`${API_URL}/network`);
        if (res.ok) {
            networkData = await res.json();
        }
    } catch (e) {
        console.error("Ошибка загрузки данных:", e);
    }

    const width = networkData.dimensions?.width || 14904;
    const height = networkData.dimensions?.height || 10528;
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
    }, 200);

    renderNetwork();
    map.on("click", handleMapClick);
}

function getNodeColor(node) {
    if (node.type === "hydrant") return "#ff4d4f";
    if (node.type === "valve") return node.status === "closed" ? "#fa8c16" : "#52c41a";
    return "#1890ff";
}

function renderNetwork() {
    nodesLayer.clearLayers();
    pipesLayer.clearLayers();

    const showLabels = document.getElementById("toggle-labels") ? document.getElementById("toggle-labels").checked : true;

    (networkData.pipes || []).forEach(pipe => {
        const polyline = L.polyline(pipe.path, {
            color: pipe.material === "пэ" ? "#1890ff" : "#52c41a",
            weight: 4
        }).addTo(pipesLayer);
        polyline.on("click", () => showPipeInfo(pipe));
    });

    (networkData.nodes || []).forEach(node => {
        const marker = L.circleMarker([node.y, node.x], {
            radius: node.type === "hydrant" ? 8 : (node.type === "valve" ? 6 : 5),
            color: getNodeColor(node),
            fillColor: getNodeColor(node),
            fillOpacity: selectedNode && selectedNode.id === node.id ? 1.0 : 0.75,
            weight: selectedNode && selectedNode.id === node.id ? 4 : 2
        }).addTo(nodesLayer);

        if (showLabels) {
            marker.bindTooltip(node.name, { 
                permanent: true, 
                direction: "top",
                className: "custom-label"
            });
        }

        marker.on("click", (e) => {
            L.DomEvent.stopPropagation(e);
            handleNodeClick(node);
        });
    });

    document.getElementById("count-nodes").innerText = (networkData.nodes || []).length;
    document.getElementById("count-pipes").innerText = (networkData.pipes || []).length;
}

function toggleLabels() {
    renderNetwork();
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
        selectedNode = node;
        renderNetwork();
        showNodeEditor(node);
    }
}

function showNodeEditor(node) {
    const inspector = document.getElementById("inspector");
    inspector.innerHTML = `
        <h3 style="margin: 0 0 4px 0; font-size: 16px; color: #fff;">Редактирование объекта</h3>
        <div class="input-group">
            <label>Номер / Название</label>
            <input type="text" id="edit-node-name" value="${node.name}" autofocus>
        </div>
        <div class="input-group">
            <label>Тип объекта</label>
            <select id="edit-node-type">
                <option value="valve" ${node.type === 'valve' || !node.type ? 'selected' : ''}>Запорная арматура (задвижка)</option>
                <option value="well" ${node.type === 'well' ? 'selected' : ''}>Колодец / Узел</option>
                <option value="hydrant" ${node.type === 'hydrant' ? 'selected' : ''}>Пожарный гидрант (ПГ)</option>
            </select>
        </div>
        <div class="input-group">
            <label>Состояние</label>
            <select id="edit-node-status">
                <option value="open" ${node.status !== 'closed' ? 'selected' : ''}>Открыта (штатный режим)</option>
                <option value="closed" ${node.status === 'closed' ? 'selected' : ''}>Закрыта (отсечена)</option>
            </select>
        </div>
        <div style="font-size: 12px; color: #9aa0a6;">Координаты: X=${node.x}, Y=${node.y}</div>
        <div class="btn-group">
            <button class="btn-primary" onclick="saveNodeEdit('${node.id}')">💾 Сохранить</button>
            <button class="btn-danger" onclick="deleteNode('${node.id}')">🗑 Удалить</button>
        </div>
    `;

    const nameInput = document.getElementById("edit-node-name");
    nameInput.focus();
    nameInput.select();
    nameInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") saveNodeEdit(node.id);
    });
}

async function saveNodeEdit(nodeId) {
    const newName = document.getElementById("edit-node-name").value.trim();
    const newType = document.getElementById("edit-node-type").value;
    const newStatus = document.getElementById("edit-node-status").value;

    const node = networkData.nodes.find(n => n.id === nodeId);
    if (!node) return;

    node.name = newName;
    node.type = newType;
    node.status = newStatus;

    await fetch(`${API_URL}/node/${nodeId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(node)
    });

    renderNetwork();
    showNodeEditor(node);
}

async function deleteNode(nodeId) {
    if (!confirm("Удалить этот узел?")) return;

    await fetch(`${API_URL}/node/${nodeId}`, {
        method: "DELETE"
    });

    networkData.nodes = networkData.nodes.filter(n => n.id !== nodeId);
    selectedNode = null;
    document.getElementById("inspector").innerHTML = '<p style="color: #9aa0a6; margin: 0;">Объект удален. Выберите следующий.</p>';
    renderNetwork();
}

function showPipeInfo(pipe) {
    const inspector = document.getElementById("inspector");
    inspector.innerHTML = `
        <h3 style="margin: 0 0 4px 0; font-size: 16px; color: #fff;">Участок трубопровода</h3>
        <p style="margin: 4px 0;">Диаметр: <b>Ду ${pipe.diameter}</b></p>
        <p style="margin: 4px 0;">Материал: <b>${pipe.material}</b></p>
        <p style="margin: 4px 0;">Узлы: ${pipe.from_node} ➔ ${pipe.to_node}</p>
    `;
}

async function handleMapClick(e) {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    if (mode === "view" || mode === "add_pipe") return;

    const y = Math.round(e.latlng.lat);
    const x = Math.round(e.latlng.lng);

    let defaultName = "";
    let defaultType = "well";

    if (mode === "add_valve") {
        defaultName = prompt("Номер задвижки (например, 157):", "");
        defaultType = "valve";
    } else if (mode === "add_hydrant") {
        defaultName = prompt("Номер гидранта (например, ПГ 101):", "ПГ ");
        defaultType = "hydrant";
    } else {
        defaultName = prompt("Номер колодца (например, к116):", "к");
        defaultType = "well";
    }

    if (!defaultName) return;

    const newNode = {
        id: "node_" + Date.now(),
        name: defaultName,
        type: defaultType,
        status: "open",
        x: x,
        y: y
    };

    await fetch(`${API_URL}/node`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newNode)
    });

    networkData.nodes.push(newNode);
    selectedNode = newNode;
    renderNetwork();
    showNodeEditor(newNode);
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
