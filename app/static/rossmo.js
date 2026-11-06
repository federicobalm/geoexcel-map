const rossmoState = {
  upload: null,
  previewPayload: null,
  mapInstance: null,
  activeLayer: null,
  renderedPayload: null,
  analysisConfirmed: false,
  currentStep: 1,
  maxUnlockedStep: 1,
  stepCompleted: {
    1: false,
    2: false,
    3: false,
    4: false,
    5: false,
  },
};

const ROSSMO_TRANSFER_KEY = "geoexcel_rossmo_upload";

const rossmoTileLayers = tileLayers;

function byId(id) {
  return document.getElementById(id);
}

function setFeedback(message, isError = false) {
  const feedback = byId("rossmo-feedback");
  feedback.hidden = false;
  feedback.textContent = message;
  feedback.style.background = isError ? "rgba(231, 111, 81, 0.12)" : "rgba(79, 195, 247, 0.12)";
  feedback.style.borderColor = isError ? "rgba(231, 111, 81, 0.22)" : "rgba(79, 195, 247, 0.22)";
}

function hideFeedback() {
  byId("rossmo-feedback").hidden = true;
}

function setStepLocked(stepId, locked) {
  const step = byId(stepId);
  step.classList.toggle("is-locked", locked);
  step.setAttribute("aria-disabled", String(locked));
}

function unlockStep(stepNumber) {
  rossmoState.maxUnlockedStep = Math.max(rossmoState.maxUnlockedStep, stepNumber);
  const step = document.querySelector(`.wizard-step[data-step="${stepNumber}"]`);
  if (step) {
    step.classList.remove("is-locked");
    step.setAttribute("aria-disabled", "false");
  }
}

function setNextEnabled(buttonId, enabled) {
  const button = byId(buttonId);
  if (button) {
    button.disabled = !enabled;
  }
}

function syncAnalysisStepState() {
  const hasValue = Boolean(byId("rossmo-personal-analysis").value.trim());
  setNextEnabled("rossmo-confirm-analysis", hasValue);
  rossmoState.stepCompleted[5] = hasValue;
}

function markStepCompleted(stepNumber, completed = true) {
  rossmoState.stepCompleted[stepNumber] = completed;
  const buttonMap = {
    1: "rossmo-next-from-upload",
    2: "rossmo-next-from-verify",
    3: "rossmo-next-from-compute",
    4: "rossmo-continue-analysis",
    5: "rossmo-confirm-analysis",
  };
  const buttonId = buttonMap[stepNumber];
  if (buttonId) {
    setNextEnabled(buttonId, completed);
  }
}

