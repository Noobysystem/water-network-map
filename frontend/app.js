const API_URL = "/api";

let currentNetworkId = "drinking";
let map = null;
let imageOverlay = null;
let networkData = { nodes: [], dimensions: { width: 14904, height: 10528 } };
let bounds = [[0, 0], [10528, 14904]];
let nodesLayer = null;
let pulseLayer = null;
let selectedNode = null;
let currentFilter = "all";

const isMobile = () => window.innerWidth <= 768;

const NETWORKS_DEF = {
    drinking: { image: "scheme.jpg", width: 14904, height: 10528 },
    tech_water: { image: "scheme_tv.jpg", width: 7445, height: 5266 }
};

async function initApp() {
    map = L.map("map", {
        crs: L.CRS.Simple,
        minZoom: -3,
        maxZoom: 2.5,
        zoomSnap: 0.1,
        zoomControl: !isMobile()
    });

    nodesLayer = L.layerGroup().addTo(map);
    pulseLayer = L.layerGroup().addTo(map);

    map.on("click", handleMapClick);

    setupSearch();
    setupMobileSearch();

    await loadNetwork("drinking");
}

async function loadNetwork(netId) {
    currentNetworkId = netId;
    selectedNode = null;
    clearSearch();
    clearMobileSearch();

    // Обновление активных кнопок
    document.querySelectorAll(".net-tab").forEach(t => t.classList.remove("active"));
    const tabDesktop = document.getElementById(`tab-${netId}`);
    const tabMobile = document.getElementById(`m-tab-${netId}`);
    if (tabDesktop) tabDesktop.classList.add("active");
    if (tabMobile) tabMobile.classList.add("active");

    const inspector = document.getElementById("inspector");
    if (inspector) inspector.innerHTML = '<p style="color: #a0a5b5; margin: 0; font-size: 13px;">Кликните по любой задвижке или найдите её через поиск для редактирования.</p>';

    try {
        const res = await fetch(`${API_URL}/${netId}/network`);
        if (res.ok) {
            networkData = await res.json();
        } else {
            console.error("Ошибка HTTP:", res.status);
            networkData = { nodes: [], dimensions: NETWORKS_DEF[netId] };
        }
    } catch (e) {
        console.error("Ошибка загрузки схемы:", e);
        networkData = { nodes: [], dimensions: NETWORKS_DEF[netId] };
    }

    const cfg = NETWORKS_DEF[netId] || NETWORKS_DEF.drinking;
    const width = networkData.dimensions?.width || cfg.width;
    const height = networkData.dimensions?.height || cfg.height;
    bounds = [[0, 0], [height, width]];

    if (imageOverlay) {
        map.removeLayer(imageOverlay);
    }

    imageOverlay = L.imageOverlay(cfg.image, bounds).addTo(map);
    map.fitBounds(bounds);

    setTimeout(() => {
        map.invalidateSize();
        map.fitBounds(bounds);
    }, 150);

    renderNetwork();
}

function switchNetwork(netId) {
    loadNetwork(netId);
    if (isMobile()) closeMobileMenu();
}

function fitMapBounds() {
    if (bounds && map) {
        map.flyToBounds(bounds, { duration: 0.8 });
    }
}

