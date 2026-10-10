import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, formatWhen } from "./api";
import { useAuth, useI18n } from "./context";
import { Bars, Button, ErrorText, Field, Note, Pill, Select } from "./ui";

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

export function ShelterPage() {
  const { section = "overview" } = useParams();
  const { user, refresh } = useAuth();
  const { t } = useI18n();
  const board = useData(user.shelter_id ? "/shelter/board" : "/shelters");
  if (!user.shelter_id) {
    return <ShelterChooser shelters={board.data?.shelters || []} onChosen={async (shelterId) => {
      const updated = await api(`/users/${user.id}/shelter`, { method: "PATCH", body: JSON.stringify({ shelter_id: shelterId }) });
      refresh(updated.user);
    }} />;
  }
  const data = board.data;
  return (
    <div className="stack">
      <ErrorText>{board.error}</ErrorText>
      {!data ? <p>Loading shelter…</p> : (
        <>
          {section === "overview" && <Overview data={data} reload={board.reload} />}
          {section === "residents" && <Residents data={data} reload={board.reload} />}
          {section === "supplies" && <Supplies data={data} reload={board.reload} />}
          {section === "shortages" && <Supplies data={data} reload={board.reload} onlyShort />}
          {section === "exchange" && <Exchange data={data} reload={board.reload} />}
          {section === "donations" && <Donations data={data} reload={board.reload} />}
          {section === "volunteers" && <Volunteers data={data} reload={board.reload} />}
          {section === "complaints" && <Complaints data={data} reload={board.reload} />}
          {section === "reports" && <Reports data={data} reload={board.reload} />}
          {!["overview", "residents", "supplies", "shortages", "exchange", "donations", "volunteers", "complaints", "reports"].includes(section) && <p>{t("Overview")}</p>}
        </>
      )}
    </div>
  );
}

function ShelterChooser({ shelters, onChosen }) {
  return (
    <div className="stack">
      <h2>Choose the shelter you coordinate</h2>
      {shelters.map((shelter) => (
        <button className="card" key={shelter.id} type="button" onClick={() => onChosen(shelter.id)} style={{ textAlign: "start" }}>
          <strong>{shelter.name}</strong>
          <div className="small muted">{shelter.region}</div>
        </button>
      ))}
    </div>
  );
}

function Overview({ data, reload }) {
  const { t } = useI18n();
  const shelter = data.shelter;
  return (
    <div className="stack">
      <div className="spread">
        <div>
          <h2>{shelter.name}</h2>
          <p className="muted">{shelter.region} · {shelter.address}</p>
        </div>
        <Pill value={shelter.overcrowded ? "shortage" : "available"}>{shelter.percent}% full</Pill>
      </div>
      <div className="stat-row">
        <div className="stat"><span className="small muted">{t("Occupancy")}</span><b>{shelter.occupancy}</b></div>
        <div className="stat"><span className="small muted">{t("Capacity")}</span><b>{shelter.capacity}</b></div>
        <div className="stat"><span className="small muted">Critical</span><b>{data.stats.critical_residents}</b></div>
        <div className="stat"><span className="small muted">{t("Shortages")}</span><b>{data.stats.shortages}</b></div>
      </div>
      <ShelterForm shelter={shelter} onDone={reload} />
      <Note>Critical counts come from reported device needs and a human confirmation. They do not assign treatment.</Note>
    </div>
  );
}

