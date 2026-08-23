const API_URL = "/api";

let map;
let networkData = { nodes: [], dimensions: { width: 14904, height: 10528 } };
let bounds;
let nodesLayer, pulseLayer;
let selectedNode = null;
let currentFilter = "all";

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
    bounds = [[0, 0], [height, width]];

    map = L.map("map", {
        crs: L.CRS.Simple,
        minZoom: -4,
        maxZoom: 3,
        zoomSnap: 0.1
    });

    L.imageOverlay("scheme.png", bounds).addTo(map);
    map.fitBounds(bounds);

    nodesLayer = L.layerGroup().addTo(map);
    pulseLayer = L.layerGroup().addTo(map);

    setTimeout(() => {
        map.invalidateSize();
        map.fitBounds(bounds);
    }, 200);

    renderNetwork();
    map.on("click", handleMapClick);

    setupSearch();
}

function fitMapBounds() {
    if (bounds && map) {
        map.flyToBounds(bounds, { duration: 0.8 });
    }
}

function getNodeStyle(node) {
    if (node.type === "hydrant") {
        return { radius: 8, color: "#ff4d4f", fillColor: "#ff7875", fillOpacity: 0.9, weight: 2 };
    }

    switch (node.status) {
        case "no_cheeks":
            return { radius: 7.5, color: "#ffffff", fillColor: "#ff4d4f", fillOpacity: 1.0, weight: 3 };
        case "hard_turn":
            return { radius: 6.5, color: "#d48806", fillColor: "#faad14", fillOpacity: 0.9, weight: 2.5 };
        case "closed":
            return { radius: 6.5, color: "#d46b08", fillColor: "#fa8c16", fillOpacity: 0.9, weight: 2.5 };
        case "jammed_closed":
            return { radius: 7.5, color: "#ffffff", fillColor: "#722ed1", fillOpacity: 1.0, weight: 3 };
        default:
            return { radius: 6, color: "#237804", fillColor: "#52c41a", fillOpacity: 0.85, weight: 2 };
    }
}

function getFilteredNodes() {
    const nodes = networkData.nodes || [];
    if (currentFilter === "all") return nodes;
    if (currentFilter === "hydrant") return nodes.filter(n => n.type === "hydrant");
    if (currentFilter === "no_cheeks") return nodes.filter(n => n.status === "no_cheeks");
    if (currentFilter === "hard_turn") return nodes.filter(n => n.status === "hard_turn" || n.status === "jammed_closed");
    if (currentFilter === "closed") return nodes.filter(n => n.status === "closed");
    return nodes;
}

function renderNetwork() {
    nodesLayer.clearLayers();
    const showLabels = document.getElementById("toggle-labels") ? document.getElementById("toggle-labels").checked : true;
    const filtered = getFilteredNodes();
    let defectCount = 0;

    (networkData.nodes || []).forEach(node => {
        if (node.status === "no_cheeks" || node.status === "hard_turn" || node.status === "jammed_closed") {
            defectCount++;
        }
    });

    filtered.forEach(node => {
        const isSelected = selectedNode && selectedNode.id === node.id;
        const style = getNodeStyle(node);

        const marker = L.circleMarker([node.y, node.x], {
            radius: isSelected ? style.radius + 3 : style.radius,
            color: isSelected ? "#00f0ff" : style.color,
            fillColor: style.fillColor,
            fillOpacity: isSelected ? 1.0 : style.fillOpacity,
            weight: isSelected ? 4 : style.weight
        }).addTo(nodesLayer);

        if (showLabels) {
            let labelText = node.name;
            if (node.status === "no_cheeks") labelText += " ⚠️(без щёк)";
            else if (node.status === "closed") labelText += " 🔒";

            marker.bindTooltip(labelText, { 
                permanent: true, 
                direction: "top",
                className: "custom-label"
            });
        }

        marker.on("click", (e) => {
            L.DomEvent.stopPropagation(e);
            focusOnNode(node);
        });
    });

    document.getElementById("count-visible").innerText = filtered.length;
    document.getElementById("count-total").innerText = (networkData.nodes || []).length;
    document.getElementById("count-defects").innerText = defectCount;
}

