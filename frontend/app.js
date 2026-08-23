const API_URL = "/api";

let map;
let networkData = { nodes: [], pipes: [], valves: [], dimensions: { width: 14904, height: 10528 } };
let nodesLayer, pipesLayer;
let lastNodeInChain = null;
let selectedObject = null;

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

    // Горячая клавиша Escape для сброса цепочки
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") resetPipeChain();
    });
}

function getNodeColor(node) {
    if (node.type === "hydrant") return "#ff4d4f";
    if (node.type === "valve") return node.status === "closed" ? "#fa8c16" : "#52c41a";
    return "#1890ff";
}

function getPipeColor(material) {
    if (material === "пэ") return "#1890ff"; // синий
    if (material === "чуг") return "#52c41a"; // зеленый
    if (material === "ст") return "#fa8c16"; // оранжевый
    return "#13c2c2";
}

function getPipeWeight(diameter) {
    if (diameter >= 300) return 6;
    if (diameter >= 200) return 5;
    if (diameter >= 150) return 4;
    return 3;
}

function renderNetwork() {
    nodesLayer.clearLayers();
    pipesLayer.clearLayers();

    const showLabels = document.getElementById("toggle-labels") ? document.getElementById("toggle-labels").checked : true;

    (networkData.pipes || []).forEach(pipe => {
        const isSelected = selectedObject && selectedObject.id === pipe.id;
        const polyline = L.polyline(pipe.path, {
            color: isSelected ? "#ffff00" : getPipeColor(pipe.material),
            weight: isSelected ? getPipeWeight(pipe.diameter) + 3 : getPipeWeight(pipe.diameter),
            opacity: 0.85
        }).addTo(pipesLayer);

        polyline.on("click", (e) => {
            L.DomEvent.stopPropagation(e);
            showPipeEditor(pipe);
        });
    });

    (networkData.nodes || []).forEach(node => {
        const isChainActive = lastNodeInChain && lastNodeInChain.id === node.id;
        const isSelected = selectedObject && selectedObject.id === node.id;

        const marker = L.circleMarker([node.y, node.x], {
            radius: node.type === "hydrant" ? 8 : (node.type === "valve" ? 6 : 5),
            color: isChainActive ? "#ffff00" : (isSelected ? "#ffffff" : getNodeColor(node)),
            fillColor: isChainActive ? "#ffff00" : getNodeColor(node),
            fillOpacity: isChainActive || isSelected ? 1.0 : 0.75,
            weight: isChainActive || isSelected ? 4 : 2
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

function onModeChange() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const pipePanel = document.getElementById("pipe-settings-panel");
    pipePanel.style.display = (mode === "add_pipe") ? "flex" : "none";
    resetPipeChain();
}

function resetPipeChain() {
    lastNodeInChain = null;
    const hint = document.getElementById("pipe-hint");
    if (hint) hint.innerHTML = "Кликните по <b>первому узлу</b> начала трассы.";
    renderNetwork();
}

async function handleNodeClick(node) {
    const mode = document.querySelector('input[name="mode"]:checked').value;

    if (mode === "add_pipe") {
        if (!lastNodeInChain) {
            lastNodeInChain = node;
            document.getElementById("pipe-hint").innerHTML = `Начало: <b>${node.name}</b>.<br>Теперь кликните по следующему узлу.`;
            renderNetwork();
        } else {
            if (lastNodeInChain.id === node.id) {
                resetPipeChain();
                return;
            }

            const diameter = parseInt(document.getElementById("default-pipe-diameter").value) || 150;
            const material = document.getElementById("default-pipe-material").value || "чуг";

            const newPipe = {
                id: "pipe_" + Date.now(),
                from_node: lastNodeInChain.id,
                to_node: node.id,
                diameter: diameter,
                material: material,
                path: [[lastNodeInChain.y, lastNodeInChain.x], [node.y, node.x]]
            };

            await fetch(`${API_URL}/pipe`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(newPipe)
            });

            networkData.pipes.push(newPipe);

            // Продолжаем цепочку от только что соединенного узла
            lastNodeInChain = node;
            document.getElementById("pipe-hint").innerHTML = `Участок построен! Текущий узел: <b>${node.name}</b>.<br>Кликайте дальше для продолжения нитки.`;
            renderNetwork();
        }
    } else {
        selectedObject = node;
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
            <input type="text" id="edit-node-name" value="${node.name}">
        </div>
        <div class="input-group">
            <label>Тип объекта</label>
            <select id="edit-node-type">
                <option value="valve" ${node.type === 'valve' ? 'selected' : ''}>Запорная арматура (задвижка)</option>
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
        <div class="btn-group">
            <button class="btn-primary" onclick="saveNodeEdit('${node.id}')">💾 Сохранить</button>
            <button class="btn-danger" onclick="deleteNode('${node.id}')">🗑 Удалить</button>
        </div>
    `;

    const nameInput = document.getElementById("edit-node-name");
    nameInput.focus();
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
    if (!confirm("Удалить этот узел и подключенные к нему трубы?")) return;

    await fetch(`${API_URL}/node/${nodeId}`, { method: "DELETE" });

    networkData.nodes = networkData.nodes.filter(n => n.id !== nodeId);
    networkData.pipes = networkData.pipes.filter(p => p.from_node !== nodeId && p.to_node !== nodeId);
    selectedObject = null;
    document.getElementById("inspector").innerHTML = '<p style="color: #9aa0a6; margin: 0;">Узел удален.</p>';
    renderNetwork();
}

function showPipeEditor(pipe) {
    selectedObject = pipe;
    renderNetwork();

    const fromNode = networkData.nodes.find(n => n.id === pipe.from_node)?.name || pipe.from_node;
    const toNode = networkData.nodes.find(n => n.id === pipe.to_node)?.name || pipe.to_node;

    const inspector = document.getElementById("inspector");
    inspector.innerHTML = `
        <h3 style="margin: 0 0 4px 0; font-size: 16px; color: #fff;">Участок трубы</h3>
        <p style="margin: 2px 0; font-size: 13px; color: #9aa0a6;">Трасса: <b>${fromNode}</b> ➔ <b>${toNode}</b></p>
        
        <div class="input-group">
            <label>Диаметр (Ду)</label>
            <select id="edit-pipe-diameter">
                <option value="50" ${pipe.diameter === 50 ? 'selected' : ''}>Ду 50</option>
                <option value="100" ${pipe.diameter === 100 ? 'selected' : ''}>Ду 100</option>
                <option value="150" ${pipe.diameter === 150 ? 'selected' : ''}>Ду 150</option>
                <option value="200" ${pipe.diameter === 200 ? 'selected' : ''}>Ду 200</option>
                <option value="250" ${pipe.diameter === 250 ? 'selected' : ''}>Ду 250</option>
                <option value="300" ${pipe.diameter === 300 ? 'selected' : ''}>Ду 300</option>
                <option value="400" ${pipe.diameter === 400 ? 'selected' : ''}>Ду 400</option>
            </select>
        </div>

        <div class="input-group">
            <label>Материал</label>
            <select id="edit-pipe-material">
                <option value="чуг" ${pipe.material === 'чуг' ? 'selected' : ''}>Чугун (чуг)</option>
                <option value="пэ" ${pipe.material === 'пэ' ? 'selected' : ''}>Полиэтилен (пэ)</option>
                <option value="ст" ${pipe.material === 'ст' ? 'selected' : ''}>Сталь (ст)</option>
            </select>
        </div>

        <div class="btn-group">
            <button class="btn-primary" onclick="savePipeEdit('${pipe.id}')">💾 Сохранить</button>
            <button class="btn-danger" onclick="deletePipe('${pipe.id}')">🗑 Удалить</button>
        </div>
    `;
}

async function savePipeEdit(pipeId) {
    const newDiameter = parseInt(document.getElementById("edit-pipe-diameter").value) || 150;
    const newMaterial = document.getElementById("edit-pipe-material").value;

    const pipe = networkData.pipes.find(p => p.id === pipeId);
    if (!pipe) return;

    pipe.diameter = newDiameter;
    pipe.material = newMaterial;

    await fetch(`${API_URL}/pipe/${pipeId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(pipe)
    });

    renderNetwork();
    showPipeEditor(pipe);
}

async function deletePipe(pipeId) {
    if (!confirm("Удалить этот участок трубы?")) return;

    await fetch(`${API_URL}/pipe/${pipeId}`, { method: "DELETE" });

    networkData.pipes = networkData.pipes.filter(p => p.id !== pipeId);
    selectedObject = null;
    document.getElementById("inspector").innerHTML = '<p style="color: #9aa0a6; margin: 0;">Участок трубы удален.</p>';
    renderNetwork();
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
    selectedObject = newNode;
    renderNetwork();
    showNodeEditor(newNode);
}

initApp();
