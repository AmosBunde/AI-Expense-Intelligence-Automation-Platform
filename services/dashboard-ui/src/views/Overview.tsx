import { useEffect, useState } from "react";
import { fetchAnomalies, fetchSpendSummary, type Anomaly, type SpendSummary } from "../lib/api";
import { CategoryBars, StatTile, TrendLine } from "../components/charts";
import { formatDate, formatMoney, formatPercent, statusTone } from "../lib/format";

export default function Overview() {
  const [period, setPeriod] = useState("month");
  const [summary, setSummary] = useState<SpendSummary | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setError(null);
    Promise.all([fetchSpendSummary(period), fetchAnomalies()])
      .then(([s, a]) => {
        if (!live) return;
        setSummary(s);
        setAnomalies(a);
      })
      .catch((err) => live && setError(err instanceof Error ? err.message : "Failed to load"));
    return () => {
      live = false;
    };
  }, [period]);

  return (
    <>
      <header className="masthead">
        <div>
          <div className="kicker">Overview</div>
          <h1 className="h1">Spend intelligence</h1>
        </div>
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="period">Period</label>
          <select id="period" value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="week">Week</option>
            <option value="month">Month</option>
            <option value="quarter">Quarter</option>
            <option value="year">Year</option>
          </select>
        </div>
      </header>

      {error ? <div className="error-note">{error}</div> : null}

      {summary ? (
        <>
          <div className="grid cols-4">
            <StatTile label="Total spend" value={formatMoney(summary.total_spend)} delta={`this ${period}`} />
            <StatTile label="Expenses" value={String(summary.expense_count)} delta="submitted" />
            <StatTile label="Flagged" value={String(summary.flagged_count)} delta="awaiting review" />
            <StatTile
              label="Auto-approved"
              value={formatPercent(summary.auto_approved_rate)}
              delta="no human touch"
            />
          </div>

          <hr className="rule" />

          <div className="grid cols-2">
            <section className="panel">
              <div className="panel-head">
                <span className="kicker">Trend</span>
                <span className="pill figure">monthly</span>
              </div>
              <TrendLine data={summary.trend} />
            </section>
            <section className="panel">
              <div className="panel-head">
                <span className="kicker">By category</span>
                <span className="pill figure">{summary.by_category.length} categories</span>
              </div>
              <CategoryBars data={summary.by_category} />
            </section>
          </div>

          <hr className="rule" />

          <section>
            <div className="panel-head">
              <span className="kicker">Anomalies & fraud signals</span>
            </div>
            {anomalies.length === 0 ? (
              <div className="empty">No anomalies detected in this period.</div>
            ) : (
              <div className="table-scroll">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>Reason</th>
                      <th>Merchant</th>
                      <th style={{ textAlign: "right" }}>Amount</th>
                      <th>Detected</th>
                    </tr>
                  </thead>
                  <tbody>
                    {anomalies.map((a) => (
                      <tr key={a.anomaly_id}>
                        <td>
                          <span className={`badge ${statusTone(a.severity)}`}>{a.severity}</span>
                        </td>
                        <td>{a.reason}</td>
                        <td>{a.merchant}</td>
                        <td className="num">{formatMoney(a.amount)}</td>
                        <td className="num muted">{formatDate(a.detected_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : !error ? (
        <div className="empty">Loading…</div>
      ) : null}
    </>
  );
}
