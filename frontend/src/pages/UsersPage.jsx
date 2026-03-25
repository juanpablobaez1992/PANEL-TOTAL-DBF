import { useCallback, useEffect, useState } from "react";
import { panelApi } from "../api";
import { UserForm } from "../components/UserForm";
import { useAuth } from "../context/AuthContext";
import { usePolling } from "../hooks/usePolling";

function UserRowEditor({ item, loading, onSave }) {
  const [form, setForm] = useState({
    username: item.username,
    role: item.role,
    activo: item.activo,
    password: "",
  });

  useEffect(() => {
    setForm({ username: item.username, role: item.role, activo: item.activo, password: "" });
  }, [item]);

  function handleSave() {
    const payload = { username: form.username, role: form.role, activo: form.activo };
    if (form.password.trim()) payload.password = form.password.trim();
    onSave(item.id, payload);
  }

  return (
    <article className="feed-item user-row" key={item.id}>
      <div className="form-grid compact-grid">
        <label className="field-stack">
          Usuario
          <input
            onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
            value={form.username}
          />
        </label>
        <label className="field-stack">
          Rol
          <select onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))} value={form.role}>
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <label className="field-stack">
          Nueva contraseña
          <input
            autoComplete="new-password"
            onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            placeholder="Dejar vacío para no cambiar"
            type="password"
            value={form.password}
          />
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
      <div className="inline-actions">
        <button disabled={loading} onClick={handleSave} type="button">
          {loading ? "Guardando..." : "Guardar"}
        </button>
        <span className="muted">Creado: {new Date(item.created_at).toLocaleString()}</span>
      </div>
    </article>
  );
}

export function UsersPage() {
  const { setError } = useAuth();
  const [users, setUsers] = useState({ items: [], total: 0, page: 1, page_size: 10 });
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [savingUserId, setSavingUserId] = useState(null);
  const [filters, setFilters] = useState({ q: "", activo: "" });

  const load = useCallback(async () => {
    try {
      const payload = await panelApi.users({
        page: currentPage,
        pageSize: users.page_size,
        q: filters.q,
        activo: filters.activo,
      });
      setUsers(payload);
    } catch (currentError) {
      setError(currentError.message);
    }
  }, [currentPage, filters.activo, filters.q, setError, users.page_size]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters]);

  usePolling(load, 45000, true);

  async function handleCreate(form) {
    setLoading(true);
    try {
      await panelApi.createUser(form);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleInlineSave(userId, form) {
    setSavingUserId(userId);
    try {
      await panelApi.updateUser(userId, form);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setSavingUserId(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil(users.total / users.page_size));

  return (
    <>
      <header className="hero">
        <div>
          <p className="eyebrow">Usuarios</p>
          <h1>Administracion de accesos</h1>
          <p className="muted">Crea editores o admins reales, filtra cuentas y ajusta cada usuario inline.</p>
        </div>
      </header>

      <section className="dual-grid">
        <UserForm loading={loading} onSubmit={handleCreate} />
        <section className="panel-card">
          <div className="section-head">
            <h3>Usuarios existentes</h3>
            <span>
              {users.total} en total - pagina {currentPage} de {totalPages}
            </span>
          </div>
          <div className="filters-row">
            <input
              onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))}
              placeholder="Buscar por usuario"
              value={filters.q}
            />
            <select onChange={(event) => setFilters((current) => ({ ...current, activo: event.target.value }))} value={filters.activo}>
              <option value="">Todos</option>
              <option value="true">Activos</option>
              <option value="false">Inactivos</option>
            </select>
          </div>
          <div className="feed-list">
            {users.items.length === 0 ? <p className="muted">No hay usuarios para los filtros actuales.</p> : null}
            {users.items.map((item) => (
              <UserRowEditor
                item={item}
                key={item.id}
                loading={savingUserId === item.id}
                onSave={handleInlineSave}
              />
            ))}
          </div>
          <div className="pager">
            <button className="ghost-button" disabled={currentPage <= 1} onClick={() => setCurrentPage((value) => value - 1)} type="button">
              Anterior
            </button>
            <span className="muted">
              Mostrando {users.items.length} de {users.total}
            </span>
            <button
              className="ghost-button"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((value) => value + 1)}
              type="button"
            >
              Siguiente
            </button>
          </div>
        </section>
      </section>
    </>
  );
}
