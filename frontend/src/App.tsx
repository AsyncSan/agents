import { Routes, Route } from "react-router-dom";
import { Header } from "./components/Header";
import { CatalogPage } from "./pages/CatalogPage";
import { AgentPage } from "./pages/AgentPage";
import { TasksPage } from "./pages/TasksPage";
import { PipelinesPage } from "./pages/PipelinesPage";
import { AuthPage } from "./pages/AuthPage";
import { ProvidersPage } from "./pages/ProvidersPage";
import { EnterprisePage } from "./pages/EnterprisePage";
import { FRIAPage } from "./pages/FRIAPage";
import { LiteracyPage } from "./pages/LiteracyPage";
import { AnnexIVPage } from "./pages/AnnexIVPage";
import { CompliancePage } from "./pages/CompliancePage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { PMMPage } from "./pages/PMMPage";
import { QMSPage } from "./pages/QMSPage";
import { DataGovernancePage } from "./pages/DataGovernancePage";
import { EUDBPage } from "./pages/EUDBPage";
import { DeclarationPage } from "./pages/DeclarationPage";
import { ModificationsPage } from "./pages/ModificationsPage";
import { OversightPage } from "./pages/OversightPage";
import { AuditSharesPage } from "./pages/AuditSharesPage";
import { AuditViewPage } from "./pages/AuditViewPage";
import { OrgProfilePage } from "./pages/OrgProfilePage";
import { SamplesPage } from "./pages/SamplesPage";
import { ComplianceSetupPage } from "./pages/ComplianceSetupPage";
import { AgentPublishPage } from "./pages/AgentPublishPage";
import { DocsLayout } from "./pages/docs/DocsLayout";
import { DocsIntro } from "./pages/docs/DocsIntro";
import { DocsQuickstart } from "./pages/docs/DocsQuickstart";
import { DocsAgents } from "./pages/docs/DocsAgents";
import { DocsTasks } from "./pages/docs/DocsTasks";
import { DocsPipelines } from "./pages/docs/DocsPipelines";
import { DocsSecrets } from "./pages/docs/DocsSecrets";
import { DocsTrust } from "./pages/docs/DocsTrust";
import { DocsAuth } from "./pages/docs/DocsAuth";
import { DocsWebhooks } from "./pages/docs/DocsWebhooks";
import { DocsScheduling } from "./pages/docs/DocsScheduling";
import { DocsCompliance } from "./pages/docs/DocsCompliance";
import { DocsCLI } from "./pages/docs/DocsCLI";
import { DocsAPI } from "./pages/docs/DocsAPI";
import { DocsAgentDev } from "./pages/docs/DocsAgentDev";

export default function App() {
  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <Header />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/providers" element={<ProvidersPage />} />
          <Route path="/enterprise" element={<EnterprisePage />} />
          <Route path="/fria" element={<FRIAPage />} />
          <Route path="/literacy" element={<LiteracyPage />} />
          <Route path="/literacy/:moduleId" element={<LiteracyPage />} />
          <Route path="/annex-iv" element={<AnnexIVPage />} />
          <Route path="/compliance" element={<CompliancePage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/pmm" element={<PMMPage />} />
          <Route path="/qms" element={<QMSPage />} />
          <Route path="/data-governance" element={<DataGovernancePage />} />
          <Route path="/eu-db" element={<EUDBPage />} />
          <Route path="/declaration" element={<DeclarationPage />} />
          <Route path="/modifications" element={<ModificationsPage />} />
          <Route path="/oversight" element={<OversightPage />} />
          <Route path="/audit-shares" element={<AuditSharesPage />} />
          <Route path="/audit/:token" element={<AuditViewPage />} />
          <Route path="/settings/org" element={<OrgProfilePage />} />
          <Route path="/sample-docs" element={<SamplesPage />} />
          <Route path="/compliance/setup" element={<ComplianceSetupPage />} />
          <Route path="/providers/new" element={<AgentPublishPage />} />
          <Route path="/agents/:id" element={<AgentPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/pipelines" element={<PipelinesPage />} />
          <Route path="/docs" element={<DocsLayout />}>
            <Route index element={<DocsIntro />} />
            <Route path="quickstart" element={<DocsQuickstart />} />
            <Route path="agents" element={<DocsAgents />} />
            <Route path="tasks" element={<DocsTasks />} />
            <Route path="pipelines" element={<DocsPipelines />} />
            <Route path="secrets" element={<DocsSecrets />} />
            <Route path="trust" element={<DocsTrust />} />
            <Route path="authentication" element={<DocsAuth />} />
            <Route path="webhooks" element={<DocsWebhooks />} />
            <Route path="scheduling" element={<DocsScheduling />} />
            <Route path="eu-ai-act" element={<DocsCompliance />} />
            <Route path="building-agents" element={<DocsAgentDev />} />
            <Route path="cli" element={<DocsCLI />} />
            <Route path="api" element={<DocsAPI />} />
          </Route>
          <Route path="/auth" element={<AuthPage />} />
        </Routes>
      </main>
    </div>
  );
}
