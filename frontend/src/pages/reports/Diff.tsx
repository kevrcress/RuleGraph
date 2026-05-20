import { useState } from "react";
import { useDiffList, useRuleDiff } from "../../api/diff";
import Layout from "../../components/Layout";
import RuleDiff from "../../components/RuleDiff";

export default function DiffPage() {
  const { data, isLoading } = useDiffList();
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const { data: diffDetail } = useRuleDiff(selectedRuleId || "");

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">Rule Changes</h1>

      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}

      <div className="grid grid-cols-1 gap-4">
        <ul data-testid="diff-list" className="space-y-2">
          {data?.items.map((item) => (
            <li
              key={item.rule_id}
              data-testid="diff-item"
              className="bg-ink-2 border border-bone-4 rounded-lg p-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-bone-0 text-sm font-medium">{item.title}</h3>
                  <p className="text-xs text-bone-3 mt-0.5">
                    {item.status} · {new Date(item.changed_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  data-testid="view-diff-link"
                  onClick={() =>
                    setSelectedRuleId(
                      selectedRuleId === item.rule_id ? null : item.rule_id
                    )
                  }
                  className="text-xs text-brass-0 hover:text-brass-1 underline"
                >
                  {selectedRuleId === item.rule_id ? "Hide diff" : "View diff"}
                </button>
              </div>

              {selectedRuleId === item.rule_id && diffDetail && (
                <div className="mt-4">
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
            <li className="text-bone-3 text-sm py-4 text-center">No changes recorded.</li>
          )}
        </ul>
      </div>
    </Layout>
  );
}
