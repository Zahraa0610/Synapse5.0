import { useState } from "react";
import { Link } from "react-router-dom";
import { api, formatWhen } from "./api";
import { useAuth, useI18n } from "./context";
import { ComplaintForm, CriticalityControl, useData } from "./PatientPages";
import { Bars, Button, Empty, ErrorText, Field, Note, Pill, Select } from "./ui";

/* ------------------------------------------------------------------ */
/* Shared helpers                                                      */
/* ------------------------------------------------------------------ */

// Runs an API call, keeps its error, and reloads the page data afterwards.
function useAction(reload) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function run(path, method, body) {
    setBusy(true);
    setError("");
    try {
      const options = { method };
      if (body !== undefined) options.body = body instanceof FormData ? body : JSON.stringify(body);
      const result = await api(path, options);
      reload?.();
      return result;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  return { run, error, busy, setError };
}

// Small controlled form helper: const [form, set, reset] = useForm({...})
function useForm(initial) {
  const [form, setForm] = useState(initial);
  const set = (key) => (e) => setForm((cur) => ({ ...cur, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));
  return [form, set, () => setForm(initial)];
}

function StatusSelect({ value, options, onChange, label }) {
  const { t } = useI18n();
  return (
    <select aria-label={t(label || "Status")} value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((option) => <option key={option} value={option}>{t(STATUS_LABELS[option] || option)}</option>)}
    </select>
  );
}

function Stat({ value, label, tone }) {
  const { t } = useI18n();
  return (
    <div className={`stat ${tone ? `stat-${tone}` : ""}`}>
      <strong>{value}</strong>
      <span className="small muted">{t(label)}</span>
    </div>
  );
}

function PageTitle({ children, sub }) {
  const { t } = useI18n();
  return (
    <div>
      <h1>{t(children)}</h1>
      {sub && <p className="muted">{t(sub)}</p>}
    </div>
  );
}

const money = (amount, currency = "USD") => (amount == null ? "" : `${Number(amount).toLocaleString()} ${currency}`);

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
  pledged: "Pledged",
  allocated: "Allocated",
  distributed: "Distributed",
  proposed: "Proposed",
  in_transit: "In transit",
  requested: "Requested",
  escalated: "Escalated",
  reported: "Reported",
  investigating: "Investigating",
  submitted: "Submitted",
  connected: "Connected",
  delivered: "Delivered",
  available: "Available",
  low: "Low",
  shortage: "Shortage",
  critical: "Critical",
  non_critical: "Not critical",
  cancelled: "Cancelled",
  documents_received: "Documents received",
  checking: "Checking",
  approved: "Approved",
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
  return (
    <div className="card stack">
      <div>
        <h2>{user.full_name}</h2>
        <p className="small muted">{[t(HELPER_LABELS[user.helper_type] || "Volunteer"), user.offers_driving ? `${t("Driver")} · ${user.car_model || ""}` : null].filter(Boolean).join(" · ")}</p>
      </div>
      <Note>{t("You can deliver supplies and accompany patients. This is non-medical help.")}</Note>
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

// Signs a volunteer may notice, grouped so the checklist is easy to scan.
const SUPPORT_SIGN_GROUPS = [
  ["Bullying", ["Bullying of a child with a disability", "Other bullying or harassment"]],
  ["Mood", ["Repeated anxiety or nightmares", "Withdrawn or constantly sad", "Aggressive or very angry"]],
  ["Daily life", ["Not eating or not sleeping", "Stopped talking or playing", "Talks about hurting themselves"]],
];

// Report a case that needs mental health support.
export function VolunteerSupportPage() {
  const { t } = useI18n();
  const { data, reload } = useData("/requests/mine");
  const shelters = useData("/shelters");
  const blank = { person_description: "", shelter_id: "", reason: "" };
  const [form, setForm] = useState(blank);
  const [signs, setSigns] = useState([]);
  const [linked, setLinked] = useState(null);
  const [linking, setLinking] = useState(false);
  const [query, setQuery] = useState("");
  const [people, setPeople] = useState([]);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const toggle = (sign) => setSigns((cur) => (cur.includes(sign) ? cur.filter((x) => x !== sign) : [...cur, sign]));
  const urgent = signs.includes("Talks about hurting themselves");

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

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSent(false);
    setBusy(true);
    try {
      await api("/support-flags", {
        method: "POST",
        body: JSON.stringify({
          person_description: form.person_description,
          profile_id: linked?.id || null,
          shelter_id: form.shelter_id || linked?.shelter_id || null,
          signs: signs.map((sign) => t(sign)),
          reason: form.reason,
        }),
      });
      setForm(blank);
      setSigns([]);
      setLinked(null);
      setLinking(false);
      setPeople([]);
      setQuery("");
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
      <PageTitle sub="Tell us about someone who may need mental health support. A professional follows up in private.">Report a support case</PageTitle>

      <form className="card stack" onSubmit={submit}>
        <section className="form-section">
          <h3>1. {t("Who needs support?")}</h3>
          <Field label="Describe the person">
            <input value={form.person_description} onChange={set("person_description")} placeholder={t("e.g. Boy, about 9, room 3")} maxLength={200} required={!linked} />
          </Field>
          <Field label="Shelter">
            <select value={form.shelter_id} onChange={set("shelter_id")}>
              <option value="">{t("Not in a shelter / not sure")}</option>
              {(shelters.data?.shelters || []).map((shelter) => <option key={shelter.id} value={shelter.id}>{shelter.name}</option>)}
            </select>
          </Field>
          {linked ? (
            <div className="linked-person">
              <span>{t("Linked to")}: <strong>{linked.full_name}</strong>{linked.shelter_name ? ` · ${linked.shelter_name}` : ""}</span>
              <button className="text-btn" type="button" onClick={() => setLinked(null)}>{t("Remove link")}</button>
            </div>
          ) : !linking ? (
            <button className="text-btn" type="button" onClick={() => setLinking(true)}>+ {t("Link a registered person (optional)")}</button>
          ) : (
            <div className="stack">
              <div className="inline">
                <input aria-label={t("Search by name")} placeholder={t("Search by name")} value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") search(e); }} />
                <Button type="button" soft onClick={search}>Search</Button>
              </div>
              {people.map((p) => (
                <button key={p.id} type="button" className="row row-button" onClick={() => { setLinked(p); setPeople([]); setLinking(false); }}>
                  <span><strong>{p.full_name}</strong><span className="small muted"> · {p.shelter_name || t("No shelter")}</span></span>
                  <span className="text-btn">{t("Choose")}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="form-section">
          <h3>2. {t("What did you notice?")}</h3>
          {SUPPORT_SIGN_GROUPS.map(([group, items]) => (
            <fieldset className="check-group" key={group}>
              <legend>{t(group)}</legend>
              {items.map((sign) => (
                <label className="check" key={sign}>
                  <input type="checkbox" checked={signs.includes(sign)} onChange={() => toggle(sign)} /> {t(sign)}
                </label>
              ))}
            </fieldset>
          ))}
          {urgent && (
            <div className="banner rose small">
              <strong>{t("If the person is in danger right now, call 140 (Lebanese Red Cross).")}</strong>
              <div>{t("Embrace Lifeline (free, confidential): 1564.")}</div>
            </div>
          )}
        </section>

        <section className="form-section">
          <h3>3. {t("Describe the case briefly")}</h3>
          <Field label="What happened?">
            <textarea rows={3} maxLength={500} value={form.reason} onChange={set("reason")} placeholder={t("A few sentences: what you saw, when, and where.")} required />
          </Field>
          <span className="small muted">{form.reason.length}/500</span>
        </section>

        <ErrorText>{error}</ErrorText>
        {sent && <div className="banner green small">{t("Sent. A professional will follow up.")}</div>}
        <Button type="submit" disabled={busy}>{busy ? "Sending…" : "Send support request"}</Button>
        <p className="small muted">{t("A flag asks for a human follow-up. It is not a diagnosis.")}</p>
      </form>

      <section className="card stack">
        <h3>{t("My previous requests")}</h3>
        {data && data.flags.length === 0 && <Empty>{t("No requests yet.")}</Empty>}
        {(data?.flags || []).map((item) => (
          <div className="row" key={item.id}>
            <div>
              <strong>{item.who}</strong>
              <div className="small muted">{[item.shelter_name, formatWhen(item.created_at)].filter(Boolean).join(" · ")}</div>
              {item.signs?.length > 0 && <div className="chip-row tight">{item.signs.map((sign) => <span key={sign} className="tag">{sign}</span>)}</div>}
              <div className="small">{item.reason}</div>
            </div>
            <StatusPill value={item.status} />
          </div>
        ))}
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Donor                                                               */
/* ------------------------------------------------------------------ */

function GiveForm({ opportunity, onDone }) {
  const { t } = useI18n();
  const [form, set] = useForm({ kind: "money", amount: "", item_description: opportunity.item_description || "" });
  const { run, error, busy } = useAction();
  const [done, setDone] = useState(false);
  async function submit(e) {
    e.preventDefault();
    const result = await run("/donations", "POST", {
      kind: form.kind,
      amount: form.kind === "money" ? form.amount : undefined,
      item_description: form.kind === "physical" ? form.item_description : undefined,
      target_type: opportunity.target_type,
      target_shelter_id: opportunity.target_shelter_id,
      target_profile_id: opportunity.target_profile_id,
      cause_label: opportunity.target_type === "cause" ? opportunity.title : undefined,
      from_recommendation: opportunity.recommended,
    });
    if (result) { setDone(true); onDone?.(); }
  }
  if (done) {
    return (
      <div className="banner green stack">
        <strong>{t("Thank you!")}</strong>
        <span className="small">{t(opportunity.kind === "request" ? "The family will confirm when they receive it." : "The shelter coordinator will confirm when it is received.")}</span>
      </div>
    );
  }
  return (
    <form className="stack" onSubmit={submit}>
      <div className="segment">
        <button type="button" className={form.kind === "money" ? "active" : ""} onClick={() => set("kind")({ target: { value: "money" } })}>{t("Money")}</button>
        <button type="button" className={form.kind === "physical" ? "active" : ""} onClick={() => set("kind")({ target: { value: "physical" } })}>{t("Supplies")}</button>
      </div>
      {form.kind === "money"
        ? <Field label="Amount (USD)"><input type="number" min="1" value={form.amount} onChange={set("amount")} required /></Field>
        : <Field label="What will you give?"><input value={form.item_description} onChange={set("item_description")} required /></Field>}
      <ErrorText>{error}</ErrorText>
      <Button type="submit" disabled={busy}>Give</Button>
    </form>
  );
}

function Opportunity({ item, onDone }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return (
    <div className="card stack">
      <div className="spread">
        <span className="eyebrow">{t(item.kind === "case" ? "Medical case" : "Shelter need")}</span>
        {item.verified && <Pill value="approved">{t("Verified")}</Pill>}
      </div>
      <strong>{item.title}</strong>
      <p className="small">{item.detail}</p>
      <p className="small muted">{[item.shelter_name, item.region].filter(Boolean).join(" · ")}</p>
      {open ? <GiveForm opportunity={item} onDone={onDone} /> : <Button type="button" onClick={() => setOpen(true)}>Give</Button>}
    </div>
  );
}

export function DonorNeedsPage() {
  const { t } = useI18n();
  const { data, error, reload } = useData("/donor/board");
  const [region, setRegion] = useState("all");
  const items = data?.opportunities || [];
  const regions = [...new Set(items.map((item) => item.region).filter(Boolean))];
  const shown = items.filter((item) => region === "all" || item.region === region);
  return (
    <div className="stack">
      <PageTitle sub="Verified needs reported by shelter coordinators.">Where help is needed</PageTitle>
      <ErrorText>{error}</ErrorText>
      {data?.recommendation && (
        <section className="stack">
          <h3>{t("Suggested if you have no recipient in mind")}</h3>
          <Note>{t("You still choose. Nothing is assigned automatically.")}</Note>
          <Opportunity item={data.recommendation} onDone={reload} />
        </section>
      )}
      {regions.length > 1 && (
        <div className="chip-row" role="group" aria-label={t("Region")}>
          {["all", ...regions].map((value) => (
            <button key={value} type="button" className={`chip ${region === value ? "active" : ""}`} aria-pressed={region === value} onClick={() => setRegion(value)}>{value === "all" ? t("All") : value}</button>
          ))}
        </div>
      )}
      {shown.filter((item) => !item.recommended).map((item) => <Opportunity key={item.key} item={item} onDone={reload} />)}
      {data && items.length === 0 && <Empty>{t("No open needs right now.")}</Empty>}
    </div>
  );
}

export function DonorGiftsPage() {
  const { t } = useI18n();
  const { data, error } = useData("/donor/board");
  const gifts = data?.donations || [];
  const total = gifts.filter((g) => g.kind === "money").reduce((sum, g) => sum + (g.amount || 0), 0);
  return (
    <div className="stack">
      <PageTitle>My donations</PageTitle>
      <ErrorText>{error}</ErrorText>
      <div className="stat-grid">
        <Stat value={gifts.length} label="Donations" />
        <Stat value={money(total)} label="Money given" />
      </div>
      <section className="card">
        {data && gifts.length === 0 && <Empty>{t("You have not donated yet.")} <Link to="/donor">{t("See needs")}</Link></Empty>}
        {gifts.map((gift) => (
          <div className="row" key={gift.id}>
            <div>
              <strong>{gift.kind === "money" ? money(gift.amount, gift.currency) : gift.item_description}</strong>
              <div className="small muted">{[gift.shelter_name || gift.cause_label, formatWhen(gift.created_at)].filter(Boolean).join(" · ")}</div>
            </div>
            <StatusPill value={gift.status} />
          </div>
        ))}
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Shelter coordinator — all pages share /shelter/board                */
/* ------------------------------------------------------------------ */

function useShelterBoard() {
  return useData("/shelter/board");
}

function ShelterFrame({ title, sub, children }) {
  const board = useShelterBoard();
  return (
    <div className="stack">
      <PageTitle sub={sub}>{title}</PageTitle>
      <ErrorText>{board.error}</ErrorText>
      {board.error && board.error.includes("Choose the shelter") && <ChooseShelter />}
      {board.data && children(board.data, board.reload)}
    </div>
  );
}

function ChooseShelter() {
  const { t } = useI18n();
  const { user, refresh } = useAuth();
  const { data } = useData("/shelters");
  const [id, setId] = useState("");
  const { run, error } = useAction();
  async function save(e) {
    e.preventDefault();
    const result = await run(`/users/${user.id}/shelter`, "PATCH", { shelter_id: Number(id) });
    if (result) { refresh(result.user); window.location.reload(); }
  }
  return (
    <form className="card stack" onSubmit={save}>
      <h3>{t("Which shelter do you coordinate?")}</h3>
      <select value={id} onChange={(e) => setId(e.target.value)} required>
        <option value="">—</option>
        {(data?.shelters || []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <ErrorText>{error}</ErrorText>
      <Button type="submit">Save</Button>
    </form>
  );
}

export function ShelterOverviewPage() {
  const { t } = useI18n();
  return (
    <ShelterFrame title="Overview">
      {(data, reload) => <ShelterOverview data={data} reload={reload} t={t} />}
    </ShelterFrame>
  );
}

function ShelterOverview({ data, reload, t }) {
  const { shelter, stats } = data;
  const [form, set] = useForm({
    capacity: shelter.capacity, occupancy: shelter.occupancy, accessible_spaces: shelter.accessible_spaces ?? 0,
    electricity_hours: shelter.electricity_hours ?? 0, accessible: shelter.accessible, has_backup_power: shelter.has_backup_power,
  });
  const update = useAction(reload);
  const [outbreak, setOutbreak, resetOutbreak] = useForm({ suspected_illness: "", case_count: 1, notes: "" });
  const report = useAction(reload);
  const relocation = useAction(reload);
  return (
    <>
      <h2>{shelter.name}</h2>
      <p className="muted">{shelter.region}</p>
      <div className="stat-grid">
        <Stat value={`${stats.percent}%`} label="Occupancy" tone={stats.overcrowded ? "rose" : ""} />
        <Stat value={stats.shortages} label="Shortages" tone={stats.shortages ? "rose" : ""} />
        <Stat value={stats.critical_residents} label="Critical residents" />
        <Stat value={stats.open_complaints} label="Open complaints" />
      </div>
      <Bars value={shelter.occupancy} max={shelter.capacity || 1} tone={stats.overcrowded ? "rose" : ""} />
      <p className="small muted">{shelter.occupancy} / {shelter.capacity} {t("residents")}{stats.overcrowded ? ` · ${t("Overcrowded")}` : ""}</p>

      <form className="card stack" onSubmit={(e) => { e.preventDefault(); update.run(`/shelters/${shelter.id}`, "PATCH", form); }}>
        <h3>{t("Update shelter")}</h3>
        <div className="grid-2">
          <Field label="Capacity"><input type="number" min="0" value={form.capacity} onChange={set("capacity")} /></Field>
          <Field label="Occupancy"><input type="number" min="0" value={form.occupancy} onChange={set("occupancy")} /></Field>
          <Field label="Accessible spaces"><input type="number" min="0" value={form.accessible_spaces} onChange={set("accessible_spaces")} /></Field>
          <Field label="Backup power (hours/day)"><input type="number" min="0" max="24" value={form.electricity_hours} onChange={set("electricity_hours")} /></Field>
        </div>
        <fieldset className="check-group">
          <legend>{t("Facilities")}</legend>
          <label className="check"><input type="checkbox" checked={form.accessible} onChange={set("accessible")} /> {t("Wheelchair accessible")}</label>
          <label className="check"><input type="checkbox" checked={form.has_backup_power} onChange={set("has_backup_power")} /> {t("Has backup power")}</label>
        </fieldset>
        <ErrorText>{update.error}</ErrorText>
        <Button type="submit" disabled={update.busy}>Save</Button>
      </form>

      <section className="card stack">
        <h3>{t("Patient move requests")}</h3>
        <ErrorText>{relocation.error}</ErrorText>
        {data.relocations.length === 0 && <Empty>{t("No move requests.")}</Empty>}
        {data.relocations.map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.who}</strong> → {item.destination_name || t("Any suitable facility")}<div className="small">{item.reason}</div></div>
            <StatusSelect value={item.status} options={["requested", "escalated", "resolved"]} onChange={(status) => relocation.run(`/relocations/${item.id}`, "PATCH", { status })} />
          </div>
        ))}
      </section>

      <section className="card stack">
        <h3>{t("Outbreak reports")}</h3>
        <Note>{t("This flags a cluster for public health staff. It does not declare an outbreak.")}</Note>
        {data.outbreaks.map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.suspected_illness}</strong><div className="small muted">{item.case_count} {t("cases")} · {formatWhen(item.created_at)}</div></div>
            <StatusPill value={item.status} />
          </div>
        ))}
        <form className="stack" onSubmit={async (e) => { e.preventDefault(); if (await report.run("/outbreaks", "POST", outbreak)) resetOutbreak(); }}>
          <div className="grid-2">
            <Field label="Suspected illness"><input value={outbreak.suspected_illness} onChange={setOutbreak("suspected_illness")} required /></Field>
            <Field label="Number of cases"><input type="number" min="1" value={outbreak.case_count} onChange={setOutbreak("case_count")} /></Field>
          </div>
          <Field label="Notes"><input value={outbreak.notes} onChange={setOutbreak("notes")} /></Field>
          <ErrorText>{report.error}</ErrorText>
          <Button type="submit" soft disabled={report.busy}>Report a cluster</Button>
        </form>
      </section>
    </>
  );
}

export function ShelterResidentsPage() {
  const { t } = useI18n();
  return (
    <ShelterFrame title="Residents" sub="Criticality is suggested from reported needs. You confirm it.">
      {(data, reload) => <ResidentTable rows={data.residents} reload={reload} t={t} />}
    </ShelterFrame>
  );
}

function ResidentTable({ rows, reload, t }) {
  return (
    <div className="card">
      <div className="table-wrap">
        <table className="data">
          <thead><tr><th>{t("Name")}</th><th>{t("Passport ID")}</th><th>{t("Age")}</th><th>{t("Status")}</th><th>{t("Change status")}</th></tr></thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td><Link to={`/lookup?id=${row.passport_id}`}>{row.full_name}</Link>{row.disability ? <div className="small muted">{t("Disability or access need")}</div> : null}</td>
                <td className="mono small">{row.passport_id}</td>
                <td>{row.age ?? "—"}</td>
                <td><StatusPill value={row.criticality.level} />{!row.criticality.confirmed && <div className="small muted">{t("Suggested")}</div>}</td>
                <td><CriticalityControl key={`${row.id}-${row.criticality.level}`} profile={row} onChanged={reload} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <Empty>{t("No residents registered yet.")}</Empty>}
    </div>
  );
}

function InventoryRow({ item, reload }) {
  const { t } = useI18n();
  const action = useAction(reload);
  const [qty, setQty] = useState(item.quantity);
  return (
    <tr>
      <td><strong>{item.item_name}</strong><div className="small muted">{item.category}{item.is_equipment ? ` · ${t("Equipment")}` : ""}{item.is_specialized ? ` · ${t("Specialized")}` : ""}</div><ErrorText>{action.error}</ErrorText></td>
      <td>
        <form className="inline" onSubmit={(e) => { e.preventDefault(); action.run(`/inventory/${item.id}`, "PATCH", { quantity: qty }); }}>
          <input aria-label={t("Quantity")} type="number" min="0" style={{ width: 80 }} value={qty} onChange={(e) => setQty(e.target.value)} />
          <span className="small muted">{item.unit}</span>
        </form>
      </td>
      <td><StatusSelect value={item.status} options={["available", "low", "shortage"]} onChange={(status) => action.run(`/inventory/${item.id}`, "PATCH", { status })} /></td>
      <td><button className="text-btn" type="button" onClick={() => action.run(`/inventory/${item.id}`, "DELETE")}>{t("Remove")}</button></td>
    </tr>
  );
}

function InventoryTable({ items, reload }) {
  const { t } = useI18n();
  if (items.length === 0) return <Empty>{t("Nothing recorded yet.")}</Empty>;
  return (
    <div className="table-wrap">
      <table className="data">
        <thead><tr><th>{t("Item")}</th><th>{t("Quantity")}</th><th>{t("Status")}</th><th /></tr></thead>
        <tbody>{items.map((item) => <InventoryRow key={item.id} item={item} reload={reload} />)}</tbody>
      </table>
    </div>
  );
}

function AddInventory({ shelterId, reload }) {
  const { t } = useI18n();
  const blank = { item_name: "", category: "medication", quantity: 0, unit: "units", status: "available", is_equipment: false, is_specialized: false };
  const [form, set, reset] = useForm(blank);
  const action = useAction(reload);
  return (
    <form className="card stack" onSubmit={async (e) => { e.preventDefault(); if (await action.run(`/shelters/${shelterId}/inventory`, "POST", { ...form, is_equipment: form.is_equipment || form.category === "equipment" })) reset(); }}>
      <h3>{t("Add item")}</h3>
      <div className="grid-2">
        <Field label="Item"><input value={form.item_name} onChange={set("item_name")} placeholder={t("e.g. Baby formula or Hospital bed")} required /></Field>
        <Field label="Category">
          <Select value={form.category} onChange={set("category")} options={[
            { value: "medication", label: "Medication" }, { value: "baby_formula", label: "Baby formula" }, { value: "sanitary", label: "Sanitary products" },
            { value: "food", label: "Food" }, { value: "equipment", label: "Medical equipment" }, { value: "other", label: "Other" },
          ]} />
        </Field>
        <Field label="Quantity"><input type="number" min="0" value={form.quantity} onChange={set("quantity")} /></Field>
        <Field label="Unit"><input value={form.unit} onChange={set("unit")} placeholder={t("e.g. boxes, pens, beds")} /></Field>
        <Field label="Status"><Select value={form.status} onChange={set("status")} options={["available", "low", "shortage"].map((value) => ({ value, label: STATUS_LABELS[value] }))} /></Field>
      </div>
      <fieldset className="check-group">
        <legend>{t("Type")}</legend>
        <label className="check"><input type="checkbox" checked={form.is_equipment || form.category === "equipment"} onChange={set("is_equipment")} /> {t("Medical equipment")}</label>
        <label className="check"><input type="checkbox" checked={form.is_specialized} onChange={set("is_specialized")} /> {t("For elderly or medically vulnerable residents")}</label>
      </fieldset>
      <ErrorText>{action.error}</ErrorText>
      <Button type="submit" disabled={action.busy}>Add item</Button>
    </form>
  );
}

const SUPPLY_FILTERS = [
  ["all", "All items"],
  ["missing", "Low or missing"],
  ["equipment", "Medical equipment"],
];

// Supplies and shortages on one page, with filters.
export function ShelterSuppliesPage() {
  const startOnShortages = window.location.pathname.endsWith("/shortages");
  return (
    <ShelterFrame title="Supplies and shortages" sub="Medication, baby formula, sanitary products, food, and medical equipment.">
      {(data, reload) => <SupplyBoard data={data} reload={reload} initial={startOnShortages ? "missing" : "all"} />}
    </ShelterFrame>
  );
}

function SupplyBoard({ data, reload, initial }) {
  const { t } = useI18n();
  const [filter, setFilter] = useState(initial);
  const items = data.inventory;
  const missing = items.filter((i) => i.status !== "available");
  const shown = filter === "missing" ? missing : filter === "equipment" ? items.filter((i) => i.is_equipment) : items;
  return (
    <>
      <div className="stat-grid">
        <Stat value={items.length} label="Items" />
        <Stat value={items.filter((i) => i.status === "low").length} label="Low" />
        <Stat value={items.filter((i) => i.status === "shortage").length} label="Shortage" tone={items.some((i) => i.status === "shortage") ? "rose" : ""} />
        <Stat value={items.filter((i) => i.is_equipment).length} label="Medical equipment" />
      </div>
      <div className="chip-row" role="group" aria-label={t("Show")}>
        {SUPPLY_FILTERS.map(([value, label]) => (
          <button key={value} type="button" className={`chip ${filter === value ? "active" : ""}`} aria-pressed={filter === value} onClick={() => setFilter(value)}>
            {t(label)}{value === "missing" && missing.length ? ` (${missing.length})` : ""}
          </button>
        ))}
      </div>
      <section className="card"><InventoryTable items={shown} reload={reload} /></section>
      <AddInventory shelterId={data.shelter.id} reload={reload} />
    </>
  );
}

export function ShelterExchangePage() {
  const { t } = useI18n();
  return (
    <ShelterFrame title="Exchange" sub="Send extra supplies to shelters that are short.">
      {(data, reload) => <Exchange data={data} reload={reload} t={t} />}
    </ShelterFrame>
  );
}

function Exchange({ data, reload, t }) {
  const shelters = useData("/shelters");
  const [form, set, reset] = useForm({ to_shelter_id: "", item_name: "", quantity: 1, needs_volunteer: true });
  const create = useAction(reload);
  const update = useAction(reload);
  const others = (shelters.data?.shelters || []).filter((s) => s.id !== data.shelter.id);
  const short = others.filter((s) => s.shortage_names.length);
  return (
    <>
      {short.length > 0 && (
        <section className="card stack">
          <h3>{t("Shelters reporting shortages")}</h3>
          {short.map((s) => <div className="row" key={s.id}><strong>{s.name}</strong><span className="small">{s.shortage_names.join(", ")}</span></div>)}
        </section>
      )}
      <form className="card stack" onSubmit={async (e) => { e.preventDefault(); if (await create.run("/exchanges", "POST", { ...form, to_shelter_id: Number(form.to_shelter_id) })) reset(); }}>
        <h3>{t("Offer supplies to another shelter")}</h3>
        <Field label="Send to">
          <select value={form.to_shelter_id} onChange={set("to_shelter_id")} required>
            <option value="">—</option>
            {others.map((s) => <option key={s.id} value={s.id}>{s.name}{s.shortage_names.length ? ` (${t("short")}: ${s.shortage_names.join(", ")})` : ""}</option>)}
          </select>
        </Field>
        <div className="grid-2">
          <Field label="Item"><input value={form.item_name} onChange={set("item_name")} required /></Field>
          <Field label="Quantity"><input type="number" min="1" value={form.quantity} onChange={set("quantity")} /></Field>
        </div>
        <div className="check-group">
          <label className="check"><input type="checkbox" checked={form.needs_volunteer} onChange={set("needs_volunteer")} /> {t("Ask a volunteer to deliver it")}</label>
        </div>
        <ErrorText>{create.error}</ErrorText>
        <Button type="submit" disabled={create.busy}>Propose exchange</Button>
      </form>
      <section className="card stack">
        <h3>{t("Exchanges")}</h3>
        <ErrorText>{update.error}</ErrorText>
        {data.exchanges.length === 0 && <Empty>{t("No exchanges yet.")}</Empty>}
        {data.exchanges.map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.quantity} × {item.item_name}</strong><div className="small muted">{item.from_shelter_name} → {item.to_shelter_name}{item.needs_volunteer ? ` · ${t("volunteer delivery")}` : ""}</div></div>
            <StatusSelect value={item.status} options={["proposed", "accepted", "in_transit", "completed"]} onChange={(status) => update.run(`/exchanges/${item.id}`, "PATCH", { status })} />
          </div>
        ))}
      </section>
    </>
  );
}

export function ShelterDonationsPage() {
  const { t } = useI18n();
  return (
    <ShelterFrame title="Donations" sub="Confirm gifts when they arrive and when they are given out.">
      {(data, reload) => <ShelterDonations rows={data.donations} reload={reload} t={t} />}
    </ShelterFrame>
  );
}

function ShelterDonations({ rows, reload, t }) {
  const action = useAction(reload);
  return (
    <section className="card">
      <ErrorText>{action.error}</ErrorText>
      {rows.length === 0 && <Empty>{t("No donations for this shelter yet.")}</Empty>}
      {rows.map((item) => (
        <div className="row" key={item.id}>
          <div><strong>{item.kind === "money" ? money(item.amount, item.currency) : item.item_description}</strong><div className="small muted">{item.donor_name}{item.cause_label ? ` · ${item.cause_label}` : ""}</div></div>
          <StatusSelect value={item.status} options={["pledged", "received", "allocated", "distributed"]} onChange={(status) => action.run(`/donations/${item.id}`, "PATCH", { status })} />
        </div>
      ))}
    </section>
  );
}

export function ShelterVolunteersPage() {
  const { t } = useI18n();
  return (
    <ShelterFrame title="Volunteers" sub="Post tasks for volunteers and announce doctor visits.">
      {(data, reload) => <ShelterVolunteers data={data} reload={reload} t={t} />}
    </ShelterFrame>
  );
}

function ShelterVolunteers({ data, reload, t }) {
  const [task, setTask, resetTask] = useForm({ kind: "delivery", title: "", details: "", location: "", scheduled_at: "" });
  const [notice, setNotice, resetNotice] = useForm({ kind: "doctor_visit", title: "", location: "", starts_at: "" });
  const addTask = useAction(reload);
  const addNotice = useAction(reload);
  return (
    <>
      <section className="card stack">
        <h3>{t("Tasks")}</h3>
        {data.tasks.length === 0 && <Empty>{t("No tasks yet.")}</Empty>}
        {data.tasks.map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.title}</strong><div className="small muted">{[t(TASK_KIND_LABELS[item.kind] || item.kind), item.assignee_name, formatWhen(item.scheduled_at)].filter(Boolean).join(" · ")}</div></div>
            <StatusPill value={item.status} />
          </div>
        ))}
      </section>
      <form className="card stack" onSubmit={async (e) => { e.preventDefault(); if (await addTask.run("/tasks", "POST", task)) resetTask(); }}>
        <h3>{t("Post a volunteer task")}</h3>
        <Field label="Type"><Select value={task.kind} onChange={setTask("kind")} options={Object.entries(TASK_KIND_LABELS).map(([value, label]) => ({ value, label }))} /></Field>
        <Field label="Title"><input value={task.title} onChange={setTask("title")} required /></Field>
        <Field label="Details"><textarea value={task.details} onChange={setTask("details")} /></Field>
        <div className="grid-2">
          <Field label="Location"><input value={task.location} onChange={setTask("location")} /></Field>
          <Field label="Date"><input type="datetime-local" value={task.scheduled_at} onChange={setTask("scheduled_at")} /></Field>
        </div>
        <ErrorText>{addTask.error}</ErrorText>
        <Button type="submit" disabled={addTask.busy}>Post task</Button>
      </form>
      <form className="card stack" onSubmit={async (e) => { e.preventDefault(); if (await addNotice.run("/announcements", "POST", notice)) resetNotice(); }}>
        <h3>{t("Announce a visit")}</h3>
        <Field label="Type"><Select value={notice.kind} onChange={setNotice("kind")} options={[{ value: "doctor_visit", label: "Volunteer doctor visit" }, { value: "free_healthcare_day", label: "Free healthcare day" }]} /></Field>
        <Field label="Title"><input value={notice.title} onChange={setNotice("title")} required /></Field>
        <div className="grid-2">
          <Field label="Location"><input value={notice.location} onChange={setNotice("location")} /></Field>
          <Field label="Date"><input type="datetime-local" value={notice.starts_at} onChange={setNotice("starts_at")} /></Field>
        </div>
        <ErrorText>{addNotice.error}</ErrorText>
        <Button type="submit" disabled={addNotice.busy}>Announce</Button>
      </form>
    </>
  );
}