function setFilter(filterType, element) {
    currentFilter = filterType;
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active", "active-danger"));
    
    if (filterType === "no_cheeks") element.classList.add("active-danger");
    else element.classList.add("active");

    renderNetwork();
}

function toggleLabels() {
    renderNetwork();
}

function focusOnNode(node) {
    selectedNode = node;
    renderNetwork();
    showNodeEditor(node);

    // Плавное приближение и центрирование
    map.flyTo([node.y, node.x], Math.max(map.getZoom(), 0.5), { duration: 0.6 });

    // Эффект пульсирующего маркера на 3 секунды
    pulseLayer.clearLayers();
    const pulseIcon = L.divIcon({
        className: 'search-target-pulse',
        iconSize: [40, 40],
        iconAnchor: [20, 20]
    });
    const pulseMarker = L.marker([node.y, node.x], { icon: pulseIcon }).addTo(pulseLayer);
    setTimeout(() => pulseLayer.removeLayer(pulseMarker), 3500);
}

function setupSearch() {
    const searchInput = document.getElementById("search-input");
    const searchClear = document.getElementById("search-clear");
    const dropdown = document.getElementById("search-dropdown");

    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.trim().toLowerCase();
        searchClear.style.display = query.length > 0 ? "block" : "none";

        if (!query) {
            dropdown.style.display = "none";
            return;
        }

        const matches = (networkData.nodes || []).filter(n => {
            const nameMatch = (n.name || "").toLowerCase().includes(query);
            const descMatch = (n.description || "").toLowerCase().includes(query);
            return nameMatch || descMatch;
        }).slice(0, 15);

        if (matches.length === 0) {
            dropdown.innerHTML = '<div style="padding: 10px; color: #8e929b; font-size: 12px; text-align: center;">Ничего не найдено</div>';
            dropdown.style.display = "block";
            return;
        }

        dropdown.innerHTML = matches.map(m => {
            let badge = `<span style="color:#52c41a;">● В работе</span>`;
            if (m.type === "hydrant") badge = `<span style="color:#ff4d4f;">🚒 ПГ</span>`;
            else if (m.status === "no_cheeks") badge = `<span style="color:#ff4d4f; font-weight:bold;">⚠️ Без щёк</span>`;
            else if (m.status === "closed") badge = `<span style="color:#fa8c16;">🔒 Закрыта</span>`;
            else if (m.status === "hard_turn") badge = `<span style="color:#faad14;">🟡 Дефект</span>`;

            return `
                <div class="search-item" onclick="selectSearchResult('${m.id}')">
                    <div>
                        <b>${m.name}</b>
                        ${m.description ? `<div style="font-size:11px; color:#8e929b;">${m.description}</div>` : ''}
                    </div>
                    <div style="font-size: 11.5px;">${badge}</div>
                </div>
            `;
        }).join("");
        dropdown.style.display = "block";
    });

    searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const query = searchInput.value.trim().toLowerCase();
            const first = (networkData.nodes || []).find(n => (n.name || "").toLowerCase().includes(query));
            if (first) {
                selectSearchResult(first.id);
            }
        }
    });

    // Закрытие выпадающего списка при клике вне него
    document.addEventListener("click", (e) => {
        if (!e.target.closest(".search-container")) {
            dropdown.style.display = "none";
        }
    });
}

function selectSearchResult(nodeId) {
    const node = (networkData.nodes || []).find(n => n.id === nodeId);
    if (node) {
        document.getElementById("search-dropdown").style.display = "none";
        document.getElementById("search-input").value = node.name;
        document.getElementById("search-clear").style.display = "block";
        focusOnNode(node);
    }
}

function clearSearch() {
    const searchInput = document.getElementById("search-input");
    searchInput.value = "";
    document.getElementById("search-clear").style.display = "none";
    document.getElementById("search-dropdown").style.display = "none";
}

