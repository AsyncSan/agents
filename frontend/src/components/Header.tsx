import { Link, NavLink } from "react-router-dom";
import { Bot, LayoutGrid, ListTodo, GitBranch, User, LogOut } from "lucide-react";

export function Header() {
  const apiKey = localStorage.getItem("af_api_key");
  const userName = localStorage.getItem("af_name");

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
            Catalog
          </NavLink>
          <NavLink to="/tasks" className={linkClass}>
            <ListTodo size={14} />
            Tasks
          </NavLink>
          <NavLink to="/pipelines" className={linkClass}>
            <GitBranch size={14} />
            Pipelines
          </NavLink>
          {apiKey ? (
            <div className="flex items-center gap-1 ml-2 pl-2 border-l border-white/[0.06]">
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
              Login
            </NavLink>
          )}
        </nav>
      </div>
    </header>
  );
}
