import { Routes, Route } from "react-router-dom";
import { Header } from "./components/Header";
import { CatalogPage } from "./pages/CatalogPage";
import { AgentPage } from "./pages/AgentPage";
import { TasksPage } from "./pages/TasksPage";

export default function App() {
  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <Header />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/agents/:id" element={<AgentPage />} />
          <Route path="/tasks" element={<TasksPage />} />
        </Routes>
      </main>
    </div>
  );
}
