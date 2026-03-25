import { useCallback, useEffect, useState } from "react";
import { panelApi } from "../api";
import { MetricCard } from "../components/MetricCard";
import { useAuth } from "../context/AuthContext";
import { usePolling } from "../hooks/usePolling";

function SchedulerCard({ title, description, enabled, interval, nextRunAt, onEnabledChange, onIntervalChange, saveLabel, loading, onSave }) {
  return (
    <article className="panel-subcard">
      <div className="section-head">
        <div>
          <h4>{title}</h4>
          <p className="muted">{description}</p>
        </div>
        <span className={`status-pill ${enabled ? "status-ok" : "status-muted"}`}>{enabled ? "Activo" : "Pausado"}</span>
      </div>

      <div className="form-grid">
        <label className="checkbox">
          <input checked={enabled} onChange={(event) => onEnabledChange(event.target.checked)} type="checkbox" />
          Habilitado
        </label>
        <label className="field-stack">
          Intervalo en minutos
          <input min="5" onChange={(event) => onIntervalChange(event.target.value)} type="number" value={interval} />
        </label>
      </div>

      <p className="muted">Proxima corrida: {nextRunAt ? new Date(nextRunAt).toLocaleString() : "deshabilitado"}</p>

      <div className="inline-actions">
        <button disabled={loading} onClick={onSave} type="button">
          {loading ? "Guardando..." : saveLabel}
        </button>
      </div>
    </article>
  );
}

