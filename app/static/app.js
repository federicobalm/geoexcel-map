const appState = {
  upload: null,
  mapPayload: null,
  mapInstance: null,
  activeLayer: null,
  busy: false,
  step: 1,
};


const mapTypeDescriptions = {
  points: ["Mapa de puntos", "Tocá un punto para consultar sus datos."],
  heatmap: ["Densidad KDE", "La intensidad representa eventos por km²; ajustá el ancho de banda en metros."],
  hotmap: ["Mapa de calor · Hot map", "Calor clásico: azul, cian, verde, amarillo y rojo. Ajustá el radio para ver las concentraciones."],
  choropleth: ["Coropleta por grilla", "Compara cantidades en celdas; no son límites de barrios."],
  cluster: ["Puntos agrupados", "Acercá el mapa para separar los grupos."],
  category: ["Puntos por categoría", "Elegí una columna para asignar un color a cada grupo."],
  proportional: ["Símbolos proporcionales", "El área de cada círculo representa la frecuencia de eventos en esa ubicación."],
};

const mapTypeLabels = Object.fromEntries(Object.entries(mapTypeDescriptions).map(([key, value]) => [key, value[0]]));

function byId(id) {
  return document.getElementById(id);
}

function setFeedback(message, isError = false) {
  const feedback = byId("upload-feedback");
  feedback.hidden = false;
  feedback.textContent = message;
  feedback.classList.toggle("is-error", isError);
}

function goToMapStep(step) {
  if (appState.busy || (step === 2 && !appState.upload) || (step === 3 && !appState.mapPayload)) return;
  appState.step = step;
  document.querySelector(".page-heading").hidden = step !== 1;
  [1, 2, 3].forEach(number => {
    byId(`map-stage-${number}`).hidden = number !== step;
  });
  document.querySelectorAll("[data-map-step]").forEach(button => {
    const number = Number(button.dataset.mapStep);
    button.disabled = (number === 2 && !appState.upload) || (number === 3 && !appState.mapPayload);
    if (number === step) button.setAttribute("aria-current", "step");
    else button.removeAttribute("aria-current");
  });
  const heading = byId(["", "upload-heading", "configure-heading", "result-heading"][step]);
  heading.focus({ preventScroll: true });
  if (step === 3 && appState.mapInstance) requestAnimationFrame(() => appState.mapInstance.invalidateSize());
}

function setBusy(busy) {
  appState.busy = busy;
  document.querySelectorAll("button").forEach(button => {
    if (busy) {
      button.dataset.wasDisabled = String(button.disabled);
      button.disabled = true;
    } else if (button.dataset.wasDisabled !== undefined) {
      button.disabled = button.dataset.wasDisabled === "true";
      delete button.dataset.wasDisabled;
    }
  });
  document.querySelector("main").setAttribute("aria-busy", String(busy));
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
  byId('map-period-confirmed').checked = false;
  byId('map-synthetic').checked = false;
  appState.mapPayload = null;
  byId("map-personal-analysis").value = "";
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
  byId("export-html").disabled = true;
  byId("export-pdf").disabled = true;
  renderLegend({ category_legend: [] });
  byId("coordinate-settings").open = !upload.suggested_lat_column || !upload.suggested_lon_column;
  syncConditionalFields();
}

function currentMapRequest() {
  const form = byId("map-config-form");
  return {
    session_id: appState.upload.session_id,
    cartographic_metadata: readCartographicMetadata('map'),
    lat_column: form.lat_column.value,
    lon_column: form.lon_column.value,
    map_type: form.map_type.value,
    tile_layer: form.tile_layer.value,
    label_column: form.label_column.value || null,
    category_column: form.category_column.value || null,
    heat_radius: Number(form.heat_radius.value),
    heat_palette: form.heat_palette.value,
    bandwidth_m: form.map_type.value === "heatmap" ? Number(form.bandwidth_m.value) : 500,
    heat_levels: ["heatmap", "hotmap"].includes(form.map_type.value) ? readHeatLevels() : [10, 38, 58, 78, 100],
    distance_metric: "manhattan",
    buffer_radius_m: 400,
    decay_exponent_out: 1.2,
    decay_exponent_in: 2.0,
    scale_constant: 1.0,
    known_anchor_lat: null,
    known_anchor_lon: null,
    personal_analysis: byId("map-personal-analysis").value.trim() || null,
  };
}

