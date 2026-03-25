import { Link } from "react-router-dom";

function InlineActionButton({ actionKey, busyAction, disabled, label, onClick }) {
  return (
    <button
      className="ghost-button inline-action-button"
      disabled={disabled || busyAction === actionKey}
      onClick={onClick}
      type="button"
    >
      {busyAction === actionKey ? "Procesando..." : label}
    </button>
  );
}

export function NewsList({
  noticias,
  selectedId,
  total,
  page,
  pageSize,
  onPageChange,
  onInlineAction,
  onStatusChange,
  busyAction,
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <section className="panel-card news-list-card">
      <div className="section-head">
        <h3>Noticias</h3>
        <span>
          {total} resultados · pagina {page} de {totalPages}
        </span>
      </div>
      <div className="news-list">
        {noticias.map((item) => (
          <article className={`news-item ${selectedId === item.id ? "selected" : ""}`} key={item.id}>
            <Link className="news-link" to={`/noticias/${item.id}`}>
              <div className="news-item-head">
                <strong>{item.titular || item.hecho}</strong>
                <span className={`badge badge-${item.estado}`}>{item.estado}</span>
              </div>
              <p>{item.bajada || item.hecho}</p>
              <small>
                {item.lugar || "Sin lugar"} · {item.categoria}
              </small>
            </Link>
            <div className="inline-actions">
              <select
                className="status-select"
                defaultValue={item.estado}
                onChange={(event) => onStatusChange(item.id, event.target.value)}
              >
                <option value="borrador">Borrador</option>
                <option value="generado">Generado</option>
                <option value="aprobado">Aprobado</option>
                <option disabled value="publicado">
                  Publicado
                </option>
                <option disabled value="error">
                  Error
                </option>
              </select>
              <InlineActionButton
                actionKey={`generar-${item.id}`}
                busyAction={busyAction}
                disabled={item.estado === "generado" || item.estado === "aprobado" || item.estado === "publicado"}
                label="Generar"
                onClick={() => onInlineAction(item.id, "generar")}
              />
              <InlineActionButton
                actionKey={`aprobar-${item.id}`}
                busyAction={busyAction}
                disabled={item.estado !== "generado"}
                label="Aprobar"
                onClick={() => onInlineAction(item.id, "aprobar")}
              />
              <InlineActionButton
                actionKey={`preflight-${item.id}`}
                busyAction={busyAction}
                disabled={false}
                label="Preflight"
                onClick={() => onInlineAction(item.id, "preflight")}
              />
              <InlineActionButton
                actionKey={`publicar-${item.id}`}
                busyAction={busyAction}
                disabled={item.estado !== "aprobado"}
                label="Publicar"
                onClick={() => onInlineAction(item.id, "publicar")}
              />
            </div>
          </article>
        ))}
      </div>
      <div className="pager">
        <button className="ghost-button" disabled={page <= 1} onClick={() => onPageChange(page - 1)} type="button">
          Anterior
        </button>
        <span className="muted">
          Mostrando {noticias.length} de {total}
        </span>
        <button
          className="ghost-button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          type="button"
        >
          Siguiente
        </button>
      </div>
    </section>
  );
}