export function ShelterComplaintsPage() {
  const { t } = useI18n();
  return (
    <ShelterFrame title="Complaints">
      {(data, reload) => <ComplaintBoard rows={data.complaints} reload={reload} t={t} />}
    </ShelterFrame>
  );
}

// Status-tracked complaint list used by the shelter coordinator and the Ministry.
function ComplaintBoard({ rows, reload, t, canAdd = true }) {
  const [filter, setFilter] = useState("all");
  const [adding, setAdding] = useState(false);
  const action = useAction(reload);
  const count = (status) => rows.filter((r) => r.status === status).length;
  const shown = rows.filter((r) => filter === "all" || r.status === filter);
  return (
    <>
      <div className="stat-grid">
        {["received", "under_review", "being_addressed", "resolved"].map((status) => <Stat key={status} value={count(status)} label={STATUS_LABELS[status]} />)}
      </div>
      <div className="spread">
        <div className="chip-row" role="group" aria-label={t("Status")}>
          {COMPLAINT_FILTERS.map((value) => (
            <button key={value} type="button" className={`chip ${filter === value ? "active" : ""}`} aria-pressed={filter === value} onClick={() => setFilter(value)}>{t(value === "all" ? "All" : STATUS_LABELS[value])}</button>
          ))}
        </div>
        {canAdd && <Button type="button" soft onClick={() => setAdding((v) => !v)}>{adding ? "Close" : "Add a complaint"}</Button>}
      </div>
      {adding && <section className="card stack"><h3>{t("Add a complaint")}</h3><ComplaintForm forOthers onDone={reload} /></section>}
      <section className="card">
        <ErrorText>{action.error}</ErrorText>
        {shown.length === 0 && <Empty>{t("No complaints here yet.")}</Empty>}
        {shown.map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{t(item.category)}</strong><div className="small muted">{[item.shelter_name, item.region, item.source, formatWhen(item.created_at)].filter(Boolean).join(" · ")}</div><div className="small">{item.description}</div></div>
            <StatusSelect value={item.status} options={["received", "under_review", "being_addressed", "resolved"]} onChange={(status) => action.run(`/complaints/${item.id}`, "PATCH", { status })} />
          </div>
        ))}
      </section>
    </>
  );
}

