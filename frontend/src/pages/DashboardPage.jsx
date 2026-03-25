import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { panelApi } from "../api";
import { FeedList } from "../components/FeedList";
import { MetricCard } from "../components/MetricCard";
import { useAuth } from "../context/AuthContext";
import { usePolling } from "../hooks/usePolling";

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

  const estadoItems = Object.entries(dashboard?.noticias_por_estado || {});
  const publicacionesItems = Object.entries(dashboard?.publicaciones_por_estado || {});
  const integraciones = dashboard?.integraciones || [];
  const isAdmin = profile?.user?.role === "admin";

  return (
    <>
      <header className="hero">
        <div>
          <p className="eyebrow">De Buena Fe Digital</p>
          <h1>Centro editorial y de publicacion</h1>
          <p className="muted">Vista general de noticias, actividad, integraciones y cola editorial.</p>
        </div>
      </header>

      {loading ? (
        <section className="panel-card">
          <p className="muted">Cargando dashboard...</p>
        </section>
      ) : null}

      <section className="metrics-grid">
        <MetricCard title="Noticias programadas" value={dashboard?.noticias_programadas?.length || 0} hint="En cola del scheduler" />
        <MetricCard title="Noticias recientes" value={dashboard?.noticias_recientes?.length || 0} hint="Ultimas 10 cargadas" />
        <MetricCard title="Notificaciones" value={notifications.length} hint="Pendientes de atencion" />
        <MetricCard title="Actividad" value={activity.length} hint="Ultimos eventos del panel" />
      </section>

      <section className="dual-grid">
        <FeedList items={notifications} title="Notificaciones" />
        <FeedList items={activity} title="Actividad reciente" />
      </section>

      <section className="dual-grid">
        <section className="panel-card">
          <div className="section-head">
            <h3>Integraciones</h3>
          </div>
          <div className="feed-list">
            {integraciones.length === 0 ? <p className="muted">Sin integraciones diagnosticadas.</p> : null}
            {integraciones.map((item) => (
              <article className={`feed-item ${item.ok ? "" : "severity-warning"}`} key={item.nombre}>
                <strong>{item.nombre}</strong>
                <p>{item.detalle}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="panel-card">
          <div className="section-head">
            <h3>Accesos rapidos</h3>
          </div>
          <div className="quick-links">
            <Link className="nav-link quick-link" to="/dashboard">
              Ver estado general
            </Link>
            <Link className="nav-link quick-link" to="/noticias">
              Abrir mesa editorial
            </Link>
            {isAdmin ? (
              <Link className="nav-link quick-link" to="/sesiones">
                Revisar sesiones
              </Link>
            ) : (
              <Link className="nav-link quick-link" to="/noticias">
                Revisar publicaciones
              </Link>
            )}
          </div>
        </section>
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