function getNodeStyle(node) {
    const scale = isMobile() ? 1.35 : 1.0;

    if (node.type === "hydrant") {
        return { radius: 8 * scale, color: "#ff4d4f", fillColor: "#ff7875", fillOpacity: 0.9, weight: 2 };
    }

    switch (node.status) {
        case "no_cheeks":
            return { radius: 7.5 * scale, color: "#ffffff", fillColor: "#ff4d4f", fillOpacity: 1.0, weight: 3 };
        case "hard_turn":
            return { radius: 6.5 * scale, color: "#d48806", fillColor: "#faad14", fillOpacity: 0.9, weight: 2.5 };
        case "closed":
            return { radius: 6.5 * scale, color: "#d46b08", fillColor: "#fa8c16", fillOpacity: 0.9, weight: 2.5 };
        case "jammed_closed":
            return { radius: 7.5 * scale, color: "#ffffff", fillColor: "#722ed1", fillOpacity: 1.0, weight: 3 };
        default:
            return { radius: 6 * scale, color: "#237804", fillColor: "#52c41a", fillOpacity: 0.85, weight: 2 };
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
    if (!nodesLayer) return;
    nodesLayer.clearLayers();

    const showLabels = document.getElementById("toggle-labels")?.checked ?? true;
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
            if (node.status === "no_cheeks") labelText += " ⚠️";
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

    const vElem = document.getElementById("count-visible");
    const tElem = document.getElementById("count-total");
    const dElem = document.getElementById("count-defects");
    if (vElem) vElem.innerText = filtered.length;
    if (tElem) tElem.innerText = (networkData.nodes || []).length;
    if (dElem) dElem.innerText = defectCount;
}

function setFilter(filterType, element) {
    currentFilter = filterType;
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active", "active-danger"));
    if (filterType === "no_cheeks") element.classList.add("active-danger");
    else element.classList.add("active");
    renderNetwork();
}

function setMobileFilter(filterType, element) {
    currentFilter = filterType;
    document.querySelectorAll(".mobile-chip").forEach(c => c.classList.remove("active", "active-danger"));
    if (filterType === "no_cheeks") element.classList.add("active-danger");
    else element.classList.add("active");
    renderNetwork();
    closeMobileMenu();
}

function toggleLabels(state) {
    if (typeof state === "boolean") {
        const dToggle = document.getElementById("toggle-labels");
        const mToggle = document.getElementById("mobile-toggle-labels");
        if (dToggle) dToggle.checked = state;
        if (mToggle) mToggle.checked = state;
    }
    renderNetwork();
}

function focusOnNode(node) {
    selectedNode = node;
    renderNetwork();

    if (isMobile()) {
        showBottomSheet(node);
    } else {
        showNodeEditor(node);
    }

    map.flyTo([node.y, node.x], Math.max(map.getZoom(), 0.5), { duration: 0.6 });

    pulseLayer.clearLayers();
    const pulseIcon = L.divIcon({
        className: 'search-target-pulse',
        iconSize: [44, 44],
        iconAnchor: [22, 22]
    });
    const pulseMarker = L.marker([node.y, node.x], { icon: pulseIcon }).addTo(pulseLayer);
    setTimeout(() => pulseLayer.removeLayer(pulseMarker), 3500);
}

function generateEditorHTML(node, prefix = "") {
    return `
        <div class="input-group">
            <label>Номер / Маркировка</label>
            <input type="text" id="${prefix}edit-node-name" value="${node.name || ''}" placeholder="например, 157 или К 12">
        </div>

        <div class="input-group">
            <label>Тип объекта</label>
            <select id="${prefix}edit-node-type">
                <option value="valve" ${node.type !== 'hydrant' ? 'selected' : ''}>Задвижка / Запорная арматура</option>
                <option value="hydrant" ${node.type === 'hydrant' ? 'selected' : ''}>Пожарный гидрант (ПГ)</option>
            </select>
        </div>

        <div class="input-group">
            <label>Состояние / Дефекты</label>
            <select id="${prefix}edit-node-status">
                <option value="open" ${node.status === 'open' || !node.status ? 'selected' : ''}>🟢 В работе (Открыта)</option>
                <option value="closed" ${node.status === 'closed' ? 'selected' : ''}>🟠 Закрыта (Отсечена)</option>
                <option value="no_cheeks" ${node.status === 'no_cheeks' ? 'selected' : ''}>🔴 Нет щёк (не перекрывается!)</option>
                <option value="hard_turn" ${node.status === 'hard_turn' ? 'selected' : ''}>🟡 Плохо закрывается / тугой ход</option>
                <option value="jammed_closed" ${node.status === 'jammed_closed' ? 'selected' : ''}>🟣 Заклинила в закрытом состоянии</option>
            </select>
        </div>

        <div class="input-group">
            <label>Диаметр (Ду)</label>
            <input type="number" id="${prefix}edit-node-diameter" value="${node.diameter || 150}" step="25">
        </div>

        <div class="input-group">
            <label>Описание и дефекты</label>
            <textarea id="${prefix}edit-node-desc" placeholder="например: обломан шток, слизана резьба...">${node.description || ''}</textarea>
        </div>

        <div class="btn-group">
            <button class="btn-primary" onclick="saveNodeEdit('${node.id}', '${prefix}')">💾 Сохранить</button>
            <button class="btn-danger" onclick="deleteNode('${node.id}')">🗑 Удалить</button>
        </div>
    `;
}

function showNodeEditor(node) {
    const inspector = document.getElementById("inspector");
    if (!inspector) return;
    inspector.innerHTML = `
        <h3 style="margin: 0 0 2px 0; font-size: 16px; color: #fff;">
            ${node.type === 'hydrant' ? '🚒 Пожарный гидрант' : '🛑 Запорная арматура'}
        </h3>
        ${generateEditorHTML(node, "")}
    `;
}

function showBottomSheet(node) {
    const sheet = document.getElementById("mobile-bottom-sheet");
    const content = document.getElementById("sheet-content");
    const title = document.getElementById("sheet-title");

    title.innerText = node.type === 'hydrant' ? '🚒 Пожарный гидрант' : '🛑 Запорная арматура';
    content.innerHTML = generateEditorHTML(node, "m_");
    sheet.classList.add("open");
}

function closeBottomSheet() {
    const sheet = document.getElementById("mobile-bottom-sheet");
    if (sheet) sheet.classList.remove("open");
}

function openMobileMenu() {
    document.getElementById("mobile-menu-modal").classList.add("active");
}

function closeMobileMenu(e) {
    if (!e || e.target.id === "mobile-menu-modal" || e.type === "click") {
        document.getElementById("mobile-menu-modal").classList.remove("active");
    }
}

function syncMobileMode(radio) {
    const dRadio = document.querySelector(`input[name="mode"][value="${radio.value}"]`);
    if (dRadio) dRadio.checked = true;
}

function getActiveMode() {
    if (isMobile()) {
        return document.querySelector('input[name="mobile-mode"]:checked')?.value || "view";
    }
    return document.querySelector('input[name="mode"]:checked')?.value || "view";
}

async function saveNodeEdit(nodeId, prefix = "") {
    const newName = document.getElementById(`${prefix}edit-node-name`).value.trim();
    const newType = document.getElementById(`${prefix}edit-node-type`).value;
    const newStatus = document.getElementById(`${prefix}edit-node-status`).value;
    const newDiameter = parseInt(document.getElementById(`${prefix}edit-node-diameter`).value) || 150;
    const newDesc = document.getElementById(`${prefix}edit-node-desc`).value.trim();

    const node = networkData.nodes.find(n => n.id === nodeId);
    if (!node) return;

    node.name = newName;
    node.type = newType;
    node.status = newStatus;
    node.diameter = newDiameter;
    node.description = newDesc;

    await fetch(`${API_URL}/${currentNetworkId}/node/${nodeId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(node)
    });

    renderNetwork();
    if (isMobile()) closeBottomSheet();
    else showNodeEditor(node);
}

async function deleteNode(nodeId) {
    if (!confirm("Удалить этот объект со схемы?")) return;

    await fetch(`${API_URL}/${currentNetworkId}/node/${nodeId}`, { method: "DELETE" });

    networkData.nodes = networkData.nodes.filter(n => n.id !== nodeId);
    selectedNode = null;
    if (isMobile()) closeBottomSheet();
    else {
        document.getElementById("inspector").innerHTML = '<p style="color: #a0a5b5; margin: 0; font-size: 13px;">Объект удален. Выберите следующий.</p>';
    }
    renderNetwork();
}

function downloadBackup() {
    window.location.href = `${API_URL}/${currentNetworkId}/export`;
}

async function uploadBackup(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!confirm(`Восстановить базу данных для текущей схемы из "${file.name}"?`)) {
        event.target.value = "";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_URL}/${currentNetworkId}/import`, {
            method: "POST",
            body: formData
        });
        if (res.ok) {
            const data = await res.json();
            alert(`База успешно обновлена! Загружено объектов: ${data.count}`);
            loadNetwork(currentNetworkId);
        } else {
            alert("Ошибка при импорте базы данных.");
        }
    } catch (e) {
        alert("Не удалось отправить файл на сервер.");
    }
    event.target.value = "";
}