function goToStep(stepNumber) {
  if (stepNumber > rossmoState.maxUnlockedStep) {
    return;
  }
  rossmoState.currentStep = stepNumber;
  document.querySelectorAll(".wizard-step").forEach((step) => {
    step.hidden = Number(step.dataset.step) !== stepNumber;
  });
  document.querySelectorAll(".wizard-progress-item").forEach((item) => {
    const itemStep = Number(item.dataset.progressStep);
    item.classList.toggle("is-active", itemStep === stepNumber);
    item.classList.toggle("is-done", itemStep < stepNumber);
  });
  if (stepNumber === 4 && rossmoState.previewPayload) {
    window.requestAnimationFrame(() => {
      renderPreviewStep();
      window.setTimeout(() => {
        renderPreviewStep();
      }, 60);
    });
  }
  if (stepNumber === 5) {
    syncAnalysisStepState();
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
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

function optionalFloat(value) {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function selectPreferredValue(selectId, preferredValues) {
  const select = byId(selectId);
  const values = Array.from(select.options).map((option) => option.value);
  const found = preferredValues.find((value) => values.includes(value));
  if (found) {
    select.value = found;
  }
}

function renderPreviewTable(rows) {
  const table = byId("rossmo-preview-table");
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

function renderSummary(upload) {
  const summary = byId("rossmo-summary");
  summary.innerHTML = `
    <div><span>Archivo</span><strong>${upload.filename}</strong></div>
    <div><span>Filas</span><strong>${upload.row_count}</strong></div>
    <div><span>Columnas</span><strong>${upload.column_count}</strong></div>
  `;
}

function renderNotes(notes) {
  const root = byId("rossmo-notes");
  root.innerHTML = "";
  notes.forEach((note) => {
    const div = document.createElement("div");
    div.className = "note-item";
    div.textContent = note;
    root.appendChild(div);
  });
}

function populateUpload(upload) {
  rossmoState.upload = upload;
  byId('rossmo-period-confirmed').checked = false;
  byId('rossmo-synthetic').checked = false;
  rossmoState.previewPayload = null;
  rossmoState.analysisConfirmed = false;
  rossmoState.stepCompleted = { 1: true, 2: false, 3: false, 4: false, 5: false };
  renderSummary(upload);
  renderNotes(upload.notes || []);
  renderPreviewTable(upload.preview_rows || []);
  fillSelect(byId("rossmo-lat-column"), upload.columns, upload.suggested_lat_column, false);
  fillSelect(byId("rossmo-lon-column"), upload.columns, upload.suggested_lon_column, false);
  fillSelect(byId("rossmo-label-column"), upload.candidate_label_columns || [], "", true);
  fillSelect(byId("rossmo-category-column"), upload.candidate_category_columns || [], "", true);
  selectPreferredValue("rossmo-lat-column", ["Latitud", "latitud", "latitude"]);
  selectPreferredValue("rossmo-lon-column", ["Longitud", "longitud", "longitude", "lon"]);
  selectPreferredValue("rossmo-label-column", ["ID_Crimen", "id_crimen", "caso"]);
  selectPreferredValue("rossmo-category-column", ["Tipo_Crimen", "tipo_crimen", "tipo"]);
  unlockStep(2);
  setStepLocked("step-compute", true);
  setStepLocked("step-preview", true);
  setStepLocked("step-analysis", true);
  setStepLocked("step-export", true);
  rossmoState.maxUnlockedStep = 2;
  byId("rossmo-export-html").disabled = true;
  byId("rossmo-export-pdf").disabled = true;
  setNextEnabled("rossmo-next-from-verify", false);
  setNextEnabled("rossmo-next-from-compute", false);
  setNextEnabled("rossmo-continue-analysis", false);
  setNextEnabled("rossmo-confirm-analysis", false);
  byId("rossmo-personal-analysis").value = "";
  byId("rossmo-systematic-analysis").innerHTML = "";
  syncAnalysisStepState();
  setNextEnabled("rossmo-next-from-upload", true);
}

function currentRequest() {
  return {
    session_id: rossmoState.upload.session_id,
    cartographic_metadata: readCartographicMetadata('rossmo'),
    lat_column: byId("rossmo-lat-column").value,
    lon_column: byId("rossmo-lon-column").value,
    map_type: "profile",
    tile_layer: byId("rossmo-tile-layer").value,
    label_column: byId("rossmo-label-column").value || null,
    category_column: byId("rossmo-category-column").value || null,
    heat_radius: 25,
    distance_metric: byId("rossmo-distance-metric").value,
    buffer_radius_m: Number(byId("rossmo-buffer-radius-m").value),
    decay_exponent_out: Number(byId("rossmo-decay-exponent-out").value),
    decay_exponent_in: Number(byId("rossmo-decay-exponent-in").value),
    scale_constant: Number(byId("rossmo-scale-constant").value),
    known_anchor_lat: optionalFloat(byId("rossmo-known-anchor-lat").value),
    known_anchor_lon: optionalFloat(byId("rossmo-known-anchor-lon").value),
    personal_analysis: byId("rossmo-personal-analysis").value.trim() || null,
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

function ensureMap() {
  if (rossmoState.mapInstance) {
    return rossmoState.mapInstance;
  }
  const map = L.map("rossmo-map", { zoomControl: true });
  trackMapView(map);
  rossmoState.mapInstance = map;
  L.tileLayer(rossmoTileLayers.OpenStreetMap.url, rossmoTileLayers.OpenStreetMap.options).addTo(map);
  map.setView([-34.6037, -58.3816], 11);
  return map;
}

function setBasemap(map, tileLayerName) {
  Object.values(map._layers).forEach((layer) => {
    if (layer instanceof L.TileLayer) {
      map.removeLayer(layer);
    }
  });
  const chosen = rossmoTileLayers[tileLayerName] || rossmoTileLayers.OpenStreetMap;
  L.tileLayer(chosen.url, chosen.options).addTo(map);
}

function renderMap(payload) {
  const map = ensureMap();
  map.invalidateSize();
  if (rossmoState.renderedPayload === payload) return;
  setBasemap(map, payload.map_config.tile_layer);
  if (rossmoState.activeLayer) {
    map.removeLayer(rossmoState.activeLayer);
  }
  byId("rossmo-map-empty").style.display = "none";

  const layer = L.layerGroup();
  const bounds = [];
  const legendColors = new Map(payload.category_legend.map((item) => [item.category, item.color]));
  const jeopardy = payload.profile.jeopardy_points || [];
  if (jeopardy.length) {
    jeopardy.forEach((item) => bounds.push([item[0], item[1]]));
    layer.addLayer(L.heatLayer(jeopardy, {
      radius: 20,
      blur: 24,
      minOpacity: 0.28,
      gradient: heatGradient('classic'),
    }));
  }
  payload.points.forEach((point) => {
    bounds.push([point.lat, point.lon]);
    const color = legendColors.get(point.category) || "#526d82";
    layer.addLayer(L.marker([point.lat, point.lon], { icon: markerIcon(color) }).bindPopup(popupHtml(point)));
  });
  const anchor = payload.profile.anchor_estimate;
  bounds.push([anchor.lat, anchor.lon]);
  layer.addLayer(L.circleMarker([anchor.lat, anchor.lon], {
    radius: 11,
    color: "#ffffff",
    weight: 2,
    fillColor: "#40365c",
    fillOpacity: 0.95,
  }).bindPopup(`<strong>Punto de anclaje estimado</strong><div>Lat: ${anchor.lat.toFixed(6)}</div><div>Lon: ${anchor.lon.toFixed(6)}</div><div>Score: ${anchor.score.toFixed(4)}</div>`));

  rossmoState.activeLayer = layer;
  rossmoState.activeLayer.addTo(map);
  if (bounds.length) {
    map.fitBounds(bounds, { padding: [24, 24], animate: false });
  }
  addCartography(map, payload);
  rossmoState.renderedPayload = payload;
}

function renderPreviewStep() {
  if (!rossmoState.previewPayload || rossmoState.currentStep !== 4) {
    return;
  }
  renderMap(rossmoState.previewPayload);
  renderIssues(rossmoState.previewPayload.summary);
  renderProfileMetrics(rossmoState.previewPayload.profile);
  renderSystematicAnalysis(rossmoState.previewPayload.profile);
}

function renderIssues(summary) {
  byId("rossmo-valid-rows").textContent = summary.valid_rows;
  byId("rossmo-invalid-rows").textContent = summary.invalid_rows;
  const list = byId("rossmo-issues-list");
  list.innerHTML = "";
  const items = summary.invalid_breakdown.length ? summary.invalid_breakdown : ["No se detectaron observaciones en las filas procesadas."];
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

function renderProfileMetrics(profile) {
  const metrics = byId("rossmo-profile-metrics");
  metrics.innerHTML = "";
  const hsValue = profile.hit_score_percentage === null ? "Sin referencia" : `${profile.hit_score_percentage.toFixed(2)} %`;
  const items = [
    ["Anclaje estimado", `${profile.anchor_estimate.lat.toFixed(5)}, ${profile.anchor_estimate.lon.toFixed(5)}`],
    ["Crimenes usados", String(profile.crimes_used)],
    ["Buffer", `${profile.buffer_radius_m} m`],
    ["Metrica", profile.distance_metric],
    ["HS%", hsValue],
    ["Proyeccion", `EPSG:${profile.projection_epsg}`],
  ];
  items.forEach(([label, value]) => {
    const div = document.createElement("div");
    div.className = "profile-metric";
    div.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    metrics.appendChild(div);
  });
}

function renderSystematicAnalysis(profile) {
  const list = byId("rossmo-systematic-analysis");
  list.innerHTML = "";
  [...(profile.warnings || []), ...(profile.systematic_analysis || []), ...(profile.notes || [])].forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
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
  const response = await postJson(url, {
    ...rossmoState.previewPayload.map_config,
    map_view: readMapView(rossmoState.mapInstance),
    personal_analysis: byId("rossmo-personal-analysis").value.trim() || null,
  });
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

async function uploadSelectedFile(file) {
  hideFeedback();
  if (!file) {
    setFeedback("Selecciona una serie antes de continuar.", true);
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  setFeedback("Analizando serie vinculada...");
  try {
    const response = await fetch("/api/upload", { method: "POST", body: formData });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "No se pudo procesar la serie." }));
      throw new Error(apiErrorMessage(error, "No se pudo procesar la serie."));
    }
    const upload = await response.json();
    populateUpload(upload);
    setFeedback("Serie cargada. Verifica columnas y habilita el analisis computacional.");
  } catch (error) {
    setFeedback(error.message, true);
  }
}

byId("rossmo-upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await uploadSelectedFile(byId("rossmo-data-file").files[0]);
});

byId("rossmo-load-dataset").addEventListener("click", async () => {
  try {
    setFeedback("Cargando dataset demo de Rossmo...");
    const response = await fetch("/sample_data/serie_rossmo_demo.csv");
    if (!response.ok) {
      throw new Error("No se pudo descargar el dataset demo.");
    }
    const blob = await response.blob();
    const file = new File([blob], "serie_rossmo_demo.csv", { type: "text/csv" });
    await uploadSelectedFile(file);
  } catch (error) {
    setFeedback(error.message, true);
  }
});

byId("rossmo-verify-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!rossmoState.upload) {
    setFeedback("Primero debes cargar una serie.", true);
    return;
  }
  if (!byId("rossmo-lat-column").value || !byId("rossmo-lon-column").value) {
    setFeedback("Debes confirmar latitud y longitud para continuar.", true);
    return;
  }
  unlockStep(3);
  markStepCompleted(2, true);
  setFeedback("Datos verificados. Ya puedes ejecutar el analisis computacional.");
});

byId("rossmo-compute-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!rossmoState.upload) {
    setFeedback("Primero debes cargar una serie.", true);
    return;
  }
  setFeedback("Ejecutando analisis Rossmo...");
  const button = event.submitter;
  if (button) button.disabled = true;
  try {
    const response = await postJson("/api/map-preview", currentRequest());
    const payload = await response.json();
    rossmoState.previewPayload = payload;
    unlockStep(4);
    markStepCompleted(3, true);
    setNextEnabled("rossmo-continue-analysis", true);
    setFeedback("Analisis computacional completado. Revisa la previsualizacion antes de continuar.");
  } catch (error) {
    setFeedback(error.message, true);
  } finally {
    if (button) button.disabled = false;
  }
});

