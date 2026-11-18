const { useState, useEffect, useCallback } = React;

const REFRESH_MS = 10000;

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch("/api" + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

function formatTime(sqliteTime) {
  if (!sqliteTime) return "never";
  // SQLite stores UTC as "YYYY-MM-DD HH:MM:SS"
  return new Date(sqliteTime.replace(" ", "T") + "Z").toLocaleString();
}

function Summary({ summary }) {
  const items = [
    { key: "total", label: "Devices" },
    { key: "up", label: "Up" },
    { key: "down", label: "Down" },
  ];
  return (
    <section className="cards" aria-label="Summary">
      {items.map((i) => (
        <div key={i.key} className={"card " + i.key}>
          <span className="count">{summary[i.key] ?? 0}</span>
          <span>{i.label}</span>
        </div>
      ))}
    </section>
  );
}

function AddDevice({ onAdded }) {
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("443");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("/devices", { method: "POST", body: { name, host, port: Number(port) } });
      setName(""); setHost("");
      onAdded();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <h2>Add a device</h2>
      <label>Name
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} placeholder="Office router" required />
      </label>
      <label>Host name or IPv4
        <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="example.com" required />
      </label>
      <label>Port
        <input type="number" min="1" max="65535" value={port} onChange={(e) => setPort(e.target.value)} required />
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? "Checking…" : "Start monitoring"}</button>
    </form>
  );
}

function DeviceCard({ device, onChanged, onSelect, selected }) {
  const status = device.status || "unknown";
  async function checkNow() {
    try { await api(`/devices/${device.id}/check`, { method: "POST" }); onChanged(); }
    catch (err) { alert(err.message); }
  }
  async function remove() {
    if (!confirm(`Stop monitoring ${device.name}?`)) return;
    try { await api(`/devices/${device.id}`, { method: "DELETE" }); onChanged(); }
    catch (err) { alert(err.message); }
  }
  return (
    <li className={"device " + status + (selected ? " selected" : "")}>
      <div className="device-head">
        <strong>{device.name}</strong>
        <span className={"pill " + status}>{status}</span>
      </div>
      <p className="muted">{device.host}:{device.port}</p>
      <p className="muted small">
        {device.status === "up" && `${device.response_ms} ms · `}
        {device.status === "down" && `${device.error} · `}
        checked {formatTime(device.checked_at)}
      </p>
      <div className="row">
        <button className="secondary" onClick={() => onSelect(device)}>History</button>
        <button className="secondary" onClick={checkNow}>Check now</button>
        <button className="danger" onClick={remove}>Remove</button>
      </div>
    </li>
  );
}

function History({ device }) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    let cancelled = false;
    api(`/devices/${device.id}/history?limit=20`).then((r) => { if (!cancelled) setRows(r); }).catch(() => {});
    return () => { cancelled = true; };
  }, [device.id, device.checked_at]);
  const max = Math.max(1, ...rows.map((r) => r.response_ms || 0));
  return (
    <section className="panel">
      <h2>History: {device.name}</h2>
      <p className="muted small">Newest first. Bar length shows response time.</p>
      <ul className="history">
        {rows.map((r, i) => (
          <li key={i}>
            <span className={"dot " + r.status} aria-label={r.status}></span>
            <span className="time">{formatTime(r.checked_at)}</span>
            <span className="bar-wrap">
              {r.status === "up"
                ? <span className="bar" style={{ width: Math.max(4, (r.response_ms / max) * 100) + "%" }}></span>
                : <span className="muted small">{r.error}</span>}
            </span>
            <span className="ms">{r.status === "up" ? r.response_ms + " ms" : ""}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Alerts({ alerts }) {
  return (
    <section className="panel">
      <h2>Recent alerts</h2>
      {alerts.length === 0 ? <p className="muted">No alerts yet.</p> : (
        <ul className="alerts">
          {alerts.map((a) => (
            <li key={a.id} className={a.kind}>
              <span>{a.message}</span>
              <span className="muted small">{formatTime(a.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function App() {
  const [devices, setDevices] = useState([]);
  const [summary, setSummary] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [d, s, a] = await Promise.all([api("/devices"), api("/summary"), api("/alerts")]);
      setDevices(d); setSummary(s); setAlerts(a); setError("");
    } catch (err) {
      setError("Cannot reach the server: " + err.message);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const selected = devices.find((d) => d.id === selectedId);

  return (
    <div className="layout">
      <header>
        <h1>Network Device Monitor</h1>
        <span className="muted small">Refreshes every {REFRESH_MS / 1000} seconds</span>
      </header>
      {error && <p className="error" role="alert">{error}</p>}
      <Summary summary={summary} />
      <div className="columns">
        <div className="stack">
          <AddDevice onAdded={load} />
          <Alerts alerts={alerts} />
        </div>
        <div className="stack">
          {devices.length === 0 ? <p className="panel muted">No devices yet. Add one to start monitoring.</p> : (
            <ul className="devices">
              {devices.map((d) => (
                <DeviceCard key={d.id} device={d} onChanged={load}
                            onSelect={(x) => setSelectedId(x.id)} selected={d.id === selectedId} />
              ))}
            </ul>
          )}
          {selected && <History device={selected} />}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
