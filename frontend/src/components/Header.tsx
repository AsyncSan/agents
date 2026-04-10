import { Link, NavLink } from "react-router-dom";
import { Bot, LayoutGrid, ListTodo } from "lucide-react";

export function Header() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
      isActive
        ? "bg-[#00d4ff]/10 text-[#00d4ff]"
        : "text-[#94a3b8] hover:text-[#f1f5f9]"
    }`;

  return (
    <header className="border-b border-white/[0.06] bg-[#111118]/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-[#f1f5f9] no-underline">
          <Bot size={20} className="text-[#00d4ff]" />
          <span className="font-semibold text-sm">agents<span className="text-[#94a3b8] font-normal">.renemurrell.de</span></span>
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
        </nav>
      </div>
    </header>
  );
}
