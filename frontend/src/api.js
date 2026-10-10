const TOKEN_KEY = "maak_token";
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && token) {
      setToken(null);
      window.dispatchEvent(new Event("maak-session-expired"));
    }
    const error = new Error(data.error || (path === "/auth/logout" && response.status === 404 ? "The running backend is outdated. Restart the updated backend before signing out." : "Something went wrong"));
    error.status = response.status;
    throw error;
  }
  return data;
}

export async function fileUrl(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!response.ok) {
    if (response.status === 401) { setToken(null); window.dispatchEvent(new Event("maak-session-expired")); }
    throw new Error("Could not open the file");
  }
  return URL.createObjectURL(await response.blob());
}

export async function logoutSession() {
  try {
    await api("/auth/logout", { method: "POST" });
  } catch (error) {
    // A 401 means this session is already expired or revoked.
    if (error.status !== 401) throw error;
  }
  setToken(null);
}

export const DEMO_ACCOUNTS = [
  ["Caregiver", "rania@maak.test"],
  ["Volunteer", "rana@maak.test"],
  ["Doctor", "nadine@maak.test"],
  ["Shelter", "jad@maak.test"],
  ["Donor", "lina@maak.test"],
  ["Ministry", "ministry@maak.test"],
  ["NGO", "ngo@maak.test"],
];

export const DEMO_PASSWORD = "maak1234";

export function homeFor(role) {
  if (role === "volunteer") return "/volunteer";
  if (role === "donor") return "/donor";
  if (role === "shelter_coordinator") return "/shelter";
  if (role === "doctor" || role === "nurse" || role === "psychologist") return "/doctor";
  if (role === "ministry") return "/ministry";
  if (role === "ngo") return "/ngo";
  return "/home";
}

export function canVisit(user, pathname) {
  if (!user) return false;
  if (pathname === "/me") return true;
  if (["doctor", "nurse", "psychologist", "shelter_coordinator", "ministry", "ngo"].includes(user.role) && user.verification_status !== "approved") return false;
  const routes = { caregiver: ["/home", "/passport", "/care", "/requests"], volunteer: ["/volunteer"], donor: ["/donor"], doctor: ["/doctor"], nurse: ["/doctor"], psychologist: ["/doctor"], shelter_coordinator: ["/shelter"], ministry: ["/ministry"], ngo: ["/ngo"] };
  return (routes[user.role] || []).some((prefix) => pathname === prefix || pathname.startsWith(prefix + "/"));
}

export function toneFor(status) {
  const value = String(status || "").toLowerCase();
  if (["shortage", "critical", "missed", "high", "declined", "cancelled", "overdue", "missing"].includes(value)) return "rose";
  if (["low", "checking", "documents_received", "requested", "under_review", "submitted", "pledged", "proposed", "open", "in_transit", "being_addressed", "acknowledged", "escalated"].includes(value)) return "amber";
  if (["available", "approved", "completed", "resolved", "accepted", "distributed", "delivered", "non_critical", "administered", "connected", "not_required", "received"].includes(value)) return "green";
  return "neutral";
}

export function formatWhen(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