function QueueItem({ item }) {
  return (
    <article className="story-item">
      <div className="story-copy">
        <strong>{item.title}</strong>
        <p>{item.excerpt || "Sin extracto"}</p>
        {item.categories?.length ? (
          <div className="chip-row">
            {item.categories.map((category) => (
              <span className="config-chip" key={`${item.id}-${category}`}>
                {category}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="story-meta">
        <a className="external-link" href={item.link} rel="noreferrer" target="_blank">
          Abrir en WP
        </a>
      </div>
    </article>
  );
}

export function AutomationPage() {
  const { setError } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [queue, setQueue] = useState([]);
  const [rules, setRules] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [evergreen, setEvergreen] = useState({ category_ids: [], categories: [] });
  const [preview, setPreview] = useState(null);
  const [schedulerForm, setSchedulerForm] = useState({
    regular_enabled: false,
    regular_interval_minutes: 60,
    evergreen_enabled: false,
    evergreen_interval_minutes: 120,
  });
  const [ruleForm, setRuleForm] = useState({ category_slug: "", prompt_rule: "" });
  const [accountForm, setAccountForm] = useState({ name: "", platform: "facebook", page_id: "", access_token: "" });
  const [busyKey, setBusyKey] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [dashboardPayload, queuePayload, rulesPayload, accountsPayload, evergreenPayload] = await Promise.all([
        panelApi.automationDashboard(),
        panelApi.automationQueue(),
        panelApi.automationRules(),
        panelApi.automationAccounts(),
        panelApi.automationEvergreen(),
      ]);
      setDashboard(dashboardPayload);
      setQueue(queuePayload);
      setRules(rulesPayload);
      setAccounts(accountsPayload);
      setEvergreen(evergreenPayload);
      setSchedulerForm({
        regular_enabled: dashboardPayload.scheduler.regular_enabled,
        regular_interval_minutes: dashboardPayload.scheduler.regular_interval_minutes,
        evergreen_enabled: dashboardPayload.scheduler.evergreen_enabled,
        evergreen_interval_minutes: dashboardPayload.scheduler.evergreen_interval_minutes,
      });
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

  async function saveScheduler(kind) {
    const payload =
      kind === "regular"
        ? {
            regular_enabled: schedulerForm.regular_enabled,
            regular_interval_minutes: Number(schedulerForm.regular_interval_minutes) || 60,
          }
        : {
            evergreen_enabled: schedulerForm.evergreen_enabled,
            evergreen_interval_minutes: Number(schedulerForm.evergreen_interval_minutes) || 120,
          };
    setBusyKey(`scheduler-${kind}`);
    try {
      await panelApi.updateAutomationScheduler(payload);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  async function runRegularNow() {
    setBusyKey("run-regular");
    try {
      await panelApi.runAutomationRegular();
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  async function prepareEvergreen() {
    setBusyKey("prepare-evergreen");
    try {
      const payload = await panelApi.prepareAutomationEvergreen();
      setPreview(payload);
      setError("");
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  async function publishEvergreen() {
    if (!preview) return;
    setBusyKey("publish-evergreen");
    try {
      await panelApi.publishAutomationEvergreen({
        post_id: preview.post_id,
        title: preview.title,
        image_url: preview.image_url,
        image_urls: preview.image_urls || [],
        utm_link: preview.utm_link,
        fb_copy: preview.fb_copy,
        ig_copy: preview.ig_copy,
        is_evergreen: true,
      });
      setPreview(null);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  async function saveRule() {
    setBusyKey("save-rule");
    try {
      await panelApi.saveAutomationRule(ruleForm);
      setRuleForm({ category_slug: "", prompt_rule: "" });
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  async function deleteRule(ruleId) {
    setBusyKey(`delete-rule-${ruleId}`);
    try {
      await panelApi.deleteAutomationRule(ruleId);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  async function saveAccount() {
    setBusyKey("save-account");
    try {
      await panelApi.createAutomationAccount(accountForm);
      setAccountForm({ name: "", platform: "facebook", page_id: "", access_token: "" });
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  async function deleteAccount(accountId) {
    setBusyKey(`delete-account-${accountId}`);
    try {
      await panelApi.deleteAutomationAccount(accountId);
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  async function saveEvergreenCategories() {
    setBusyKey("save-evergreen-categories");
    try {
      await panelApi.updateAutomationEvergreen({ category_ids: evergreen.category_ids });
      await load();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyKey("");
    }
  }

  function toggleEvergreenCategory(categoryId) {
    setEvergreen((current) => ({
      ...current,
      category_ids: current.category_ids.includes(categoryId)
        ? current.category_ids.filter((item) => item !== categoryId)
        : [...current.category_ids, categoryId],
    }));
  }

  const scheduler = dashboard?.scheduler;
  const kpis = dashboard?.kpis;
  const logs = dashboard?.recent_logs || [];

  return (
    <>
      <header className="hero">
        <div>
          <p className="eyebrow">Automation</p>
          <h1>Modulo AUTOPUBLICATE integrado</h1>
          <p className="muted">
            Usa WordPress, Gemini y Meta desde la misma webapp para correr el bot regular, configurar evergreen, administrar cuentas
            extras y revisar el historial real de ejecuciones.
          </p>
        </div>
      </header>

      {loading ? (
        <section className="panel-card">
          <p className="muted">Cargando modulo automation...</p>
        </section>
      ) : null}

      <section className="metrics-grid">
        <MetricCard title="Ejecuciones" value={kpis?.total_ejecuciones || 0} hint="Historico total" />
        <MetricCard title="Exitos FB" value={kpis?.exitos_fb || 0} hint="Publicaciones con salida OK" />
        <MetricCard title="Exitos IG" value={kpis?.exitos_ig || 0} hint="Publicaciones con salida OK" />
        <MetricCard title="En cola" value={dashboard?.queue_count || 0} hint="Posts pendientes desde WordPress" />
      </section>

      <section className="dual-grid">
        <SchedulerCard
          description="Procesa automaticamente la siguiente noticia pendiente de WordPress."
          enabled={schedulerForm.regular_enabled}
          interval={schedulerForm.regular_interval_minutes}
          loading={busyKey === "scheduler-regular"}
          nextRunAt={scheduler?.regular_next_run_at}
          onEnabledChange={(value) => setSchedulerForm((current) => ({ ...current, regular_enabled: value }))}
          onIntervalChange={(value) => setSchedulerForm((current) => ({ ...current, regular_interval_minutes: value }))}
          onSave={() => saveScheduler("regular")}
          saveLabel="Guardar bot regular"
          title="Bot regular"
        />
        <SchedulerCard
          description="Busca una nota vieja, genera copies evergreen y la republica por intervalo."
          enabled={schedulerForm.evergreen_enabled}
          interval={schedulerForm.evergreen_interval_minutes}
          loading={busyKey === "scheduler-evergreen"}
          nextRunAt={scheduler?.evergreen_next_run_at}
          onEnabledChange={(value) => setSchedulerForm((current) => ({ ...current, evergreen_enabled: value }))}
          onIntervalChange={(value) => setSchedulerForm((current) => ({ ...current, evergreen_interval_minutes: value }))}
          onSave={() => saveScheduler("evergreen")}
          saveLabel="Guardar bot evergreen"
          title="Bot evergreen"
        />
      </section>

      <section className="dual-grid">
        <section className="panel-card">
          <div className="section-head">
            <div>
              <h3>Cola de WordPress</h3>
              <p className="muted">Ultimo ID procesado: {scheduler?.last_processed_post_id ?? 0}</p>
            </div>
            <button disabled={busyKey === "run-regular"} onClick={runRegularNow} type="button">
              {busyKey === "run-regular" ? "Publicando..." : "Publicar siguiente ahora"}
            </button>
          </div>
          <div className="story-list">
            {queue.length === 0 ? <p className="muted">No hay posts pendientes en WordPress.</p> : null}
            {queue.slice(0, 8).map((item) => (
              <QueueItem item={item} key={item.id} />
            ))}
          </div>
        </section>

        <section className="panel-card">
          <div className="section-head">
            <div>
              <h3>Evergreen manual</h3>
              <p className="muted">Prepara una nota vieja, revisa los copies y lanzala cuando quieras.</p>
            </div>
            <button className="ghost-button" disabled={busyKey === "prepare-evergreen"} onClick={prepareEvergreen} type="button">
              {busyKey === "prepare-evergreen" ? "Buscando..." : "Buscar post evergreen"}
            </button>
          </div>

          {!preview ? <p className="muted">Todavia no hay una preview evergreen cargada.</p> : null}

          {preview ? (
            <div className="stack-form">
              <div className="story-item">
                <div className="story-copy">
                  <strong>{preview.title}</strong>
                  <p>{preview.excerpt}</p>
                </div>
                <div className="story-meta">
                  <a className="external-link" href={preview.link} rel="noreferrer" target="_blank">
                    Abrir origen
                  </a>
                </div>
              </div>

              <label className="field-stack">
                Copy Facebook
                <textarea
                  onChange={(event) => setPreview((current) => ({ ...current, fb_copy: event.target.value }))}
                  rows={6}
                  value={preview.fb_copy}
                />
              </label>

              <label className="field-stack">
                Copy Instagram
                <textarea
                  onChange={(event) => setPreview((current) => ({ ...current, ig_copy: event.target.value }))}
                  rows={6}
                  value={preview.ig_copy}
                />
              </label>

              <div className="inline-actions">
                <button disabled={busyKey === "publish-evergreen"} onClick={publishEvergreen} type="button">
                  {busyKey === "publish-evergreen" ? "Publicando..." : "Aprobar y publicar"}
                </button>
              </div>
            </div>
          ) : null}
        </section>
      </section>

      <section className="dual-grid">
        <section className="panel-card">
          <div className="section-head">
            <div>
              <h3>Reglas IA</h3>
              <p className="muted">Personaliza la salida de Gemini segun la categoria del post.</p>
            </div>
          </div>

          <div className="stack-form">
            <label className="field-stack">
              Categoria slug
              <input
                onChange={(event) => setRuleForm((current) => ({ ...current, category_slug: event.target.value }))}
                value={ruleForm.category_slug}
              />
            </label>
            <label className="field-stack">
              Instruccion
              <textarea
                onChange={(event) => setRuleForm((current) => ({ ...current, prompt_rule: event.target.value }))}
                rows={5}
                value={ruleForm.prompt_rule}
              />
            </label>
            <div className="inline-actions">
              <button disabled={busyKey === "save-rule"} onClick={saveRule} type="button">
                {busyKey === "save-rule" ? "Guardando..." : "Guardar regla"}
              </button>
            </div>
          </div>

          <div className="feed-list">
            {rules.length === 0 ? <p className="muted">No hay reglas creadas todavia.</p> : null}
            {rules.map((rule) => (
              <article className="feed-item" key={rule.id}>
                <div className="section-head">
                  <span className="config-chip">{rule.category_slug}</span>
                  <button
                    className="ghost-button"
                    disabled={busyKey === `delete-rule-${rule.id}`}
                    onClick={() => deleteRule(rule.id)}
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
                <p>{rule.prompt_rule}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel-card">
          <div className="section-head">
            <div>
              <h3>Cuentas Meta</h3>
              <p className="muted">Agrega fanpages o cuentas IG Business extra para publicar en paralelo.</p>
            </div>
          </div>

          <div className="stack-form">
            <label className="field-stack">
              Nombre
              <input onChange={(event) => setAccountForm((current) => ({ ...current, name: event.target.value }))} value={accountForm.name} />
            </label>
            <div className="form-grid">
              <label className="field-stack">
                Plataforma
                <select onChange={(event) => setAccountForm((current) => ({ ...current, platform: event.target.value }))} value={accountForm.platform}>
                  <option value="facebook">Facebook</option>
                  <option value="instagram">Instagram</option>
                </select>
              </label>
              <label className="field-stack">
                Page ID / Account ID
                <input onChange={(event) => setAccountForm((current) => ({ ...current, page_id: event.target.value }))} value={accountForm.page_id} />
              </label>
            </div>
            <label className="field-stack">
              Access token
              <input
                onChange={(event) => setAccountForm((current) => ({ ...current, access_token: event.target.value }))}
                type="password"
                value={accountForm.access_token}
              />
            </label>
            <div className="inline-actions">
              <button disabled={busyKey === "save-account"} onClick={saveAccount} type="button">
                {busyKey === "save-account" ? "Guardando..." : "Guardar cuenta"}
              </button>
            </div>
          </div>

          <div className="feed-list">
            {accounts.length === 0 ? <p className="muted">No hay cuentas extra configuradas.</p> : null}
            {accounts.map((account) => (
              <article className="feed-item" key={account.id}>
                <div className="section-head">
                  <div>
                    <strong>{account.name}</strong>
                    <p className="muted">
                      {account.platform} - {account.page_id}
                    </p>
                  </div>
                  <button
                    className="ghost-button"
                    disabled={busyKey === `delete-account-${account.id}`}
                    onClick={() => deleteAccount(account.id)}
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
                <p className="muted">Token: {account.token_hint}</p>
              </article>
            ))}
          </div>
        </section>
      </section>

      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>Categorias evergreen</h3>
            <p className="muted">Selecciona de que categorias de WordPress puede salir el reciclaje evergreen.</p>
          </div>
          <button
            className="ghost-button"
            disabled={busyKey === "save-evergreen-categories"}
            onClick={saveEvergreenCategories}
            type="button"
          >
            {busyKey === "save-evergreen-categories" ? "Guardando..." : "Guardar categorias"}
          </button>
        </div>

        <div className="chip-row">
          {evergreen.categories.map((item) => (
            <label className="config-chip checkbox-chip" key={item.id}>
              <input checked={evergreen.category_ids.includes(item.id)} onChange={() => toggleEvergreenCategory(item.id)} type="checkbox" />
              {item.name}
            </label>
          ))}
        </div>
      </section>

      <section className="panel-card">
        <div className="section-head">
          <h3>Ultimas ejecuciones</h3>
        </div>
        <div className="feed-list">
          {logs.length === 0 ? <p className="muted">No hay ejecuciones registradas todavia.</p> : null}
          {logs.map((item) => (
            <article className="feed-item" key={item.id}>
              <div className="section-head">
                <div>
                  <strong>{item.title}</strong>
                  <p className="muted">{new Date(item.created_at).toLocaleString()}</p>
                </div>
                <div className="chip-row">
                  <span className={`status-pill ${item.is_evergreen ? "status-warning" : "status-info"}`}>
                    {item.is_evergreen ? "Evergreen" : "Regular"}
                  </span>
                  <span className={`status-pill ${item.fb_success ? "status-ok" : "status-error"}`}>FB</span>
                  <span className={`status-pill ${item.ig_success ? "status-ok" : "status-error"}`}>IG</span>
                </div>
              </div>
              <p>{item.error_msg || "Ejecucion completada sin errores."}</p>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