function popupHtml(point) {
  const entries = Object.entries(point.popup || {});
  const lines = entries.map(([key, value]) => `<div><strong>${escapeHtml(key)}:</strong> ${escapeHtml(value)}</div>`).join("");
  return `${point.label ? `<div style="font-weight:700;margin-bottom:8px;">${escapeHtml(point.label)}</div>` : ""}${lines || "<span>Sin datos adicionales</span>"}`;
}

function markerIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 0 0 2px rgba(0,0,0,.22);"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function colorForRatio(ratio) {
  if (ratio >= 0.8) return "#7f1d1d";
  if (ratio >= 0.6) return "#dc2626";
  if (ratio >= 0.4) return "#f97316";
  if (ratio >= 0.2) return "#facc15";
  return "#38bdf8";
}

function buildGridCells(points, divisions = 7) {
  if (!points.length) return [];
  const lats = points.map((point) => point.lat);
  const lons = points.map((point) => point.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const latSpan = Math.max(maxLat - minLat, 0.0001);
  const lonSpan = Math.max(maxLon - minLon, 0.0001);
  const cellLat = latSpan / divisions;
  const cellLon = lonSpan / divisions;
  const cells = new Map();

  points.forEach((point) => {
    const row = Math.min(Math.floor((point.lat - minLat) / cellLat), divisions - 1);
    const col = Math.min(Math.floor((point.lon - minLon) / cellLon), divisions - 1);
    const key = `${row}:${col}`;
    const current = cells.get(key) || { row, col, count: 0 };
    current.count += 1;
    cells.set(key, current);
  });

  const maxCount = Math.max(...Array.from(cells.values()).map((cell) => cell.count));
  return Array.from(cells.values()).map((cell) => ({
    count: cell.count,
    ratio: cell.count / maxCount,
    bounds: [
      [minLat + cell.row * cellLat, minLon + cell.col * cellLon],
      [minLat + (cell.row + 1) * cellLat, minLon + (cell.col + 1) * cellLon],
    ],
  }));
}

function buildHeatmapLayer(points, radius, paletteName = "classic", levels) {
  const palette = HEAT_PALETTES[paletteName] || HEAT_PALETTES.classic;
  const layer = L.layerGroup();
  const heatData = points.map((point) => [point.lat, point.lon, 0.9]);
  if (typeof L.heatLayer === "function") {
    layer.addLayer(
      L.heatLayer(heatData, {
        radius: Math.round(radius * 1.65),
        blur: Math.max(34, Math.round(radius * 1.45)),
        minOpacity: 0.42,
        maxZoom: 18,
        gradient: heatGradient(paletteName, levels),
      })
    );
  }
  if (typeof L.heatLayer !== "function") points.forEach((point) => {
    layer.addLayer(
      L.circleMarker([point.lat, point.lon], {
        radius: Math.max(18, Math.round(radius * 0.85)),
        stroke: false,
        fillColor: palette.gradient[0.38],
        fillOpacity: 0.08,
      }).bindPopup(popupHtml(point))
    );
  });
  return layer;
}

function ensureMap() {
  if (appState.mapInstance) {
    return appState.mapInstance;
  }
  const map = L.map("map", { zoomControl: true });
  trackMapView(map);
  appState.mapInstance = map;
  L.tileLayer(tileLayers.OpenStreetMap.url, tileLayers.OpenStreetMap.options).addTo(map);
  map.setView([-34.6037, -58.3816], 11);
  return map;
}

function setBasemap(map, tileLayerName) {
  Object.values(map._layers).forEach((layer) => {
    if (layer instanceof L.TileLayer) {
      map.removeLayer(layer);
    }
  });
  const chosen = tileLayers[tileLayerName] || tileLayers.OpenStreetMap;
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
    li.innerHTML = `<span class="legend-swatch" style="background:${item.color}"></span><span>${escapeHtml(item.category)}</span>`;
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

function renderSystematicAnalysis(items) {
  const list = byId("map-systematic-analysis");
  list.innerHTML = "";
  (items || []).forEach((item) => {
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
    bounds.push(...payload.density.bounds);
    appState.activeLayer = renderDensity(payload.density, payload.map_config);
  } else if (payload.map_config.map_type === "hotmap") {
    payload.points.forEach(point => bounds.push([point.lat, point.lon]));
    appState.activeLayer = buildHeatmapLayer(payload.points, payload.map_config.heat_radius, payload.map_config.heat_palette, payload.map_config.heat_levels);
  } else if (payload.map_config.map_type === "proportional") {
    payload.points.forEach(point => bounds.push([point.lat, point.lon]));
    appState.activeLayer = renderProportional(payload.points);
  } else if (payload.map_config.map_type === "choropleth") {
    const layer = L.layerGroup();
    payload.points.forEach((point) => bounds.push([point.lat, point.lon]));
    buildGridCells(payload.points).forEach((cell) => {
      layer.addLayer(
        L.rectangle(cell.bounds, {
          color: "#ffffff",
          weight: 1,
          opacity: 0.42,
          fillColor: colorForRatio(cell.ratio),
          fillOpacity: 0.34 + cell.ratio * 0.46,
        }).bindPopup(`<strong>Celda de coropleta</strong><div>Registros: ${cell.count}</div>`)
      );
    });
    appState.activeLayer = layer;
  } else if (payload.map_config.map_type === "cluster") {
    const layer = L.markerClusterGroup();
    payload.points.forEach((point) => {
      bounds.push([point.lat, point.lon]);
      layer.addLayer(L.marker([point.lat, point.lon], { icon: markerIcon("#526d82") }).bindPopup(popupHtml(point)));
    });
    appState.activeLayer = layer;
  } else {
    const layer = L.layerGroup();
    payload.points.forEach((point) => {
      bounds.push([point.lat, point.lon]);
      const color = payload.map_config.map_type === "category" ? (legendColors.get(point.category) || "#526d82") : "#526d82";
      layer.addLayer(L.marker([point.lat, point.lon], { icon: markerIcon(color) }).bindPopup(popupHtml(point)));
    });
    appState.activeLayer = layer;
  }

  appState.activeLayer.addTo(map);
  if (bounds.length) {
    map.fitBounds(bounds, { padding: [24, 24], animate: false });
  }
  renderLegend(payload);
  renderIssues(payload.summary);
  renderSystematicAnalysis(payload.cartography.systematic_analysis);
  addCartography(map, payload);
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
    throw new Error(apiErrorMessage(error));
  }
  return response;
}

async function downloadExport(url) {
  const request = {
    ...appState.mapPayload.map_config,
    map_view: readMapView(appState.mapInstance),
    personal_analysis: byId("map-personal-analysis").value.trim() || null,
  };
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
  const isHeat = ["heatmap", "hotmap"].includes(mapType);
  byId("heat-radius-wrap").hidden = mapType !== "hotmap";
  byId("bandwidth-wrap").hidden = mapType !== "heatmap";
  byId("bandwidth-m").disabled = mapType !== "heatmap";
  byId("heat-palette-wrap").hidden = !isHeat;
  byId("heat-levels-wrap").hidden = !isHeat;
  if (isHeat && byId("heat-palette").dataset.mapType !== mapType) {
    byId("heat-palette").value = mapType === "hotmap" ? "classic" : "blues";
    byId("heat-palette").dataset.mapType = mapType;
  }
  for (let i = 0; i < 5; i++) byId(`heat-level-${i}`).disabled = !isHeat;
  updatePalettePreview();
  byId("category-column").disabled = mapType !== "category";
  byId("category-column").required = mapType === "category";
  byId("category-wrap").hidden = mapType !== "category";
  const [title, description] = mapTypeDescriptions[mapType] || mapTypeDescriptions.points;
  byId("map-type-title").textContent = title;
  byId("map-type-description").textContent = description;
}

function updatePalettePreview() {
  const palette = HEAT_PALETTES[byId("heat-palette").value];
  const colors = Object.entries(palette.gradient).sort((a, b) => Number(a[0]) - Number(b[0])).map(entry => entry[1]);
  const levels = readHeatLevels();
  if (validHeatLevels(levels)) byId("heat-palette-preview").style.background = `linear-gradient(to right, ${colors.map((color, index) => `${color} ${levels[index]}%`).join(", ")})`;
  document.querySelectorAll(".level-swatch").forEach((swatch, index) => swatch.style.background = colors[index]);
}

function readHeatLevels() {
  return Array.from({ length: 5 }, (_, index) => byId(`heat-level-${index}`).valueAsNumber);
}

function validHeatLevels(levels) {
  return levels.every((level, index) => Number.isInteger(level) && level >= 1 && level <= 100 && (index === 0 || level > levels[index - 1])) && levels[4] === 100;
}

document.querySelectorAll('.heat-levels input').forEach(input => input.addEventListener('input', () => {
  byId('heat-levels-error').hidden = validHeatLevels(readHeatLevels());
  updatePalettePreview();
}));
byId('reset-heat-levels').addEventListener('click', () => {
  [10, 38, 58, 78, 100].forEach((value, index) => byId(`heat-level-${index}`).value = value);
  byId('heat-levels-error').hidden = true;
  updatePalettePreview();
});

byId("heat-palette").addEventListener("change", updatePalettePreview);
byId("heat-radius").addEventListener("input", (event) => {
  byId("heat-radius-value").textContent = event.target.value;
});

byId("map-type").addEventListener("change", syncConditionalFields);
document.querySelectorAll('input[name="map_choice"]').forEach(input => {
  input.addEventListener("change", () => {
    byId("map-type").value = input.value;
    syncConditionalFields();
  });
});
document.querySelectorAll("[data-map-step], [data-go-step]").forEach(button => {
  button.addEventListener("click", () => {
    hideFeedback();
    goToMapStep(Number(button.dataset.mapStep || button.dataset.goStep));
  });
});
byId("data-file").addEventListener("change", () => {
  byId("selected-file").textContent = byId("data-file").files[0]?.name || "Ningún archivo seleccionado";
});
byId("fit-map").addEventListener("click", () => {
  if (appState.mapPayload?.density) {
    appState.mapInstance.fitBounds(appState.mapPayload.density.bounds, { padding: [30,30] });
    return;
  }
  if (appState.mapPayload?.points.length) {
    appState.mapInstance.fitBounds(appState.mapPayload.points.map(point => [point.lat, point.lon]), { padding: [30, 30] });
  }
});
syncConditionalFields();

async function uploadDataset(file) {
  if (appState.busy) return;
  hideFeedback();
  if (!file) {
    setFeedback("Selecciona un archivo antes de continuar.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  setFeedback("Analizando archivo...");
  setBusy(true);

  try {
    const response = await fetch("/api/upload", { method: "POST", body: formData });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "No se pudo procesar el archivo." }));
      throw new Error(apiErrorMessage(error, "No se pudo procesar el archivo."));
    }
    const upload = await response.json();
    setBusy(false);
    populateValidation(upload);
    goToMapStep(2);
    hideFeedback();
  } catch (error) {
    setBusy(false);
    setFeedback(error.message, true);
  }
}

