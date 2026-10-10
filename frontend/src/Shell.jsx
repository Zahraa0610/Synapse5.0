import { Component } from "react";
import { NavLink, Navigate, useLocation, useNavigate } from "react-router-dom";
import { homeFor } from "./api";
import { useAuth, useI18n } from "./context";
import { LangToggle, Mark } from "./ui";

const PHONE_NAV = {
  caregiver: [
    ["/home", "Home", "home"],
    ["/passport", "Passport", "passport"],
    ["/care", "Care", "care"],
    ["/requests", "Rides", "map"],
    ["/me", "Support", "support"],
  ],
  volunteer: [
    ["/volunteer", "Tasks", "tasks"],
    ["/volunteer/support", "Map", "map"],
    ["/volunteer/notices", "Alerts", "alerts"],
    ["/me", "Profile", "profile"],
  ],
  donor: [
    ["/donor", "Needs", "home"],
    ["/donor/gifts", "My gifts", "tasks"],
    ["/me", "Profile", "profile"],
  ],
};

const DESK_NAV = {
  shelter_coordinator: [
    ["/shelter", "Overview"],
    ["/shelter/residents", "Residents"],
    ["/shelter/supplies", "Supplies"],
    ["/shelter/shortages", "Shortages"],
    ["/shelter/exchange", "Exchange"],
    ["/shelter/donations", "Donations"],
    ["/shelter/volunteers", "Volunteers"],
    ["/shelter/complaints", "Complaints"],
    ["/shelter/reports", "Reports"],
  ],
  doctor: [["/doctor", "Patients"]],
  nurse: [["/doctor", "Patients"]],
  psychologist: [["/doctor", "Patients"]],
  ministry: [
    ["/ministry", "Overview"],
    ["/ministry/shelters", "Shelters"],
    ["/ministry/complaints", "Complaints"],
    ["/ministry/ngos", "NGOs"],
    ["/ministry/donations", "Donations"],
    ["/ministry/reports", "Reports"],
  ],
  ngo: [["/ngo", "Coordination"]],
};

class PageBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error">
          This page could not open. {this.state.error.message}
        </div>
      );
    }
    return this.props.children;
  }
}

export default function Shell({ children }) {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const phone = PHONE_NAV[user.role];
  if (phone) {
    const volunteer = user.role === "volunteer";
    return (
      <div className={`shell ${volunteer ? "volunteer-shell" : ""}`}>
        <div className="phone-shell">
          <header className={`topbar ${volunteer ? "volunteer-topbar" : ""}`}>
            <div className="inline"><Mark /><strong>Ma'ak</strong></div>
            <LangToggle />
          </header>
          <PageBoundary resetKey={location.pathname}>{children}</PageBoundary>
        </div>
        <nav className="bottom-nav">
          {phone.map(([to, label, icon]) => (
            <NavLink key={to} to={to} end={to.split("/").length <= 2}>
              {icon && <NavIcon name={icon} />}
              {t(label)}
            </NavLink>
          ))}
        </nav>
      </div>
    );
  }
  const links = DESK_NAV[user.role] || [];
  return (
    <div className="desk">
      <aside className="sidebar">
        <div className="brand-block" style={{ padding: "8px 12px 16px" }}>
          <div className="inline"><Mark /><strong>Ma'ak</strong></div>
          <div className="small" style={{ opacity: 0.8, marginTop: 8 }}>{user.full_name}</div>
        </div>
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/shelter" || to === "/ministry" || to === "/doctor" || to === "/ngo"}>
            {t(label)}
          </NavLink>
        ))}
        <div style={{ marginTop: "auto" }} />
        <button className="linkish" type="button" onClick={async () => { try { await logout(); navigate("/login"); } catch (err) { window.alert(err.message); } }}>{t("Sign out")}</button>
      </aside>
      <main className="desk-main">
        <div className="desk-top">
          <div>
            <div className="muted small">{t(roleLabel(user.role))}</div>
            <h2>{user.full_name}</h2>
          </div>
          <LangToggle />
        </div>
        <PageBoundary resetKey={location.pathname}>{children}</PageBoundary>
      </main>
    </div>
  );
}

function NavIcon({ name }) {
  const paths = {
    tasks: <><path d="M5 5h14v15H5z" /><path d="m8 10 2 2 4-4M8 16h7" /></>,
    map: <><path d="M12 21s6-5.2 6-11a6 6 0 1 0-12 0c0 5.8 6 11 6 11Z" /><circle cx="12" cy="10" r="2" /></>,
    alerts: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
    profile: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
    home: <><path d="m3 11 9-8 9 8" /><path d="M5 10v11h14V10M9 21v-7h6v7" /></>,
    passport: <><path d="M5 3h14v18H5z" /><path d="M9 8h6M12 5v6" /></>,
    care: <><path d="M3 12h4l2-5 4 10 2-5h6" /></>,
    support: <><path d="M4 5h16v13H8l-4 3V5Z" /></>,
  };
  return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
}

export function roleLabel(role) {
  return {
    caregiver: "User / caregiver",
    volunteer: "Volunteer",
    doctor: "Doctor",
    nurse: "Nurse",
    psychologist: "Psychologist",
    shelter_coordinator: "Shelter coordinator",
    donor: "Donor",
    ministry: "Ministry of Public Health",
    ngo: "NGO",
  }[role] || role;
}

export function Guard({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="app-loading">Ma'ak</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export function Guest({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="app-loading">Ma'ak</div>;
  if (user) return <Navigate to={user.requested_role ? "/me" : homeFor(user.role)} replace />;
  return children;
}
