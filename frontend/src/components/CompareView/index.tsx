import * as Tabs from "@radix-ui/react-tabs";
import type { RuleDetail } from "../../api/rules";
import { useViewStore } from "../../store/viewStore";
import StatusBadge from "../StatusBadge";

function getCompareStatus(rule: RuleDetail): string {
  if (rule.status === "drift" || rule.status === "needs_update") return "drift";
  if (rule.status === "active" || rule.status === "approved" || rule.status === "verified") return "verified";
  if (!rule.definition) return "undocumented";
  return "missing";
}

export default function CompareView({ rule }: { rule: RuleDetail }) {
  const { mode } = useViewStore();
  const compareStatus = getCompareStatus(rule);

  const tabTriggerStyle = (active: boolean): React.CSSProperties => ({
    padding: "8px 16px", background: "transparent", border: "none",
    borderBottom: active ? `2px solid var(--accent)` : "2px solid transparent",
    color: active ? "var(--accent-deep)" : "var(--ink2)",
    fontSize: 14, fontWeight: active ? 600 : 400,
    cursor: "pointer", fontFamily: "var(--font-sans)",
    transition: "color 150ms, border-color 150ms",
  });

  return (
    <Tabs.Root defaultValue="defined" style={{ width: "100%" }}>
      <Tabs.List style={{ display: "flex", borderBottom: "1px solid var(--line)", marginBottom: 18 }}>
        {["Defined", "Implemented", "Compare"].map((tab) => (
          <Tabs.Trigger key={tab} value={tab.toLowerCase()} asChild>
            <button role="tab" style={tabTriggerStyle(false)}>{tab}</button>
          </Tabs.Trigger>
        ))}
      </Tabs.List>

      <Tabs.Content value="defined" style={{ outline: "none" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{rule.title}</h3>
          {rule.definition ? (
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.65, color: "var(--ink2)" }}>{rule.definition}</p>
          ) : (
            <p style={{ margin: 0, fontSize: 13, color: "var(--ink3)", fontStyle: "italic" }}>No definition provided.</p>
          )}
          <div style={{ fontSize: 12, color: "var(--ink3)" }}>
            Status: <StatusBadge status={rule.status} />
          </div>
          {mode === "technical" && (
            <div style={{ fontSize: 12, color: "var(--ink3)", fontFamily: "var(--font-mono)" }}>ID: {rule.id}</div>
          )}
        </div>
      </Tabs.Content>

      <Tabs.Content value="implemented" style={{ outline: "none" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p style={{ margin: 0, fontSize: 14, color: "var(--ink2)" }}>
            {rule.source_type ? `Source type: ${rule.source_type}` : "No implementation reference found."}
          </p>
          {mode === "technical" && rule.workitem_url && (
            <a href={rule.workitem_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent)", fontSize: 13, fontWeight: 500 }}>
              Work item: {rule.workitem_id}
            </a>
          )}
          {mode === "technical" && rule.cognee_node_id && (
            <p style={{ margin: 0, fontSize: 12, color: "var(--ink3)", fontFamily: "var(--font-mono)" }}>Graph node: {rule.cognee_node_id}</p>
          )}
        </div>
      </Tabs.Content>

      <Tabs.Content value="compare" style={{ outline: "none" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div data-testid="compare-status">
            <StatusBadge status={compareStatus} />
          </div>
          <p style={{ margin: 0, fontSize: 14, color: "var(--ink2)" }}>
            {compareStatus === "verified"     && "Rule definition and implementation are in alignment."}
            {compareStatus === "drift"        && "Rule definition exists but code behavior has diverged."}
            {compareStatus === "undocumented" && "Code behavior exists but no formal rule has been defined."}
            {compareStatus === "missing"      && "Rule is defined but no implementation has been found."}
          </p>
          {rule.coverage_status && (
            <div style={{ fontSize: 12, color: "var(--ink3)" }}>Coverage: <span style={{ color: "var(--ink)" }}>{rule.coverage_status}</span></div>
          )}
          {rule.updated_at && (
            <div style={{ fontSize: 12, color: "var(--ink3)" }}>Last updated: {new Date(rule.updated_at).toLocaleDateString()}</div>
          )}
        </div>
      </Tabs.Content>
    </Tabs.Root>
  );
}
