import { useState } from "react";
import { useRules } from "../../api/rules";
import { useWikiPromote } from "../../api/feedback";
import { useRuleDiff } from "../../api/diff";
import Layout from "../../components/Layout";
import RuleDiff from "../../components/RuleDiff";

function RuleDiffForRule({ ruleId }: { ruleId: string }) {
  const { data, isLoading } = useRuleDiff(ruleId);
  if (isLoading) return <p className="text-xs text-bone-3">Loading diff…</p>;
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

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handlePromote = async () => {
    const ids = selected.size > 0 ? Array.from(selected) : approved.map((r) => r.id);
    const res = await promote.mutateAsync({ change_ids: ids });
    setResult(res.message || "Promotion complete");
    setSelected(new Set());
  };

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-xl font-serif text-bone-0">QA Wiki Promotion</h1>
        <p className="text-sm text-bone-3 mt-1">
          Review approved rule changes and promote them to the main wiki.
        </p>
      </div>

      {isLoading && <p className="text-bone-3 text-sm">Loading…</p>}

      {result && (
        <div className="mb-4 p-3 bg-green-900/20 border border-green-500/30 rounded text-green-400 text-sm">
          {result}
        </div>
      )}

      {approved.length === 0 && !isLoading && (
        <p className="text-bone-3 text-sm">No approved rules pending promotion.</p>
      )}

      <ul className="space-y-3">
        {approved.map((rule) => (
          <li key={rule.id} className="bg-ink-2 border border-bone-4 rounded-lg">
            <div className="flex items-center gap-3 p-4">
              <input
                type="checkbox"
                checked={selected.has(rule.id)}
                onChange={() => toggle(rule.id)}
                className="rounded border-bone-4 bg-ink-3"
              />
              <div className="flex-1 min-w-0">
                <h3 className="text-bone-0 font-medium truncate">{rule.title}</h3>
                <span className="text-xs text-blue-400">approved</span>
              </div>
              <button
                onClick={() => setExpandedId(expandedId === rule.id ? null : rule.id)}
                className="text-xs text-bone-3 hover:text-bone-1 border border-bone-4 rounded px-2 py-1"
              >
                {expandedId === rule.id ? "Hide diff" : "View diff"}
              </button>
            </div>

            {expandedId === rule.id && (
              <div className="border-t border-bone-4 p-4">
                <RuleDiffForRule ruleId={rule.id} />
              </div>
            )}
          </li>
        ))}
      </ul>

      {approved.length > 0 && (
        <div className="mt-6 flex items-center gap-4">
          <button
            onClick={handlePromote}
            disabled={promote.isPending}
            className="px-4 py-2 bg-brass-0 text-ink-0 rounded text-sm font-semibold hover:bg-brass-1 disabled:opacity-50"
          >
            {promote.isPending
              ? "Promoting…"
              : selected.size > 0
              ? `Promote ${selected.size} selected`
              : `Promote all ${approved.length}`}
          </button>
          {selected.size > 0 && (
            <button
              onClick={() => setSelected(new Set())}
              className="text-xs text-bone-3 hover:text-bone-1"
            >
              Clear selection
            </button>
          )}
        </div>
      )}
    </Layout>
  );
}
