import { Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { AutomationPage } from "./pages/AutomationPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CanalesPage } from "./pages/CanalesPage";
import { LoginPage } from "./pages/LoginPage";
import { NewsPage } from "./pages/NewsPage";
import { SessionsPage } from "./pages/SessionsPage";
import { UsersPage } from "./pages/UsersPage";

function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <AppShell />
    </ProtectedRoute>
  );
}

function AdminOnly({ children }) {
  return <ProtectedRoute requireAdmin>{children}</ProtectedRoute>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<LoginPage />} path="/login" />
        <Route element={<ProtectedLayout />}>
          <Route element={<DashboardPage />} path="/" />
          <Route element={<DashboardPage />} path="/dashboard" />
          <Route element={<NewsPage />} path="/noticias/:id?" />
          <Route
            element={
              <AdminOnly>
                <AutomationPage />
              </AdminOnly>
            }
            path="/automation"
          />
          <Route
            element={
              <AdminOnly>
                <CanalesPage />
              </AdminOnly>
            }
            path="/canales"
          />
          <Route
            element={
              <AdminOnly>
                <UsersPage />
              </AdminOnly>
            }
            path="/usuarios"
          />
          <Route
            element={
              <AdminOnly>
                <SessionsPage />
              </AdminOnly>
            }
            path="/sesiones"
          />
        </Route>
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </AuthProvider>
  );
}
