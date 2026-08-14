const appState = {
  upload: null,
  lastPreviewRequest: null,
  mapPayload: null,
  mapInstance: null,
  activeLayer: null,
};

const tileLayers = {
  "OpenStreetMap": { url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", options: { maxZoom: 19, attribution: "OpenStreetMap" } },
  "CartoDB Positron": { url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", options: { attribution: "CARTO", subdomains: "abcd", maxZoom: 20 } },
  "CartoDB DarkMatter": { url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", options: { attribution: "CARTO", subdomains: "abcd", maxZoom: 20 } },
  "Esri World Imagery": { url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", options: { attribution: "Esri", maxZoom: 18 } },
};

function byId(id) {
  return document.getElementById(id);
}

function setFeedback(message, isError = false) {
  const feedback = byId("upload-feedback");
  feedback.hidden = false;
  feedback.textContent = message;
  feedback.style.background = isError ? "rgba(231, 111, 81, 0.12)" : "rgba(79, 195, 247, 0.12)";
  feedback.style.borderColor = isError ? "rgba(231, 111, 81, 0.22)" : "rgba(79, 195, 247, 0.22)";
}

function hideFeedback() {
  byId("upload-feedback").hidden = true;
}

function fillSelect(select, values, selectedValue = "", includeEmpty = true) {
  select.innerHTML = "";
  if (includeEmpty) {
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "No usar";
    select.appendChild(empty);
  }
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    if (value === selectedValue) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

function renderPreviewTable(rows) {
  const table = byId("preview-table");
  table.innerHTML = "";
  if (!rows.length) {
    return;
  }
  const headers = Object.keys(rows[0]);
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  headers.forEach((header) => {
    const th = document.createElement("th");
    th.textContent = header;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    headers.forEach((header) => {
      const td = document.createElement("td");
      td.textContent = row[header];
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(thead);
  table.appendChild(tbody);
}

function renderNotes(notes) {
  const root = byId("validation-notes");
  root.innerHTML = "";
  notes.forEach((note) => {
    const div = document.createElement("div");
    div.className = "note-item";
    div.textContent = note;
    root.appendChild(div);
  });
}

function populateValidation(upload) {
  appState.upload = upload;
  byId("validation-empty").hidden = true;
  byId("validation-content").hidden = false;
  byId("summary-filename").textContent = upload.filename;
  byId("summary-rows").textContent = upload.row_count;
  byId("summary-columns").textContent = upload.column_count;
  renderNotes(upload.notes || []);
  renderPreviewTable(upload.preview_rows || []);

  fillSelect(byId("lat-column"), upload.columns, upload.suggested_lat_column, false);
  fillSelect(byId("lon-column"), upload.columns, upload.suggested_lon_column, false);
  fillSelect(byId("label-column"), upload.candidate_label_columns || [], "", true);
  fillSelect(byId("category-column"), upload.candidate_category_columns || [], "", true);
}

function currentMapRequest() {
  const form = byId("map-config-form");
  return {
    session_id: appState.upload.session_id,
    lat_column: form.lat_column.value,
    lon_column: form.lon_column.value,
    map_type: form.map_type.value,
    tile_layer: form.tile_layer.value,
    label_column: form.label_column.value || null,
    category_column: form.category_column.value || null,
    heat_radius: Number(form.heat_radius.value),
  };
}

function popupHtml(point) {
  const entries = Object.entries(point.popup || {});
  const lines = entries.map(([key, value]) => `<div><strong>${key}:</strong> ${value}</div>`).join("");
  return `${point.label ? `<div style="font-weight:700;margin-bottom:8px;">${point.label}</div>` : ""}${lines || "<span>Sin datos adicionales</span>"}`;
}

function markerIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 0 0 2px rgba(0,0,0,.22);"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function ensureMap() {
  if (appState.mapInstance) {
    return appState.mapInstance;
  }
  const map = L.map("map", { zoomControl: true });
  appState.mapInstance = map;
  L.tileLayer(tileLayers["OpenStreetMap"].url, tileLayers["OpenStreetMap"].options).addTo(map);
  map.setView([-34.6037, -58.3816], 11);
  return map;
}

function setBasemap(map, tileLayerName) {
  Object.values(map._layers).forEach((layer) => {
    if (layer instanceof L.TileLayer) {
      map.removeLayer(layer);
    }
  });
  const chosen = tileLayers[tileLayerName] || tileLayers["OpenStreetMap"];
  L.tileLayer(chosen.url, chosen.options).addTo(map);
}

function renderLegend(payload) {
  const card = byId("legend-card");
  const list = byId("legend-list");
  list.innerHTML = "";
  if (!payload.category_legend.length) {
    card.hidden = true;
    return;
  }
  payload.category_legend.forEach((item) => {
    const li = document.createElement("li");
    li.className = "legend-item";
    li.innerHTML = `<span class="legend-swatch" style="background:${item.color}"></span><span>${item.category}</span>`;
    list.appendChild(li);
  });
  card.hidden = false;
}

function renderIssues(summary) {
  byId("valid-rows").textContent = summary.valid_rows;
  byId("invalid-rows").textContent = summary.invalid_rows;
  const list = byId("issues-list");
  list.innerHTML = "";
  if (!summary.invalid_breakdown.length) {
    const li = document.createElement("li");
    li.textContent = "No se detectaron observaciones en las filas procesadas.";
    list.appendChild(li);
    return;
  }
  summary.invalid_breakdown.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

function renderMap(payload) {
  const map = ensureMap();
  setBasemap(map, payload.map_config.tile_layer);
  if (appState.activeLayer) {
    map.removeLayer(appState.activeLayer);
  }
  byId("map-empty").style.display = "none";

  const bounds = [];
  const legendColors = new Map(payload.category_legend.map((item) => [item.category, item.color]));

  if (payload.map_config.map_type === "heatmap") {
    const heatData = payload.points.map((point) => {
      bounds.push([point.lat, point.lon]);
      return [point.lat, point.lon, 1];
    });
    appState.activeLayer = L.heatLayer(heatData, { radius: payload.map_config.heat_radius, blur: 20 });
  } else if (payload.map_config.map_type === "cluster") {
    const layer = L.markerClusterGroup();
    payload.points.forEach((point) => {
      bounds.push([point.lat, point.lon]);
      layer.addLayer(L.marker([point.lat, point.lon], { icon: markerIcon("#ff6b6b") }).bindPopup(popupHtml(point)));
    });
    appState.activeLayer = layer;
  } else {
    const layer = L.layerGroup();
    payload.points.forEach((point) => {
      bounds.push([point.lat, point.lon]);
      const color = payload.map_config.map_type === "category" ? (legendColors.get(point.category) || "#4fc3f7") : "#ff6b6b";
      layer.addLayer(L.marker([point.lat, point.lon], { icon: markerIcon(color) }).bindPopup(popupHtml(point)));
    });
    appState.activeLayer = layer;
  }

  appState.activeLayer.addTo(map);

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [24, 24] });
  }
  renderLegend(payload);
  renderIssues(payload.summary);
  byId("export-html").disabled = false;
  byId("export-pdf").disabled = false;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Ocurrio un error inesperado." }));
    throw new Error(error.detail || "Ocurrio un error inesperado.");
  }
  return response;
}

async function downloadExport(url) {
  const request = currentMapRequest();
  const response = await postJson(url, request);
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : "geoexcel_export";
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(blobUrl);
}

function syncConditionalFields() {
  const mapType = byId("map-type").value;
  byId("heat-radius-wrap").style.display = mapType === "heatmap" ? "grid" : "none";
  byId("category-column").disabled = mapType !== "category";
}

byId("heat-radius").addEventListener("input", (event) => {
  byId("heat-radius-value").textContent = event.target.value;
});

byId("map-type").addEventListener("change", syncConditionalFields);
syncConditionalFields();

byId("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const file = byId("data-file").files[0];
  if (!file) {
    setFeedback("Selecciona un archivo antes de continuar.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  setFeedback("Analizando archivo...");

  try {
    const response = await fetch("/api/upload", { method: "POST", body: formData });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "No se pudo procesar el archivo." }));
      throw new Error(error.detail || "No se pudo procesar el archivo.");
    }
    const upload = await response.json();
    populateValidation(upload);
    setFeedback("Archivo procesado. Revisa las sugerencias y genera el mapa.");
  } catch (error) {
    setFeedback(error.message, true);
  }
});

byId("map-config-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!appState.upload) {
    setFeedback("Primero debes analizar un archivo.", true);
    return;
  }

  const request = currentMapRequest();
  appState.lastPreviewRequest = request;
  setFeedback("Generando vista del mapa...");
  try {
    const response = await postJson("/api/map-preview", request);
    const payload = await response.json();
    appState.mapPayload = payload;
    renderMap(payload);
    setFeedback("Mapa generado. Ya puedes exportar el resultado.");
  } catch (error) {
    setFeedback(error.message, true);
  }
});

byId("export-html").addEventListener("click", async () => {
  try {
    setFeedback("Preparando exportacion HTML...");
    await downloadExport("/api/export/html");
    setFeedback("Exportacion HTML lista.");
  } catch (error) {
    setFeedback(error.message, true);
  }
});

byId("export-pdf").addEventListener("click", async () => {
  try {
    setFeedback("Preparando exportacion PDF...");
    await downloadExport("/api/export/pdf");
    setFeedback("Exportacion PDF lista.");
  } catch (error) {
    setFeedback(error.message, true);
  }
});
