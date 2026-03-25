import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function AppShell() {
  const { profile, signOut, error, setError } = useAuth();
  const isAdmin = profile.user.role === "admin";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-frame">
          <div className="brand-block">
            <p className="eyebrow">Despacho editorial</p>
            <h2 className="brand-title">Panel De Buena Fe</h2>
            <p className="muted">Operacion diaria, revision de noticias y salidas a canales.</p>
          </div>

          <div className="sidebar-section">
            <p className="sidebar-label">Navegacion</p>
            <nav className="nav-list">
              <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/dashboard">
                Dashboard
              </NavLink>
              <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/noticias">
                Noticias
              </NavLink>
              {isAdmin ? (
                <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/automation">
                  Automation
                </NavLink>
              ) : null}
              {isAdmin ? (
                <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/canales">
                  Canales
                </NavLink>
              ) : null}
              {isAdmin ? (
                <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/usuarios">
                  Usuarios
                </NavLink>
              ) : null}
              {isAdmin ? (
                <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/sesiones">
                  Sesiones
                </NavLink>
              ) : null}
            </nav>
          </div>

          <div className="sidebar-profile">
            <p className="sidebar-label">Sesion activa</p>
            <strong>{profile.user.username}</strong>
            <p className="muted">Perfil {profile.user.role}</p>
            <button className="ghost-button sidebar-signout" onClick={signOut} type="button">
              Cerrar sesion
            </button>
          </div>
        </div>
      </aside>
      <main className="content">
        <div className="content-frame">
          {error ? (
            <section className="inline-error global-error">
              <span>{error}</span>
              <button className="ghost-button" onClick={() => setError("")} type="button">
                Cerrar
              </button>
            </section>
          ) : null}
          <Outlet />
        </div>
      </main>
    </div>
  );
}
