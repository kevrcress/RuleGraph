import { useState } from "react";
import { useConflicts } from "../../api/admin";
import { useDriftRules } from "../../api/rules";
import { useSubscriptions, useSubscribe, useUnsubscribe } from "../../api/chat";
import Layout from "../../components/Layout";
import RuleDiff from "../../components/RuleDiff";

const SEV_CONFIG = {
  high:   { fg: "var(--danger)", bg: "var(--danger-soft)", label: "High" },
  medium: { fg: "var(--warn)",   bg: "var(--warn-soft)",   label: "Medium" },
  low:    { fg: "var(--ink3)",   bg: "#eeeae0",            label: "Low" },
};

function PolicyVsCodeSection() {
  const { data: driftRules, isLoading } = useDriftRules();
  const [expanded, setExpanded] = useState<string | null>(null);

  if (isLoading) return <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>;

  const items = driftRules ?? [];

  return (
    <div>
      <h2 style={{ margin: "0 0 6px", fontSize: 18, fontWeight: 600, letterSpacing: "-0.015em" }}>Policy vs Code Divergence</h2>
      <p style={{ color: "var(--ink2)", fontSize: 14, margin: "0 0 16px", maxWidth: 720 }}>
        Rules where the written definition (policy) no longer matches what the code implementation was found to do on the last ingest.
      </p>

      {items.length === 0 && (
        <div style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: "24px 0" }}>
          No policy–code divergence detected.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {items.map((rule) => (
          <div
            key={rule.id}
            style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, overflow: "hidden" }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 18px" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 14, fontWeight: 500, color: "var(--ink)" }}>{rule.title}</h3>
                {rule.source_file && (
                  <span style={{ fontSize: 12, color: "var(--ink3)", fontFamily: "var(--font-mono)", marginTop: 2, display: "block" }}>
                    {rule.source_file}
                  </span>
                )}
              </div>
              <button
                onClick={() => setExpanded(expanded === rule.id ? null : rule.id)}
                style={{
                  border: "1px solid var(--line)", background: "var(--panel)",
                  padding: "5px 11px", borderRadius: 999, fontSize: 12,
                  color: "var(--accent)", fontWeight: 600, cursor: "pointer",
                  fontFamily: "var(--font-sans)",
                }}
              >
                {expanded === rule.id ? "Hide diff" : "View diff"}
              </button>
            </div>

            {expanded === rule.id && (
              <div style={{ borderTop: "1px solid var(--line2)", padding: "16px 18px", background: "var(--panel2)" }}>
                <PolicyCodeDiff rule={rule} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function PolicyCodeDiff({ rule }: { rule: { definition: string; code_behavior: string | null; title: string } }) {
  const panelBase: React.CSSProperties = {
    whiteSpace: "pre-wrap", fontSize: 13, padding: "12px 14px",
    borderRadius: 8, fontFamily: "var(--font-mono)", minHeight: 80,
    opacity: 0.85,
  };

  return (
    <div style={{ width: "100%" }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>
        {rule.title} — Policy vs Code
      </h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div>
          <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 8 }}>Policy</div>
          <pre style={{ ...panelBase, background: "var(--ok-soft)", color: "var(--ok)", border: "1px solid var(--ok)" }}>
            {rule.definition}
          </pre>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 8 }}>Code</div>
          {rule.code_behavior ? (
            <pre style={{ ...panelBase, background: "var(--danger-soft)", color: "var(--danger)", border: "1px solid var(--danger)" }}>
              {rule.code_behavior}
            </pre>
          ) : (
            <div style={{ color: "var(--ink4)", fontSize: 13, fontStyle: "italic", padding: 12 }}>No code behavior recorded</div>
          )}
        </div>
      </div>
    </div>
  );
}

function ConflictSubscribeButton({ conflictId }: { conflictId: string }) {
  const { data: subs } = useSubscriptions();
  const subscribe = useSubscribe();
  const unsubscribe = useUnsubscribe();
  const existing = subs?.items.find((s) => s.target_type === "conflict" && s.target_id === conflictId);

  const btnStyle: React.CSSProperties = {
    border: "1px solid var(--line)", background: "var(--panel)",
    padding: "5px 11px", borderRadius: 999, fontSize: 12,
    color: "var(--ink2)", cursor: "pointer", fontFamily: "var(--font-sans)",
  };

  return existing ? (
    <button onClick={() => unsubscribe.mutate(existing.id)} style={btnStyle}>Unsubscribe</button>
  ) : (
    <button onClick={() => subscribe.mutate({ target_type: "conflict", target_id: conflictId })} style={btnStyle}>Subscribe</button>
  );
}

export default function Conflicts() {
  const { data, isLoading } = useConflicts();
  const items = data?.items ?? [];

  const high   = items.filter((c: any) => c.severity === "high").length;
  const medium = items.filter((c: any) => c.severity === "medium").length;
  const low    = items.filter((c: any) => !c.severity || c.severity === "low").length;

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 4 }}>
        <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Conflicts</h1>
      </div>
      <p style={{ color: "var(--ink2)", fontSize: 14, marginBottom: 32, maxWidth: 720 }}>
        Rules that diverge between policy and code, or that conflict across services.
      </p>

      {/* Policy vs Code section */}
      <PolicyVsCodeSection />

      <div style={{ borderTop: "1px solid var(--line)", margin: "32px 0" }} />

      {/* Cross-service conflicts section */}
      <h2 style={{ margin: "0 0 6px", fontSize: 18, fontWeight: 600, letterSpacing: "-0.015em" }}>Cross-service Conflicts</h2>
      <p style={{ color: "var(--ink2)", fontSize: 14, margin: "0 0 16px", maxWidth: 720 }}>
        Where two or more rules implement the same business concept with different values or behavior.
      </p>

      {/* Severity stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginBottom: 24 }}>
        {[
          { label: "High severity", count: high,   color: "var(--danger)" },
          { label: "Medium",        count: medium, color: "var(--warn)" },
          { label: "Low",           count: low,    color: "var(--ink3)" },
        ].map(({ label, count, color }) => (
          <div key={label} style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "18px 20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: color }} />
              <span style={{ fontSize: 13, color: "var(--ink2)", fontWeight: 500 }}>{label}</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.025em", marginTop: 6 }}>{count}</div>
            <div style={{ fontSize: 12.5, color: "var(--ink3)", marginTop: 2 }}>conflicts</div>
          </div>
        ))}
      </div>

      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((c: any) => {
          const sev = SEV_CONFIG[c.severity as keyof typeof SEV_CONFIG] ?? SEV_CONFIG.low;
          return (
            <div
              key={c.id}
              style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "18px 20px" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6, flexWrap: "wrap" }}>
                {c.id && <span style={{ fontSize: 11.5, fontFamily: "var(--font-mono)", color: "var(--ink3)" }}>{c.id}</span>}
                <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-0.01em" }}>
                  {c.rule_a_title ?? c.rule} ↔ {c.rule_b_title}
                </span>
                {c.severity && (
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, color: sev.fg, background: sev.bg, padding: "2px 9px", borderRadius: 999, fontWeight: 500 }}>
                    <span style={{ width: 5, height: 5, borderRadius: 999, background: sev.fg }} />
                    {sev.label}
                  </span>
                )}
                <div style={{ flex: 1 }} />
                <ConflictSubscribeButton conflictId={c.id} />
                <button
                  style={{
                    border: 0, background: "var(--accent)", color: "#fff",
                    padding: "5px 12px", borderRadius: 999, fontSize: 12, fontWeight: 600,
                    cursor: "pointer", fontFamily: "var(--font-sans)",
                  }}
                >
                  Resolve
                </button>
              </div>
              {c.description && (
                <p style={{ fontSize: 13.5, color: "var(--ink2)", margin: 0 }}>{c.description}</p>
              )}
              {c.conflict_type && (
                <span style={{ fontSize: 12, color: "var(--ink3)", display: "block", marginTop: 4 }}>{c.conflict_type}</span>
              )}
            </div>
          );
        })}
        {items.length === 0 && !isLoading && (
          <div style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: 32 }}>
            No cross-service conflicts detected.
          </div>
        )}
      </div>
    </Layout>
  );
}
