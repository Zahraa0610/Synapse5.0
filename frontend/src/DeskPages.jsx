import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, fileUrl, formatWhen } from "./api";
import { useAuth } from "./context";
import { Bars, Button, ErrorText, Field, Note, Pill, Select } from "./ui";

function useData(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(Boolean(path));

  const reload = async () => {
    if (!path) {
      setData(null);
      setLoading(false);
      return null;
    }
    setLoading(true);
    try {
      const next = await api(path);
      setData(next);
      setError("");
      return next;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    setData(null);
    setError("");
    if (!path) {
      setLoading(false);
      return undefined;
    }
    setLoading(true);
    api(path)
      .then((next) => {
        if (!ignore) setData(next);
      })
      .catch((err) => {
        if (!ignore) setError(err.message);
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [path]);

  return { data, error, loading, reload };
}

export function DoctorPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [chart, setChart] = useState(null);

  async function search(event) {
    event?.preventDefault();
    try {
      const data = await api(`/doctor/patients?q=${encodeURIComponent(query)}`);
      setPatients(data.patients);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }
  useEffect(() => { search(); }, []);

  async function openPatient(patient) {
    setSelected(patient);
    const data = await api(`/doctor/profiles/${patient.id}`);
    setChart(data);
  }

  if (user.verification_status !== "approved") {
    return (
      <div className="card stack">
        <h2>Credentials under review</h2>
        <Pill value={user.verification_status}>{user.verification_status}</Pill>
        <Note>You can sign in, but clinical records stay closed until the Ministry marks the license approved. Patient-entered and clinician-entered records stay distinct.</Note>
      </div>
    );
  }

  return (
    <div className="card-grid two">
      <div className="stack">
        <form className="inline" onSubmit={search}>
          <input placeholder="Find a patient who shared access" value={query} onChange={(e) => setQuery(e.target.value)} />
          <Button type="submit">Find a patient</Button>
        </form>
        <ErrorText>{error}</ErrorText>
        <Note>Patients grant access. You cannot open a passport they have not shared.</Note>
        <div className="card">
          {(patients || []).map((patient) => (
            <button className="row" key={patient.id} type="button" onClick={() => openPatient(patient)} style={{ width: "100%", background: "transparent", borderInline: 0 }}>
              <strong>{patient.full_name}</strong>
              <Pill value={patient.criticality.level}>{patient.criticality.level === "critical" ? "Critical" : "Non-critical"}</Pill>
            </button>
          ))}
          {patients && patients.length === 0 && <p className="muted">No shared passport matches that name.</p>}
        </div>
        {chart && <ClinicianForm profile={chart.profile} onDone={() => openPatient(selected)} />}
      </div>
      <div className="card stack">
        {!chart && <p className="muted">Choose a patient who has granted you access.</p>}
        {chart && (
          <>
            <h2>{chart.profile.full_name}</h2>
            <p className="small muted">{chart.profile.blood_type} · {chart.profile.shelter_name}</p>
            {chart.entries.map((entry) => (
              <div className="row" key={entry.id}>
                <div>
                  <strong>{entry.title}</strong>
                  <div className="small muted">{entry.entry_type} · {entry.facility_name || "No facility"} · {entry.occurred_on || ""}</div>
                  <div className="small">{entry.author_type === "clinician" ? "Clinician-entered" : "Patient-entered"} · {entry.author_name}</div>
                  {entry.result_text && <div className="small">Result: {entry.result_text}</div>}
                  {entry.attachments?.map((file) => (
                    <button key={file.id} className="text-btn" type="button" onClick={async () => window.open(await fileUrl(`/attachments/${file.id}`), "_blank")}>{file.filename}</button>
                  ))}
                </div>
                {entry.vaccine_status && <Pill value={entry.vaccine_status}>{entry.vaccine_status}</Pill>}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

function ClinicianForm({ profile, onDone }) {
  const { user } = useAuth();
  const [form, setForm] = useState({ entry_type: "lab", title: "", details: "", occurred_on: "", facility_name: "", result_text: "", doctor_name: user.full_name, vaccine_status: "administered" });
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const created = await api(`/profiles/${profile.id}/entries`, { method: "POST", body: JSON.stringify(form) });
      if (file) {
        const body = new FormData();
        body.append("file", file);
        await api(`/entries/${created.entry.id}/attachments`, { method: "POST", body });
      }
      setForm({ ...form, title: "", details: "", result_text: "" });
      onDone();
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <form className="card stack" onSubmit={submit}>
      <h3>Add a clinician record</h3>
      <Field label="Title"><input value={form.title} onChange={set("title")} required /></Field>
      <div className="grid-2">
        <Field label="Type">
          <Select value={form.entry_type} onChange={set("entry_type")} options={["condition", "allergy", "medication", "operation", "lab", "report", "vaccine", "note"].map((value) => ({ value, label: value }))} />
        </Field>
        <Field label="Date"><input type="date" value={form.occurred_on} onChange={set("occurred_on")} /></Field>
      </div>
      <Field label="Facility"><input value={form.facility_name} onChange={set("facility_name")} required /></Field>
      <Field label="Clinician name"><input value={form.doctor_name} onChange={set("doctor_name")} /></Field>
      <Field label="Result"><input value={form.result_text} onChange={set("result_text")} /></Field>
      <Field label="Details"><textarea value={form.details} onChange={set("details")} /></Field>
      <Field label="Attach a file"><input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} /></Field>
      <ErrorText>{error}</ErrorText>
      <Button type="submit">Save to health passport</Button>
    </form>
  );
}

export function MinistryPage() {
  const { section = "overview" } = useParams();
  const path = {
    overview: "/ministry/overview",
    shelters: "/ministry/shelters",
    complaints: "/ministry/complaints",
    ngos: "/ministry/ngos",
    donations: "/ministry/donations",
    reports: "/ministry/reports",
  }[section] || "/ministry/overview";
  const view = useData(path);
  const queue = useData(section === "reports" ? "/verification-queue" : null);
  const ready = view.data && payloadMatches(section, view.data);
  return (
    <div className="stack">
      <ErrorText>{view.error}</ErrorText>
      {view.loading && <p className="muted">Loading this page…</p>}
      {ready && section === "overview" && <MinistryOverview data={view.data} />}
      {ready && section === "shelters" && <MinistryShelters data={view.data} />}
      {ready && section === "complaints" && <MinistryComplaints data={view.data} reload={view.reload} />}
      {ready && section === "ngos" && <MinistryNgos data={view.data} reload={view.reload} />}
      {ready && section === "donations" && <MinistryDonations data={view.data} />}
      {ready && section === "reports" && <MinistryReports data={view.data} queue={queue.data} reload={queue.reload} />}
    </div>
  );
}

function payloadMatches(section, data) {
  if (section === "overview") return Array.isArray(data.ranked);
  if (section === "shelters") return Array.isArray(data.shelters);
  if (section === "complaints") return Array.isArray(data.complaints);
  if (section === "ngos") return Array.isArray(data.requests);
  if (section === "donations") return Array.isArray(data.donations);
  if (section === "reports") return Boolean(data.high_risk);
  return false;
}

function MinistryOverview({ data }) {
  const top = Math.max(...data.ranked.map((row) => row.priority.score), 1);
  return (
    <div className="stack">
      <h2>National shelter overview</h2>
      <Note>{data.note}</Note>
      <div className="stat-row">
        <div className="stat"><span className="small muted">Shelters</span><b>{data.shelter_count}</b></div>
        <div className="stat"><span className="small muted">Residents reported</span><b>{data.occupancy}</b></div>
        <div className="stat"><span className="small muted">Critical residents</span><b>{data.critical_residents}</b></div>
        <div className="stat"><span className="small muted">Open shortages</span><b>{data.open_shortages}</b></div>
      </div>
      <div className="card">
        <h3>Where assistance is most urgent</h3>
        <p className="small muted">Score uses shortages, critical residents, open complaints, and overcrowding. A person decides the response.</p>
        {data.ranked.map((row) => (
          <div key={row.id} className="row">
            <div style={{ flex: 1 }}>
              <strong>{row.name}</strong>
              <div className="small muted">{row.region} · {row.priority.shortages} shortages · {row.priority.critical_residents} critical · {row.percent}% full</div>
              <Bars value={row.priority.score} max={top} tone={row.priority.score > top * 0.6 ? "rose" : ""} />
            </div>
            <b>{row.priority.score}</b>
          </div>
        ))}
      </div>
      <Forecast forecast={data.forecast} />
    </div>
  );
}

function Forecast({ forecast }) {
  return (
    <div className="card stack">
      <h3>Demand forecast</h3>
      <Note>Planning estimate from reported shortages. A person decides what to send.</Note>
      {forecast.map((row) => (
        <div key={row.region}>
          <div className="spread"><strong>{row.region}</strong><Pill value={row.direction === "rising" ? "shortage" : "available"}>{row.direction} · next {row.estimate_shortages}</Pill></div>
          <div className="h-scroll">
            {row.history.map((point) => (
              <div key={point.month} className="small" style={{ minWidth: 64 }}>
                <div>{point.month.slice(5)}</div>
                <Bars value={point.shortages} max={Math.max(...row.history.map((item) => item.shortages), 1)} />
                <div>{point.shortages}</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function MinistryShelters({ data }) {
  return (
    <div className="stack">
      {data.shelters.map((shelter) => (
        <article className="card" key={shelter.id}>
          <div className="spread">
            <div>
              <h3>{shelter.name}</h3>
              <p className="small muted">{shelter.region} · {shelter.occupancy}/{shelter.capacity} · trend {shelter.history.trend}</p>
            </div>
            <div className="inline">
              <Pill value={shelter.accessible ? "available" : "shortage"}>{shelter.accessible ? `${shelter.accessible_spaces} accessible` : "Not accessible"}</Pill>
              <Pill value={shelter.has_backup_power ? "available" : "low"}>{shelter.has_backup_power ? `${shelter.electricity_hours}h power` : "No backup"}</Pill>
            </div>
          </div>
          <div className="inline" style={{ flexWrap: "wrap", marginTop: 8 }}>
            {shelter.inventory.filter((item) => item.status !== "available").map((item) => (
              <Pill key={item.item_name} value={item.status}>{item.item_name}</Pill>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function MinistryComplaints({ data, reload }) {
  return (
    <div className="stack">
      <div className="card">
        <h3>Regional complaint trends</h3>
        {data.regions.map((region) => (
          <div className="row" key={region.region}>
            <div>
              <strong>{region.region}</strong>
              <div className="small muted">{region.categories.map((item) => `${item.category} (${item.count})`).join(" · ")}</div>
            </div>
            <span>{region.open} open / {region.total}</span>
          </div>
        ))}
      </div>
      <div className="card">
        <h3>Repeated problems</h3>
        {data.patterns.map((pattern) => (
          <div className="row" key={`${pattern.shelter_id}-${pattern.category}`}>
            <div><strong>{pattern.category}</strong><div className="small muted">{pattern.shelter_name} · {pattern.count} reports · {pattern.open_count} open</div></div>
            {pattern.reopened && <Pill value="shortage">Reopened</Pill>}
          </div>
        ))}
      </div>
      <div className="card">
        {data.complaints.map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.category}</strong><div className="small">{item.description}</div><div className="small muted">{item.region} · {item.source}</div></div>
            <select value={item.status} onChange={async (e) => { await api(`/complaints/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) }); reload(); }}>
              {["received", "under_review", "being_addressed", "resolved"].map((status) => <option key={status}>{status}</option>)}
            </select>
          </div>
        ))}
      </div>
      <div className="card">
        <h3>Mental health flags by shelter</h3>
        <Note>Counts only. The reason stays with the shelter coordinator.</Note>
        {data.support_counts.map((row) => (
          <div className="row" key={row.shelter_id}><span>{row.shelter_name}</span><span>{row.open} open</span></div>
        ))}
      </div>
    </div>
  );
}

function MinistryNgos({ data, reload }) {
  const shelters = useData("/shelters");
  return (
    <div className="stack">
      {data.requests.map((item) => (
        <article className="card stack" key={item.id}>
          <div className="spread"><strong>{item.organization}</strong><Pill value={item.status}>{item.status}</Pill></div>
          <p>{item.description}</p>
          <p className="small muted">{item.shelter_name || "Not connected yet"} · {formatWhen(item.created_at)}</p>
          <div className="grid-2">
            <select defaultValue={item.shelter_id || ""} onChange={async (e) => { await api(`/ngo/requests/${item.id}`, { method: "PATCH", body: JSON.stringify({ shelter_id: Number(e.target.value) }) }); reload(); }}>
              <option value="">Connect a shelter</option>
              {(shelters.data?.shelters || []).map((shelter) => <option key={shelter.id} value={shelter.id}>{shelter.name}</option>)}
            </select>
            <select value={item.status} onChange={async (e) => { await api(`/ngo/requests/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) }); reload(); }}>
              {["submitted", "connected", "accepted", "delivered", "completed"].map((status) => <option key={status}>{status}</option>)}
            </select>
          </div>
        </article>
      ))}
    </div>
  );
}

function MinistryDonations({ data }) {
  return (
    <div className="stack">
      <div className="card">
        <h3>Donation activity</h3>
        <table>
          <thead><tr><th>Donor</th><th>Gift</th><th>Recipient</th><th>Status</th></tr></thead>
          <tbody>
            {data.donations.map((item) => (
              <tr key={item.id}>
                <td>{item.donor_name}</td>
                <td>{item.kind === "money" ? `${item.amount} ${item.currency}` : item.item_description}</td>
                <td>{item.shelter_name || item.cause_label}</td>
                <td><Pill value={item.status}>{item.status}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>Distribution gaps</h3>
        <Note>Compare gifts already recorded with shortages shelters still report.</Note>
        {data.distribution.map((row) => (
          <div className="row" key={row.shelter_id}>
            <div>
              <strong>{row.shelter_name}</strong>
              <div className="small muted">{row.region} · {row.money} USD recorded · {row.donation_count} gifts</div>
              <div className="small">{row.gaps.length ? `Still short: ${row.gaps.join(", ")}` : "Reported shortages have a matching gift description."}</div>
            </div>
            {row.underserved && <Pill value="shortage">Underserved</Pill>}
          </div>
        ))}
      </div>
    </div>
  );
}

function MinistryReports({ data, queue, reload }) {
  return (
    <div className="stack">
      <div className="card stack">
        <h3>High-risk counts</h3>
        <Note>{data.high_risk.note}</Note>
        <table>
          <thead><tr><th>Group</th><th>Elderly</th><th>Children</th><th>Pregnant</th><th>Disability</th><th>Devices</th></tr></thead>
          <tbody>
            {data.high_risk.regions.map((row) => (
              <tr key={row.label}><td>{row.label}</td><td>{row.elderly}</td><td>{row.children}</td><td>{row.pregnant}</td><td>{row.disability}</td><td>{row.device_dependent}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <Forecast forecast={data.forecast} />
      <div className="card">
        <h3>Shelter reporting history</h3>
        {data.history.map((row) => (
          <div className="row" key={row.shelter.id}>
            <div><strong>{row.shelter.name}</strong><div className="small muted">{row.trend}</div></div>
            <span className="small">{row.history.map((item) => item.shortages).join(" · ")}</span>
          </div>
        ))}
      </div>
      <div className="card stack">
        <h3>Outbreak reports</h3>
        <Note>This flags a cluster for public health staff. It does not declare an outbreak.</Note>
        {data.outbreaks.map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.suspected_illness}</strong><div className="small muted">{item.shelter_name} · {item.case_count} people</div></div>
            <select value={item.status} onChange={async (e) => { await api(`/outbreaks/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) }); window.location.reload(); }}>
              {["reported", "under_review", "investigating"].map((status) => <option key={status}>{status}</option>)}
            </select>
          </div>
        ))}
      </div>
      <div className="card stack">
        <h3>Verification queue</h3>
        {(queue?.users || []).map((person) => (
          <div className="row" key={person.id}>
            <div><strong>{person.full_name}</strong><div className="small muted">{person.requested_role || person.role} · {person.license_number} · {person.license_body}</div>
              {(person.credentials || []).map((document) => <button key={document.id} className="text-btn" type="button" onClick={async () => window.open(await fileUrl(`/credentials/${document.id}/file`), "_blank")}>{document.document_kind}: {document.filename}</button>)}
            </div>
            <div className="inline">
              <Pill value={person.verification_status}>{person.verification_status}</Pill>
              <VerificationReview person={person} reload={reload} />
            </div>
          </div>
        ))}
        {queue && queue.users.length === 0 && <p className="muted">No accounts are waiting.</p>}
      </div>
    </div>
  );
}

function VerificationReview({ person, reload }) {
  const [error, setError] = useState("");
  const [shelterId, setShelterId] = useState("");
  const shelters = useData(person.requested_role === "shelter_coordinator" ? "/shelters" : null);
  async function review(status) {
    try { await api(`/users/${person.id}/verification`, { method: "PATCH", body: JSON.stringify({ status, shelter_id: shelterId || null, note: "Manual review by authorized Ministry reviewer" }) }); await reload(); setError(""); }
    catch (err) { setError(err.message); }
  }
  return <div className="stack">
    {person.requested_role === "shelter_coordinator" && <select value={shelterId} onChange={event => setShelterId(event.target.value)}><option value="">Assign shelter</option>{(shelters.data?.shelters || []).map(shelter => <option key={shelter.id} value={shelter.id}>{shelter.name}</option>)}</select>}
    <div className="inline"><Button type="button" onClick={() => review("approved")}>Approve</Button><Button ghost type="button" onClick={() => review("rejected")}>Reject</Button></div>
    <ErrorText>{error}</ErrorText>
  </div>;
}

export function NgoPage() {
  const board = useData("/ngo/board");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  return (
    <div className="stack">
      <h2>NGO coordination</h2>
      <Note>Assistance requests go to the Ministry, separate from volunteer tasks. Transport requests can be accepted here.</Note>
      <ErrorText>{board.error || error}</ErrorText>
      <form className="card stack" onSubmit={async (e) => {
        e.preventDefault();
        try {
          await api("/ngo/requests", { method: "POST", body: JSON.stringify({ description, organization: "Cedar Health Relief" }) });
          setDescription("");
          board.reload();
        } catch (err) {
          setError(err.message);
        }
      }}>
        <Field label="Details"><textarea value={description} onChange={(e) => setDescription(e.target.value)} required /></Field>
        <Button type="submit">Submit</Button>
      </form>
      <div className="card">
        <h3>My requests</h3>
        {(board.data?.requests || []).map((item) => (
          <div className="row" key={item.id}>
            <div><strong>{item.shelter_name || "Waiting for a shelter"}</strong><div className="small">{item.description}</div></div>
            <div className="inline">
              <Pill value={item.status}>{item.status}</Pill>
              {item.status !== "submitted" && item.status !== "completed" && (
                <select value={item.status} onChange={async (e) => { await api(`/ngo/requests/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) }); board.reload(); }}>
                  {["accepted", "delivered", "completed"].map((status) => <option key={status}>{status}</option>)}
                </select>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="card">
        <h3>Transport requests</h3>
        {(board.data?.transports || []).map((item) => (
          <div className="row" key={item.id}>
            <div>
              <strong>{item.who}</strong>
              <div className="small muted">{item.destination} · {item.destination_type}{item.wheelchair_required ? " · wheelchair" : ""}</div>
            </div>
            <div className="inline">
              <Pill value={item.status}>{item.status}</Pill>
              {item.status === "requested" && <Button type="button" onClick={async () => { await api(`/transport/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: "accepted" }) }); board.reload(); }}>Accept</Button>}
              {item.status === "accepted" && <Button ghost type="button" onClick={async () => { await api(`/transport/${item.id}`, { method: "PATCH", body: JSON.stringify({ status: "completed" }) }); board.reload(); }}>Complete</Button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
