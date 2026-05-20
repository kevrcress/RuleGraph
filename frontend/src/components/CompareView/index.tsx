import * as Tabs from "@radix-ui/react-tabs";
import type { RuleDetail } from "../../api/rules";
import { useViewStore } from "../../store/viewStore";

const STATUS_COLORS: Record<string, string> = {
  Verified: "text-green-400",
  Drift: "text-yellow-400",
  Undocumented: "text-blue-400",
  Orphaned: "text-red-400",
};

function getCompareStatus(rule: RuleDetail): string {
  if (rule.status === "drift" || rule.status === "needs_update") return "Drift";
  if (rule.status === "active" || rule.status === "approved") return "Verified";
  if (!rule.definition) return "Undocumented";
  return "Orphaned";
}

interface Props {
  rule: RuleDetail;
}

export default function CompareView({ rule }: Props) {
  const { mode } = useViewStore();
  const compareStatus = getCompareStatus(rule);
  const statusColor = STATUS_COLORS[compareStatus] || "text-bone-1";

  return (
    <Tabs.Root defaultValue="defined" className="w-full">
      <Tabs.List className="flex border-b border-bone-4 mb-4">
        {["Defined", "Implemented", "Compare"].map((tab) => (
          <Tabs.Trigger
            key={tab}
            value={tab.toLowerCase()}
            role="tab"
            className="px-4 py-2 text-sm text-bone-2 hover:text-bone-0 data-[state=active]:text-brass-0 data-[state=active]:border-b-2 data-[state=active]:border-brass-0 transition-colors"
          >
            {tab}
          </Tabs.Trigger>
        ))}
      </Tabs.List>

      <Tabs.Content value="defined" className="focus:outline-none">
        <div className="space-y-3">
          <h3 className="text-bone-0 font-semibold">{rule.title}</h3>
          {rule.definition ? (
            <p className="text-bone-1 text-sm leading-relaxed">{rule.definition}</p>
          ) : (
            <p className="text-bone-3 text-sm italic">No definition provided.</p>
          )}
          <div className="text-xs text-bone-3">
            Status: <span className="text-bone-1">{rule.status}</span>
          </div>
          {mode === "technical" && (
            <div className="text-xs text-bone-3 font-mono">
              ID: {rule.id}
            </div>
          )}
        </div>
      </Tabs.Content>

      <Tabs.Content value="implemented" className="focus:outline-none">
        <div className="space-y-3">
          <p className="text-bone-1 text-sm">
            {rule.source_type
              ? `Source type: ${rule.source_type}`
              : "No implementation reference found."}
          </p>
          {mode === "technical" && rule.workitem_url && (
            <a
              href={rule.workitem_url}
              target="_blank"
              rel="noreferrer"
              className="text-brass-0 text-xs hover:underline"
            >
              Work item: {rule.workitem_id}
            </a>
          )}
          {mode === "technical" && rule.cognee_node_id && (
            <p className="text-xs text-bone-3 font-mono">
              Graph node: {rule.cognee_node_id}
            </p>
          )}
        </div>
      </Tabs.Content>

      <Tabs.Content value="compare" className="focus:outline-none">
        <div className="space-y-3">
          <div
            data-testid="compare-status"
            className={`text-lg font-semibold ${statusColor}`}
          >
            {compareStatus}
          </div>
          <p className="text-bone-2 text-sm">
            {compareStatus === "Verified" &&
              "Rule definition and implementation are in alignment."}
            {compareStatus === "Drift" &&
              "Rule definition exists but code behavior has diverged."}
            {compareStatus === "Undocumented" &&
              "Code behavior exists but no formal rule has been defined."}
            {compareStatus === "Orphaned" &&
              "Rule is defined but no implementation has been found."}
          </p>
          {rule.coverage_status && (
            <div className="text-xs text-bone-3">
              Coverage: <span className="text-bone-1">{rule.coverage_status}</span>
            </div>
          )}
          {rule.updated_at && (
            <div className="text-xs text-bone-3">
              Last updated: {new Date(rule.updated_at).toLocaleDateString()}
            </div>
          )}
        </div>
      </Tabs.Content>
    </Tabs.Root>
  );
}
