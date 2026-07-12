import { useRef, useState } from "react";
import { uploadReceipt } from "../lib/api";

const ACCEPT = ".jpg,.jpeg,.png,.webp,.heic,.pdf";
const MAX_MB = 10;

export default function Upload() {
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);
    setResult(null);
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File is ${(file.size / 1048576).toFixed(1)} MB — the limit is ${MAX_MB} MB.`);
      return;
    }
    setBusy(true);
    try {
      const res = await uploadReceipt(file);
      setResult(`Submitted as ${res.expense_id}. ${res.message}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="masthead">
        <div>
          <div className="kicker">Upload</div>
          <h1 className="h1">Submit a receipt</h1>
        </div>
      </header>

      {error ? <div className="error-note" role="alert">{error}</div> : null}
      <div aria-live="polite">
        {result ? (
          <div className="panel" style={{ marginBottom: 16 }}>
            <span className="badge good">submitted</span>
            <p style={{ marginTop: 8, fontSize: 14 }}>{result}</p>
          </div>
        ) : null}
      </div>

      <div
        className={`dropzone ${over ? "over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          const file = e.dataTransfer.files[0];
          if (file) void handleFile(file);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        aria-label="Upload a receipt"
      >
        <div className="big">{busy ? "Uploading…" : "Drop a receipt here"}</div>
        <p className="muted" style={{ marginTop: 8 }}>
          or click to browse — JPEG, PNG, WebP, HEIC, PDF · max {MAX_MB} MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
            e.target.value = "";
          }}
        />
      </div>

      <hr className="rule" />

      <div className="grid cols-2">
        <div className="panel">
          <div className="kicker" style={{ marginBottom: 8 }}>
            What happens next
          </div>
          <ol style={{ paddingLeft: 20, fontSize: 14, display: "grid", gap: 6 }}>
            <li>OCR + LLM extraction pulls merchant, amount, date, and line items.</li>
            <li>The AI engine scores the expense for anomalies and fraud signals.</li>
            <li>Policy rules run — under-limit, low-risk expenses auto-approve.</li>
            <li>Anything flagged lands in a manager's review queue with the reasoning attached.</li>
          </ol>
        </div>
        <div className="panel">
          <div className="kicker" style={{ marginBottom: 8 }}>
            Tips for clean extraction
          </div>
          <ul style={{ paddingLeft: 20, fontSize: 14, display: "grid", gap: 6 }}>
            <li>Capture the full receipt, including totals and the merchant header.</li>
            <li>PDFs from email invoices extract more reliably than photos.</li>
            <li>One receipt per file — batch CSVs belong to the finance batch flow.</li>
          </ul>
        </div>
      </div>
    </>
  );
}
