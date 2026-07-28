import { Link, NavLink } from "react-router-dom";
import { Bot, LayoutGrid, ListTodo, GitBranch, Book, User, LogOut, ShieldCheck } from "lucide-react";
import { useT } from "../i18n";

export function Header() {
  const apiKey = localStorage.getItem("af_api_key");
  const userName = localStorage.getItem("af_name");
  const { lang, setLang, t } = useT();

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
      isActive
        ? "bg-[#00d4ff]/10 text-[#00d4ff]"
        : "text-[#94a3b8] hover:text-[#f1f5f9]"
    }`;

  const handleLogout = () => {
    localStorage.removeItem("af_api_key");
    localStorage.removeItem("af_role");
    localStorage.removeItem("af_name");
    window.location.href = "/auth";
  };

  return (
    <header className="border-b border-white/[0.06] bg-[#111118]/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-[#f1f5f9] no-underline">
          <Bot size={20} className="text-[#00d4ff]" />
          <span className="font-semibold text-sm">
            agents<span className="text-[#94a3b8] font-normal">.renemurrell.de</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          <NavLink to="/" end className={linkClass}>
            <LayoutGrid size={14} />
            {t("nav.catalog")}
          </NavLink>
          <NavLink to="/tasks" className={linkClass}>
            <ListTodo size={14} />
            {t("nav.tasks")}
          </NavLink>
          <NavLink to="/pipelines" className={linkClass}>
            <GitBranch size={14} />
            {t("nav.pipelines")}
          </NavLink>
          {apiKey && (
            <NavLink to="/compliance" className={linkClass}>
              <ShieldCheck size={14} />
              {t("nav.compliance")}
            </NavLink>
          )}
          <NavLink to="/docs" className={linkClass}>
            <Book size={14} />
            {t("nav.docs")}
          </NavLink>
          <div className="ml-2 pl-2 border-l border-white/[0.06] flex items-center gap-0.5">
            <button
              onClick={() => setLang("en")}
              className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${
                lang === "en"
                  ? "bg-[#00d4ff]/10 text-[#00d4ff]"
                  : "text-[#64748b] hover:text-[#f1f5f9]"
              }`}
              title="English"
            >
              EN
            </button>
            <button
              onClick={() => setLang("de")}
              className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${
                lang === "de"
                  ? "bg-[#00d4ff]/10 text-[#00d4ff]"
                  : "text-[#64748b] hover:text-[#f1f5f9]"
              }`}
              title="Deutsch"
            >
              DE
            </button>
          </div>
          {apiKey ? (
            <div className="flex items-center gap-1 ml-1 pl-2 border-l border-white/[0.06]">
              <span className="text-xs text-[#64748b] flex items-center gap-1">
                <User size={12} />
                {userName || "Connected"}
              </span>
              <button
                onClick={handleLogout}
                className="p-1.5 rounded-lg text-[#64748b] hover:text-red-400 transition-colors"
                title="Disconnect"
              >
                <LogOut size={12} />
              </button>
            </div>
          ) : (
            <NavLink to="/auth" className={linkClass}>
              <User size={14} />
              {t("nav.login")}
            </NavLink>
          )}
        </nav>
      </div>
    </header>
  );
}