byId("upload-form").addEventListener("submit", (event) => {
  event.preventDefault();
  uploadDataset(byId("data-file").files[0]);
});

byId("load-demo").addEventListener("click", async () => {
  if (appState.busy) return;
  setBusy(true);
  setFeedback("Cargando el ejemplo de Buenos Aires…");
  try {
    const response = await fetch("/sample_data/plantilla_geoexcel_map.xlsx");
    if (!response.ok) throw new Error("No pudimos cargar el ejemplo. Volvé a intentarlo.");
    const blob = await response.blob();
    setBusy(false);
    await uploadDataset(new File([blob], "Ejemplo_CABA_300_casos.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
  } catch (error) {
    setBusy(false);
    setFeedback(error.message, true);
  }
});

byId("map-config-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (appState.busy) return;
  if (!appState.upload) {
    setFeedback("Primero debes analizar un archivo.", true);
    return;
  }

  const request = currentMapRequest();
  if (["heatmap", "hotmap"].includes(request.map_type) && !validHeatLevels(request.heat_levels)) {
    byId("heat-levels-wrap").open = true;
    byId("heat-levels-error").hidden = false;
    setFeedback("Revisá los niveles de color: deben aumentar de izquierda a derecha hasta 100 %.", true);
    return;
  }
  setFeedback("Generando vista del mapa...");
  setBusy(true);
  try {
    const response = await postJson("/api/map-preview", request);
    const payload = await response.json();
    setBusy(false);
    appState.mapPayload = payload;
    goToMapStep(3);
    renderMap(payload);
    byId("result-map-type").textContent = mapTypeLabels[payload.map_config.map_type];
    hideFeedback();
  } catch (error) {
    setBusy(false);
    if (appState.step === 3) goToMapStep(2);
    setFeedback(error.message, true);
  }
});

byId("export-html").addEventListener("click", async () => {
  if (appState.busy) return;
  setBusy(true);
  try {
    setFeedback("Preparando exportacion HTML...");
    await downloadExport("/api/export/html");
    setFeedback("Exportacion HTML lista.");
  } catch (error) {
    setFeedback(error.message, true);
  } finally {
    setBusy(false);
  }
});

byId("export-pdf").addEventListener("click", async () => {
  if (appState.busy) return;
  setBusy(true);
  try {
    setFeedback("Preparando exportacion PDF...");
    await downloadExport("/api/export/pdf");
    setFeedback("Exportacion PDF lista.");
  } catch (error) {
    setFeedback(error.message, true);
  } finally {
    setBusy(false);
  }
});
