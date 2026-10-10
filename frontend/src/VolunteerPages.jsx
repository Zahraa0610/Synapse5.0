import { useEffect, useState } from "react";
import { api, formatWhen } from "./api";
import { useAuth, useI18n } from "./context";
import { ComplaintForm } from "./PatientPages";
import { Button, ErrorText, Field, Note, Pill, Select } from "./ui";

function useData(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  async function reload() {
    try {
      setData(await api(path));
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }
  useEffect(() => { reload(); }, [path]);
  return { data, error, reload };
}

export function VolunteerPage({ mode = "tasks" }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const board = useData("/volunteer/board");
  const tasks = board.data?.tasks || [];
  const notices = board.data?.announcements || [];
  return (
    <div className={mode === "tasks" ? "volunteer-dashboard" : "stack"}>
      {mode !== "tasks" && <h1>{mode === "notices" ? t("Notices") : t("Support")}</h1>}
      <ErrorText>{board.error}</ErrorText>
      {mode === "tasks" && <VolunteerDashboard user={user} tasks={tasks} onDone={board.reload} />}
      {mode === "notices" && notices.map((item) => (
        <article className="card" key={item.id}>
          <Pill value={item.kind}>{item.kind === "doctor_visit" ? "Doctor visit" : "Free healthcare day"}</Pill>
          <h3 style={{ marginTop: 8 }}>{item.title}</h3>
          <p className="small muted">{item.location} · {formatWhen(item.starts_at)}</p>
          <p>{item.details}</p>
        </article>
      ))}
      {mode === "support" && <VolunteerSupport />}
    </div>
  );
}

function VolunteerDashboard({ user, tasks, onDone }) {
  const { setLang } = useI18n();
  const match = tasks.find((task) => task.status === "open") || tasks[0];
  const upcoming = tasks.filter((task) => task.id !== match?.id && (task.mine || task.status === "accepted")).slice(0, 2);
  const helperLabel = user?.helper_type ? user.helper_type.replaceAll("_", " ") : null;
  return (
    <>
      <section className="volunteer-profile">
        <div className="volunteer-avatar">{initials(user?.full_name || "Volunteer")}</div>
        <div className="volunteer-identity">
          <strong>{user?.full_name || "Omar Saleh"}</strong>
          {helperLabel && <span>{helperLabel}</span>}
        </div>
        <button className="arabic-chip" type="button" aria-label="Switch to Arabic" onClick={() => setLang("ar")}>عربي</button>
      </section>

      <section className="verification-card">
        <ShieldIcon />
        <div><strong>{user?.verification_status === "approved" ? "Verified volunteer" : "Non-clinical helper"}</strong><span>{helperLabel ? `Registered for ${helperLabel} support.` : "Your assigned volunteer tasks appear here."}</span></div>
      </section>

      <section className="volunteer-section match-section">
        <div className="volunteer-heading"><strong>New match for you</strong></div>
        {match ? <MatchCard task={match} onDone={onDone} /> : <p className="small muted">No new matches right now.</p>}
      </section>

      <section className="volunteer-section upcoming-section">
        <div className="volunteer-heading"><strong>My upcoming tasks</strong></div>
        <div className="upcoming-list">
          {upcoming.map((task) => <UpcomingTask key={task.id} task={task} />)}
          {!upcoming.length && <p className="small muted">Accepted tasks will appear here.</p>}
        </div>
      </section>

      {helperLabel && <section className="volunteer-section skills-section">
        <div className="volunteer-heading"><strong>I can help with</strong></div>
        <div className="volunteer-skills"><span>{helperLabel}</span></div>
      </section>}
    </>
  );
}

function MatchCard({ task, onDone }) {
  const [busy, setBusy] = useState(false);
  async function respond(action) {
    setBusy(true);
    try {
      await api(`/tasks/${task.id}/respond`, { method: "POST", body: JSON.stringify({ action }) });
      await onDone();
    } finally { setBusy(false); }
  }
  const route = splitRoute(task.location);
  return (
    <article className="match-card">
      <div className="match-tags"><span>{task.kind === "companion" ? "HOSPITAL COMPANION" : task.kind?.toUpperCase()}</span></div>
      <h2>{task.title}</h2>
      <div className="route-line">
        <i className="route-dot round" /><div><small>Pick up · surplus</small><strong>{route[0]}</strong></div>
        <i className="route-rail" />
        <i className="route-dot square" /><div><small>Drop off · shortage</small><strong>{route[1]}</strong></div>
      </div>
      <div className="match-facts"><span><small>When</small><b>{shortWhen(task.scheduled_at)}</b></span>{task.shelter_name && <span><small>Shelter</small><b>{task.shelter_name}</b></span>}</div>
      <div className="match-actions"><button disabled={busy} onClick={() => respond("decline")}>Decline</button><button disabled={busy} onClick={() => respond("accept")}>Accept task</button></div>
    </article>
  );
}

function UpcomingTask({ task }) {
  return (
    <article className="upcoming-card">
      <div><span>{task.kind === "companion" ? "HOSPITAL COMPANION" : "SUPPLY DELIVERY"}</span><time>{shortDate(task.scheduled_at)}</time></div>
      <strong>{task.title}</strong>
      <p>{task.location}{task.details ? ` · ${task.details}` : ""}</p>
    </article>
  );
}

function initials(name) { return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); }
function splitRoute(location = "") {
  const parts = location.split(/\s+to\s+/i);
  return [parts[0] || "Location not specified", parts[1] || parts[0] || "Location not specified"];
}
function shortWhen(value) { return value ? new Date(value).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "Not scheduled"; }
function shortDate(value) { return value ? new Date(value).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : ""; }
function ShieldIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 4.5 2.8 7.8 7 10 4.2-2.2 7-5.5 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-5"/></svg>; }

