import { useState } from "react";
import { useTLDashboard } from "../../api/admin";
import Layout from "../../components/Layout";
import apiClient from "../../api/client";

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
        repo: "", project: "",
      });
      setWorkitem(null);
      refetch();
    } catch { /* fail silently */ }
  };

  const handleNoCode = async (ruleId: string) => {
    try {
      await apiClient.put(`/admin/tech-lead-dashboard/${ruleId}/no-code`);
      refetch();
    } catch { /* fail silently */ }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "8px 12px",
    border: "1px solid var(--line)", borderRadius: 8,
    fontSize: 13, fontFamily: "var(--font-sans)",
    background: "var(--panel)", color: "var(--ink)", outline: "none",
  };

  return (
    <Layout>
      <div data-testid="tl-dashboard" style={{ maxWidth: 800 }}>
        <h1 style={{ margin: "0 0 8px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>TL Dashboard</h1>
        <p style={{ margin: "0 0 24px", fontSize: 14, color: "var(--ink3)" }}>
          Approved rules awaiting implementation.
        </p>
        {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}
        {data?.items?.length === 0 && !isLoading && (
          <p style={{ color: "var(--ink3)", fontSize: 13 }}>No approved rules awaiting action.</p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {data?.items?.map((rule: any) => (
            <div key={rule.id} style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "18px 20px" }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>{rule.title}</h3>
                  {rule.definition && (
                    <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--ink2)" }}>
                      {rule.definition.slice(0, 200)}{rule.definition.length > 200 ? "…" : ""}
                    </p>
                  )}
                </div>
                <div style={{ display: "flex", gap: 8, marginLeft: 16 }}>
                  <button
                    onClick={() => { setWorkitem({ ruleId: rule.id, title: rule.title }); setWiTitle(rule.title); setWiBody(rule.definition || ""); }}
                    style={{ padding: "7px 14px", border: "1px solid var(--info)", borderRadius: 999, background: "var(--info-soft)", color: "var(--info)", fontSize: 13, cursor: "pointer", fontFamily: "var(--font-sans)" }}
                  >
                    Create Work Item
                  </button>
                  <button
                    onClick={() => handleNoCode(rule.id)}
                    style={{ padding: "7px 14px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 13, cursor: "pointer", fontFamily: "var(--font-sans)" }}
                  >
                    No Code Change
                  </button>
                </div>
              </div>

              {workitem?.ruleId === rule.id && (
                <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                  <input value={wiTitle} onChange={(e) => setWiTitle(e.target.value)} placeholder="Work item title" style={inputStyle} />
                  <textarea value={wiBody} onChange={(e) => setWiBody(e.target.value)} rows={3} placeholder="Description" style={{ ...inputStyle, resize: "vertical" }} />
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={handleCodeChange} style={{ padding: "7px 14px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                      Confirm
                    </button>
                    <button onClick={() => setWorkitem(null)} style={{ padding: "7px 14px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 13, cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
