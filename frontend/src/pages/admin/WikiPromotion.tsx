import { useState } from "react";
import { useRules } from "../../api/rules";
import { useWikiPromote } from "../../api/feedback";
import { useRuleDiff } from "../../api/diff";
import Layout from "../../components/Layout";
import RuleDiff from "../../components/RuleDiff";

function RuleDiffForRule({ ruleId }: { ruleId: string }) {
  const { data, isLoading } = useRuleDiff(ruleId);
  if (isLoading) return <p style={{ fontSize: 12, color: "var(--ink3)" }}>Loading diff…</p>;
  return (
    <RuleDiff
      before={data?.before?.definition ?? null}
      after={data?.after?.definition ?? null}
      title="Definition change"
    />
  );
}

export default function WikiPromotion() {
  const { data, isLoading } = useRules(1, 200);
  const promote = useWikiPromote();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const approved = data?.items.filter((r) => r.status === "approved") ?? [];

  const toggle = (id: string) => setSelected((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const handlePromote = async () => {
    const ids = selected.size > 0 ? Array.from(selected) : approved.map((r) => r.id);
    const res = await promote.mutateAsync({ change_ids: ids });
    setResult(res.message || "Promotion complete");
    setSelected(new Set());
  };

  return (
    <Layout>
      <h1 style={{ margin: "0 0 8px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Wiki Promotion</h1>
      <p style={{ margin: "0 0 24px", fontSize: 14, color: "var(--ink3)" }}>
        Review approved rule changes and promote them to the main wiki.
      </p>

      {isLoading && <p style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</p>}

      {result && (
        <div style={{ marginBottom: 16, padding: "12px 16px", background: "var(--ok-soft)", border: "1px solid var(--ok)", borderRadius: 10, color: "var(--ok)", fontSize: 13 }}>
          {result}
        </div>
      )}

      {approved.length === 0 && !isLoading && (
        <p style={{ color: "var(--ink3)", fontSize: 13 }}>No approved rules pending promotion.</p>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {approved.map((rule) => (
          <div key={rule.id} style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "14px 18px" }}>
              <input
                type="checkbox"
                checked={selected.has(rule.id)}
                onChange={() => toggle(rule.id)}
                style={{ width: 16, height: 16, accentColor: "var(--accent)", cursor: "pointer" }}
              />
              <div style={{ flex: 1 }}>
                <h3 style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>{rule.title}</h3>
                <span style={{ fontSize: 12, color: "var(--ok)", fontWeight: 500 }}>approved</span>
              </div>
              <button
                onClick={() => setExpandedId(expandedId === rule.id ? null : rule.id)}
                style={{ border: "1px solid var(--line)", background: "var(--panel)", padding: "5px 11px", borderRadius: 999, fontSize: 12, color: "var(--ink2)", cursor: "pointer", fontFamily: "var(--font-sans)" }}
              >
                {expandedId === rule.id ? "Hide diff" : "View diff"}
              </button>
            </div>
            {expandedId === rule.id && (
              <div style={{ borderTop: "1px solid var(--line2)", padding: "16px 18px", background: "var(--panel2)" }}>
                <RuleDiffForRule ruleId={rule.id} />
              </div>
            )}
          </div>
        ))}
      </div>

      {approved.length > 0 && (
        <div style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 16 }}>
          <button
            onClick={handlePromote}
            disabled={promote.isPending}
            style={{
              padding: "9px 20px", border: 0, borderRadius: 999,
              background: "var(--accent)", color: "#fff",
              fontSize: 14, fontWeight: 600, cursor: promote.isPending ? "not-allowed" : "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            {promote.isPending ? "Promoting…" : selected.size > 0 ? `Promote ${selected.size} selected` : `Promote all ${approved.length}`}
          </button>
          {selected.size > 0 && (
            <button
              onClick={() => setSelected(new Set())}
              style={{ border: 0, background: "none", fontSize: 13, color: "var(--ink3)", cursor: "pointer", fontFamily: "var(--font-sans)" }}
            >
              Clear selection
            </button>
          )}
        </div>
      )}
    </Layout>
  );
}