function TaskCard({ task, onDone }) {
  const { t } = useI18n();
  async function respond(action) {
    await api(`/tasks/${task.id}/respond`, { method: "POST", body: JSON.stringify({ action }) });
    onDone();
  }
  return (
    <article className="card stack">
      <div className="spread">
        <Pill value={task.kind}>{task.kind === "companion" ? "Hospital companion" : task.kind}</Pill>
        <Pill value={task.status}>{task.status}</Pill>
      </div>
      <h3>{task.title}</h3>
      <p className="small">{task.details}</p>
      <p className="small muted">{task.location} · {formatWhen(task.scheduled_at)}</p>
      {task.kind === "companion" && <Note>This is non-medical guidance inside the hospital. It does not replace clinical staff.</Note>}
      <div className="action-row">
        {task.status !== "accepted" && task.status !== "completed" && <Button type="button" onClick={() => respond("accept")}>{t("Accept")}</Button>}
        {task.mine && task.status === "accepted" && <Button type="button" onClick={() => respond("complete")}>{t("Complete")}</Button>}
        {task.status !== "completed" && <Button ghost type="button" onClick={() => respond("decline")}>{t("Decline")}</Button>}
      </div>
    </article>
  );
}

function VolunteerSupport() {
  const [query, setQuery] = useState("");
  const [people, setPeople] = useState([]);
  const [profileId, setProfileId] = useState("");
  const [reason, setReason] = useState("");
  const [bullying, setBullying] = useState(false);
  const [message, setMessage] = useState("");
  async function search(event) {
    event.preventDefault();
    const data = await api(`/roster?q=${encodeURIComponent(query)}`);
    setPeople(data.people);
  }
  async function flag(event) {
    event.preventDefault();
    await api("/support-flags", { method: "POST", body: JSON.stringify({ profile_id: Number(profileId), reason, includes_bullying: bullying }) });
    setMessage("Support flag recorded for follow-up.");
    setReason("");
  }
  return (
    <div className="stack">
      <Note>Flag a person who may need mental health support, including a child facing bullying. This is a request for human follow-up.</Note>
      <form className="card stack" onSubmit={search}>
        <Field label="Full name"><input value={query} onChange={(e) => setQuery(e.target.value)} /></Field>
        <Button type="submit">Find a patient</Button>
        {people.map((person) => (
          <button type="button" key={person.id} className={`person-chip ${profileId === person.id ? "active" : ""}`} onClick={() => setProfileId(person.id)}>
            {person.full_name}<div className="small muted">{person.shelter_name}</div>
          </button>
        ))}
      </form>
      <form className="card stack" onSubmit={flag}>
        <Field label="Reason"><textarea value={reason} onChange={(e) => setReason(e.target.value)} required /></Field>
        <label className="check"><input type="checkbox" checked={bullying} onChange={(e) => setBullying(e.target.checked)} /> Includes bullying</label>
        <Button type="submit" disabled={!profileId}>Flag for support</Button>
        {message && <p className="small">{message}</p>}
      </form>
      <div className="card"><ComplaintForm onDone={() => setMessage("Complaint recorded.")} /></div>
    </div>
  );
}

