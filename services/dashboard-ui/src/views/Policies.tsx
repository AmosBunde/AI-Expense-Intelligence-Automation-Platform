import { useEffect, useState } from "react";
import { createPolicy, fetchPolicies, type Policy } from "../lib/api";

const CAN_EDIT = new Set(["admin", "finance"]);

export default function Policies(props: { role: string }) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [ruleType, setRuleType] = useState("amount_threshold");
  const [threshold, setThreshold] = useState("");
  const [note, setNote] = useState<string | null>(null);

  function load() {
    fetchPolicies()
      .then(setPolicies)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }

  useEffect(load, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNote(null);
    try {
      await createPolicy({
        name,
        description,
        rule_type: ruleType,
        threshold: threshold ? Number(threshold) : undefined,
      });
      setNote(`Policy "${name}" created`);
      setName("");
      setDescription("");
      setThreshold("");
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  const editor = CAN_EDIT.has(props.role);

  return (
    <>
      <header className="masthead">
        <div>
          <div className="kicker">Policies</div>
          <h1 className="h1">The rulebook</h1>
        </div>
        {editor ? (
          <button className="btn primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "New policy"}
          </button>
        ) : (
          <span className="pill">read-only · {props.role}</span>
        )}
      </header>

      {error ? <div className="error-note">{error}</div> : null}
      {note ? <div className="pill" style={{ marginBottom: 16, display: "inline-block" }}>{note}</div> : null}

      {showForm && editor ? (
        <form className="panel" style={{ marginBottom: 24 }} onSubmit={submit}>
          <div className="grid cols-2">
            <div className="field">
              <label htmlFor="pname">Name</label>
              <input id="pname" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="ptype">Rule type</label>
              <select id="ptype" value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
                <option value="amount_threshold">Amount threshold</option>
                <option value="per_head_limit">Per-head limit</option>
                <option value="duplicate_window">Duplicate window (days)</option>
                <option value="auto_approve">Auto-approval floor</option>
              </select>
            </div>
          </div>
          <div className="field">
            <label htmlFor="pdesc">Description</label>
            <textarea
              id="pdesc"
              required
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="field" style={{ maxWidth: 220 }}>
            <label htmlFor="pthresh">Threshold</label>
            <input
              id="pthresh"
              type="number"
              min="0"
              step="any"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          </div>
          <button className="btn primary">Create policy</button>
        </form>
      ) : null}

      {policies.length === 0 ? (
        <div className="empty">No policies configured yet.</div>
      ) : (
        <div className="grid cols-2">
          {policies.map((p) => (
            <article className="panel" key={p.policy_id}>
              <div className="panel-head">
                <span className="h2">{p.name}</span>
                <span className={`badge ${p.active ? "good" : "neutral"}`}>
                  {p.active ? "active" : "off"}
                </span>
              </div>
              <p style={{ fontSize: 14, marginBottom: 12 }}>{p.description}</p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <span className="pill figure">{p.rule_type}</span>
                {typeof p.threshold === "number" ? (
                  <span className="pill figure">threshold: {p.threshold}</span>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
