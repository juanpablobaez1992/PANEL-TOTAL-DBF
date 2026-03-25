const ACCESS_TOKEN_KEY = "despacho_panel_access_token";
const REFRESH_TOKEN_KEY = "despacho_panel_refresh_token";

export function getStoredTokens() {
  return {
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
  };
}

export function storeTokens({ access_token, refresh_token }) {
  localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || JSON.stringify(payload);
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export async function login(username, password) {
  return request("/api/panel/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function refreshSession(refreshToken) {
  return request("/api/panel/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function logout(refreshToken) {
  return request("/api/panel/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

async function authorizedRequest(path, options = {}, retry = true) {
  const { accessToken, refreshToken } = getStoredTokens();
  if (!accessToken) {
    throw new Error("No hay sesion activa.");
  }

  try {
    return await request(path, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Bearer ${accessToken}`,
      },
    });
  } catch (error) {
    if (!retry || !refreshToken || !String(error.message).includes("401")) {
      throw error;
    }
    const refreshed = await refreshSession(refreshToken);
    storeTokens(refreshed);
    return authorizedRequest(path, options, false);
  }
}

export const panelApi = {
  me: () => authorizedRequest("/api/panel/me"),
  dashboard: () => authorizedRequest("/api/panel/dashboard"),
  activity: () => authorizedRequest("/api/panel/actividad"),
  notifications: () => authorizedRequest("/api/panel/notificaciones"),
  sessions: ({ page = 1, pageSize = 20, q = "", soloActivas = false } = {}) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (q) params.set("q", q);
    if (soloActivas) params.set("solo_activas", "true");
    return authorizedRequest(`/api/panel/sesiones?${params.toString()}`);
  },
  users: ({ page = 1, pageSize = 20, q = "", activo = "" } = {}) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (q) params.set("q", q);
    if (activo !== "") params.set("activo", String(activo));
    return authorizedRequest(`/api/panel/usuarios?${params.toString()}`);
  },
  createUser: (payload) =>
    authorizedRequest("/api/panel/usuarios", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateUser: (userId, payload) =>
    authorizedRequest(`/api/panel/usuarios/${userId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  revokeSession: (sessionId) =>
    authorizedRequest(`/api/panel/sesiones/revocar/${sessionId}`, {
      method: "POST",
    }),
  noticias: ({ page = 1, pageSize = 12, q = "", estado = "", soloProgramadas = false } = {}) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (q) params.set("q", q);
    if (estado) params.set("estado", estado);
    if (soloProgramadas) params.set("solo_programadas", "true");
    return authorizedRequest(`/api/panel/noticias?${params.toString()}`);
  },
  noticiaDetalle: (noticiaId) => authorizedRequest(`/api/panel/noticias/${noticiaId}`),
  actualizarEstadoNoticia: (noticiaId, estado) =>
    authorizedRequest(`/api/panel/noticias/${noticiaId}/estado`, {
      method: "PATCH",
      body: JSON.stringify({ estado }),
    }),
  actualizarEditorialNoticia: (noticiaId, payload) =>
    authorizedRequest(`/api/panel/noticias/${noticiaId}/editorial`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  actualizarPublicacion: (publicacionId, payload) =>
    authorizedRequest(`/api/panel/publicaciones/${publicacionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  actualizarEstadoPublicacion: (publicacionId, payload) =>
    authorizedRequest(`/api/panel/publicaciones/${publicacionId}/estado`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  publicarPublicacion: (publicacionId) =>
    authorizedRequest(`/api/panel/publicaciones/${publicacionId}/publicar`, {
      method: "POST",
    }),
  reintentarPublicacion: (publicacionId) =>
    authorizedRequest(`/api/panel/publicaciones/${publicacionId}/reintentar`, {
      method: "POST",
    }),
  generar: (noticiaId) =>
    authorizedRequest(`/api/panel/noticias/${noticiaId}/acciones/generar`, { method: "POST" }),
  aprobar: (noticiaId) =>
    authorizedRequest(`/api/panel/noticias/${noticiaId}/acciones/aprobar`, { method: "POST" }),
  preflight: (noticiaId) =>
    authorizedRequest(`/api/panel/noticias/${noticiaId}/acciones/preflight`),
  programar: (noticiaId, programadaPara) =>
    authorizedRequest(`/api/panel/noticias/${noticiaId}/acciones/programar`, {
      method: "POST",
      body: JSON.stringify({ programada_para: programadaPara }),
    }),
  cancelarProgramacion: (noticiaId) =>
    authorizedRequest(`/api/panel/noticias/${noticiaId}/acciones/cancelar-programacion`, {
      method: "POST",
    }),
  publicar: (noticiaId) =>
    authorizedRequest(`/api/panel/noticias/${noticiaId}/acciones/publicar`, { method: "POST" }),
};
