import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const initialLogin = { username: "admin", password: "admin" };

export function LoginPage() {
  const { isAuthenticated, signIn, error: authError, setError } = useAuth();
  const [form, setForm] = useState(initialLogin);
  const [loading, setLoading] = useState(false);
  const location = useLocation();

  if (isAuthenticated) {
    return <Navigate replace to={location.state?.from || "/dashboard"} />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await signIn(form);
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <p className="eyebrow">Despacho Panel</p>
        <h1>Ingresar al centro de publicación</h1>
        <p className="muted">Administrá noticias, validá integraciones y dispará publicaciones desde un solo lugar.</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Usuario
            <input
              value={form.username}
              onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
            />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            />
          </label>
          {authError ? <div className="inline-error">{authError}</div> : null}
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
      </div>
    </div>
  );
}
