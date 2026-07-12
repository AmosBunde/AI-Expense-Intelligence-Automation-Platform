/**
 * Gateway API client. All requests go through /api/v1 (nginx proxies to the
 * gateway in production; the Vite dev server proxies in development).
 *
 * When the backend is unreachable and demo mode is on (dev default, or
 * VITE_DEMO_MODE=true), read endpoints fall back to seeded sample data so the
 * dashboard is explorable standalone. `demoActive` flips to true the first
 * time a fallback is served, and the shell shows a "demo data" pill.
 */

export interface Expense {
  expense_id: string;
  merchant: string;
  category: string;
  amount: number;
  currency: string;
  status: string;
  submitted_by?: string;
  created_at: string;
  ai_summary?: string;
  fraud_score?: number;
  policy_verdict?: string;
}

export interface SpendSummary {
  total_spend: number;
  expense_count: number;
  flagged_count: number;
  auto_approved_rate: number;
  by_category: { category: string; amount: number }[];
  trend: { date: string; amount: number }[];
}

export interface Anomaly {
  anomaly_id: string;
  expense_id: string;
  severity: string;
  reason: string;
  merchant: string;
  amount: number;
  detected_at: string;
}

export interface Policy {
  policy_id: string;
  name: string;
  description: string;
  rule_type: string;
  threshold?: number;
  active: boolean;
}

export interface ChatReply {
  reply: string;
  sources?: string[];
}

export interface Session {
  token: string;
  email: string;
  role: string;
}

const DEMO_MODE =
  (import.meta.env.VITE_DEMO_MODE ?? (import.meta.env.DEV ? "true" : "false")) === "true";

let session: Session | null = null;
export let demoActive = false;

