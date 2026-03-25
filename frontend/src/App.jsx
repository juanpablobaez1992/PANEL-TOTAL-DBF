import { Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
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

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<LoginPage />} path="/login" />
        <Route element={<ProtectedLayout />}>
          <Route element={<DashboardPage />} path="/" />
          <Route element={<DashboardPage />} path="/dashboard" />
          <Route element={<NewsPage />} path="/noticias/:id?" />
          <Route element={<UsersPage />} path="/usuarios" />
          <Route element={<SessionsPage />} path="/sesiones" />
        </Route>
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </AuthProvider>
  );
}