function ShelterForm({ shelter, onDone }) {
  const [form, setForm] = useState({
    capacity: shelter.capacity,
    occupancy: shelter.occupancy,
    accessible: shelter.accessible,
    accessible_spaces: shelter.accessible_spaces,
    has_backup_power: shelter.has_backup_power,
    electricity_hours: shelter.electricity_hours,
  });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  return (
    <form className="card grid-2" onSubmit={async (e) => { e.preventDefault(); await api(`/shelters/${shelter.id}`, { method: "PATCH", body: JSON.stringify(form) }); onDone(); }}>
      <Field label="Capacity"><input type="number" value={form.capacity} onChange={set("capacity")} /></Field>
      <Field label="Occupancy"><input type="number" value={form.occupancy} onChange={set("occupancy")} /></Field>
      <Field label="Accessible spaces"><input type="number" value={form.accessible_spaces} onChange={set("accessible_spaces")} /></Field>
      <Field label="Hours left"><input type="number" value={form.electricity_hours} onChange={set("electricity_hours")} /></Field>
      <label className="check"><input type="checkbox" checked={form.accessible} onChange={set("accessible")} /> Disability-accessible</label>
      <label className="check"><input type="checkbox" checked={form.has_backup_power} onChange={set("has_backup_power")} /> Backup power</label>
      <Button type="submit">Update shelter</Button>
    </form>
  );
}

function Residents({ data, reload }) {
  const { t } = useI18n();
  return (
    <div className="card">
      <h3>{t("Residents")}</h3>
      <Note>Names and criticality only. Open a passport only when the patient grants access to a clinician.</Note>
      {data.residents.map((person) => (
        <div className="row" key={person.id}>
          <div>
            <strong>{person.full_name}</strong>
            <div className="small muted">{person.age ?? "—"} yrs {person.disability ? "· access need" : ""}</div>
            <div className="small">{(person.criticality.reasons || []).join(" · ")}</div>
          </div>
          <div className="stack">
            <Pill value={person.criticality.level}>{person.criticality.confirmed ? "Confirmed" : "Suggested"}</Pill>
            <button className="text-btn" type="button" onClick={async () => {
              await api(`/profiles/${person.id}/criticality-review`, { method: "POST", body: JSON.stringify({ classification: person.criticality.level === "critical" ? "non_critical" : "critical", note: "Reviewed on the shelter roster." }) });
              reload();
            }}>Confirm flip</button>
            <button className="text-btn" type="button" onClick={async () => {
              await api(`/relocations/${(await api("/relocations", { method: "POST", body: JSON.stringify({ profile_id: person.id, reason: "Urgent relocation requested by the shelter coordinator." }) })).relocation.id}`, { method: "PATCH", body: JSON.stringify({ status: "escalated" }) });
              reload();
            }}>{t("Escalate")}</button>
          </div>
        </div>
      ))}
      <h3 className="section-title">Relocation requests</h3>
      {data.relocations.map((item) => (
        <div className="row" key={item.id}>
          <div><strong>{item.who}</strong><div className="small">{item.reason}</div></div>
          <Pill value={item.status}>{item.status}</Pill>
        </div>
      ))}
    </div>
  );
}

