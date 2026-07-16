(function () {
  const RISK_COLOR = { verde: "#16a34a", amarillo: "#f59e0b", rojo: "#e11d48" };
  const EVENT_ICONS = {
    incendio: "fa-fire", deslizamiento: "fa-mountain", inundacion: "fa-water",
    accidente: "fa-car-burst", manifestacion: "fa-people-group", protesta: "fa-people-group",
    huelga: "fa-hand", bloqueo: "fa-road-barrier", cierre_vial: "fa-road-circle-xmark",
    orden_publico: "fa-shield-halved", delito: "fa-user-secret", lluvia_intensa: "fa-cloud-showers-heavy",
    congestion_extrema: "fa-car", interrupcion_transporte: "fa-bus", falla_infraestructura: "fa-bolt",
    obra_vial: "fa-person-digging", evento_masivo: "fa-users", emergencia: "fa-truck-medical",
  };
  let map, routesLayer, nodesLayer, alertsLayer, eventsLayer;

  function initMap() {
    map = L.map("gdMap", { scrollWheelZoom: true }).setView([4.5, -74.0], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    routesLayer = L.layerGroup().addTo(map);
    nodesLayer = L.layerGroup().addTo(map);
    alertsLayer = L.layerGroup().addTo(map);
    eventsLayer = L.layerGroup().addTo(map);
  }

  function scaleRadius(total, min = 6, max = 22) {
    return Math.min(max, min + Math.sqrt(total) * 1.1);
  }

  function scaleWeight(total, min = 1.5, max = 7) {
    return Math.min(max, min + Math.log(total + 1) * 0.9);
  }

  function renderRoutes(routes) {
    routesLayer.clearLayers();
    routes.forEach((r) => {
      const color = RISK_COLOR[r.semaforo] || RISK_COLOR.verde;
      const line = L.polyline(
        [[r.origen.lat, r.origen.lon], [r.destino.lat, r.destino.lon]],
        { color, weight: scaleWeight(r.total_embarques), opacity: 0.55 }
      );
      line.bindPopup(`
        <div class="gd-popup-title">${r.corredor}</div>
        <div class="gd-popup-row"><b>${gdFormatNumber(r.total_embarques, 0)}</b> embarques</div>
        <div class="gd-popup-row">OTIF: <b>${gdFormatPct(r.otif_pct)}</b></div>
        <div class="gd-popup-row">Riesgo promedio: <b style="color:${color}">${gdFormatPct(r.riesgo_promedio_pct)}</b></div>
        <div class="gd-popup-row">Lead Time promedio: <b>${gdFormatNumber(r.leadtime_promedio_dias)} días</b></div>
      `);
      line.addTo(routesLayer);
    });
  }

  function renderNodes(nodes) {
    nodesLayer.clearLayers();
    nodes.forEach((n) => {
      const color = RISK_COLOR[n.semaforo] || RISK_COLOR.verde;
      const marker = L.circleMarker([n.lat, n.lon], {
        radius: scaleRadius(n.total_embarques),
        color: "#fff", weight: 2, fillColor: color, fillOpacity: 0.85,
      });
      const tags = [];
      if (n.es_puerto) tags.push("Puerto marítimo");
      if (n.es_aeropuerto_principal) tags.push("Aeropuerto principal");
      marker.bindPopup(`
        <div class="gd-popup-title">${n.municipio}</div>
        ${tags.length ? `<div class="gd-popup-row">${tags.join(" · ")}</div>` : ""}
        <div class="gd-popup-row"><b>${gdFormatNumber(n.total_embarques, 0)}</b> embarques (origen + destino)</div>
        <div class="gd-popup-row">OTIF: <b>${gdFormatPct(n.otif_pct)}</b></div>
        <div class="gd-popup-row">Riesgo promedio: <b style="color:${color}">${gdFormatPct(n.riesgo_promedio_pct)}</b> (${n.nivel_riesgo})</div>
      `);
      marker.addTo(nodesLayer);
    });
  }

  function renderAlerts(alerts) {
    alertsLayer.clearLayers();
    alerts.forEach((a) => {
      const icon = L.divIcon({
        className: "",
        html: `<div style="background:#e11d48;color:#fff;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 3px rgba(225,29,72,.25);font-size:11px;"><i class="fa-solid fa-triangle-exclamation"></i></div>`,
        iconSize: [22, 22], iconAnchor: [11, 11],
      });
      const jitter = () => (Math.random() - 0.5) * 0.15;
      const marker = L.marker([a.lat + jitter(), a.lon + jitter()], { icon });
      marker.bindPopup(`
        <div class="gd-popup-title gd-mono">${a.id_viaje}</div>
        <div class="gd-popup-row">${a.municipio_origen} → ${a.municipio_destino}</div>
        <div class="gd-popup-row">Corredor: ${a.corredor}</div>
        <div class="gd-popup-row">Probabilidad de incumplimiento: <b style="color:#e11d48;">${gdFormatPct(a.probabilidad_pct)}</b></div>
      `);
      marker.addTo(alertsLayer);
    });
  }

  const ESTADO_LABEL = {
    confirmado: "Confirmado", probable: "Probable", previsto: "Previsto",
    activo: "Activo", resuelto: "Resuelto", no_confirmado: "Sin confirmar",
  };

  function confianzaTono(c) {
    if (c >= 0.6) return "rojo";
    if (c >= 0.35) return "amarillo";
    return "verde";
  }

  function renderEvents(events) {
    eventsLayer.clearLayers();
    events.forEach((e) => {
      const tono = confianzaTono(e.confidence);
      const icon = L.divIcon({
        className: "",
        html: `<div style="background:${RISK_COLOR[tono]};color:#fff;width:26px;height:26px;border-radius:8px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,.3);font-size:12px;"><i class="fa-solid ${EVENT_ICONS[e.event_type] || "fa-circle-exclamation"}"></i></div>`,
        iconSize: [26, 26], iconAnchor: [13, 13],
      });
      const marker = L.marker([e.latitude, e.longitude], { icon });
      marker.bindPopup(`
        <div class="gd-popup-title">${e.title}</div>
        <div class="gd-popup-row"><b>Tipo:</b> ${e.event_type.replace(/_/g, " ")}</div>
        <div class="gd-popup-row"><b>Ubicación:</b> ${e.location_text}</div>
        <div class="gd-popup-row"><b>Estado:</b> ${ESTADO_LABEL[e.status] || e.status}</div>
        <div class="gd-popup-row"><b>Confianza:</b> ${gdFormatPct(e.confidence * 100)} (${e.sources_count} fuente${e.sources_count > 1 ? "s" : ""})</div>
        <div class="gd-popup-row"><b>Fuente:</b> ${e.source_name}</div>
        <div class="gd-popup-row" style="margin-top:4px;"><a href="${e.source_url}" target="_blank" rel="noopener">Ver noticia original →</a></div>
      `);
      marker.addTo(eventsLayer);
    });
  }

  function renderEventsList(events) {
    const subtitle = document.getElementById("gdEventosSubtitle");
    const lista = document.getElementById("gdEventosLista");
    subtitle.textContent = `${events.length} evento(s) detectado(s) en las últimas 48h`;

    if (!events.length) {
      lista.innerHTML = `<div class="gd-empty-state"><i class="fa-regular fa-circle-check"></i><div>Sin eventos relevantes detectados</div></div>`;
      return;
    }

    lista.innerHTML = events.map((e) => {
      const tono = confianzaTono(e.confidence);
      return `
        <div style="padding:10px 0;border-bottom:1px solid var(--gd-border);">
          <div class="d-flex justify-content-between align-items-start gap-2">
            <div style="font-weight:600;">${e.title}</div>
            <span class="gd-badge ${tono}" style="flex-shrink:0;">${gdFormatPct(e.confidence * 100)}</span>
          </div>
          <div style="color:var(--gd-text-muted);margin-top:2px;">
            ${e.event_type.replace(/_/g, " ")} · ${e.location_text} · ${ESTADO_LABEL[e.status] || e.status}
          </div>
          <div style="color:var(--gd-text-subtle);font-size:11px;margin-top:2px;">
            ${e.source_name} · ${e.sources_count} fuente${e.sources_count > 1 ? "s" : ""} independiente${e.sources_count > 1 ? "s" : ""}
          </div>
        </div>`;
    }).join("");
  }

  async function loadEvents() {
    const { events } = await GeodisAPI.get("/api/events/live");
    renderEvents(events);
    renderEventsList(events);
  }

  async function loadWeather() {
    const data = await GeodisAPI.get("/api/events/weather");
    const row = document.getElementById("gdWeatherRow");
    if (!data.disponible) {
      row.innerHTML = `<div class="col-12"><div class="gd-card"><div class="gd-card-body" style="font-size:12.5px;color:var(--gd-text-muted);">
        <i class="fa-solid fa-cloud me-1"></i> Clima en tiempo real no configurado (falta OPENWEATHER_API_KEY). Configúrala en Render para activar esta tarjeta.
      </div></div></div>`;
      return;
    }
    const tono = data.nivel_riesgo_lluvia === "Alto" ? "gd-bg-danger" : data.nivel_riesgo_lluvia === "Medio" ? "gd-bg-warning" : "gd-bg-success";
    row.innerHTML = `
      <div class="col-6 col-lg-3"><div class="gd-kpi"><div class="gd-kpi-icon gd-bg-blue"><i class="fa-solid fa-temperature-half"></i></div>
        <div class="gd-kpi-label">Temperatura Bogotá</div><div class="gd-kpi-value">${gdFormatNumber(data.temperatura_c, 1)}°C</div></div></div>
      <div class="col-6 col-lg-3"><div class="gd-kpi"><div class="gd-kpi-icon ${tono}"><i class="fa-solid fa-cloud-rain"></i></div>
        <div class="gd-kpi-label">Lluvia (última hora)</div><div class="gd-kpi-value">${gdFormatNumber(data.lluvia_mm_1h, 1)} mm</div></div></div>
      <div class="col-6 col-lg-3"><div class="gd-kpi"><div class="gd-kpi-icon gd-bg-blue"><i class="fa-solid fa-droplet"></i></div>
        <div class="gd-kpi-label">Humedad</div><div class="gd-kpi-value">${gdFormatNumber(data.humedad_pct, 0)}%</div></div></div>
      <div class="col-6 col-lg-3"><div class="gd-kpi"><div class="gd-kpi-icon ${tono}"><i class="fa-solid fa-triangle-exclamation"></i></div>
        <div class="gd-kpi-label">Riesgo por lluvia</div><div class="gd-kpi-value">${data.nivel_riesgo_lluvia}</div></div></div>`;
  }

  async function loadAll() {
    const transporte = document.getElementById("mapTransporte").value;
    const qs = transporte ? `?tipo_transporte=${encodeURIComponent(transporte)}` : "";
    const [{ routes }, { nodes }, { alerts }] = await Promise.all([
      GeodisAPI.get(`/api/map/routes${qs}`),
      GeodisAPI.get(`/api/map/nodes${qs}`),
      GeodisAPI.get(`/api/map/alerts`),
    ]);
    renderRoutes(routes);
    renderNodes(nodes);
    renderAlerts(alerts);
    await loadEvents();
  }

  function bindLayerToggles() {
    document.getElementById("capaRutas").addEventListener("change", (e) => {
      if (e.target.checked) map.addLayer(routesLayer); else map.removeLayer(routesLayer);
    });
    document.getElementById("capaNodos").addEventListener("change", (e) => {
      if (e.target.checked) map.addLayer(nodesLayer); else map.removeLayer(nodesLayer);
    });
    document.getElementById("capaAlertas").addEventListener("change", (e) => {
      if (e.target.checked) map.addLayer(alertsLayer); else map.removeLayer(alertsLayer);
    });
    document.getElementById("capaEventos").addEventListener("change", (e) => {
      if (e.target.checked) map.addLayer(eventsLayer); else map.removeLayer(eventsLayer);
    });
    document.getElementById("mapTransporte").addEventListener("change", loadAll);

    document.getElementById("btnRefrescarEventos").addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      const original = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Consultando fuentes...';
      try {
        await GeodisAPI.post("/api/events/refresh");
        await loadEvents();
      } catch (err) {
        alert(err.message || "No fue posible refrescar eventos.");
      } finally {
        btn.disabled = false;
        btn.innerHTML = original;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    initMap();
    bindLayerToggles();
    await Promise.all([loadAll(), loadWeather()]);
  });
})();
