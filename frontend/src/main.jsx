import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import "./styles.css";
import { AuthProvider, I18nProvider, useAuth } from "./context";
import { homeFor } from "./api";
import Shell, { Guard, Guest } from "./Shell";
import { EmergencyPage, LandingPage, LoginPage, PublicEmergencyPage, RegisterPage } from "./AuthPages";
import { CarePage, HomePage, PassportPage, ProfilePage, RequestsPage } from "./PatientPages";
import { ROLE_ROUTES } from "./RolePages";

const PATIENT = ["caregiver"];

// Wraps a signed-in page in the guard + role shell (bottom nav or sidebar).
function Private({ children, roles }) {
  return (
    <Guard roles={roles}>
      <Shell>{children}</Shell>
    </Guard>
  );
}

function NotFound() {
  const { user } = useAuth();
  return (
    <div className="center-page">
      <div className="auth-wrap stack">
        <h1>Page not found</h1>
        <p className="muted">This page does not exist.</p>
        <Link to={user ? homeFor(user.role) : "/"}>Go back home</Link>
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Guest><LandingPage /></Guest>} />
      <Route path="/login" element={<Guest><LoginPage /></Guest>} />
      <Route path="/register" element={<Guest><RegisterPage /></Guest>} />
      <Route path="/emergency" element={<EmergencyPage />} />
      <Route path="/e/:token" element={<PublicEmergencyPage />} />

      {/* Patient / caregiver */}
      <Route path="/home" element={<Private roles={PATIENT}><HomePage /></Private>} />
      <Route path="/passport" element={<Private roles={PATIENT}><PassportPage /></Private>} />
      <Route path="/care" element={<Private roles={PATIENT}><CarePage /></Private>} />
      <Route path="/requests" element={<Private roles={PATIENT}><RequestsPage /></Private>} />
      <Route path="/me" element={<Private><ProfilePage /></Private>} />

      {/* Volunteer, donor, shelter, doctor, ministry, NGO */}
      {ROLE_ROUTES.map(([path, Page, roles]) => (
        <Route key={path} path={path} element={<Private roles={roles}><Page /></Private>} />
      ))}

      <Route path="/dashboard" element={<Guard><RoleHome /></Guard>} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

function RoleHome() {
  const { user } = useAuth();
  return <Navigate to={homeFor(user.role)} replace />;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <I18nProvider>
      <AuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthProvider>
    </I18nProvider>
  </StrictMode>
);