// Changing verified inputs invalidates downstream results and exports.
function invalidateRossmo(fromStep) {
  rossmoState.previewPayload = null;
  rossmoState.analysisConfirmed = false;
  rossmoState.maxUnlockedStep = fromStep;
  for (let step = fromStep; step <= 5; step++) markStepCompleted(step, false);
  byId("rossmo-export-html").disabled = true;
  byId("rossmo-export-pdf").disabled = true;
}
byId("rossmo-verify-form").addEventListener("input", () => invalidateRossmo(2));
byId("rossmo-compute-form").addEventListener("input", () => invalidateRossmo(3));

byId("rossmo-continue-analysis").addEventListener("click", () => {
  if (!rossmoState.previewPayload) {
    setFeedback("Debes completar primero el analisis computacional.", true);
    return;
  }
  unlockStep(5);
  markStepCompleted(4, true);
  setFeedback("Ahora redacta tu analisis personal y revisa el analisis sistematizado.");
  goToStep(5);
});

byId("rossmo-personal-analysis").addEventListener("input", syncAnalysisStepState);
byId("rossmo-personal-analysis").addEventListener("change", syncAnalysisStepState);
byId("rossmo-personal-analysis").addEventListener("keyup", syncAnalysisStepState);

byId("rossmo-confirm-analysis").addEventListener("click", () => {
  const value = byId("rossmo-personal-analysis").value.trim();
  if (!value) {
    setFeedback("Debes redactar un analisis personal antes de habilitar la exportacion.", true);
    return;
  }
  rossmoState.analysisConfirmed = true;
  unlockStep(6);
  markStepCompleted(5, true);
  byId("rossmo-export-html").disabled = false;
  byId("rossmo-export-pdf").disabled = false;
  setFeedback("Analisis confirmado. Ya puedes exportar el informe final.");
  goToStep(6);
});

