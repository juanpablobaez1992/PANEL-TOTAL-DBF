import { useEffect, useMemo, useState } from "react";
import { ProgramForm } from "./ProgramForm";

function resolveImageUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const normalized = path.replaceAll("\\", "/");
  const marker = "/uploads/";
  const markerIndex = normalized.indexOf(marker);
  if (markerIndex >= 0) {
    return normalized.slice(markerIndex);
  }
  return "";
}

function EditorialForm({ noticia, loading, onSave }) {
  const [form, setForm] = useState({
    titular: noticia.titular || "",
    bajada: noticia.bajada || "",
    cuerpo: noticia.cuerpo || "",
  });

  useEffect(() => {
    setForm({
      titular: noticia.titular || "",
      bajada: noticia.bajada || "",
      cuerpo: noticia.cuerpo || "",
    });
  }, [noticia]);

  return (
    <section className="panel-subcard">
      <div className="section-head">
        <h4>Editorial</h4>
      </div>
      <div className="stack-form">
        <label className="field-stack">
          Titular
          <input onChange={(event) => setForm((current) => ({ ...current, titular: event.target.value }))} value={form.titular} />
        </label>
        <label className="field-stack">
          Bajada
          <textarea onChange={(event) => setForm((current) => ({ ...current, bajada: event.target.value }))} rows={3} value={form.bajada} />
        </label>
        <label className="field-stack">
          Cuerpo
          <textarea onChange={(event) => setForm((current) => ({ ...current, cuerpo: event.target.value }))} rows={8} value={form.cuerpo} />
        </label>
        <div className="inline-actions">
          <button disabled={loading} onClick={() => onSave(form)} type="button">
            {loading ? "Guardando..." : "Guardar editorial"}
          </button>
        </div>
      </div>
    </section>
  );
}

function PublicacionTimeline({ timeline }) {
  if (!timeline?.eventos?.length) {
    return <p className="muted">Sin eventos todavia.</p>;
  }

  return (
    <div className="mini-timeline">
      {timeline.eventos.map((evento) => (
        <article className="timeline-item compact-item" key={`${timeline.publicacion_id}-${evento.evento}-${evento.fecha}`}>
          <strong>{evento.evento}</strong>
          <span>{new Date(evento.fecha).toLocaleString()}</span>
          <p>{evento.detalle}</p>
        </article>
      ))}
    </div>
  );
}

function PublicacionCard({
  item,
  timeline,
  loadingKey,
  onSave,
  onSaveEstado,
  onPublicar,
  onReintentar,
}) {
  const [contenido, setContenido] = useState(item.contenido || "");
  const [estado, setEstado] = useState(item.estado);
  const [externalUrl, setExternalUrl] = useState(item.external_url || "");
  const [errorLog, setErrorLog] = useState(item.error_log || "");

  useEffect(() => {
    setContenido(item.contenido || "");
    setEstado(item.estado);
    setExternalUrl(item.external_url || "");
    setErrorLog(item.error_log || "");
  }, [item]);

  const imageUrl = resolveImageUrl(item.imagen_path);
  const isSavingCopy = loadingKey === `publicacion-${item.id}`;
  const isSavingState = loadingKey === `publicacion-estado-${item.id}`;
  const isPublishing = loadingKey === `publicacion-publicar-${item.id}`;
  const isRetrying = loadingKey === `publicacion-reintentar-${item.id}`;

  return (
    <article className="feed-item publication-card">
      <div className="section-head">
        <div>
          <strong>{item.canal.nombre}</strong>
          <p className="muted">{item.canal.tipo}</p>
        </div>
        <span className={`badge badge-${item.estado}`}>{item.estado}</span>
      </div>

      {imageUrl ? <img alt={`Preview ${item.canal.nombre}`} className="publication-image" src={imageUrl} /> : null}

      <label className="field-stack">
        Copy del canal
        <textarea onChange={(event) => setContenido(event.target.value)} rows={4} value={contenido} />
      </label>

      <div className="form-grid">
        <label className="field-stack">
          Estado manual
          <select onChange={(event) => setEstado(event.target.value)} value={estado}>
            <option disabled value="pendiente">
              pendiente
            </option>
            <option value="omitido">omitido</option>
            <option value="publicado">publicado</option>
            <option value="error">error</option>
          </select>
        </label>
        <label className="field-stack">
          URL externa
          <input onChange={(event) => setExternalUrl(event.target.value)} placeholder="https://..." value={externalUrl} />
        </label>
      </div>

      <label className="field-stack">
        Error log
        <textarea onChange={(event) => setErrorLog(event.target.value)} rows={3} value={errorLog} />
      </label>

      <div className="inline-actions">
        <button disabled={isSavingCopy} onClick={() => onSave(item.id, { contenido })} type="button">
          {isSavingCopy ? "Guardando..." : "Guardar copy"}
        </button>
        <button
          className="ghost-button"
          disabled={isSavingState}
          onClick={() => onSaveEstado(item.id, { estado, external_url: externalUrl || null, error_log: errorLog || null })}
          type="button"
        >
          {isSavingState ? "Guardando..." : "Guardar estado"}
        </button>
        <button
          disabled={isPublishing || item.estado === "publicado" || item.estado === "omitido"}
          onClick={() => onPublicar(item.id)}
          type="button"
        >
          {isPublishing ? "Publicando..." : "Publicar canal"}
        </button>
        <button
          className="ghost-button"
          disabled={isRetrying || item.estado !== "error"}
          onClick={() => onReintentar(item.id)}
          type="button"
        >
          {isRetrying ? "Reintentando..." : "Reintentar"}
        </button>
        {item.external_url ? (
          <a className="external-link" href={item.external_url} rel="noreferrer" target="_blank">
            Abrir publicacion
          </a>
        ) : null}
      </div>

      <div className="meta-grid">
        <span className="muted">External ID: {item.external_id || "sin registrar"}</span>
        <span className="muted">Publicado: {item.publicado_at ? new Date(item.publicado_at).toLocaleString() : "pendiente"}</span>
      </div>

      <div>
        <h5>Timeline del canal</h5>
        <PublicacionTimeline timeline={timeline} />
      </div>
    </article>
  );
}