function setupSearch() {
    const searchInput = document.getElementById("search-input");
    const searchClear = document.getElementById("search-clear");
    const dropdown = document.getElementById("search-dropdown");

    if (!searchInput) return;

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

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".search-container")) dropdown.style.display = "none";
    });
}

function setupMobileSearch() {
    const mInput = document.getElementById("mobile-search-input");
    const mClear = document.getElementById("mobile-search-clear");
    const mDropdown = document.getElementById("mobile-search-dropdown");

    if (!mInput) return;

    mInput.addEventListener("input", (e) => {
        const query = e.target.value.trim().toLowerCase();
        mClear.style.display = query.length > 0 ? "block" : "none";

        if (!query) {
            mDropdown.style.display = "none";
            return;
        }

        const matches = (networkData.nodes || []).filter(n => {
            const nameMatch = (n.name || "").toLowerCase().includes(query);
            const descMatch = (n.description || "").toLowerCase().includes(query);
            return nameMatch || descMatch;
        }).slice(0, 15);

        if (matches.length === 0) {
            mDropdown.innerHTML = '<div style="padding: 10px; color: #8e929b; font-size: 12px; text-align: center;">Ничего не найдено</div>';
            mDropdown.style.display = "block";
            return;
        }

        const dropdownContent = matches.map(m => {
            let badge = `<span style="color:#52c41a;">● В работе</span>`;
            if (m.type === "hydrant") badge = `<span style="color:#ff4d4f;">🚒 ПГ</span>`;
            else if (m.status === "no_cheeks") badge = `<span style="color:#ff4d4f; font-weight:bold;">⚠️ Без щёк</span>`;
            else if (m.status === "closed") badge = `<span style="color:#fa8c16;">🔒 Закрыта</span>`;
            else if (m.status === "hard_turn") badge = `<span style="color:#faad14;">🟡 Дефект</span>`;

            return `
                <div class="search-item" onclick="selectMobileSearchResult('${m.id}')">
                    <div>
                        <b>${m.name}</b>
                        ${m.description ? `<div style="font-size:11px; color:#8e929b;">${m.description}</div>` : ''}
                    </div>
                    <div style="font-size: 11.5px;">${badge}</div>
                </div>
            `;
        }).join("");
        mDropdown.innerHTML = dropdownContent;
        mDropdown.style.display = "block";
    });

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".mobile-top-bar")) mDropdown.style.display = "none";
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