byId("rossmo-next-from-upload").addEventListener("click", () => goToStep(2));
byId("rossmo-next-from-verify").addEventListener("click", () => goToStep(3));
byId("rossmo-next-from-compute").addEventListener("click", () => goToStep(4));

byId("rossmo-back-to-upload").addEventListener("click", () => goToStep(1));
byId("rossmo-back-to-verify").addEventListener("click", () => goToStep(2));
byId("rossmo-back-to-compute").addEventListener("click", () => goToStep(3));
byId("rossmo-back-to-preview").addEventListener("click", () => goToStep(4));
byId("rossmo-back-to-analysis").addEventListener("click", () => goToStep(5));

byId("rossmo-export-html").addEventListener("click", async () => {
  try {
    setFeedback("Preparando exportacion HTML...");
    await downloadExport("/api/export/html");
    setFeedback("Exportacion HTML lista.");
  } catch (error) {
    setFeedback(error.message, true);
  }
});

byId("rossmo-export-pdf").addEventListener("click", async () => {
  try {
    setFeedback("Preparando exportacion PDF...");
    await downloadExport("/api/export/pdf");
    setFeedback("Exportacion PDF lista.");
  } catch (error) {
    setFeedback(error.message, true);
  }
});

try {
  const transferred = localStorage.getItem(ROSSMO_TRANSFER_KEY);
  if (transferred) {
    const upload = JSON.parse(transferred);
    populateUpload(upload);
    localStorage.removeItem(ROSSMO_TRANSFER_KEY);
    setFeedback("Se recupero automaticamente la serie Rossmo cargada desde la vista general. Usa Siguiente para continuar.");
  }
} catch {
  localStorage.removeItem(ROSSMO_TRANSFER_KEY);
}

goToStep(1);
