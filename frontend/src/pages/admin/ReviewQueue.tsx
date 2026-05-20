import { useState } from "react";
import { useReviewQueue, useApproveRule, useRejectRule } from "../../api/admin";
import Layout from "../../components/Layout";

export default function ReviewQueue() {
  const { data, isLoading } = useReviewQueue();
  const { mutate: approve } = useApproveRule();
  const { mutate: reject } = useRejectRule();
  const [rejecting, setRejecting] = useState<string | null>(null);
  const [rejectNote, setRejectNote] = useState("");

  return (
    <Layout>
      <div data-testid="review-queue" className="max-w-4xl">
        <h1 className="text-xl font-serif text-bone-0 mb-4">Review Queue</h1>
        {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}

        {data?.items?.length === 0 && !isLoading && (
          <p className="text-bone-3 text-sm">No rules pending review.</p>
        )}

        <ul className="space-y-3">
          {data?.items?.map((rule: { id: string; title: string; definition?: string; status: string; created_at: string }) => (
            <li key={rule.id} className="bg-ink-2 border border-bone-4 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-bone-0 font-medium">{rule.title}</h3>
                  {rule.definition && (
                    <p className="text-sm text-bone-2 mt-1 line-clamp-2">{rule.definition}</p>
                  )}
                  <p className="text-xs text-bone-3 mt-1">
                    Proposed {new Date(rule.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => approve(rule.id)}
                    className="px-3 py-1 text-xs bg-green-800 text-green-200 rounded hover:bg-green-700"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => setRejecting(rule.id)}
                    className="px-3 py-1 text-xs bg-ember/20 text-ember rounded hover:bg-ember/30"
                  >
                    Reject
                  </button>
                </div>
              </div>

              {rejecting === rule.id && (
                <div className="mt-3 flex gap-2">
                  <input
                    value={rejectNote}
                    onChange={(e) => setRejectNote(e.target.value)}
                    placeholder="Rejection reason…"
                    className="flex-1 bg-ink-3 border border-bone-4 rounded px-2 py-1 text-xs text-bone-0 focus:outline-none"
                  />
                  <button
                    onClick={() => {
                      reject({ ruleId: rule.id, note: rejectNote });
                      setRejecting(null);
                      setRejectNote("");
                    }}
                    className="px-2 py-1 text-xs bg-ember text-white rounded"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setRejecting(null)}
                    className="px-2 py-1 text-xs text-bone-3"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Layout>
  );
}
