import { useState } from "react";
import { api, formatWhen } from "./api";
import { useAuth, useI18n } from "./context";
import { ComplaintForm, useData } from "./PatientPages";
import { Button, Empty, ErrorText, Field, Note, Pill } from "./ui";

/* ------------------------------------------------------------------ */
/* Shared helpers                                                      */
/* ------------------------------------------------------------------ */

const STATUS_LABELS = {
  received: "Received",
  under_review: "Under review",
  being_addressed: "Being addressed",
  resolved: "Resolved",
  open: "Open",
  accepted: "Accepted",
  completed: "Completed",
  acknowledged: "Acknowledged",
  closed: "Closed",
};

export function StatusPill({ value }) {
  const { t } = useI18n();
  return <Pill value={value}>{t(STATUS_LABELS[value] || value)}</Pill>;
}

const HELPER_LABELS = {
  general: "General help",
  medical_student: "Medical student",
  nursing_student: "Nursing student",
  transport: "Transportation",
  companion: "Hospital companion",
};

const TASK_KIND_LABELS = { delivery: "Supply delivery", companion: "Hospital companion", other: "Other help" };

/* ------------------------------------------------------------------ */
/* Volunteer                                                           */
/* ------------------------------------------------------------------ */

function VolunteerHeader() {
  const { user } = useAuth();
  const { t } = useI18n();
  const clinical = user.helper_type === "medical_student" || user.helper_type === "nursing_student";
  return (
    <div className="card stack">
      <div>
        <h2>{user.full_name}</h2>
        <p className="small muted">{t(HELPER_LABELS[user.helper_type] || "Volunteer")}</p>
      </div>
      <Note>
        {clinical
          ? t("You can deliver supplies and accompany patients. Clinical tasks need a verified license.")
          : t("You can deliver supplies and accompany patients. This is non-medical help.")}
      </Note>
    </div>
  );
}

