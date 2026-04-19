import { useEffect, useState } from "react";

type Slot = {
  slot_id: string;
  occupied: boolean;
};

type Summary = {
  total_slots: number;
  occupied_slots: number;
  available_slots: number;
  updated_at: string;
};

type LogEntry = {
  camera_id: string;
  timestamp: string;
  updated_slots: number;
};

type WsPayload = {
  event: "snapshot" | "occupancy_updated";
  data: {
    summary: Summary;
    slots: Slot[];
    logs: LogEntry[];
  };
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
const wsUrl = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws";

const initialSummary: Summary = {
  total_slots: 0,
  occupied_slots: 0,
  available_slots: 0,
  updated_at: "",
};

function App() {
  const [summary, setSummary] = useState<Summary>(initialSummary);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const isAdminView = window.location.pathname.startsWith("/admin");

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        setError("");

        const [summaryResponse, slotsResponse, logsResponse] = await Promise.all([
          fetch(`${apiBaseUrl}/summary`),
          fetch(`${apiBaseUrl}/slots`),
          fetch(`${apiBaseUrl}/logs`),
        ]);

        if (!summaryResponse.ok || !slotsResponse.ok || !logsResponse.ok) {
          throw new Error("Cannot load dashboard data from backend.");
        }

        const summaryData = (await summaryResponse.json()) as Summary;
        const slotsData = (await slotsResponse.json()) as { slots: Slot[] };
        const logsData = (await logsResponse.json()) as { logs: LogEntry[] };

        setSummary(summaryData);
        setSlots(slotsData.slots);
        setLogs(logsData.logs);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    void loadInitialData();
  }, []);

  useEffect(() => {
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setConnectionStatus("connected");
    };

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as WsPayload;
      setError("");
      setSummary(payload.data.summary);
      setSlots(payload.data.slots);
      setLogs(payload.data.logs);
    };

    socket.onclose = () => {
      setConnectionStatus("disconnected");
    };

    socket.onerror = () => {
      setConnectionStatus("error");
    };

    return () => {
      socket.close();
    };
  }, []);

  return (
    <div className="page-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Parking Space Detection System</p>
          <h1>{isAdminView ? "Admin Dashboard" : "User Dashboard"}</h1>
          <p className="subtitle">
            Realtime parking slot monitoring powered by FastAPI, WebSocket, and React.
          </p>
        </div>
        <div className={`status-pill status-${connectionStatus}`}>{connectionStatus}</div>
      </header>

      <section className="summary-grid">
        <StatCard label="Total Slots" value={summary.total_slots} />
        <StatCard label="Occupied" value={summary.occupied_slots} />
        <StatCard label="Available" value={summary.available_slots} />
        <StatCard
          label="Last Update"
          value={summary.updated_at ? new Date(summary.updated_at).toLocaleTimeString() : "--"}
        />
      </section>

      <section className="content-grid">
        <article className="panel">
          <div className="panel-header">
            <h2>Parking Map</h2>
            <p>{isAdminView ? "Full slot monitoring view" : "Current slot availability"}</p>
          </div>
          {loading ? (
            <div className="empty-state">Loading parking slots...</div>
          ) : error ? (
            <div className="error-state">{error}</div>
          ) : slots.length === 0 ? (
            <div className="empty-state">No slot data available.</div>
          ) : (
            <div className="slot-grid">
              {slots.map((slot) => (
                <div
                  key={slot.slot_id}
                  className={`slot-card ${slot.occupied ? "slot-occupied" : "slot-vacant"}`}
                >
                  <span className="slot-name">{slot.slot_id}</span>
                  <span className="slot-state">{slot.occupied ? "Occupied" : "Vacant"}</span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>{isAdminView ? "Recent Logs" : "System Snapshot"}</h2>
            <p>{isAdminView ? "Latest AI updates pushed to backend" : "Monitoring status and endpoints"}</p>
          </div>

          {isAdminView ? (
            <div className="log-list">
              {loading ? (
                <div className="empty-state">Loading monitoring logs...</div>
              ) : error ? (
                <div className="error-state">{error}</div>
              ) : logs.length === 0 ? (
                <div className="empty-state">No updates received yet.</div>
              ) : (
                logs
                  .slice()
                  .reverse()
                  .map((log, index) => (
                    <div key={`${log.timestamp}-${index}`} className="log-item">
                      <strong>{log.camera_id}</strong>
                      <span>{new Date(log.timestamp).toLocaleString()}</span>
                      <span>{log.updated_slots} slots updated</span>
                    </div>
                  ))
              )}
            </div>
          ) : (
            <div className="info-list">
              <InfoRow label="API" value={apiBaseUrl} />
              <InfoRow label="WebSocket" value={wsUrl} />
              <InfoRow label="Admin View" value="/admin" />
            </div>
          )}
        </article>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <code>{value}</code>
    </div>
  );
}

export default App;