function Supplies({ data, reload, onlyShort = false }) {
  const items = data.inventory.filter((item) => !onlyShort || item.status !== "available");
  const [form, setForm] = useState({ item_name: "", category: "medication", quantity: 0, status: "shortage", is_equipment: false, is_specialized: false });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  return (
    <div className="stack">
      <div className="card">
        <table>
          <thead><tr><th>Item</th><th>Qty</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.item_name}{item.is_specialized ? " · specialized" : ""}{item.is_equipment ? " · equipment" : ""}</td>
                <td>{item.quantity} {item.unit}</td>
                <td><Pill value={item.status}>{item.status}</Pill></td>
                <td>
                  <select value={item.status} onChange={async (e) => { await api(`/inventory/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value, quantity: item.quantity }) }); reload(); }}>
                    <option value="available">available</option>
                    <option value="low">low</option>
                    <option value="shortage">shortage</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <form className="card stack" onSubmit={async (e) => { e.preventDefault(); await api(`/shelters/${data.shelter.id}/inventory`, { method: "POST", body: JSON.stringify(form) }); reload(); }}>
        <h3>Add item</h3>
        <Field label="Title"><input value={form.item_name} onChange={set("item_name")} required /></Field>
        <div className="grid-2">
          <Field label="Status">
            <Select value={form.status} onChange={set("status")} options={["available", "low", "shortage"].map((value) => ({ value, label: value }))} />
          </Field>
          <Field label="Amount"><input type="number" value={form.quantity} onChange={set("quantity")} /></Field>
        </div>
        <label className="check"><input type="checkbox" checked={form.is_equipment} onChange={set("is_equipment")} /> Specialized equipment</label>
        <label className="check"><input type="checkbox" checked={form.is_specialized} onChange={set("is_specialized")} /> Specialized medical item</label>
        <Button type="submit">Add item</Button>
      </form>
    </div>
  );
}

function Exchange({ data, reload }) {
  const [shelters, setShelters] = useState([]);
  const [form, setForm] = useState({ to_shelter_id: "", item_name: "", quantity: 1, needs_volunteer: true });
  useEffect(() => { api("/shelters").then((result) => setShelters(result.shelters)); }, []);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  return (
    <div className="stack">
      <form className="card stack" onSubmit={async (e) => { e.preventDefault(); await api("/exchanges", { method: "POST", body: JSON.stringify({ ...form, to_shelter_id: Number(form.to_shelter_id), quantity: Number(form.quantity) }) }); reload(); }}>
        <h3>Send supplies to another shelter</h3>
        <Field label="Shelter">
          <select value={form.to_shelter_id} onChange={set("to_shelter_id")} required>
            <option value="">Choose</option>
            {shelters.filter((shelter) => shelter.id !== data.shelter.id).map((shelter) => <option key={shelter.id} value={shelter.id}>{shelter.name}</option>)}
          </select>
        </Field>
        <Field label="Title"><input value={form.item_name} onChange={set("item_name")} required /></Field>
        <Field label="Amount"><input type="number" value={form.quantity} onChange={set("quantity")} /></Field>
        <label className="check"><input type="checkbox" checked={form.needs_volunteer} onChange={set("needs_volunteer")} /> Ask a volunteer to deliver</label>
        <Button type="submit">Save</Button>
      </form>
      <div className="card">
        {data.exchanges.map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.item_name}</strong><div className="small muted">{item.from_shelter_name} → {item.to_shelter_name} · {item.quantity}</div></div>
            <select value={item.status} onChange={async (e) => { await api(`/exchanges/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) }); reload(); }}>
              {["proposed", "accepted", "in_transit", "completed"].map((status) => <option key={status}>{status}</option>)}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}

