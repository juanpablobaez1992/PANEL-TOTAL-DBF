import { useCallback, useEffect, useState } from "react";
import { panelApi } from "../api";
import { useAuth } from "../context/AuthContext";
import { usePolling } from "../hooks/usePolling";

function prettyConfig(config) {
  return JSON.stringify(config || {}, null, 2);
}

function keySummary(config) {
  return Object.keys(config || {}).filter(Boolean);
}

function IntegrationCard({ item }) {
  return (
    <article className={`integration-card ${item.ok ? "is-ok" : "is-warning"}`}>
      <div className="integration-header">
        <strong>{item.nombre}</strong>
        <span className={`status-pill ${item.ok ? "status-ok" : "status-warning"}`}>{item.ok ? "Activo" : "Revisar"}</span>
      </div>
      <p className="muted">{item.detalle}</p>
    </article>
  );
}

function CanalCard({ canal, loadingKey, onToggleActivo, onToggleAuto, onSave }) {
  const [nombre, setNombre] = useState(canal.nombre);
  const [orden, setOrden] = useState(canal.orden);
  const [configText, setConfigText] = useState(prettyConfig(canal.config));
  const [jsonError, setJsonError] = useState("");

  useEffect(() => {
    setNombre(canal.nombre);
    setOrden(canal.orden);
    setConfigText(prettyConfig(canal.config));
    setJsonError("");
  }, [canal]);

  async function handleSave() {
    try {
      const config = JSON.parse(configText || "{}");
      setJsonError("");
      await onSave(canal.id, {
        nombre,
        orden: Number(orden) || 0,
        config,
      });
    } catch {
      setJsonError("El JSON de configuracion no es valido.");
    }
  }

  const configKeys = keySummary(canal.config);
  const saving = loadingKey === `save-${canal.id}`;
  const togglingActive = loadingKey === `toggle-active-${canal.id}`;
  const togglingAuto = loadingKey === `toggle-auto-${canal.id}`;

  return (
    <article className="channel-card">
      <div className="channel-card-head">
        <div>
          <p className="eyebrow">{canal.tipo}</p>
          <h3>{canal.nombre}</h3>
        </div>
        <div className="status-row">
          <span className={`status-pill ${canal.activo ? "status-ok" : "status-warning"}`}>
            {canal.activo ? "Activo" : "Pausado"}
          </span>
          <span className={`status-pill ${canal.auto_publicar ? "status-info" : "status-muted"}`}>
            {canal.auto_publicar ? "Auto ON" : "Manual"}
          </span>
        </div>
      </div>

      <div className="meta-row">
        <span className="muted">Orden {canal.orden}</span>
        <span className="muted">{configKeys.length ? `${configKeys.length} claves configuradas` : "Sin configuracion cargada"}</span>
      </div>

      {configKeys.length ? (
        <div className="chip-row">
          {configKeys.map((key) => (
            <span className="config-chip" key={key}>
              {key}
            </span>
          ))}
        </div>
      ) : null}

      <div className="form-grid">
        <label className="field-stack">
          Nombre visible
          <input onChange={(event) => setNombre(event.target.value)} value={nombre} />
        </label>
        <label className="field-stack">
          Orden
          <input min="0" onChange={(event) => setOrden(event.target.value)} type="number" value={orden} />
        </label>
      </div>

      <label className="field-stack">
        Configuracion JSON
        <textarea className="code-textarea" onChange={(event) => setConfigText(event.target.value)} rows={8} value={configText} />
      </label>

      {jsonError ? <div className="inline-error">{jsonError}</div> : null}

      <div className="inline-actions">
        <button className="ghost-button" disabled={togglingActive} onClick={() => onToggleActivo(canal.id)} type="button">
          {togglingActive ? "Actualizando..." : canal.activo ? "Desactivar canal" : "Activar canal"}
        </button>
        <button className="ghost-button" disabled={togglingAuto} onClick={() => onToggleAuto(canal.id)} type="button">
          {togglingAuto ? "Actualizando..." : canal.auto_publicar ? "Pasar a manual" : "Activar auto"}
        </button>
        <button disabled={saving} onClick={handleSave} type="button">
          {saving ? "Guardando..." : "Guardar canal"}
        </button>
      </div>
    </article>
  );
}

export function CanalesPage() {
  const { setError } = useAuth();
  const [canales, setCanales] = useState([]);
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingKey, setLoadingKey] = useState("");

  const load = useCallback(async () => {
    try {
      const [canalesPayload, integrationsPayload] = await Promise.all([
        panelApi.canales(),
        panelApi.integrations(),
      ]);
      setCanales(canalesPayload);
      setIntegrations(integrationsPayload);
      setError("");
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setLoading(false);
    }
  }, [setError]);

  useEffect(() => {
    load();
  }, [load]);

  usePolling(load, 45000, true);

  async function handleToggleActivo(canalId) {
    setLoadingKey(`toggle-active-${canalId}`);
    try {
      await panelApi.toggleCanalActivo(canalId);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setLoadingKey("");
    }
  }

  async function handleToggleAuto(canalId) {
    setLoadingKey(`toggle-auto-${canalId}`);
    try {
      await panelApi.toggleCanalAuto(canalId);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setLoadingKey("");
    }
  }

  async function handleSave(canalId, payload) {
    setLoadingKey(`save-${canalId}`);
    try {
      await panelApi.actualizarCanal(canalId, payload);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setLoadingKey("");
    }
  }

  async function handleSeed() {
    setLoadingKey("seed");
    try {
      await panelApi.seedCanales();
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setLoadingKey("");
    }
  }

  return (
    <>
      <header className="hero">
        <div>
          <p className="eyebrow">Canales y cuentas</p>
          <h1>Centro de conexiones y publicacion</h1>
          <p className="muted">Activa o pausa salidas, ajusta auto-publicacion y administra la configuracion por canal desde un unico panel.</p>
        </div>
      </header>

      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>Estado de integraciones</h3>
            <p className="muted">Diagnostico rapido de las credenciales y servicios conectados.</p>
          </div>
        </div>
        <div className="integration-grid">
          {integrations.length === 0 ? <p className="muted">No hay integraciones diagnosticadas todavia.</p> : null}
          {integrations.map((item) => (
            <IntegrationCard item={item} key={item.nombre} />
          ))}
        </div>
      </section>

      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>Canales de salida</h3>
            <p className="muted">La configuracion se guarda cifrada en backend y se aplica sobre las publicaciones ya generadas.</p>
          </div>
          <button className="ghost-button" disabled={loadingKey === "seed"} onClick={handleSeed} type="button">
            {loadingKey === "seed" ? "Creando..." : "Sembrar canales base"}
          </button>
        </div>

        {loading ? <p className="muted">Cargando canales...</p> : null}
        {!loading && canales.length === 0 ? <p className="muted">No hay canales cargados todavia.</p> : null}

        <div className="channel-grid">
          {canales.map((canal) => (
            <CanalCard
              canal={canal}
              key={canal.id}
              loadingKey={loadingKey}
              onSave={handleSave}
              onToggleActivo={handleToggleActivo}
              onToggleAuto={handleToggleAuto}
            />
          ))}
        </div>
      </section>
    </>
  );
}
