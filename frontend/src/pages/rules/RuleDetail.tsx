import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Bell, BellOff, ThumbsUp, ThumbsDown, AlertTriangle, CheckCircle, ChevronDown, ChevronRight } from "lucide-react";
import { useRule } from "../../api/rules";
import { useSubscriptions, useSubscribe, useUnsubscribe } from "../../api/chat";
import { useImpact, useFeedback } from "../../api/feedback";
import { useAuthStore } from "../../store/authStore";
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

function FeedbackButtons({ ruleId }: { ruleId: string }) {
  const feedback = useFeedback();
  const [sent, setSent] = useState<string | null>(null);

  const send = (signal_type: string) => {
    feedback.mutate({ signal_type, rule_id: ruleId });
    setSent(signal_type);
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-bone-3">Was this helpful?</span>
      <button
        onClick={() => send("thumbs_up")}
        disabled={feedback.isPending}
        className={`inline-flex items-center gap-1 text-xs border rounded px-2 py-1 transition-colors ${
          sent === "thumbs_up"
            ? "text-green-400 border-green-400"
            : "text-bone-3 border-bone-4 hover:text-green-400 hover:border-green-400"
        }`}
        title="Thumbs up"
      >
        <ThumbsUp size={12} />
      </button>
      <button
        onClick={() => send("thumbs_down")}
        disabled={feedback.isPending}
        className={`inline-flex items-center gap-1 text-xs border rounded px-2 py-1 transition-colors ${
          sent === "thumbs_down"
            ? "text-ember border-ember"
            : "text-bone-3 border-bone-4 hover:text-ember hover:border-ember"
        }`}
        title="Thumbs down"
      >
        <ThumbsDown size={12} />
      </button>
      <button
        onClick={() => send("this_is_wrong")}
        disabled={feedback.isPending}
        className={`inline-flex items-center gap-1 text-xs border rounded px-2 py-1 transition-colors ${
          sent === "this_is_wrong"
            ? "text-orange-400 border-orange-400"
            : "text-bone-3 border-bone-4 hover:text-orange-400"
        }`}
        title="This is wrong"
      >
        <AlertTriangle size={12} /> This is wrong
      </button>
      <button
        onClick={() => send("mark_as_verified")}
        disabled={feedback.isPending}
        className={`inline-flex items-center gap-1 text-xs border rounded px-2 py-1 transition-colors ${
          sent === "mark_as_verified"
            ? "text-brass-0 border-brass-0"
            : "text-bone-3 border-bone-4 hover:text-brass-0"
        }`}
        title="Mark as verified"
      >
        <CheckCircle size={12} /> Mark as verified
      </button>
    </div>
  );
}

function ImpactPanel({ ruleId, view }: { ruleId: string; view: string }) {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useImpact(ruleId, view);

  return (
    <div className="mt-4 bg-ink-2 border border-bone-4 rounded-lg">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between p-4 text-sm font-semibold text-bone-2 hover:text-bone-0"
      >
        <span>Impact Analysis</span>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3">
          {isLoading && <p className="text-xs text-bone-3">Loading impact…</p>}

          {data && (
            <>
              {data.summary && (
                <p className="text-sm text-bone-2">{data.summary}</p>
              )}

              {data.services.length > 0 && (
                <div>
                  <h5 className="text-xs font-semibold text-bone-3 uppercase mb-1">Affected Services</h5>
                  <ul className="space-y-1">
                    {data.services.map((s, i) => (
                      <li key={i} className="text-xs text-bone-1">{s.name}</li>
                    ))}
                  </ul>
                </div>
              )}

              {data.rules.length > 0 && (
                <div>
                  <h5 className="text-xs font-semibold text-bone-3 uppercase mb-1">Related Rules</h5>
                  <ul className="space-y-1">
                    {data.rules.map((r, i) => (
                      <li key={i} className="text-xs">
                        {r.id ? (
                          <Link to={`/rules/${r.id}`} className="text-brass-0 hover:text-brass-1">
                            {r.title}
                          </Link>
                        ) : (
                          <span className="text-bone-1">{r.title}</span>
                        )}
                        <span className="text-bone-3 ml-1">({r.status})</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {data.subscribed_count > 0 && (
                <p className="text-xs text-bone-3">
                  {data.subscribed_count} subscriber(s) will be notified on change.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function RuleDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: rule, isLoading, isError } = useRule(id || "");
  const { user } = useAuthStore();
  const view = user?.role === "user" || user?.role === "business_admin" ? "business" : "technical";

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
              {rule.graph_quality_score != null && (
                <>
                  <dt>Quality Score</dt>
                  <dd>{Math.round(rule.graph_quality_score * 100)}%</dd>
                </>
              )}
              <dt>Created</dt>
              <dd>{rule.created_at ? new Date(rule.created_at).toLocaleString() : "—"}</dd>
            </dl>
          </div>

          {/* Feedback signals */}
          <div className="mt-4 bg-ink-2 border border-bone-4 rounded-lg p-4">
            <FeedbackButtons ruleId={rule.id} />
          </div>

          {/* Impact panel — collapsible, lazy loaded */}
          <ImpactPanel ruleId={rule.id} view={view} />
        </div>
      )}
    </Layout>
  );
}
