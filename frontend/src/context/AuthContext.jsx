import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { clearTokens, getStoredTokens, login, logout, panelApi, storeTokens } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [profile, setProfile] = useState(null);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState("");

  async function hydrate() {
    const { accessToken } = getStoredTokens();
    if (!accessToken) {
      setProfile(null);
      setBooting(false);
      return;
    }
    try {
      const payload = await panelApi.me();
      setProfile(payload);
      setError("");
    } catch (currentError) {
      clearTokens();
      setProfile(null);
      setError(currentError.message);
    } finally {
      setBooting(false);
    }
  }

  useEffect(() => {
    hydrate();
  }, []);

  async function signIn(form) {
    const payload = await login(form.username, form.password);
    storeTokens(payload);
    const me = await panelApi.me();
    setProfile(me);
    setError("");
    return payload;
  }

  async function signOut() {
    const { refreshToken } = getStoredTokens();
    if (refreshToken) {
      try {
        await logout(refreshToken);
      } catch {
        // no-op
      }
    }
    clearTokens();
    setProfile(null);
    setError("");
  }

  const value = useMemo(
    () => ({
      profile,
      booting,
      error,
      setError,
      signIn,
      signOut,
      refreshProfile: hydrate,
      isAuthenticated: Boolean(profile),
    }),
    [profile, booting, error],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de AuthProvider.");
  }
  return context;
}
