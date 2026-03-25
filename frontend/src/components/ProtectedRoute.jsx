import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function ProtectedRoute({ children, requireAdmin = false }) {
  const { isAuthenticated, booting, profile } = useAuth();
  const location = useLocation();

  if (booting) {
    return <div className="center-shell">Cargando panel...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  }

  if (requireAdmin && profile?.user?.role !== "admin") {
    return <Navigate replace to="/dashboard" />;
  }

  return children;
}
