import { useCallback, useEffect, useState } from "react";
import { panelApi } from "../api";
import { useAuth } from "../context/AuthContext";
import { usePolling } from "../hooks/usePolling";

export function SessionsPage() {
  const { setError } = useAuth();
  const [sessions, setSessions] = useState({ items: [], total: 0, page: 1, page_size: 10 });
  const [currentPage, setCurrentPage] = useState(1);
  const [revokingId, setRevokingId] = useState(null);
  const [filters, setFilters] = useState({ q: "", soloActivas: false });

  const load = useCallback(async () => {
    try {
      const payload = await panelApi.sessions({
        page: currentPage,
        pageSize: sessions.page_size,
        q: filters.q,
        soloActivas: filters.soloActivas,
      });
      setSessions(payload);
    } catch (currentError) {
      setError(currentError.message);
    }
  }, [currentPage, filters.q, filters.soloActivas, setError, sessions.page_size]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters]);

  usePolling(load, 30000, true);

  async function handleRevoke(sessionId) {
    setRevokingId(sessionId);
    try {
      await panelApi.revokeSession(sessionId);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setRevokingId(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil(sessions.total / sessions.page_size));

  return (
    <>
      <header className="hero">
        <div>
          <p className="eyebrow">Sesiones</p>
          <h1>Control de sesiones revocables</h1>
          <p className="muted">Filtra accesos activos, busca por user-agent y revoca sesiones puntuales.</p>
        </div>
      </header>

      <section className="panel-card">
        <div className="section-head">
          <h3>Sesiones registradas</h3>
          <span>
            {sessions.total} sesiones - pagina {currentPage} de {totalPages}
          </span>
        </div>
        <div className="filters-row">
          <input
            onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))}
            placeholder="Buscar por user-agent"
            value={filters.q}
          />
          <label className="checkbox">
            <input
              checked={filters.soloActivas}
              onChange={(event) => setFilters((current) => ({ ...current, soloActivas: event.target.checked }))}
              type="checkbox"
            />
            Solo activas
          </label>
        </div>
        <div className="feed-list">
          {sessions.items.length === 0 ? <p className="muted">No hay sesiones para los filtros actuales.</p> : null}
          {sessions.items.map((item) => (
            <article className="session-item" key={item.id}>
              <div>
                <strong>Sesion #{item.id}</strong>
                <p>{item.user_agent || "Sin user-agent"}</p>
                <small className="muted">Expira: {new Date(item.expires_at).toLocaleString()}</small>
              </div>
              <button disabled={revokingId === item.id} onClick={() => handleRevoke(item.id)} type="button">
                {revokingId === item.id ? "Revocando..." : "Revocar"}
              </button>
            </article>
          ))}
        </div>
        <div className="pager">
          <button className="ghost-button" disabled={currentPage <= 1} onClick={() => setCurrentPage((value) => value - 1)} type="button">
            Anterior
          </button>
          <span className="muted">
            Mostrando {sessions.items.length} de {sessions.total}
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
    </>
  );
}