function selectMobileSearchResult(nodeId) {
    const node = (networkData.nodes || []).find(n => n.id === nodeId);
    if (node) {
        document.getElementById("mobile-search-dropdown").style.display = "none";
        document.getElementById("mobile-search-input").value = node.name;
        document.getElementById("mobile-search-clear").style.display = "block";
        focusOnNode(node);
    }
}

function clearSearch() {
    const input = document.getElementById("search-input");
    if (input) input.value = "";
    const clear = document.getElementById("search-clear");
    if (clear) clear.style.display = "none";
    const dropdown = document.getElementById("search-dropdown");
    if (dropdown) dropdown.style.display = "none";
}

function clearMobileSearch() {
    const input = document.getElementById("mobile-search-input");
    if (input) input.value = "";
    const clear = document.getElementById("mobile-search-clear");
    if (clear) clear.style.display = "none";
    const dropdown = document.getElementById("mobile-search-dropdown");
    if (dropdown) dropdown.style.display = "none";
}

async function handleMapClick(e) {
    const mode = getActiveMode();
    if (mode === "view") {
        if (isMobile()) closeBottomSheet();
        return;
    }

    const y = Math.round(e.latlng.lat);
    const x = Math.round(e.latlng.lng);

    let defaultName = "";
    let defaultType = (mode === "add_hydrant") ? "hydrant" : "valve";

    if (mode === "add_valve") {
        defaultName = prompt("Номер задвижки / колодца (например, 78 или К 12):", "");
    } else if (mode === "add_hydrant") {
        defaultName = prompt("Номер гидранта (например, ПГ 28):", "ПГ ");
    }

    if (!defaultName) return;

    const newNode = {
        id: "node_" + Date.now(),
        name: defaultName,
        type: defaultType,
        status: "open",
        description: "",
        diameter: 150,
        x: x,
        y: y
    };

    await fetch(`${API_URL}/${currentNetworkId}/node`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newNode)
    });

    networkData.nodes.push(newNode);
    focusOnNode(newNode);
}

initApp();
