import { useParams, Link } from "react-router-dom";
import { Bell, BellOff } from "lucide-react";
import { useRule } from "../../api/rules";
import { useSubscriptions, useSubscribe, useUnsubscribe } from "../../api/chat";
import Layout from "../../components/Layout";
import CompareView from "../../components/CompareView";

function SubscribeButton({ ruleId }: { ruleId: string }) {
  const { data: subs } = useSubscriptions();
  const subscribe = useSubscribe();
  const unsubscribe = useUnsubscribe();

  const existing = subs?.items.find(
    (s) => s.target_type === "rule" && s.target_id === ruleId
  );

  if (existing) {
    return (
      <button
        onClick={() => unsubscribe.mutate(existing.id)}
        className="inline-flex items-center gap-1 text-xs text-bone-3 hover:text-ember border border-bone-4 rounded px-2 py-1"
      >
        <BellOff size={12} /> Unsubscribe
      </button>
    );
  }

  return (
    <button
      onClick={() => subscribe.mutate({ target_type: "rule", target_id: ruleId })}
      className="inline-flex items-center gap-1 text-xs text-bone-2 hover:text-brass-0 border border-bone-4 rounded px-2 py-1"
    >
      <Bell size={12} /> Subscribe
    </button>
  );
}

export default function RuleDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: rule, isLoading, isError } = useRule(id || "");

  return (
    <Layout>
      <div className="mb-4 flex items-center justify-between">
        <Link to="/rules" className="text-sm text-bone-3 hover:text-bone-1">
          ← Back to Rules
        </Link>
        {rule && <SubscribeButton ruleId={rule.id} />}
      </div>

      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}
      {isError && <div className="text-ember text-sm">Rule not found.</div>}

      {rule && (
        <div className="max-w-3xl">
          <div className="bg-ink-2 border border-bone-4 rounded-lg p-6">
            <CompareView rule={rule} />
          </div>

          <div className="mt-4 bg-ink-2 border border-bone-4 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-bone-2 mb-2">Details</h4>
            <dl className="grid grid-cols-2 gap-2 text-xs text-bone-3">
              <dt>ID</dt>
              <dd className="font-mono">{rule.id}</dd>
              <dt>Source</dt>
              <dd>{rule.source_type || "—"}</dd>
              {rule.extraction_confidence != null && (
                <>
                  <dt>Confidence</dt>
                  <dd>{Math.round(rule.extraction_confidence * 100)}%</dd>
                </>
              )}
              <dt>Created</dt>
              <dd>{rule.created_at ? new Date(rule.created_at).toLocaleString() : "—"}</dd>
            </dl>
          </div>
        </div>
      )}
    </Layout>
  );
}
