import { useCallback, useEffect, useState } from "react";
import { FeedList } from "../components/FeedList";
import { MetricCard } from "../components/MetricCard";
import { useAuth } from "../context/AuthContext";
import { usePolling } from "../hooks/usePolling";
import { panelApi } from "../api";

export function DashboardPage() {
  const { setError } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [activity, setActivity] = useState([]);
  const [notifications, setNotifications] = useState([]);

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
    } catch (currentError) {
      setError(currentError.message);
    }
  }, [setError]);

  useEffect(() => {
    load();
  }, [load]);

  usePolling(load, 30000, true);

  const estadoItems = Object.entries(dashboard?.noticias_por_estado || {});
  const publicacionesItems = Object.entries(dashboard?.publicaciones_por_estado || {});

  return (
    <>
      <header className="hero">
        <div>
          <p className="eyebrow">De Buena Fe Digital</p>
          <h1>Centro editorial y de publicación</h1>
          <p className="muted">Vista general de noticias, actividad, integraciones y cola editorial.</p>
        </div>
      </header>

      <section className="metrics-grid">
        <MetricCard title="Noticias programadas" value={dashboard?.noticias_programadas?.length || 0} hint="En cola del scheduler" />
        <MetricCard title="Noticias recientes" value={dashboard?.noticias_recientes?.length || 0} hint="Últimas 10 cargadas" />
        <MetricCard title="Notificaciones" value={notifications.length} hint="Pendientes de atención" />
        <MetricCard title="Actividad" value={activity.length} hint="Últimos eventos del panel" />
      </section>

      <section className="dual-grid">
        <FeedList items={notifications} title="Notificaciones" />
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