function TaskCard({ task, onChanged }) {
  const { t } = useI18n();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function respond(action) {
    setBusy(true);
    setError("");
    try {
      await api(`/tasks/${task.id}/respond`, { method: "POST", body: JSON.stringify({ action }) });
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="card stack">
      <div className="spread">
        <span className="eyebrow">{t(TASK_KIND_LABELS[task.kind] || task.kind)}</span>
        <StatusPill value={task.status} />
      </div>
      <strong>{task.title}</strong>
      {task.details && <p className="small">{task.details}</p>}
      <p className="small muted">{[task.location || task.shelter_name, formatWhen(task.scheduled_at)].filter(Boolean).join(" · ")}</p>
      <ErrorText>{error}</ErrorText>
      {task.status === "open" && (
        <div className="action-row">
          <Button ghost type="button" disabled={busy} onClick={() => respond("decline")}>Decline</Button>
          <Button type="button" disabled={busy} onClick={() => respond("accept")}>Accept task</Button>
        </div>
      )}
      {task.mine && task.status === "accepted" && (
        <div className="action-row">
          <Button ghost type="button" disabled={busy} onClick={() => respond("decline")}>Give back</Button>
          <Button type="button" disabled={busy} onClick={() => respond("complete")}>Mark as done</Button>
        </div>
      )}
    </div>
  );
}

export function VolunteerTasksPage() {
  const { t } = useI18n();
  const { data, error, reload } = useData("/volunteer/board");
  const tasks = data?.tasks || [];
  const open = tasks.filter((task) => task.status === "open");
  const mine = tasks.filter((task) => task.mine && task.status === "accepted");
  const done = tasks.filter((task) => task.mine && task.status === "completed");
  return (
    <div className="stack">
      <h1>{t("Tasks")}</h1>
      <VolunteerHeader />
      <ErrorText>{error}</ErrorText>
      <section className="stack">
        <h3>{t("New matches for you")}</h3>
        {open.length === 0 && <Empty>{t("No open tasks right now.")}</Empty>}
        {open.map((task) => <TaskCard key={task.id} task={task} onChanged={reload} />)}
      </section>
      <section className="stack">
        <h3>{t("My upcoming tasks")}</h3>
        {mine.length === 0 && <Empty>{t("You have not accepted a task yet.")}</Empty>}
        {mine.map((task) => <TaskCard key={task.id} task={task} onChanged={reload} />)}
      </section>
      {done.length > 0 && (
        <section className="stack">
          <h3>{t("Completed")}</h3>
          {done.map((task) => <TaskCard key={task.id} task={task} onChanged={reload} />)}
        </section>
      )}
    </div>
  );
}

export function VolunteerNoticesPage() {
  const { t } = useI18n();
  const { data, error } = useData("/volunteer/board");
  const items = data?.announcements || [];
  return (
    <div className="stack">
      <h1>{t("Notices")}</h1>
      <p className="muted">{t("Volunteer doctor visits and free healthcare days.")}</p>
      <ErrorText>{error}</ErrorText>
      {data && items.length === 0 && <Empty>{t("No visits announced.")}</Empty>}
      {items.map((item) => (
        <div className="card stack" key={item.id}>
          <span className="eyebrow">{t(item.kind === "doctor_visit" ? "Volunteer doctor visit" : "Free healthcare day")}</span>
          <strong>{item.title}</strong>
          <p className="small muted">{[item.location || item.shelter_name, formatWhen(item.starts_at)].filter(Boolean).join(" · ")}</p>
          {item.details && <p className="small">{item.details}</p>}
        </div>
      ))}
    </div>
  );
}

const COMPLAINT_FILTERS = ["all", "received", "under_review", "being_addressed", "resolved"];

// Separate complaints dashboard: volunteers record complaints they hear about and follow them.
export function VolunteerComplaintsPage() {
  const { t } = useI18n();
  const { data, error, reload } = useData("/requests/mine");
  const [filter, setFilter] = useState("all");
  const [adding, setAdding] = useState(false);
  const complaints = data?.complaints || [];
  const count = (status) => complaints.filter((item) => item.status === status).length;
  const shown = complaints.filter((item) => filter === "all" || item.status === filter);
  return (
    <div className="stack">
      <div className="spread">
        <h1>{t("Complaints")}</h1>
        <Button type="button" soft onClick={() => setAdding((v) => !v)}>{adding ? "Close" : "Add a complaint"}</Button>
      </div>
      <ErrorText>{error}</ErrorText>

      {adding && (
        <section className="card stack">
          <h3>{t("Add a complaint")}</h3>
          <p className="small muted">{t("Record a complaint a resident told you about, by phone, message, photo, note, or in person.")}</p>
          <ComplaintForm forOthers onDone={reload} />
        </section>
      )}

      <div className="stat-grid">
        {["received", "under_review", "being_addressed", "resolved"].map((status) => (
          <div className="stat" key={status}>
            <strong>{count(status)}</strong>
            <span className="small muted">{t(STATUS_LABELS[status])}</span>
          </div>
        ))}
      </div>

      <div className="chip-row" role="group" aria-label={t("Status")}>
        {COMPLAINT_FILTERS.map((value) => (
          <button key={value} type="button" className={`chip ${filter === value ? "active" : ""}`} aria-pressed={filter === value} onClick={() => setFilter(value)}>
            {t(value === "all" ? "All" : STATUS_LABELS[value])}
          </button>
        ))}
      </div>

      <section className="card">
        {data && shown.length === 0 && <Empty>{t("No complaints here yet.")}</Empty>}
        {shown.map((item) => (
          <div className="row" key={item.id}>
            <div>
              <strong>{t(item.category)}</strong>
              <div className="small muted">{[item.shelter_name, formatWhen(item.created_at)].filter(Boolean).join(" · ")}</div>
              <div className="small">{item.description}</div>
            </div>
            <StatusPill value={item.status} />
          </div>
        ))}
      </section>
    </div>
  );
}

const SUPPORT_SIGNS = [
  "Bullying of a child with a disability",
  "Bullying",
  "Repeated anxiety or nightmares",
  "Withdrawn or constantly sad",
  "Aggressive or very angry",
  "Not eating or not sleeping",
];

// Mental health support: flag a person so a professional follows up.
export function VolunteerSupportPage() {
  const { t } = useI18n();
  const { data, reload } = useData("/requests/mine");
  const [query, setQuery] = useState("");
  const [people, setPeople] = useState([]);
  const [person, setPerson] = useState(null);
  const [signs, setSigns] = useState([]);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function search(event) {
    event.preventDefault();
    setError("");
    try {
      const result = await api(`/roster?q=${encodeURIComponent(query.trim())}`);
      setPeople(result.people);
      if (result.people.length === 0) setError(t("Nobody found with that name."));
    } catch (err) {
      setError(err.message);
    }
  }
  const toggle = (sign) => setSigns((current) => (current.includes(sign) ? current.filter((s) => s !== sign) : [...current, sign]));

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSent(false);
    if (!person) return setError(t("Choose the person first."));
    if (signs.length === 0 && !notes.trim()) return setError(t("Tick what you noticed or write a short note."));
    setBusy(true);
    try {
      const reason = [...signs.map((s) => t(s)), notes.trim()].filter(Boolean).join(" · ");
      await api("/support-flags", {
        method: "POST",
        body: JSON.stringify({ profile_id: person.id, reason, includes_bullying: signs.some((s) => s.startsWith("Bullying")) }),
      });
      setPerson(null);
      setPeople([]);
      setQuery("");
      setSigns([]);
      setNotes("");
      setSent(true);
      reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <h1>{t("Mental health support")}</h1>
      <div className="banner green stack">
        <strong>{t("How this works")}</strong>
        <ol className="steps small">
          <li>{t("Find the person you are worried about.")}</li>
          <li>{t("Tick what you noticed.")}</li>
          <li>{t("Send. A mental health professional follows up in private.")}</li>
        </ol>
        <p className="small muted">{t("A flag asks for a human follow-up. It is not a diagnosis.")}</p>
      </div>

      <section className="card stack">
        <h3>1. {t("Who needs support?")}</h3>
        {person ? (
          <div className="spread">
            <div><strong>{person.full_name}</strong><div className="small muted">{person.shelter_name}</div></div>
            <button className="text-btn" type="button" onClick={() => setPerson(null)}>{t("Change")}</button>
          </div>
        ) : (
          <>
            <form className="inline" onSubmit={search}>
              <input aria-label={t("Search by name")} placeholder={t("Search by name")} value={query} onChange={(e) => setQuery(e.target.value)} />
              <Button type="submit" soft>Search</Button>
            </form>
            {people.map((p) => (
              <button key={p.id} type="button" className="row row-button" onClick={() => { setPerson(p); setPeople([]); }}>
                <span><strong>{p.full_name}</strong><span className="small muted"> · {p.shelter_name || t("No shelter")}</span></span>
                <span className="text-btn">{t("Choose")}</span>
              </button>
            ))}
          </>
        )}
      </section>

      <form className="card stack" onSubmit={submit}>
        <h3>2. {t("What did you notice?")}</h3>
        <div className="stack">
          {SUPPORT_SIGNS.map((sign) => (
            <label className="check" key={sign}>
              <input type="checkbox" checked={signs.includes(sign)} onChange={() => toggle(sign)} /> {t(sign)}
            </label>
          ))}
        </div>
        <Field label="Anything else? (optional)"><textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <h3>3. {t("Send")}</h3>
        <ErrorText>{error}</ErrorText>
        {sent && <div className="banner green small">{t("Sent. A professional will follow up.")}</div>}
        <Button type="submit" disabled={busy}>{busy ? "Sending…" : "Send support request"}</Button>
      </form>

      <section className="card stack">
        <h3>{t("My previous requests")}</h3>
        {data && data.flags.length === 0 && <Empty>{t("No requests yet.")}</Empty>}
        {(data?.flags || []).map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.who}</strong><div className="small">{item.reason}</div><div className="small muted">{formatWhen(item.created_at)}</div></div>
            <StatusPill value={item.status} />
          </div>
        ))}
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Route table: [path, Component, allowed roles]                       */
/* ------------------------------------------------------------------ */

const VOLUNTEER = ["volunteer"];

export const ROLE_ROUTES = [
  ["/volunteer", VolunteerTasksPage, VOLUNTEER],
  ["/volunteer/notices", VolunteerNoticesPage, VOLUNTEER],
  ["/volunteer/complaints", VolunteerComplaintsPage, VOLUNTEER],
  ["/volunteer/support", VolunteerSupportPage, VOLUNTEER],
];