const listeners = new Set<() => void>();
export function onAuthChange(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function getSession(): Session | null {
  if (!session) {
    const raw = sessionStorage.getItem("meridian.session");
    if (raw) session = JSON.parse(raw) as Session;
  }
  return session;
}

function setSession(next: Session | null) {
  session = next;
  if (next) sessionStorage.setItem("meridian.session", JSON.stringify(next));
  else sessionStorage.removeItem("meridian.session");
  listeners.forEach((fn) => fn());
}

export function logout() {
  setSession(null);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const s = getSession();
  if (s) headers.set("Authorization", `Bearer ${s.token}`);
  const res = await fetch(`/api/v1${path}`, { ...init, headers });
  if (res.status === 401) {
    setSession(null);
    throw new Error("Session expired — please sign in again");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

/** Read endpoint with a demo-data fallback when the backend is down. */
async function readOrDemo<T>(path: string, demo: T): Promise<T> {
  try {
    return await request<T>(path);
  } catch (err) {
    if (err instanceof Error && err.message.startsWith("Session expired")) throw err;
    if (!DEMO_MODE) throw err;
    demoActive = true;
    return demo;
  }
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function login(email: string, password: string): Promise<Session> {
  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? "Login failed");
    }
    const data = (await res.json()) as { access_token: string };
    const role = email.startsWith("admin")
      ? "admin"
      : email.startsWith("finance")
        ? "finance"
        : "employee";
    const next = { token: data.access_token, email, role };
    setSession(next);
    return next;
  } catch (err) {
    // Network failure (backend down) in demo mode: local demo session
    if (DEMO_MODE && err instanceof TypeError) {
      demoActive = true;
      const next = { token: "demo-token", email, role: "finance" };
      setSession(next);
      return next;
    }
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Reads
// ---------------------------------------------------------------------------

export function fetchSpendSummary(period: string): Promise<SpendSummary> {
  return readOrDemo(`/analytics/spend-summary?period=${period}`, DEMO_SUMMARY);
}

export function fetchAnomalies(): Promise<Anomaly[]> {
  return readOrDemo<{ anomalies?: Anomaly[] } | Anomaly[]>("/analytics/anomalies", DEMO_ANOMALIES).then(
    (r) => (Array.isArray(r) ? r : (r.anomalies ?? [])),
  );
}

export function fetchExpenses(params: {
  page: number;
  status?: string;
  category?: string;
}): Promise<{ items: Expense[]; total: number }> {
  const q = new URLSearchParams({ page: String(params.page), page_size: "20" });
  if (params.status) q.set("status_filter", params.status);
  if (params.category) q.set("category", params.category);
  return readOrDemo<{ items?: Expense[]; expenses?: Expense[]; total?: number }>(
    `/expenses?${q}`,
    { items: DEMO_EXPENSES, total: DEMO_EXPENSES.length },
  ).then((r) => ({ items: r.items ?? r.expenses ?? [], total: r.total ?? 0 }));
}

export function fetchPolicies(): Promise<Policy[]> {
  return readOrDemo<{ policies?: Policy[] } | Policy[]>("/policies", DEMO_POLICIES).then((r) =>
    Array.isArray(r) ? r : (r.policies ?? []),
  );
}

// ---------------------------------------------------------------------------
// Writes (no demo fallback — mutations must be honest about failure)
// ---------------------------------------------------------------------------

export function approveExpense(expenseId: string): Promise<unknown> {
  return request(`/expenses/${expenseId}/approve`, { method: "POST" });
}

export function uploadReceipt(file: File): Promise<{ expense_id: string; message: string }> {
  const form = new FormData();
  form.append("file", file);
  return request("/expenses/upload", { method: "POST", body: form });
}

export async function sendChat(message: string): Promise<ChatReply> {
  try {
    return await request<ChatReply>("/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  } catch (err) {
    if (!DEMO_MODE) throw err;
    demoActive = true;
    return {
      reply:
        "Demo mode — the AI engine is not reachable. In a live deployment I answer from your expense data and company policy via RAG. Example: your Q3 travel spend is $48.2K, 12% over the same quarter last year, driven by airfare.",
      sources: ["travel-policy.md"],
    };
  }
}

export function createPolicy(policy: Omit<Policy, "policy_id" | "active">): Promise<unknown> {
  return request("/policies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(policy),
  });
}

// ---------------------------------------------------------------------------
// Demo data (explorable UI when the backend is down; labeled in the shell)
// ---------------------------------------------------------------------------

const DEMO_SUMMARY: SpendSummary = {
  total_spend: 128_460,
  expense_count: 342,
  flagged_count: 11,
  auto_approved_rate: 0.87,
  by_category: [
    { category: "Travel", amount: 48_200 },
    { category: "Software", amount: 31_900 },
    { category: "Meals", amount: 18_750 },
    { category: "Office", amount: 12_310 },
    { category: "Training", amount: 9_800 },
    { category: "Other", amount: 7_500 },
  ],
  trend: [
    { date: "2026-01-01", amount: 88_100 },
    { date: "2026-02-01", amount: 94_600 },
    { date: "2026-03-01", amount: 103_200 },
    { date: "2026-04-01", amount: 97_400 },
    { date: "2026-05-01", amount: 112_900 },
    { date: "2026-06-01", amount: 121_300 },
    { date: "2026-07-01", amount: 128_460 },
  ],
};

const DEMO_EXPENSES: Expense[] = [
  {
    expense_id: "exp-9013",
    merchant: "United Airlines",
    category: "Travel",
    amount: 1_842.4,
    currency: "USD",
    status: "flagged",
    submitted_by: "j.rivera",
    created_at: "2026-07-09T14:22:00Z",
    ai_summary:
      "Round-trip SFO→JFK booked 2 days before departure. 3.1× the median route fare for the org; traveler has two prior late bookings this quarter.",
    fraud_score: 0.71,
    policy_verdict: "Exceeds airfare cap ($1,200) — manager approval required",
  },
  {
    expense_id: "exp-9012",
    merchant: "AWS",
    category: "Software",
    amount: 4_310.0,
    currency: "USD",
    status: "approved",
    submitted_by: "infra-bot",
    created_at: "2026-07-08T03:00:00Z",
    ai_summary: "Monthly infrastructure invoice, within 4% of the 6-month average.",
    fraud_score: 0.02,
    policy_verdict: "Auto-approved — recurring vendor under contract",
  },
  {
    expense_id: "exp-9011",
    merchant: "Nobu Palo Alto",
    category: "Meals",
    amount: 386.9,
    currency: "USD",
    status: "pending",
    submitted_by: "k.osei",
    created_at: "2026-07-07T21:40:00Z",
    ai_summary: "Client dinner, 4 attendees listed. $96.73/head — just under the $100 cap.",
    fraud_score: 0.12,
    policy_verdict: "Within per-head meal limit — pending receipt itemization",
  },
  {
    expense_id: "exp-9010",
    merchant: "Uber",
    category: "Travel",
    amount: 64.2,
    currency: "USD",
    status: "approved",
    submitted_by: "j.rivera",
    created_at: "2026-07-07T09:12:00Z",
    ai_summary: "Airport transfer matching the flagged SFO→JFK itinerary.",
    fraud_score: 0.05,
    policy_verdict: "Auto-approved",
  },
  {
    expense_id: "exp-9009",
    merchant: "Staples",
    category: "Office",
    amount: 212.75,
    currency: "USD",
    status: "processing",
    submitted_by: "m.chen",
    created_at: "2026-07-06T16:05:00Z",
    ai_summary: "OCR extraction complete; awaiting policy evaluation.",
    fraud_score: 0.04,
  },
  {
    expense_id: "exp-9008",
    merchant: "Coursera",
    category: "Training",
    amount: 399.0,
    currency: "USD",
    status: "rejected",
    submitted_by: "t.nguyen",
    created_at: "2026-07-05T11:30:00Z",
    ai_summary: "Annual subscription — duplicate of exp-8714 submitted in March.",
    fraud_score: 0.44,
    policy_verdict: "Rejected — duplicate submission detected",
  },
];

const DEMO_ANOMALIES: Anomaly[] = [
  {
    anomaly_id: "anom-201",
    expense_id: "exp-9013",
    severity: "high",
    reason: "Airfare 3.1× route median; booked outside travel window",
    merchant: "United Airlines",
    amount: 1_842.4,
    detected_at: "2026-07-09T14:25:00Z",
  },
  {
    anomaly_id: "anom-200",
    expense_id: "exp-9008",
    severity: "medium",
    reason: "Duplicate submission — same vendor, amount, and card in March",
    merchant: "Coursera",
    amount: 399.0,
    detected_at: "2026-07-05T11:31:00Z",
  },
  {
    anomaly_id: "anom-199",
    expense_id: "exp-8992",
    severity: "medium",
    reason: "Weekend charge from a weekday-only vendor pattern",
    merchant: "WeWork",
    amount: 850.0,
    detected_at: "2026-07-04T08:15:00Z",
  },
];

const DEMO_POLICIES: Policy[] = [
  {
    policy_id: "pol-01",
    name: "Airfare cap",
    description: "Domestic airfare above $1,200 requires manager approval.",
    rule_type: "amount_threshold",
    threshold: 1200,
    active: true,
  },
  {
    policy_id: "pol-02",
    name: "Meal per-head limit",
    description: "Client meals capped at $100 per attendee with itemized receipt.",
    rule_type: "per_head_limit",
    threshold: 100,
    active: true,
  },
  {
    policy_id: "pol-03",
    name: "Duplicate detection",
    description: "Same vendor + amount within 90 days is auto-flagged for review.",
    rule_type: "duplicate_window",
    threshold: 90,
    active: true,
  },
  {
    policy_id: "pol-04",
    name: "Auto-approval floor",
    description: "Expenses under $75 with fraud score < 0.2 are approved automatically.",
    rule_type: "auto_approve",
    threshold: 75,
    active: true,
  },
];
