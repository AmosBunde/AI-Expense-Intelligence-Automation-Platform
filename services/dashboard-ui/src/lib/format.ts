export function formatMoney(amount: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: amount >= 1000 ? 0 : 2,
  }).format(amount);
}

export function formatCompact(amount: number): string {
  if (Math.abs(amount) >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (Math.abs(amount) >= 1_000) return `$${(amount / 1_000).toFixed(1)}K`;
  return `$${amount.toFixed(0)}`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

/** Map an expense/anomaly status onto one of the four badge tones. */
export function statusTone(status: string): "good" | "warn" | "serious" | "neutral" {
  const s = status.toLowerCase();
  if (["approved", "auto_approved", "reimbursed", "processed"].includes(s)) return "good";
  if (["pending", "needs_review", "in_review"].includes(s)) return "warn";
  if (["flagged", "rejected", "fraud_suspected", "high"].includes(s)) return "serious";
  return "neutral";
}