function showNodeEditor(node) {
    const inspector = document.getElementById("inspector");
    inspector.innerHTML = `
        <h3 style="margin: 0 0 2px 0; font-size: 16px; color: #fff;">
            ${node.type === 'hydrant' ? '🚒 Пожарный гидрант' : '🛑 Запорная арматура'}
        </h3>
        
        <div class="input-group">
            <label>Номер / Маркировка</label>
            <input type="text" id="edit-node-name" value="${node.name || ''}" placeholder="например, 157">
        </div>

        <div class="input-group">
            <label>Тип объекта</label>
            <select id="edit-node-type">
                <option value="valve" ${node.type !== 'hydrant' ? 'selected' : ''}>Задвижка / Запорная арматура</option>
                <option value="hydrant" ${node.type === 'hydrant' ? 'selected' : ''}>Пожарный гидрант (ПГ)</option>
            </select>
        </div>

        <div class="input-group">
            <label>Состояние / Дефекты</label>
            <select id="edit-node-status">
                <option value="open" ${node.status === 'open' || !node.status ? 'selected' : ''}>🟢 В работе (Открыта)</option>
                <option value="closed" ${node.status === 'closed' ? 'selected' : ''}>🟠 Закрыта (Отсечена)</option>
                <option value="no_cheeks" ${node.status === 'no_cheeks' ? 'selected' : ''}>🔴 Нет щёк (не перекрывается!)</option>
                <option value="hard_turn" ${node.status === 'hard_turn' ? 'selected' : ''}>🟡 Плохо закрывается / тугой ход / пропуск</option>
                <option value="jammed_closed" ${node.status === 'jammed_closed' ? 'selected' : ''}>🟣 Заклинила в закрытом состоянии</option>
            </select>
        </div>

        <div class="input-group">
            <label>Диаметр (Ду)</label>
            <input type="number" id="edit-node-diameter" value="${node.diameter || 150}" step="25">
        </div>

        <div class="input-group">
            <label>Описание и дефекты</label>
            <textarea id="edit-node-desc" placeholder="например: обломан шток, слизана резьба, колодец завален...">${node.description || ''}</textarea>
        </div>

        <div class="btn-group">
            <button class="btn-primary" onclick="saveNodeEdit('${node.id}')">💾 Сохранить</button>
            <button class="btn-danger" onclick="deleteNode('${node.id}')">🗑 Удалить</button>
        </div>
    `;

    const nameInput = document.getElementById("edit-node-name");
    nameInput.focus();
    nameInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) saveNodeEdit(node.id);
    });
}

async function saveNodeEdit(nodeId) {
    const newName = document.getElementById("edit-node-name").value.trim();
    const newType = document.getElementById("edit-node-type").value;
    const newStatus = document.getElementById("edit-node-status").value;
    const newDiameter = parseInt(document.getElementById("edit-node-diameter").value) || 150;
    const newDesc = document.getElementById("edit-node-desc").value.trim();

    const node = networkData.nodes.find(n => n.id === nodeId);
    if (!node) return;

    node.name = newName;
    node.type = newType;
    node.status = newStatus;
    node.diameter = newDiameter;
    node.description = newDesc;

    await fetch(`${API_URL}/node/${nodeId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(node)
    });

    renderNetwork();
    showNodeEditor(node);
}

async function deleteNode(nodeId) {
    if (!confirm("Удалить этот объект со схемы?")) return;

    await fetch(`${API_URL}/node/${nodeId}`, { method: "DELETE" });

    networkData.nodes = networkData.nodes.filter(n => n.id !== nodeId);
    selectedNode = null;
    document.getElementById("inspector").innerHTML = '<p style="color: #9aa0a6; margin: 0; font-size: 13px;">Объект удален. Выберите следующий.</p>';
    renderNetwork();
}

async function handleMapClick(e) {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    if (mode === "view") return;

    const y = Math.round(e.latlng.lat);
    const x = Math.round(e.latlng.lng);

    let defaultName = "";
    let defaultType = (mode === "add_hydrant") ? "hydrant" : "valve";

    if (mode === "add_valve") {
        defaultName = prompt("Номер задвижки (например, 157):", "");
    } else if (mode === "add_hydrant") {
        defaultName = prompt("Номер гидранта (например, ПГ 101):", "ПГ ");
    }

    if (!defaultName) return;

    const newNode = {
        id: "valve_" + Date.now(),
        name: defaultName,
        type: defaultType,
        status: "open",
        description: "",
        diameter: 150,
        x: x,
        y: y
    };

    await fetch(`${API_URL}/node`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newNode)
    });

    networkData.nodes.push(newNode);
    focusOnNode(newNode);
}

initApp();
