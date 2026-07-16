/* Cliente REST minimalista compartido por todas las paginas. */
const GeodisAPI = (() => {
  async function request(path, options = {}) {
    const opts = {
      method: options.method || "GET",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      credentials: "same-origin",
    };
    if (options.body !== undefined) opts.body = JSON.stringify(options.body);

    const res = await fetch(path, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { /* respuesta sin cuerpo JSON */ }

    if (!res.ok) {
      const message = (data && data.error) || `Error ${res.status}`;
      if (res.status === 401 && !path.includes("/auth/")) {
        window.location.href = "/login";
      }
      throw new Error(message);
    }
    return data;
  }

  return {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body }),
    put: (path, body) => request(path, { method: "PUT", body }),
    del: (path) => request(path, { method: "DELETE" }),
  };
})();

function gdFormatCOP(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(value);
}
function gdFormatNumber(value, decimals = 1) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("es-CO", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
}
function gdFormatPct(value, decimals = 1) {
  if (value === null || value === undefined) return "—";
  return `${gdFormatNumber(value, decimals)}%`;
}
function gdFormatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d)) return value;
  return new Intl.DateTimeFormat("es-CO", { year: "numeric", month: "short", day: "2-digit" }).format(d);
}
function gdInitials(name) {
  if (!name) return "?";
  return name.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
}
function gdDebounce(fn, wait = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
}
