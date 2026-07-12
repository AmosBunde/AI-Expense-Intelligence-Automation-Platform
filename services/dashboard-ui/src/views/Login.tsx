import { useState } from "react";
import { login } from "../lib/api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <section className="poster">
        <div className="wordmark">
          <span className="tick" aria-hidden />
          Meridian
        </div>
        <div>
          <div className="kicker">Expense Intelligence Platform</div>
          <h1 className="giant">
            Every receipt,
            <br />
            <em>read</em>, priced,
            <br />
            and policed.
          </h1>
          <div className="meta-row">
            <span className="pill figure">OCR + LLM extraction</span>
            <span className="pill figure">RAG policy grounding</span>
            <span className="pill figure">Fraud scoring</span>
          </div>
        </div>
        <p className="muted" style={{ maxWidth: 420, fontSize: 14 }}>
          Receipts and invoices are extracted by an LLM pipeline, checked against
          your company policy via retrieval, scored for anomalies, and routed for
          approval — before anyone opens a spreadsheet.
        </p>
      </section>

      <section className="form-col">
        <h2 className="h2" style={{ marginBottom: 24 }}>
          Sign in
        </h2>
        {error ? <div className="error-note">{error}</div> : null}
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="email">Work email</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <button className="btn primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="muted" style={{ fontSize: 13, marginTop: 16 }}>
          Local dev runs in demo mode: any credentials work and sample data loads
          if the backend is offline. Production requires configured accounts.
        </p>
      </section>
    </div>
  );
}
