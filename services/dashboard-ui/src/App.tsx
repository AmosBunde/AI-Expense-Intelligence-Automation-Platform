import { useEffect, useState } from "react";
import { demoActive, getSession, logout, onAuthChange, type Session } from "./lib/api";
import Login from "./views/Login";
import Overview from "./views/Overview";
import Expenses from "./views/Expenses";
import Upload from "./views/Upload";
import Chat from "./views/Chat";
import Policies from "./views/Policies";

const VIEWS = [
  { key: "overview", label: "Overview", num: "01" },
  { key: "expenses", label: "Expenses", num: "02" },
  { key: "upload", label: "Upload", num: "03" },
  { key: "chat", label: "AI Analyst", num: "04" },
  { key: "policies", label: "Policies", num: "05" },
] as const;

type ViewKey = (typeof VIEWS)[number]["key"];

function useTheme() {
  const [theme, setTheme] = useState<string>(() => localStorage.getItem("meridian.theme") ?? "auto");
  useEffect(() => {
    if (theme === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("meridian.theme", theme);
  }, [theme]);
  const cycle = () => setTheme(theme === "auto" ? "dark" : theme === "dark" ? "light" : "auto");
  return { theme, cycle };
}

export default function App() {
  const [session, setSession] = useState<Session | null>(getSession());
  const [view, setView] = useState<ViewKey>("overview");
  const { theme, cycle } = useTheme();

  useEffect(() => onAuthChange(() => setSession(getSession())), []);

  if (!session) return <Login />;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="wordmark">
          <span className="tick" aria-hidden />
          Meridian
        </div>
        <nav className="nav" aria-label="Primary">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              className={view === v.key ? "active" : ""}
              onClick={() => setView(v.key)}
              aria-current={view === v.key ? "page" : undefined}
            >
              <span className="num">{v.num}</span>
              {v.label}
            </button>
          ))}
        </nav>
        <div className="foot">
          {demoActive ? <span className="pill">demo data</span> : null}
          <span className="pill figure">{session.email}</span>
          <button className="theme-toggle" onClick={cycle}>
            theme: {theme}
          </button>
          <button className="btn" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main">
        {view === "overview" && <Overview />}
        {view === "expenses" && <Expenses role={session.role} />}
        {view === "upload" && <Upload />}
        {view === "chat" && <Chat />}
        {view === "policies" && <Policies role={session.role} />}
      </main>

      <nav className="tabbar" aria-label="Primary">
        {VIEWS.map((v) => (
          <button
            key={v.key}
            className={view === v.key ? "active" : ""}
            onClick={() => setView(v.key)}
            aria-current={view === v.key ? "page" : undefined}
          >
            <span aria-hidden>{v.num}</span>
            {v.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
