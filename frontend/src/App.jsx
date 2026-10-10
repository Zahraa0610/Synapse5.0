import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { EmergencyPage, LandingPage, LoginPage, PublicEmergencyPage, RegisterPage } from "./AuthPages";
import { DoctorPage, MinistryPage, NgoPage } from "./DeskPages";
import { CarePage, HomePage, PassportPage, ProfilePage, RequestsPage } from "./PatientPages";
import { ShelterPage } from "./ShelterPages";
import Shell from "./Shell";
import { DonorPage, VolunteerPage } from "./VolunteerPages";
import { homeFor } from "./api";
import { useAuth } from "./context";
import { Guest } from "./Shell";

function Protected() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="app-loading">Ma'ak</div>;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <Shell>
      <Outlet />
    </Shell>
  );
}

function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={homeFor(user.role)} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Guest><LandingPage /></Guest>} />
      <Route path="/login" element={<Guest><LoginPage /></Guest>} />
      <Route path="/register" element={<Guest><RegisterPage /></Guest>} />
      <Route path="/emergency" element={<EmergencyPage />} />
      <Route path="/e/:token" element={<PublicEmergencyPage />} />
      <Route element={<Protected />}>
        <Route path="/home" element={<HomePage />} />
        <Route path="/passport" element={<PassportPage />} />
        <Route path="/care" element={<CarePage />} />
        <Route path="/requests" element={<RequestsPage />} />
        <Route path="/me" element={<ProfilePage />} />
        <Route path="/volunteer" element={<VolunteerPage mode="tasks" />} />
        <Route path="/volunteer/notices" element={<VolunteerPage mode="notices" />} />
        <Route path="/volunteer/support" element={<VolunteerPage mode="support" />} />
        <Route path="/donor" element={<DonorPage />} />
        <Route path="/donor/gifts" element={<DonorPage gifts />} />
        <Route path="/shelter" element={<ShelterPage />} />
        <Route path="/shelter/:section" element={<ShelterPage />} />
        <Route path="/doctor" element={<DoctorPage />} />
        <Route path="/ministry" element={<MinistryPage />} />
        <Route path="/ministry/:section" element={<MinistryPage />} />
        <Route path="/ngo" element={<NgoPage />} />
        <Route path="*" element={<HomeRedirect />} />
      </Route>
    </Routes>
  );
}
