import { useTLDashboard } from "../../api/admin";
import Layout from "../../components/Layout";
import apiClient from "../../api/client";
import { useState } from "react";

export default function TechLeadDashboard() {
  const { data, isLoading, refetch } = useTLDashboard();
  const [workitem, setWorkitem] = useState<{ ruleId: string; title: string } | null>(null);
  const [wiTitle, setWiTitle] = useState("");
  const [wiBody, setWiBody] = useState("");

  const handleCodeChange = async () => {
    if (!workitem) return;
    try {
      await apiClient.put(`/admin/tech-lead-dashboard/${workitem.ruleId}/code-change`, {
        workitem_title: wiTitle || workitem.title,
        workitem_body: wiBody,
        repo: "",
        project: "",
      });
      setWorkitem(null);
      refetch();
    } catch {
      // fail silently
    }
  };

  const handleNoCode = async (ruleId: string) => {
    try {
      await apiClient.put(`/admin/tech-lead-dashboard/${ruleId}/no-code`);
      refetch();
    } catch {
      // fail silently
    }
  };

  return (
    <Layout>
      <div data-testid="tl-dashboard" className="max-w-4xl">
        <h1 className="text-xl font-serif text-bone-0 mb-4">Tech Lead Dashboard</h1>
        <p className="text-sm text-bone-3 mb-4">Rules approved and awaiting implementation.</p>
        {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}

        {data?.items?.length === 0 && !isLoading && (
          <p className="text-bone-3 text-sm">No approved rules awaiting action.</p>
        )}

        <ul className="space-y-3">
          {data?.items?.map((rule: { id: string; title: string; definition?: string; status: string; approved_by?: string }) => (
            <li key={rule.id} className="bg-ink-2 border border-bone-4 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-bone-0 font-medium">{rule.title}</h3>
                  {rule.definition && (
                    <p className="text-sm text-bone-2 mt-1 line-clamp-2">{rule.definition}</p>
                  )}
                </div>
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => {
                      setWorkitem({ ruleId: rule.id, title: rule.title });
                      setWiTitle(rule.title);
                      setWiBody(rule.definition || "");
                    }}
                    className="px-3 py-1 text-xs bg-blue-800 text-blue-200 rounded hover:bg-blue-700"
                  >
                    Create Work Item
                  </button>
                  <button
                    onClick={() => handleNoCode(rule.id)}
                    className="px-3 py-1 text-xs bg-ink-3 text-bone-2 rounded hover:bg-ink-4"
                  >
                    No Code Change
                  </button>
                </div>
              </div>

              {workitem?.ruleId === rule.id && (
                <div className="mt-3 space-y-2">
                  <input
                    value={wiTitle}
                    onChange={(e) => setWiTitle(e.target.value)}
                    placeholder="Work item title"
                    className="w-full bg-ink-3 border border-bone-4 rounded px-2 py-1 text-sm text-bone-0"
                  />
                  <textarea
                    value={wiBody}
                    onChange={(e) => setWiBody(e.target.value)}
                    rows={3}
                    placeholder="Description"
                    className="w-full bg-ink-3 border border-bone-4 rounded px-2 py-1 text-sm text-bone-0 resize-y"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleCodeChange}
                      className="px-3 py-1 text-xs bg-brass-0 text-ink-0 rounded"
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => setWorkitem(null)}
                      className="px-3 py-1 text-xs text-bone-3"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Layout>
  );
}
