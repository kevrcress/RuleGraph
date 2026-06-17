import { useState } from "react";
import { useDiffList, useRuleDiff } from "../../api/diff";
import Layout from "../../components/Layout";
import RuleDiff from "../../components/RuleDiff";
import StatusBadge from "../../components/StatusBadge";

export default function DiffPage() {
  const { data, isLoading } = useDiffList();
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const { data: diffDetail } = useRuleDiff(selectedRuleId || "");

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Policy vs Code Diff</h1>
      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}

      <ul data-testid="diff-list" style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        {data?.items.map((item) => (
          <li
            key={item.rule_id}
            data-testid="diff-item"
            style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, overflow: "hidden" }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 18px" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 14, fontWeight: 500, color: "var(--ink)" }}>{item.title}</h3>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 4 }}>
                  <StatusBadge status={item.status} />
                  <span style={{ fontSize: 12, color: "var(--ink3)" }}>
                    {new Date(item.changed_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <button
                data-testid="view-diff-link"
                onClick={() => setSelectedRuleId(selectedRuleId === item.rule_id ? null : item.rule_id)}
                style={{
                  border: "1px solid var(--line)", background: "var(--panel)",
                  padding: "5px 11px", borderRadius: 999, fontSize: 12,
                  color: "var(--accent)", fontWeight: 600, cursor: "pointer",
                  fontFamily: "var(--font-sans)",
                }}
              >
                {selectedRuleId === item.rule_id ? "Hide diff" : "View diff"}
              </button>
            </div>

            {selectedRuleId === item.rule_id && diffDetail && (
              <div style={{ borderTop: "1px solid var(--line2)", padding: "16px 18px", background: "var(--panel2)" }}>
                <RuleDiff
                  before={diffDetail.before?.definition ?? null}
                  after={diffDetail.after?.definition ?? null}
                  title={`${diffDetail.rule_title} — Definition change`}
                />
              </div>
            )}
          </li>
        ))}
        {data?.items.length === 0 && !isLoading && (
          <div style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: 32 }}>
            No changes recorded.
          </div>
        )}
      </ul>
    </Layout>
  );
}