export function DonorPage({ gifts = false }) {
  const { t } = useI18n();
  const board = useData("/donor/board");
  const data = board.data;
  return (
    <div className="stack">
      <h1>{gifts ? t("My gifts") : t("Where help is needed")}</h1>
      <ErrorText>{board.error}</ErrorText>
      {data && !gifts && (
        <>
          <Note>{t("You still choose. Nothing is assigned automatically.")}</Note>
          {data.recommendation && (
            <article className="banner amber stack">
              <strong>{t("Suggested if you have no recipient in mind")}</strong>
              <div>{data.recommendation.title}</div>
              <p className="small">{data.recommendation.detail} · {data.recommendation.shelter_name}</p>
              <GiveForm opportunity={data.recommendation} recommended onDone={board.reload} />
            </article>
          )}
          {data.opportunities.map((item) => (
            <article className="card stack" key={item.key}>
              <div className="spread">
                <Pill value={item.kind === "case" ? "critical" : item.confirmed ? "shortage" : "low"}>{item.kind}</Pill>
                <span className="small muted">{item.region}</span>
              </div>
              <h3>{item.title}</h3>
              <p className="small">{item.detail}</p>
              <p className="small muted">{item.shelter_name} · verified shelter report{item.confirmed ? "" : " · pending confirmation"}</p>
              <GiveForm opportunity={item} onDone={board.reload} />
            </article>
          ))}
        </>
      )}
      {data && gifts && data.donations.map((item) => (
        <article className="card" key={item.id}>
          <div className="spread">
            <strong>{item.kind === "money" ? `${item.amount} ${item.currency}` : item.item_description}</strong>
            <Pill value={item.status}>{item.status}</Pill>
          </div>
          <p className="small muted">{item.shelter_name || item.cause_label} · {item.target_type}</p>
        </article>
      ))}
    </div>
  );
}

function GiveForm({ opportunity, recommended = false, onDone }) {
  const [kind, setKind] = useState("physical");
  const [amount, setAmount] = useState("");
  const [item, setItem] = useState(opportunity.item_description || "");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/donations", {
        method: "POST",
        body: JSON.stringify({
          kind,
          amount: kind === "money" ? Number(amount) : null,
          item_description: item,
          target_type: opportunity.target_type,
          target_shelter_id: opportunity.target_shelter_id,
          target_profile_id: opportunity.target_profile_id,
          cause_label: opportunity.shelter_name || opportunity.title,
          from_recommendation: recommended,
        }),
      });
      setDone(true);
      onDone();
    } catch (err) {
      setError(err.message);
    }
  }
  if (done) return <p className="small">Gift recorded. A coordinator distributes it.</p>;
  return (
    <form className="stack" onSubmit={submit}>
      <div className="segment">
        <button type="button" className={kind === "physical" ? "active" : ""} onClick={() => setKind("physical")}>Supplies</button>
        <button type="button" className={kind === "money" ? "active" : ""} onClick={() => setKind("money")}>Money</button>
      </div>
      {kind === "money" ? (
        <Field label="Amount"><input type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} required /></Field>
      ) : (
        <Field label="Supplies"><input value={item} onChange={(e) => setItem(e.target.value)} required /></Field>
      )}
      <ErrorText>{error}</ErrorText>
      <Button type="submit">Give</Button>
    </form>
  );
}

export { Select };