function PublicacionesForm({
  publicaciones,
  publicacionesTimeline,
  loadingKey,
  onSave,
  onSaveEstado,
  onPublicar,
  onReintentar,
}) {
  const timelineByPublication = useMemo(
    () => Object.fromEntries((publicacionesTimeline || []).map((item) => [item.publicacion_id, item])),
    [publicacionesTimeline],
  );

  return (
    <section className="panel-subcard">
      <div className="section-head">
        <h4>Canales y resultados</h4>
      </div>
      <div className="feed-list">
        {publicaciones.map((item) => (
          <PublicacionCard
            item={item}
            key={item.id}
            loadingKey={loadingKey}
            onPublicar={onPublicar}
            onReintentar={onReintentar}
            onSave={onSave}
            onSaveEstado={onSaveEstado}
            timeline={timelineByPublication[item.id]}
          />
        ))}
      </div>
    </section>
  );
}

export function NewsDetail({
  detail,
  onAction,
  onSaveEditorial,
  onSavePublicacion,
  onSaveEstadoPublicacion,
  onPublicarPublicacion,
  onReintentarPublicacion,
  busyAction,
}) {
  if (!detail) {
    return (
      <section className="panel-card detail-card">
        <p className="muted">Selecciona una noticia para ver el detalle editorial.</p>
      </section>
    );
  }

  const { noticia, timeline, publicaciones_timeline: publicacionesTimeline, preflight } = detail;
  const isBusy = (action) => busyAction === action || busyAction === `${action}-${noticia.id}`;

  return (
    <section className="panel-card detail-card">
      <div className="section-head">
        <div>
          <h3>{noticia.titular || noticia.hecho}</h3>
          <p className="muted">{noticia.bajada || "Sin bajada"}</p>
        </div>
        <span className={`badge badge-${noticia.estado}`}>{noticia.estado}</span>
      </div>

      <div className="action-grid">
        <button disabled={isBusy("generar")} onClick={() => onAction("generar")} type="button">
          Generar
        </button>
        <button disabled={isBusy("aprobar")} onClick={() => onAction("aprobar")} type="button">
          Aprobar
        </button>
        <button disabled={isBusy("publicar")} onClick={() => onAction("publicar")} type="button">
          Publicar
        </button>
        <button disabled={isBusy("preflight")} onClick={() => onAction("preflight")} type="button">
          Revalidar
        </button>
      </div>

      <ProgramForm
        currentValue={noticia.programada_para}
        loading={isBusy("programar") || isBusy("cancelar-programacion")}
        onCancel={() => onAction("cancelar-programacion")}
        onSubmit={(value) => onAction("programar", value)}
      />

      <EditorialForm loading={busyAction === `editorial-${noticia.id}`} noticia={noticia} onSave={onSaveEditorial} />
      <PublicacionesForm
        loadingKey={busyAction}
        onPublicar={onPublicarPublicacion}
        onReintentar={onReintentarPublicacion}
        onSave={onSavePublicacion}
        onSaveEstado={onSaveEstadoPublicacion}
        publicaciones={noticia.publicaciones || []}
        publicacionesTimeline={publicacionesTimeline || []}
      />

      <div className="detail-columns">
        <div>
          <h4>Timeline general</h4>
          <div className="timeline-list">
            {timeline.map((item) => (
              <article className="timeline-item" key={`${item.evento}-${item.fecha}`}>
                <strong>{item.evento}</strong>
                <span>{new Date(item.fecha).toLocaleString()}</span>
                <p>{item.detalle}</p>
              </article>
            ))}
          </div>
        </div>
        <div>
          <h4>Preflight</h4>
          <p className={`preflight-state ${preflight.lista_para_publicar ? "ok" : "warn"}`}>
            {preflight.detalle_general}
          </p>
          <div className="timeline-list">
            {preflight.canales.map((item) => (
              <article className="timeline-item" key={item.publicacion_id || item.canal_id}>
                <strong>{item.canal_nombre}</strong>
                <span>{item.listo ? "Listo" : "Con bloqueos"}</span>
                <p>{item.detalle}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
