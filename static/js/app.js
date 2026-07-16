/* Logica comun de shell: usuario en topbar, logout, toggle sidebar movil. */
document.addEventListener("DOMContentLoaded", async () => {
  const toggle = document.getElementById("gdSidebarToggle");
  const sidebar = document.getElementById("gdSidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (window.innerWidth < 992 && sidebar.classList.contains("open") &&
          !sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove("open");
      }
    });
  }

  const logoutBtn = document.getElementById("gdLogoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      try { await GeodisAPI.post("/api/auth/logout"); } catch (err) { /* noop */ }
      window.location.href = "/login";
    });
  }

  try {
    const { user } = await GeodisAPI.get("/api/auth/me");
    if (user) {
      const nameEl = document.getElementById("gdUserName");
      const roleEl = document.getElementById("gdUserRole");
      const avatarEl = document.getElementById("gdUserAvatar");
      if (nameEl) nameEl.textContent = user.nombre_completo;
      if (roleEl) roleEl.textContent = user.rol;
      if (avatarEl) avatarEl.textContent = gdInitials(user.nombre_completo);
      window.gdCurrentUser = user;
    }
  } catch (err) { /* no autenticado: paginas protegidas ya redirigen via Flask-Login */ }
});