const currentMonth = () => new Date().toISOString().slice(0, 7);

function downloadReport(name, history) {
  const header = "Month,Shortages,Occupancy,Complaints,Critical residents";
  const lines = history.map((r) => [r.month, r.shortages, r.occupancy, r.complaints, r.critical].join(","));
  const blob = new Blob([[header, ...lines].join("\n")], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${name.replace(/\W+/g, "-")}-monthly-report.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function HistoryTable({ history }) {
  const { t } = useI18n();
  if (!history || history.length === 0) return <Empty>{t("No reports yet.")}</Empty>;
  return (
    <div className="table-wrap">
      <table className="data">
        <thead><tr><th>{t("Month")}</th><th>{t("Shortages")}</th><th>{t("Occupancy")}</th><th>{t("Complaints")}</th><th>{t("Critical")}</th></tr></thead>
        <tbody>{history.map((row) => <tr key={row.month}><td>{row.month}{row.month === currentMonth() ? <span className="small muted"> · {t("this month, live")}</span> : null}</td><td>{row.shortages}</td><td>{row.occupancy}</td><td>{row.complaints}</td><td>{row.critical}</td></tr>)}</tbody>
      </table>
    </div>
  );
}

export function ShelterReportsPage() {
  const { t } = useI18n();
  return (
    <ShelterFrame title="Monthly report" sub="Shortages, occupancy, complaints and critical residents, month by month.">
      {(data) => (
        <section className="card stack">
          <div className="spread">
            <h3>{data.shelter.name}</h3>
            <Button type="button" soft onClick={() => downloadReport(data.shelter.name, data.history.history)}>Download CSV</Button>
          </div>
          <Note>{t("The app makes this report automatically from your shelter's data. The current month keeps updating until it ends, then it is saved as history.")}</Note>
          <HistoryTable history={data.history.history} />
          <p className="small muted">{t("Trend")}: {t(data.history.trend || "stable")}</p>
        </section>
      )}
    </ShelterFrame>
  );
}

/* ------------------------------------------------------------------ */
/* Doctor / nurse / psychologist                                       */
/* ------------------------------------------------------------------ */

export function DoctorPage() {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const { data, error } = useData(`/doctor/patients${search ? `?q=${encodeURIComponent(search)}` : ""}`);
  if (data && data.verification_status !== "approved") {
    return (
      <div className="stack">
        <PageTitle>Patients</PageTitle>
        <div className="banner amber stack">
          <strong>{t("Your license is being checked")}</strong>
          <p className="small">{t("You can add medical records once the Ministry approves your credentials.")}</p>
          <StatusPill value={data.verification_status} />
        </div>
      </div>
    );
  }
  return (
    <div className="stack">
      <PageTitle sub="Search by name or passport ID. Open a passport to add a clinician record.">Patients</PageTitle>
      <form className="card inline" onSubmit={(e) => { e.preventDefault(); setSearch(q.trim()); }}>
        <input aria-label={t("Find a patient")} placeholder={t("Name or MAK-0000-0000")} value={q} onChange={(e) => setQ(e.target.value)} />
        <Button type="submit">Search</Button>
      </form>
      <ErrorText>{error}</ErrorText>
      <section className="card">
        {data && data.patients.length === 0 && <Empty>{search ? t("No patient found.") : t("Patients you write records for appear here. Search a passport ID to start.")}</Empty>}
        <div className="table-wrap">
          {data && data.patients.length > 0 && (
            <table className="data">
              <thead><tr><th>{t("Name")}</th><th>{t("Passport ID")}</th><th>{t("Age")}</th><th>{t("Shelter")}</th><th>{t("Status")}</th></tr></thead>
              <tbody>
                {data.patients.map((p) => (
                  <tr key={p.id}>
                    <td><Link to={`/lookup?id=${p.passport_id}`}>{p.full_name}</Link></td>
                    <td className="mono small">{p.passport_id}</td>
                    <td>{p.age ?? "—"}</td>
                    <td>{p.shelter_name || "—"}</td>
                    <td><CriticalityControl key={`${p.id}-${p.criticality.level}`} profile={p} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Ministry of Public Health                                           */
/* ------------------------------------------------------------------ */

function MinistryFrame({ path, title, sub, children }) {
  const { data, error, reload } = useData(path);
  return (
    <div className="stack">
      <PageTitle sub={sub}>{title}</PageTitle>
      <ErrorText>{error}</ErrorText>
      {data && children(data, reload)}
    </div>
  );
}

export function MinistryOverviewPage() {
  const { t } = useI18n();
  return (
    <MinistryFrame path="/ministry/overview" title="National shelter overview">
      {(data) => (
        <>
          <div className="stat-grid">
            <Stat value={data.shelter_count} label="Shelters" />
            <Stat value={data.occupancy.toLocaleString()} label="Residents" />
            <Stat value={data.critical_residents} label="Critical residents" />
            <Stat value={data.open_shortages} label="Shortages" tone={data.open_shortages ? "rose" : ""} />
            <Stat value={data.open_complaints} label="Open complaints" />
            <Stat value={data.outbreak_count} label="Outbreak reports" />
          </div>
          <Note>{t(data.note)}</Note>
          <section className="card stack">
            <h3>{t("Where help is needed first")}</h3>
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>{t("Shelter")}</th><th>{t("Region")}</th><th>{t("Priority")}</th><th>{t("Shortages")}</th><th>{t("Critical")}</th><th>{t("Occupancy")}</th></tr></thead>
                <tbody>
                  {data.ranked.map((row) => (
                    <tr key={row.id}>
                      <td><strong>{row.name}</strong></td>
                      <td>{row.region}</td>
                      <td>{row.priority.score}</td>
                      <td>{row.priority.shortages}</td>
                      <td>{row.priority.critical_residents}</td>
                      <td>{row.percent}%{row.overcrowded ? ` · ${t("Overcrowded")}` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <Forecast rows={data.forecast} />
          <VerificationQueue />
        </>
      )}
    </MinistryFrame>
  );
}

function Forecast({ rows }) {
  const { t } = useI18n();
  return (
    <section className="card stack">
      <h3>{t("Demand forecast")}</h3>
      <Note>{t("Planning estimate from reported shortages. A person decides what to send.")}</Note>
      {rows.length === 0 && <Empty>{t("Not enough history yet.")}</Empty>}
      {rows.map((row) => (
        <div className="row" key={row.region}>
          <div><strong>{row.region}</strong><div className="small muted">{row.history.map((h) => `${h.month}: ${h.shortages}`).join(" · ")}</div></div>
          <div className="stack" style={{ alignItems: "flex-end" }}>
            <strong>{row.estimate_shortages}</strong>
            <Pill value={row.direction === "rising" ? "high" : row.direction === "falling" ? "resolved" : "neutral"}>{t(row.direction)}</Pill>
          </div>
        </div>
      ))}
    </section>
  );
}

function VerificationQueue() {
  const { t } = useI18n();
  const { data, reload } = useData("/verification-queue");
  const action = useAction(reload);
  const users = data?.users || [];
  return (
    <section className="card stack">
      <h3>{t("Verification queue")}</h3>
      <ErrorText>{action.error}</ErrorText>
      {data && users.length === 0 && <Empty>{t("No accounts waiting.")}</Empty>}
      {users.map((u) => (
        <div className="row" key={u.id}>
          <div><strong>{u.full_name}</strong><div className="small muted">{[u.role, u.specialty, u.license_number, u.license_body].filter(Boolean).join(" · ")}</div></div>
          <div className="inline">
            <StatusPill value={u.verification_status} />
            <Button type="button" soft disabled={action.busy} onClick={() => action.run(`/users/${u.id}/verification`, "PATCH", { status: "approved" })}>Approve</Button>
          </div>
        </div>
      ))}
    </section>
  );
}

export function MinistrySheltersPage() {
  const { t } = useI18n();
  return (
    <MinistryFrame path="/ministry/shelters" title="Shelters" sub="Every registered shelter, ordered by need.">
      {(data) => (
        <section className="card">
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>{t("Shelter")}</th><th>{t("Capacity")}</th><th>{t("Accessible spaces")}</th><th>{t("Backup power")}</th><th>{t("Shortages")}</th><th>{t("Trend")}</th></tr></thead>
              <tbody>
                {data.shelters.map((s) => (
                  <tr key={s.id}>
                    <td><strong>{s.name}</strong><div className="small muted">{s.region}</div></td>
                    <td>{s.occupancy}/{s.capacity} ({s.percent}%)</td>
                    <td>{s.accessible ? s.accessible_spaces ?? "✓" : "—"}</td>
                    <td>{s.has_backup_power ? `${s.electricity_hours}h` : "—"}</td>
                    <td className="small">{s.inventory.filter((i) => i.status === "shortage").map((i) => i.item_name).join(", ") || "—"}</td>
                    <td>{t(s.history.trend)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </MinistryFrame>
  );
}

export function MinistryComplaintsPage() {
  const { t } = useI18n();
  const shelters = useData("/shelters");
  const names = Object.fromEntries((shelters.data?.shelters || []).map((s) => [s.id, s.name]));
  return (
    <MinistryFrame path="/ministry/complaints" title="Complaints">
      {(data, reload) => (
        <>
          <ComplaintBoard rows={data.complaints.map((c) => ({ ...c, shelter_name: names[c.shelter_id] }))} reload={reload} t={t} canAdd={false} />
          <section className="card stack">
            <h3>{t("Recurring problems")}</h3>
            {data.patterns.filter((p) => p.count > 1 || p.reopened).map((p) => (
              <div className="row" key={`${p.shelter_id}-${p.category}`}>
                <div><strong>{t(p.category)}</strong><div className="small muted">{p.shelter_name} · {p.region}</div></div>
                <div className="inline"><span>{p.count}×</span>{p.reopened && <Pill value="high">{t("Came back after resolved")}</Pill>}</div>
              </div>
            ))}
          </section>
          <section className="card stack">
            <h3>{t("By region")}</h3>
            {data.regions.map((r) => (
              <div className="row" key={r.region}>
                <div><strong>{r.region}</strong><div className="small muted">{r.categories.map((c) => `${t(c.category)} ${c.count}`).join(" · ")}</div></div>
                <span>{r.open} {t("open")} / {r.total}</span>
              </div>
            ))}
          </section>
        </>
      )}
    </MinistryFrame>
  );
}

export function MinistryNgosPage() {
  const { t } = useI18n();
  const shelters = useData("/shelters");
  return (
    <MinistryFrame path="/ministry/ngos" title="NGOs" sub="Connect NGO offers with shelters that need them.">
      {(data, reload) => <NgoConnect rows={data.requests} shelters={shelters.data?.shelters || []} reload={reload} t={t} />}
    </MinistryFrame>
  );
}

function NgoConnect({ rows, shelters, reload, t }) {
  const action = useAction(reload);
  return (
    <section className="card">
      <ErrorText>{action.error}</ErrorText>
      {rows.length === 0 && <Empty>{t("No NGO requests yet.")}</Empty>}
      {rows.map((item) => (
        <div className="row" key={item.id}>
          <div><strong>{item.organization}</strong><div className="small">{item.description}</div><div className="small muted">{item.shelter_name ? `→ ${item.shelter_name}` : t("Not connected yet")}</div></div>
          <div className="stack" style={{ alignItems: "flex-end" }}>
            <select aria-label={t("Connect to shelter")} value={item.shelter_id || ""} onChange={(e) => action.run(`/ngo/requests/${item.id}`, "PATCH", { shelter_id: Number(e.target.value) })}>
              <option value="">{t("Connect to shelter")}</option>
              {shelters.map((s) => <option key={s.id} value={s.id}>{s.name}{s.shortage_names.length ? ` (${s.shortage_names.length} ${t("short")})` : ""}</option>)}
            </select>
            <StatusSelect value={item.status} options={["submitted", "connected", "accepted", "delivered", "completed"]} onChange={(status) => action.run(`/ngo/requests/${item.id}`, "PATCH", { status })} />
          </div>
        </div>
      ))}
    </section>
  );
}

export function MinistryDonationsPage() {
  const { t } = useI18n();
  return (
    <MinistryFrame path="/ministry/donations" title="Donations" sub="Every gift and where it is going.">
      {(data) => (
        <>
          <div className="stat-grid">
            <Stat value={data.donations.length} label="Gifts" />
            <Stat value={money(data.donations.filter((d) => d.kind === "money").reduce((s, d) => s + (d.amount || 0), 0))} label="Money pledged" />
            <Stat value={data.distribution.filter((r) => r.underserved).length} label="Underserved shelters" tone="rose" />
          </div>
          <section className="card stack">
            <h3>{t("Distribution gaps")}</h3>
            {data.distribution.filter((r) => r.gaps.length).map((r) => (
              <div className="row" key={r.shelter_id}>
                <div><strong>{r.shelter_name}</strong><div className="small muted">{r.region} · {r.donation_count} {t("gifts")} · {money(r.money)}</div><div className="small">{t("Still short")}: {r.gaps.join(", ")}</div></div>
                {r.underserved && <Pill value="high">{t("Underserved")}</Pill>}
              </div>
            ))}
          </section>
          <section className="card">
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>{t("Donor")}</th><th>{t("Gift")}</th><th>{t("Recipient")}</th><th>{t("Status")}</th></tr></thead>
                <tbody>
                  {data.donations.map((d) => (
                    <tr key={d.id}>
                      <td>{d.donor_name}</td>
                      <td>{d.kind === "money" ? money(d.amount, d.currency) : d.item_description}</td>
                      <td>{d.shelter_name || d.cause_label || "—"}<div className="small muted">{d.region}</div></td>
                      <td><StatusPill value={d.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </MinistryFrame>
  );
}

const RISK_KEYS = [["elderly", "Elderly"], ["children", "Children"], ["pregnant", "Pregnant"], ["disability", "Disability"], ["device_dependent", "Device-dependent"]];

export function MinistryReportsPage() {
  const { t } = useI18n();
  return (
    <MinistryFrame path="/ministry/reports" title="Reports">
      {(data, reload) => (
        <>
          <section className="card stack">
            <h3>{t("High-risk counts")}</h3>
            <Note>{t("Counts only. Individual health passports stay with the patient.")}</Note>
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>{t("Region")}</th>{RISK_KEYS.map(([k, l]) => <th key={k}>{t(l)}</th>)}</tr></thead>
                <tbody>{data.high_risk.regions.map((r) => <tr key={r.label}><td><strong>{r.label}</strong></td>{RISK_KEYS.map(([k]) => <td key={k}>{r[k]}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </section>
          <OutbreakReview rows={data.outbreaks} reload={reload} />
          <Forecast rows={data.forecast} />
          <section className="card stack">
            <h3>{t("Shelter reporting history")}</h3>
            {data.history.map((row) => (
              <details key={row.shelter.id}>
                <summary><strong>{row.shelter.name}</strong> · {t(row.trend)}</summary>
                <HistoryTable history={row.history} />
              </details>
            ))}
          </section>
        </>
      )}
    </MinistryFrame>
  );
}

function OutbreakReview({ rows, reload }) {
  const { t } = useI18n();
  const action = useAction(reload);
  return (
    <section className="card stack">
      <h3>{t("Outbreak reports")}</h3>
      <Note>{t("This flags a cluster for public health staff. It does not declare an outbreak.")}</Note>
      <ErrorText>{action.error}</ErrorText>
      {rows.length === 0 && <Empty>{t("No reports.")}</Empty>}
      {rows.map((item) => (
        <div className="row" key={item.id}>
          <div><strong>{item.suspected_illness}</strong> · {item.case_count} {t("cases")}<div className="small muted">{item.shelter_name} · {item.region} · {formatWhen(item.created_at)}</div></div>
          <StatusSelect value={item.status} options={["reported", "under_review", "investigating"]} onChange={(status) => action.run(`/outbreaks/${item.id}`, "PATCH", { status })} />
        </div>
      ))}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* NGO                                                                 */
/* ------------------------------------------------------------------ */

export function NgoPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const { data, error, reload } = useData(user.verification_status === "approved" ? "/ngo/board" : null);
  const [form, set, reset] = useForm({ organization: user.full_name, description: "" });
  const submit = useAction(reload);
  const update = useAction(reload);
  if (user.verification_status !== "approved") {
    return (
      <div className="stack">
        <PageTitle>Coordination</PageTitle>
        <div className="banner amber stack"><strong>{t("Your organization is being checked")}</strong><p className="small">{t("The Ministry reviews NGO accounts before they can coordinate.")}</p><StatusPill value={user.verification_status} /></div>
      </div>
    );
  }
  return (
    <div className="stack">
      <PageTitle sub="Offer help to the Ministry. It connects you with a shelter that needs it.">Coordination</PageTitle>
      <ErrorText>{error}</ErrorText>
      <form className="card stack" onSubmit={async (e) => { e.preventDefault(); if (await submit.run("/ngo/requests", "POST", form)) reset(); }}>
        <h3>{t("Offer assistance")}</h3>
        <Field label="Organization"><input value={form.organization} onChange={set("organization")} /></Field>
        <Field label="What can you offer?"><textarea rows={3} value={form.description} onChange={set("description")} required /></Field>
        <ErrorText>{submit.error}</ErrorText>
        <Button type="submit" disabled={submit.busy}>Submit</Button>
      </form>
      <section className="card stack">
        <h3>{t("My requests")}</h3>
        <ErrorText>{update.error}</ErrorText>
        {data && data.requests.length === 0 && <Empty>{t("No requests yet.")}</Empty>}
        {(data?.requests || []).map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.description}</strong><div className="small muted">{item.shelter_name ? `→ ${item.shelter_name}` : t("Waiting for the Ministry to connect a shelter")}</div></div>
            {item.status === "submitted" ? <StatusPill value={item.status} /> : (
              <StatusSelect value={item.status} options={["connected", "accepted", "delivered", "completed"]} onChange={(status) => update.run(`/ngo/requests/${item.id}`, "PATCH", { status })} />
            )}
          </div>
        ))}
      </section>
      <section className="card stack">
        <h3>{t("Patient transport requests")}</h3>
        {data && data.transports.length === 0 && <Empty>{t("No rides waiting.")}</Empty>}
        {(data?.transports || []).map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.who} → {item.destination}</strong><div className="small muted">{item.destination_type}{item.wheelchair_required ? ` · ${t("Wheelchair access")}` : ""}</div></div>
            {item.status === "requested"
              ? <Button type="button" soft disabled={update.busy} onClick={() => update.run(`/transport/${item.id}`, "PATCH", { status: "accepted" })}>Accept</Button>
              : <Button type="button" soft disabled={update.busy} onClick={() => update.run(`/transport/${item.id}`, "PATCH", { status: "completed" })}>Complete</Button>}
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
const DONOR = ["donor"];
const SHELTER = ["shelter_coordinator"];
const CLINICIAN = ["doctor", "nurse", "psychologist"];
const MINISTRY = ["ministry"];
const NGO = ["ngo"];

export const ROLE_ROUTES = [
  ["/volunteer", VolunteerTasksPage, VOLUNTEER],
  ["/volunteer/notices", VolunteerNoticesPage, VOLUNTEER],
  ["/volunteer/complaints", VolunteerComplaintsPage, VOLUNTEER],
  ["/volunteer/support", VolunteerSupportPage, VOLUNTEER],
  ["/donor", DonorNeedsPage, DONOR],
  ["/donor/gifts", DonorGiftsPage, DONOR],
  ["/shelter", ShelterOverviewPage, SHELTER],
  ["/shelter/residents", ShelterResidentsPage, SHELTER],
  ["/shelter/supplies", ShelterSuppliesPage, SHELTER],
  ["/shelter/shortages", ShelterSuppliesPage, SHELTER],
  ["/shelter/exchange", ShelterExchangePage, SHELTER],
  ["/shelter/donations", ShelterDonationsPage, SHELTER],
  ["/shelter/volunteers", ShelterVolunteersPage, SHELTER],
  ["/shelter/complaints", ShelterComplaintsPage, SHELTER],
  ["/shelter/reports", ShelterReportsPage, SHELTER],
  ["/doctor", DoctorPage, CLINICIAN],
  ["/ministry", MinistryOverviewPage, MINISTRY],
  ["/ministry/shelters", MinistrySheltersPage, MINISTRY],
  ["/ministry/complaints", MinistryComplaintsPage, MINISTRY],
  ["/ministry/ngos", MinistryNgosPage, MINISTRY],
  ["/ministry/donations", MinistryDonationsPage, MINISTRY],
  ["/ministry/reports", MinistryReportsPage, MINISTRY],
  ["/ngo", NgoPage, NGO],
];
