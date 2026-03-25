import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function AppShell() {
  const { profile, signOut, error, setError } = useAuth();
  const isAdmin = profile.user.role === "admin";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Panel conectado</p>
          <h2>{profile.user.username}</h2>
          <p className="muted">Rol: {profile.user.role}</p>
        </div>
        <nav className="nav-list">
          <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/dashboard">
            Dashboard
          </NavLink>
          <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/noticias">
            Noticias
          </NavLink>
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
        <div className="permissions-box">
          <strong>Permisos</strong>
          <div className="permissions-list">
            {profile.permissions.map((permission) => (
              <span className="permission-chip" key={permission}>
                {permission}
              </span>
            ))}
          </div>
        </div>
        <button className="ghost-button" onClick={signOut} type="button">
          Cerrar sesion
        </button>
      </aside>
      <main className="content">
        {error ? (
          <section className="inline-error global-error">
            <span>{error}</span>
            <button className="ghost-button" onClick={() => setError("")} type="button">
              Cerrar
            </button>
          </section>
        ) : null}
        <Outlet />
      </main>
    </div>
  );
}
