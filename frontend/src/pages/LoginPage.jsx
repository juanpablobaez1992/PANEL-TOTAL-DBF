import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const initialLogin = { username: "", password: "" };

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
        <h1>Ingresar al centro de publicacion</h1>
        <p className="muted">Administra noticias, valida integraciones y dispara publicaciones desde un solo lugar.</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Usuario
            <input
              onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
              value={form.username}
            />
          </label>
          <label>
            Contrasena
            <input
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              type="password"
              value={form.password}
            />
          </label>
          {authError ? <div className="inline-error">{authError}</div> : null}
          <p className="muted">Usa el usuario del panel configurado en el archivo `.env` del backend.</p>
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
      </div>
    </div>
  );
}
