import { useEffect, useState } from "react";
import { approveExpense, fetchExpenses, type Expense } from "../lib/api";
import { formatDate, formatMoney, statusTone } from "../lib/format";

const STATUSES = ["", "processing", "pending", "approved", "flagged", "rejected"];
const CAN_APPROVE = new Set(["manager", "admin", "finance"]);

export default function Expenses(props: { role: string }) {
  const [items, setItems] = useState<Expense[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<Expense | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  function load() {
    setError(null);
    fetchExpenses({ page, status: status || undefined })
      .then((r) => {
        setItems(r.items);
        setTotal(r.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }

  useEffect(load, [page, status]);

  async function approve(exp: Expense) {
    setNote(null);
    try {
      await approveExpense(exp.expense_id);
      setNote(`Approved ${exp.expense_id}`);
      setSelected(null);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    }
  }

  return (
    <>
      <header className="masthead">
        <div>
          <div className="kicker">Expenses</div>
          <h1 className="h1">Ledger</h1>
        </div>
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="status">Status</label>
          <select
            id="status"
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value);
            }}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s === "" ? "All" : s}
              </option>
            ))}
          </select>
        </div>
      </header>

      {error ? <div className="error-note">{error}</div> : null}
      {note ? <div className="pill" style={{ marginBottom: 16, display: "inline-block" }}>{note}</div> : null}

      {items.length === 0 ? (
        <div className="empty">No expenses match this filter.</div>
      ) : (
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th>Merchant</th>
                <th>Category</th>
                <th style={{ textAlign: "right" }}>Amount</th>
                <th>Status</th>
                <th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {items.map((exp) => (
                <tr key={exp.expense_id} className="rowbtn" onClick={() => setSelected(exp)}>
                  <td>{exp.merchant}</td>
                  <td className="muted">{exp.category}</td>
                  <td className="num">{formatMoney(exp.amount, exp.currency)}</td>
                  <td>
                    <span className={`badge ${statusTone(exp.status)}`}>{exp.status}</span>
                  </td>
                  <td className="num muted">{formatDate(exp.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 16, alignItems: "center" }}>
        <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          ← Prev
        </button>
        <span className="pill figure">page {page}</span>
        <button className="btn" disabled={items.length < 20 && total <= page * 20} onClick={() => setPage(page + 1)}>
          Next →
        </button>
      </div>

      {selected ? (
        <>
          <div className="drawer-scrim" onClick={() => setSelected(null)} />
          <aside className="drawer" aria-label="Expense detail">
            <div className="panel-head">
              <span className="kicker">{selected.expense_id}</span>
              <button className="theme-toggle" onClick={() => setSelected(null)}>
                close
              </button>
            </div>
            <h2 className="h2" style={{ marginBottom: 4 }}>
              {selected.merchant}
            </h2>
            <div className="figure" style={{ fontSize: 30, fontWeight: 600, marginBottom: 16 }}>
              {formatMoney(selected.amount, selected.currency)}
            </div>
            <dl className="kv">
              <dt>Status</dt>
              <dd>
                <span className={`badge ${statusTone(selected.status)}`}>{selected.status}</span>
              </dd>
              <dt>Category</dt>
              <dd>{selected.category}</dd>
              <dt>Submitted by</dt>
              <dd className="figure">{selected.submitted_by ?? "—"}</dd>
              <dt>Date</dt>
              <dd className="figure">{formatDate(selected.created_at)}</dd>
              {typeof selected.fraud_score === "number" ? (
                <>
                  <dt>Fraud score</dt>
                  <dd className="figure">{selected.fraud_score.toFixed(2)} / 1.00</dd>
                </>
              ) : null}
            </dl>

            {selected.ai_summary ? (
              <>
                <hr className="rule" />
                <div className="kicker" style={{ marginBottom: 8 }}>
                  AI analysis
                </div>
                <p style={{ fontSize: 14 }}>{selected.ai_summary}</p>
              </>
            ) : null}

            {selected.policy_verdict ? (
              <>
                <hr className="rule" />
                <div className="kicker" style={{ marginBottom: 8 }}>
                  Policy verdict
                </div>
                <p style={{ fontSize: 14 }}>{selected.policy_verdict}</p>
              </>
            ) : null}

            {CAN_APPROVE.has(props.role) && ["flagged", "pending"].includes(selected.status) ? (
              <>
                <hr className="rule" />
                <button className="btn primary" style={{ width: "100%" }} onClick={() => approve(selected)}>
                  Approve expense
                </button>
              </>
            ) : null}
          </aside>
        </>
      ) : null}
    </>
  );
}
