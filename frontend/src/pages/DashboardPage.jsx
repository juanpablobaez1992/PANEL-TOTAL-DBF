import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { panelApi } from "../api";
import { FeedList } from "../components/FeedList";
import { MetricCard } from "../components/MetricCard";
import { useAuth } from "../context/AuthContext";
import { usePolling } from "../hooks/usePolling";

function OperationCard({ title, description, to, tone = "default" }) {
  return (
    <Link className={`operation-card tone-${tone}`} to={to}>
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
      <span className="operation-link">Abrir modulo</span>
    </Link>
  );
}

function QueueCard({ title, items, emptyText }) {
  return (
    <section className="panel-card">
      <div className="section-head">
        <h3>{title}</h3>
      </div>
      <div className="story-list">
        {items.length === 0 ? <p className="muted">{emptyText}</p> : null}
        {items.map((item) => (
          <Link className="story-item" key={item.id} to={`/noticias/${item.id}`}>
            <div className="story-copy">
              <strong>{item.titular || item.hecho}</strong>
              <p>{item.bajada || item.hecho}</p>
            </div>
            <div className="story-meta">
              <span className={`status-pill status-${item.estado}`}>{item.estado}</span>
              <small>{new Date(item.updated_at || item.created_at).toLocaleString()}</small>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

function IntegrationList({ items }) {
  return (
    <div className="integration-grid">
      {items.length === 0 ? <p className="muted">Sin integraciones diagnosticadas.</p> : null}
      {items.map((item) => (
        <article className={`integration-card ${item.ok ? "is-ok" : "is-warning"}`} key={item.nombre}>
          <div className="integration-header">
            <strong>{item.nombre}</strong>
            <span className={`status-pill ${item.ok ? "status-ok" : "status-warning"}`}>{item.ok ? "Activo" : "Revisar"}</span>
          </div>
          <p className="muted">{item.detalle}</p>
        </article>
      ))}
    </div>
  );
}

export function DashboardPage() {
  const { profile, setError } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [activity, setActivity] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [dashboardPayload, activityPayload, notificationsPayload] = await Promise.all([
        panelApi.dashboard(),
        panelApi.activity(),
        panelApi.notifications(),
      ]);
      setDashboard(dashboardPayload);
      setActivity(activityPayload);
      setNotifications(notificationsPayload);
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

  usePolling(load, 30000, true);

  const estadoItems = useMemo(() => Object.entries(dashboard?.noticias_por_estado || {}), [dashboard]);
  const publicacionesItems = useMemo(() => Object.entries(dashboard?.publicaciones_por_estado || {}), [dashboard]);
  const integraciones = dashboard?.integraciones || [];
  const isAdmin = profile?.user?.role === "admin";
  const programadas = (dashboard?.noticias_programadas || []).slice(0, 6);
  const recientes = (dashboard?.noticias_recientes || []).slice(0, 6);

  return (
    <>
      <header className="hero">
        <div>
          <p className="eyebrow">AUTOPUBLICATE x DBF</p>
          <h1>Centro de operaciones de publicacion</h1>
          <p className="muted">
            Monitorea el estado general, revisa integraciones, abre la cola editorial y opera canales desde una interfaz mas cercana al
            dashboard operativo de AUTOPUBLICATE.
          </p>
        </div>
      </header>

      {loading ? (
        <section className="panel-card">
          <p className="muted">Cargando tablero operativo...</p>
        </section>
      ) : null}

      <section className="metrics-grid">
        <MetricCard title="En cola" value={programadas.length} hint="Noticias programadas" />
        <MetricCard title="Recientes" value={recientes.length} hint="Ultimas noticias cargadas" />
        <MetricCard title="Alertas" value={notifications.length} hint="Pendientes de atencion" />
        <MetricCard title="Actividad" value={activity.length} hint="Eventos recientes del panel" />
      </section>

      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>Acciones rapidas</h3>
            <p className="muted">Los accesos de uso diario quedan arriba, como en el tablero de autopublicacion.</p>
          </div>
        </div>
        <div className="operation-grid">
          <OperationCard
            description="Abri la mesa editorial para generar, aprobar, programar y publicar noticias."
            title="Mesa editorial"
            to="/noticias"
            tone="primary"
          />
          <OperationCard
            description="Corre el bot regular, revisa evergreen, reglas IA, cuentas Meta e historial de autopublicacion."
            title="Automation"
            to={isAdmin ? "/automation" : "/dashboard"}
            tone="primary"
          />
          <OperationCard
            description="Gestiona credenciales, auto-publicacion y estado de cada canal conectado."
            title="Canales y cuentas"
            to={isAdmin ? "/canales" : "/dashboard"}
            tone="success"
          />
          <OperationCard
            description="Controla accesos activos y revoca sesiones comprometidas o viejas."
            title="Sesiones"
            to={isAdmin ? "/sesiones" : "/dashboard"}
            tone="default"
          />
          <OperationCard
            description="Administra usuarios del panel y su nivel de acceso operativo."
            title="Usuarios"
            to={isAdmin ? "/usuarios" : "/dashboard"}
            tone="default"
          />
        </div>
      </section>

      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>Estado de conexiones</h3>
            <p className="muted">Diagnostico inmediato de WordPress, Meta, X y demas integraciones configuradas.</p>
          </div>
          {isAdmin ? (
            <Link className="ghost-button link-button" to="/canales">
              Administrar canales
            </Link>
          ) : null}
        </div>
        <IntegrationList items={integraciones} />
      </section>

      <section className="dual-grid">
        <QueueCard emptyText="No hay noticias programadas en este momento." items={programadas} title="Cola programada" />
        <QueueCard emptyText="Todavia no se cargaron noticias recientes." items={recientes} title="Revision reciente" />
      </section>

      <section className="dual-grid">
        <FeedList items={notifications} title="Alertas del panel" />
        <FeedList items={activity} title="Actividad reciente" />
      </section>

      <section className="metrics-grid compact">
        {estadoItems.map(([key, value]) => (
          <MetricCard hint="Noticias" key={key} title={key} value={value} />
        ))}
        {publicacionesItems.map(([key, value]) => (
          <MetricCard hint="Publicaciones" key={key} title={key} value={value} />
        ))}
      </section>
    </>
  );
}
