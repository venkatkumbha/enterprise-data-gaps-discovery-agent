import { useEffect, useState } from "react";
import { fetchSystems, runDiscovery } from "./api.js";

const AGENT_LABELS = {
  schema_explorer: "Schema explorer",
  profiler: "Profiler",
  reconciliation: "Reconciliation",
  reporter: "Reporter",
};

function App() {
  const [systems, setSystems] = useState([]);
  const [systemsError, setSystemsError] = useState("");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState("");
  const [result, setResult] = useState(null);
  const [openId, setOpenId] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchSystems()
      .then((payload) => {
        if (!cancelled) setSystems(payload.systems || []);
      })
      .catch((error) => {
        if (!cancelled) setSystemsError(error.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onRun() {
    setRunning(true);
    setRunError("");
    try {
      const payload = await runDiscovery();
      setResult(payload);
      setOpenId(payload.findings?.[0]?.id || "");
    } catch (error) {
      setRunError(error.message);
    } finally {
      setRunning(false);
    }
  }

  const counts = result?.report?.counts;

  return (
    <div className="page">
      <header className="top">
        <div>
          <p className="eyebrow">Telco BSS/OSS · read-only tools · LangGraph</p>
          <h1>Enterprise Data Gaps Discovery Agent</h1>
          <p className="lede">
            Four specialists compare synthetic BSS and OSS systems: Customer Management, Catalog, Orders, Billing, Service Inventory, Resources, Assurance, and Analytics. Every finding keeps the query and the rows that support it.
          </p>
        </div>
        <button className="run" type="button" onClick={onRun} disabled={running}>
          {running ? "Agents running…" : "Run discovery"}
        </button>
      </header>

      <section className="systems" aria-label="Systems">
        {systemsError ? (
          <p className="banner">{systemsError}. Start the Python API on port 8000, then refresh.</p>
        ) : systems.length === 0 ? (
          <p className="banner">No SQLite systems yet. Run scripts/bootstrap.ps1, then refresh.</p>
        ) : (
          systems.map((system) => (
            <article key={system.name} className="system-card">
              <h2>{system.name.replaceAll("_", " ")}</h2>
              <p>{(system.tables || []).join(" · ")}</p>
            </article>
          ))
        )}
      </section>

      {runError ? <p className="banner danger">{runError}</p> : null}

      {result ? (
        <main className="results">
          <section className="summary" aria-label="Summary">
            <p className="narrative">{result.report?.summary}</p>
            <dl className="counts">
              <div>
                <dt>High</dt>
                <dd>{counts?.high ?? 0}</dd>
              </div>
              <div>
                <dt>Medium</dt>
                <dd>{counts?.medium ?? 0}</dd>
              </div>
              <div>
                <dt>Low</dt>
                <dd>{counts?.low ?? 0}</dd>
              </div>
            </dl>
            <p className="source">Narrative: {result.report?.narrative_source}</p>
          </section>

          <section className="trace" aria-label="Agent trace">
            <h2>Agent trace</h2>
            <ol>
              {(result.trace || []).map((step, index) => (
                <li key={`${step.agent}-${index}`}>
                  <strong>{AGENT_LABELS[step.agent] || step.agent}</strong>
                  <span>{step.summary}</span>
                  <em>
                    {step.finding_count} findings · {step.duration_ms} ms
                  </em>
                </li>
              ))}
            </ol>
          </section>

          <section className="findings" aria-label="Findings">
            <h2>Findings</h2>
            {(result.findings || []).map((finding) => {
              const open = openId === finding.id;
              return (
                <article key={finding.id} className={`finding ${finding.severity}`}>
                  <button type="button" onClick={() => setOpenId(open ? "" : finding.id)}>
                    <span className="pill">{finding.severity}</span>
                    <span className="finding-title">{finding.title}</span>
                    <span className="agent">{AGENT_LABELS[finding.agent] || finding.agent}</span>
                  </button>
                  {open ? (
                    <div className="detail">
                      <p>{finding.summary}</p>
                      {(finding.evidence || []).map((item, index) => (
                        <div key={`${finding.id}-${index}`} className="evidence">
                          <p>
                            <code>{item.system || "n/a"}</code> · {item.tool}
                          </p>
                          <pre>{item.detail}</pre>
                          <EvidenceTable rows={item.rows || []} />
                        </div>
                      ))}
                    </div>
                  ) : null}
                </article>
              );
            })}
          </section>
        </main>
      ) : (
        <p className="waiting">Run discovery to see the supervisor call each specialist and come back with evidence.</p>
      )}
    </div>
  );
}

function EvidenceTable({ rows }) {
  if (!rows.length) {
    return <p className="empty-rows">No rows returned.</p>;
  }
  const columns = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default App;
