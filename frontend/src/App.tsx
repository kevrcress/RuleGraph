import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import RuleBrowser from "./pages/rules/RuleBrowser";
import RuleDetail from "./pages/rules/RuleDetail";
import NewRule from "./pages/rules/NewRule";
import DocumentLibrary from "./pages/documents/DocumentLibrary";
import DiffPage from "./pages/reports/Diff";
import Conflicts from "./pages/reports/Conflicts";
import Coverage from "./pages/reports/Coverage";
import Terminology from "./pages/reports/Terminology";
import ReviewQueue from "./pages/admin/ReviewQueue";
import TechLeadDashboard from "./pages/admin/TechLeadDashboard";
import AuditLog from "./pages/admin/AuditLog";
import Users from "./pages/admin/Users";
import IngestErrors from "./pages/admin/IngestErrors";
import Settings from "./pages/admin/Settings";
import UserSettings from "./pages/settings/UserSettings";
import Chat from "./pages/chat/Chat";
import WikiPromotion from "./pages/admin/WikiPromotion";
import GraphPage from "./pages/graph/GraphPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected — all authenticated users */}
          <Route
            path="/rules"
            element={
              <ProtectedRoute>
                <RuleBrowser />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rules/new"
            element={
              <ProtectedRoute>
                <NewRule />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rules/:id"
            element={
              <ProtectedRoute>
                <RuleDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/documents"
            element={
              <ProtectedRoute>
                <DocumentLibrary />
              </ProtectedRoute>
            }
          />
          <Route
            path="/diff"
            element={
              <ProtectedRoute>
                <DiffPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/conflicts"
            element={
              <ProtectedRoute>
                <Conflicts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/coverage"
            element={
              <ProtectedRoute>
                <Coverage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/terminology"
            element={
              <ProtectedRoute>
                <Terminology />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <UserSettings />
              </ProtectedRoute>
            }
          />

          {/* BA + Admin */}
          <Route
            path="/admin/review-queue"
            element={
              <ProtectedRoute roles={["business_admin", "admin"]}>
                <ReviewQueue />
              </ProtectedRoute>
            }
          />

          {/* TL + Admin */}
          <Route
            path="/admin/tech-lead-dashboard"
            element={
              <ProtectedRoute roles={["tech_lead", "admin"]}>
                <TechLeadDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/wiki-promotion"
            element={
              <ProtectedRoute roles={["tech_lead", "admin"]}>
                <WikiPromotion />
              </ProtectedRoute>
            }
          />

          {/* Graph — TL + Admin */}
          <Route
            path="/graph"
            element={
              <ProtectedRoute roles={["tech_lead", "admin"]}>
                <GraphPage />
              </ProtectedRoute>
            }
          />

          {/* Admin only */}
          <Route
            path="/admin/audit-log"
            element={
              <ProtectedRoute roles={["admin"]}>
                <AuditLog />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute roles={["admin"]}>
                <Users />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/ingest-errors"
            element={
              <ProtectedRoute roles={["admin"]}>
                <IngestErrors />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/settings"
            element={
              <ProtectedRoute roles={["admin"]}>
                <Settings />
              </ProtectedRoute>
            }
          />

          {/* Chat */}
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <Chat />
              </ProtectedRoute>
            }
          />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/rules" replace />} />
          <Route path="*" element={<Navigate to="/rules" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
