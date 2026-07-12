import { useEffect, useRef, useState } from "react";
import { sendChat } from "../lib/api";

interface Message {
  who: "user" | "ai";
  text: string;
  sources?: string[];
}

const SUGGESTIONS = [
  "What did we spend on travel this quarter?",
  "Which expenses look risky right now?",
  "Summarize our meal policy",
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      who: "ai",
      text: "I'm the Meridian analyst. Ask me about spend patterns, specific expenses, or what company policy says — my answers are grounded in your data and policy documents.",
    },
  ]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setMessages((m) => [...m, { who: "user", text }]);
    setDraft("");
    setBusy(true);
    try {
      const res = await sendChat(text);
      setMessages((m) => [...m, { who: "ai", text: res.reply, sources: res.sources }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { who: "ai", text: err instanceof Error ? err.message : "Something went wrong." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="masthead">
        <div>
          <div className="kicker">AI Analyst</div>
          <h1 className="h1">Ask the ledger</h1>
        </div>
      </header>

      <div className="chat">
        <div className="scroll" ref={scrollRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.who}`}>
              <span className="who">{m.who === "user" ? "You" : "Analyst"}</span>
              {m.text}
              {m.sources?.length ? (
                <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {m.sources.map((s) => (
                    <span key={s} className="pill">
                      {s}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
          {busy ? (
            <div className="msg ai">
              <span className="who">Analyst</span>
              <span className="muted">Thinking…</span>
            </div>
          ) : null}
        </div>
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send(draft);
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about spend, expenses, or policy…"
            aria-label="Message the AI analyst"
          />
          <button className="btn primary" disabled={busy || !draft.trim()}>
            Send
          </button>
        </form>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
        {SUGGESTIONS.map((s) => (
          <button key={s} className="theme-toggle" onClick={() => void send(s)} disabled={busy}>
            {s}
          </button>
        ))}
      </div>
    </>
  );
}
