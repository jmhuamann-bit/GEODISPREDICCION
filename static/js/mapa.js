(function () {
  const RISK_COLOR = { verde: "#16a34a", amarillo: "#f59e0b", rojo: "#e11d48" };
  let map, routesLayer, nodesLayer, alertsLayer;

  function initMap() {
    map = L.map("gdMap", { scrollWheelZoom: true }).setView([4.5, -74.0], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    routesLayer = L.layerGroup().addTo(map);
    nodesLayer = L.layerGroup().addTo(map);
    alertsLayer = L.layerGroup().addTo(map);
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
    document.getElementById("mapTransporte").addEventListener("change", loadAll);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    initMap();
    bindLayerToggles();
    await loadAll();
  });
})();