function Donations({ data, reload }) {
  return (
    <div className="card">
      {data.donations.map((item) => (
        <div className="row" key={item.id}>
          <div><strong>{item.donor_name}</strong><div className="small">{item.kind === "money" ? `${item.amount} ${item.currency}` : item.item_description}</div></div>
          <select value={item.status} onChange={async (e) => { await api(`/donations/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) }); reload(); }}>
            {["pledged", "received", "allocated", "distributed"].map((status) => <option key={status}>{status}</option>)}
          </select>
        </div>
      ))}
      {data.donations.length === 0 && <p className="muted">No gifts recorded for this shelter yet.</p>}
    </div>
  );
}

function Volunteers({ data, reload }) {
  const [form, setForm] = useState({ title: "", kind: "companion", location: "", details: "" });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  return (
    <div className="stack">
      <div className="card">
        {data.tasks.map((task) => (
          <div className="row" key={task.id}>
            <div><strong>{task.title}</strong><div className="small muted">{task.kind} · {task.assignee_name || "Unassigned"} · {formatWhen(task.scheduled_at)}</div></div>
            <Pill value={task.status}>{task.status}</Pill>
          </div>
        ))}
      </div>
      <form className="card stack" onSubmit={async (e) => { e.preventDefault(); await api("/tasks", { method: "POST", body: JSON.stringify(form) }); reload(); }}>
        <h3>Post a volunteer task</h3>
        <Field label="Title"><input value={form.title} onChange={set("title")} required /></Field>
        <Field label="Type">
          <Select value={form.kind} onChange={set("kind")} options={[{ value: "companion", label: "Hospital companion" }, { value: "delivery", label: "Delivery" }, { value: "other", label: "Other" }]} />
        </Field>
        <Field label="Destination"><input value={form.location} onChange={set("location")} /></Field>
        <Field label="Details"><textarea value={form.details} onChange={set("details")} /></Field>
        <Button type="submit">Save</Button>
      </form>
      <AnnouncementForm shelterId={data.shelter.id} />
    </div>
  );
}

function AnnouncementForm({ shelterId }) {
  const [form, setForm] = useState({ kind: "doctor_visit", title: "", location: "", starts_at: "", details: "", shelter_id: shelterId });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const [done, setDone] = useState(false);
  return (
    <form className="card stack" onSubmit={async (e) => { e.preventDefault(); await api("/announcements", { method: "POST", body: JSON.stringify(form) }); setDone(true); }}>
      <h3>Announce a visit or free healthcare day</h3>
      <Field label="Type">
        <Select value={form.kind} onChange={set("kind")} options={[{ value: "doctor_visit", label: "Doctor visit" }, { value: "free_healthcare_day", label: "Free healthcare day" }]} />
      </Field>
      <Field label="Title"><input value={form.title} onChange={set("title")} required /></Field>
      <Field label="Destination"><input value={form.location} onChange={set("location")} /></Field>
      <Field label="Date"><input type="datetime-local" value={form.starts_at} onChange={set("starts_at")} /></Field>
      <Button type="submit">Save</Button>
      {done && <p className="small">Announcement posted to resident and volunteer dashboards.</p>}
    </form>
  );
}

function Complaints({ data, reload }) {
  async function setStatus(id, status) {
    await api(`/complaints/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    reload();
  }
  return (
    <div className="card">
      {data.complaints.map((item) => (
        <div className="row" key={item.id}>
          <div>
            <strong>{item.category}</strong>
            <div className="small">{item.description}</div>
            <div className="small muted">{item.source}</div>
          </div>
          <select value={item.status} onChange={(e) => setStatus(item.id, e.target.value)}>
            {["received", "under_review", "being_addressed", "resolved"].map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </div>
      ))}
    </div>
  );
}

function Reports({ data, reload }) {
  const history = data.history?.history || [];
  const max = Math.max(1, ...history.map((item) => item.shortages));
  const [form, setForm] = useState({ suspected_illness: "", case_count: 2, notes: "" });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  return (
    <div className="stack">
      <div className="card stack">
        <h3>Reported shortages over time</h3>
        <p className="small muted">Trend: {data.history?.trend}. Compare months before deciding where to send help.</p>
        {history.map((item) => (
          <div key={item.month}>
            <div className="spread small"><span>{item.month}</span><span>{item.shortages}</span></div>
            <Bars value={item.shortages} max={max} />
          </div>
        ))}
      </div>
      <div className="card">
        <h3>Infection cluster reports</h3>
        <Note>This flags a cluster for public health staff. It does not declare an outbreak.</Note>
        {data.outbreaks.map((item) => (
          <div className="row" key={item.id}><div><strong>{item.suspected_illness}</strong><div className="small">{item.case_count} people · {item.notes}</div></div><Pill value={item.status}>{item.status}</Pill></div>
        ))}
      </div>
      <form className="card stack" onSubmit={async (e) => { e.preventDefault(); await api("/outbreaks", { method: "POST", body: JSON.stringify(form) }); reload(); }}>
        <Field label="Title"><input placeholder="Suspected illness" value={form.suspected_illness} onChange={set("suspected_illness")} required /></Field>
        <Field label="Amount"><input type="number" value={form.case_count} onChange={set("case_count")} /></Field>
        <Field label="Details"><textarea value={form.notes} onChange={set("notes")} /></Field>
        <Button type="submit">Submit</Button>
      </form>
    </div>
  );
}
