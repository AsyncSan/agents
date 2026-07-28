import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Book,
  Zap,
  Key,
  Cpu,
  FileText,
  GitBranch,
  Bell,
  Clock,
  Lock,
  Shield,
  Terminal,
  Code2,
  ChevronRight,
  Menu,
  X,
} from "lucide-react";
import { useT, type Language } from "../../i18n";

interface NavGroup {
  label: string;
  items: { path: string; label: string; icon: React.ReactNode }[];
}

function navForLang(lang: Language): NavGroup[] {
  const de = lang === "de";
  return [
    {
      label: de ? "Überblick" : "Overview",
      items: [
        { path: "/docs", label: de ? "Einführung" : "Introduction", icon: <Book size={14} /> },
        { path: "/docs/quickstart", label: de ? "Schnellstart" : "Quickstart", icon: <Zap size={14} /> },
      ],
    },
    {
      label: de ? "Kernkonzepte" : "Core Concepts",
      items: [
        { path: "/docs/agents", label: de ? "Agenten" : "Agents", icon: <Cpu size={14} /> },
        {
          path: "/docs/tasks",
          label: de ? "Aufgaben & Ausführung" : "Tasks & Execution",
          icon: <FileText size={14} />,
        },
        { path: "/docs/pipelines", label: "Pipelines", icon: <GitBranch size={14} /> },
        { path: "/docs/secrets", label: de ? "Geheimnisse" : "Secrets", icon: <Lock size={14} /> },
        {
          path: "/docs/trust",
          label: de ? "Vertrauensbewertung" : "Trust Scoring",
          icon: <Shield size={14} />,
        },
      ],
    },
    {
      label: de ? "Für Agent-Entwickler" : "Agent Developers",
      items: [
        {
          path: "/docs/building-agents",
          label: de ? "Agenten erstellen" : "Building an Agent",
          icon: <Code2 size={14} />,
        },
      ],
    },
    {
      label: de ? "Integrationen" : "Integrations",
      items: [
        {
          path: "/docs/authentication",
          label: de ? "Authentifizierung" : "Authentication",
          icon: <Key size={14} />,
        },
        { path: "/docs/webhooks", label: "Webhooks", icon: <Bell size={14} /> },
        {
          path: "/docs/scheduling",
          label: de ? "Zeitplanung" : "Scheduling",
          icon: <Clock size={14} />,
        },
      ],
    },
    {
      label: "Compliance",
      items: [
        { path: "/docs/eu-ai-act", label: "EU AI Act", icon: <Shield size={14} /> },
      ],
    },
    {
      label: de ? "Referenz" : "Reference",
      items: [
        { path: "/docs/cli", label: "CLI", icon: <Terminal size={14} /> },
        {
          path: "/docs/api",
          label: de ? "API-Referenz" : "API Reference",
          icon: <Code2 size={14} />,
        },
      ],
    },
  ];
}

const linkClass = (isActive: boolean) =>
  `flex items-center gap-2 px-3 py-1.5 rounded-lg text-[13px] transition-all duration-200 ${
    isActive
      ? "bg-[#00d4ff]/10 text-[#00d4ff] font-medium"
      : "text-[#64748b] hover:text-[#c8d6e0] hover:bg-white/[0.03]"
  }`;

function Sidebar({ onClose }: { onClose?: () => void }) {
  const location = useLocation();
  const { lang } = useT();
  const nav = navForLang(lang);

  return (
    <div className="space-y-5">
      {nav.map((group) => (
        <div key={group.label}>
          <span className="text-[10px] uppercase tracking-widest text-[#475569] font-semibold px-3 mb-1.5 block">
            {group.label}
          </span>
          <div className="space-y-0.5">
            {group.items.map((item) => {
              const isActive =
                item.path === "/docs"
                  ? location.pathname === "/docs"
                  : location.pathname.startsWith(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === "/docs"}
                  onClick={onClose}
                  className={() => linkClass(isActive)}
                >
                  {item.icon}
                  {item.label}
                  {isActive && (
                    <ChevronRight size={11} className="ml-auto text-[#00d4ff]/50" />
                  )}
                </NavLink>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export function DocsLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  // Scroll to top on page change
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="flex gap-0 min-h-[calc(100vh-5rem)] -mx-4 -mt-8">
      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-56 shrink-0 border-r border-white/[0.06] sticky top-14 self-start h-[calc(100vh-3.5rem)] overflow-y-auto py-6 px-2 scrollbar-thin">
        <Sidebar />
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        className={`fixed top-0 left-0 h-full w-64 bg-[#111118] border-r border-white/[0.06] z-50 transform transition-transform duration-300 lg:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } overflow-y-auto py-6 px-3`}
      >
        <div className="flex items-center justify-between mb-6 px-2">
          <span className="text-sm font-semibold text-[#f1f5f9] flex items-center gap-2">
            <Book size={16} className="text-[#00d4ff]" />
            Documentation
          </span>
          <button
            onClick={() => setMobileOpen(false)}
            className="p-1 rounded text-[#64748b] hover:text-[#f1f5f9]"
          >
            <X size={18} />
          </button>
        </div>
        <Sidebar onClose={() => setMobileOpen(false)} />
      </aside>

      {/* Content area */}
      <main className="flex-1 min-w-0">
        {/* Mobile nav toggle */}
        <div className="lg:hidden sticky top-14 z-30 bg-[#0a0a0f]/90 backdrop-blur-sm border-b border-white/[0.06] px-4 py-2">
          <button
            onClick={() => setMobileOpen(true)}
            className="flex items-center gap-2 text-sm text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
          >
            <Menu size={16} />
            <span>Navigation</span>
          </button>
        </div>

        <div className="max-w-3xl mx-auto px-6 lg:px-10 py-8 lg:py-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
