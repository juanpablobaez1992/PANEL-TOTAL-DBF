import { useState } from "react";

const initialForm = {
  username: "",
  password: "",
  role: "editor",
  activo: true,
};

export function UserForm({ onSubmit, loading }) {
  const [form, setForm] = useState(initialForm);

  async function handleSubmit(event) {
    event.preventDefault();
    await onSubmit(form);
    setForm(initialForm);
  }

  return (
    <section className="panel-card">
      <div className="section-head">
        <h3>Crear usuario</h3>
      </div>
      <form className="stack-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label className="field-stack">
            Usuario
            <input
              onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
              required
              value={form.username}
            />
          </label>
          <label className="field-stack">
            Contrasena
            <input
              minLength={6}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              required
              type="password"
              value={form.password}
            />
          </label>
          <label className="field-stack">
            Rol
            <select value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}>
              <option value="editor">Editor</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <label className="checkbox">
            <input
              checked={form.activo}
              onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))}
              type="checkbox"
            />
            Activo
          </label>
        </div>
        <button className="primary-button" disabled={!form.username || !form.password || loading} type="submit">
          {loading ? "Guardando..." : "Crear usuario"}
        </button>
      </form>
    </section>
  );
}
