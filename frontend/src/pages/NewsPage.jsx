import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { panelApi } from "../api";
import { NewsDetail } from "../components/NewsDetail";
import { NewsFilters } from "../components/NewsFilters";
import { NewsList } from "../components/NewsList";
import { useAuth } from "../context/AuthContext";
import { usePolling } from "../hooks/usePolling";

export function NewsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { setError } = useAuth();
  const [filters, setFilters] = useState({ q: "", estado: "", soloProgramadas: false });
  const [page, setPage] = useState({ items: [], total: 0, page: 1, page_size: 12 });
  const [detail, setDetail] = useState(null);
  const [busyAction, setBusyAction] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const selectedId = id ? Number(id) : null;

  const loadList = useCallback(async () => {
    try {
      const payload = await panelApi.noticias({ ...filters, page: currentPage, pageSize: page.page_size });
      setPage(payload);
      if (!selectedId && payload.items?.[0]?.id) {
        navigate(`/noticias/${payload.items[0].id}`, { replace: true });
      }
    } catch (currentError) {
      setError(currentError.message);
    }
  }, [currentPage, filters, navigate, page.page_size, selectedId, setError]);

  const loadDetail = useCallback(async () => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    try {
      const payload = await panelApi.noticiaDetalle(selectedId);
      setDetail(payload);
    } catch (currentError) {
      setError(currentError.message);
    }
  }, [selectedId, setError]);

  useEffect(() => {
    loadList();
  }, [loadList]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  usePolling(() => {
    loadList();
    loadDetail();
  }, 30000, true);

  async function runAction(targetId, action, value) {
    setBusyAction(`${action}-${targetId}`);
    try {
      if (action === "generar") await panelApi.generar(targetId);
      if (action === "aprobar") await panelApi.aprobar(targetId);
      if (action === "preflight") await panelApi.preflight(targetId);
      if (action === "publicar") await panelApi.publicar(targetId);
      if (action === "programar") await panelApi.programar(targetId, new Date(value).toISOString());
      if (action === "cancelar-programacion") await panelApi.cancelarProgramacion(targetId);
      await loadList();
      if (selectedId === targetId) {
        await loadDetail();
      } else if (action === "preflight") {
        navigate(`/noticias/${targetId}`);
      }
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handleAction(action, value) {
    if (!selectedId) return;
    await runAction(selectedId, action, value);
  }

  async function handleStatusChange(targetId, estado) {
    try {
      setBusyAction(`estado-${targetId}`);
      await panelApi.actualizarEstadoNoticia(targetId, estado);
      await loadList();
      if (selectedId === targetId) {
        await loadDetail();
      }
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handleSaveEditorial(payload) {
    if (!selectedId) return;
    try {
      setBusyAction(`editorial-${selectedId}`);
      const updated = await panelApi.actualizarEditorialNoticia(selectedId, payload);
      setDetail(updated);
      await loadList();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handleSavePublicacion(publicacionId, payload) {
    try {
      setBusyAction(`publicacion-${publicacionId}`);
      const updated = await panelApi.actualizarPublicacion(publicacionId, payload);
      setDetail(updated);
      await loadList();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handleSaveEstadoPublicacion(publicacionId, payload) {
    try {
      setBusyAction(`publicacion-estado-${publicacionId}`);
      const updated = await panelApi.actualizarEstadoPublicacion(publicacionId, payload);
      setDetail(updated);
      await loadList();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handlePublicarPublicacion(publicacionId) {
    try {
      setBusyAction(`publicacion-publicar-${publicacionId}`);
      const updated = await panelApi.publicarPublicacion(publicacionId);
      setDetail(updated);
      await loadList();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handleReintentarPublicacion(publicacionId) {
    try {
      setBusyAction(`publicacion-reintentar-${publicacionId}`);
      const updated = await panelApi.reintentarPublicacion(publicacionId);
      setDetail(updated);
      await loadList();
    } catch (currentError) {
      setError(currentError.message);
    } finally {
      setBusyAction("");
    }
  }

  return (
    <>
      <header className="hero">
        <div>
          <p className="eyebrow">Noticias</p>
          <h1>Revision editorial y acciones rapidas</h1>
          <p className="muted">Filtra noticias, revisa preflight por canal y opera el flujo completo.</p>
        </div>
      </header>

      <section className="workspace-grid">
        <div>
          <NewsFilters filters={filters} onChange={setFilters} />
          <NewsList
            busyAction={busyAction}
            noticias={page.items || []}
            onInlineAction={runAction}
            onPageChange={setCurrentPage}
            onStatusChange={handleStatusChange}
            page={currentPage}
            pageSize={page.page_size || 12}
            selectedId={selectedId}
            total={page.total || 0}
          />
        </div>
        <NewsDetail
          busyAction={busyAction}
          detail={detail}
          onAction={handleAction}
          onPublicarPublicacion={handlePublicarPublicacion}
          onReintentarPublicacion={handleReintentarPublicacion}
          onSaveEditorial={handleSaveEditorial}
          onSavePublicacion={handleSavePublicacion}
          onSaveEstadoPublicacion={handleSaveEstadoPublicacion}
        />
      </section>
    </>
  );
}
