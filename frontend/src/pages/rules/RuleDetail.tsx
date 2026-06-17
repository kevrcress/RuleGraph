import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ThumbsUp, ThumbsDown, ChevronDown, ChevronRight } from "lucide-react";
import { useRule, useUpdateRuleStatus } from "../../api/rules";
import { useSubscriptions, useSubscribe, useUnsubscribe } from "../../api/chat";
import { useImpact, useFeedback } from "../../api/feedback";
import { useAuthStore } from "../../store/authStore";
import Layout from "../../components/Layout";
import CompareView from "../../components/CompareView";
import StatusBadge from "../../components/StatusBadge";

const secondaryBtn: React.CSSProperties = {
  border: "1px solid var(--line)", background: "var(--panel)",
  padding: "7px 13px", borderRadius: 999, fontSize: 13,
  color: "var(--ink2)", cursor: "pointer", fontFamily: "var(--font-sans)", fontWeight: 500,
};

function SubscribeButton({ ruleId }: { ruleId: string }) {
  const { data: subs } = useSubscriptions();
  const subscribe = useSubscribe();
  const unsubscribe = useUnsubscribe();
  const existing = subs?.items.find((s) => s.target_type === "rule" && s.target_id === ruleId);

  return existing ? (
    <button onClick={() => unsubscribe.mutate(existing.id)} style={secondaryBtn}>
      Unsubscribe
    </button>
  ) : (
    <button onClick={() => subscribe.mutate({ target_type: "rule", target_id: ruleId })} style={secondaryBtn}>
      Subscribe
    </button>
  );
}

function FeedbackPanel({ ruleId }: { ruleId: string }) {
  const feedback = useFeedback();
  const [sent, setSent] = useState<string | null>(null);

  const send = (signal_type: string) => {
    feedback.mutate({ signal_type, rule_id: ruleId });
    setSent(signal_type);
  };

  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: 18 }}>
      <div style={{ fontSize: 12, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 12 }}>
        Feedback
      </div>
      <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
        <button
          onClick={() => send("thumbs_up")}
          disabled={feedback.isPending}
          style={{
            flex: 1, padding: 10, border: "1px solid var(--ok-soft)",
            background: sent === "thumbs_up" ? "var(--ok-soft)" : "var(--panel)",
            color: sent === "thumbs_up" ? "var(--ok)" : "var(--ink2)",
            borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: "pointer",
            fontFamily: "var(--font-sans)",
          }}
        >
          <ThumbsUp size={13} style={{ display: "inline", marginRight: 6 }} />
          This looks right
        </button>
        <button
          onClick={() => send("thumbs_down")}
          disabled={feedback.isPending}
          style={{
            flex: 1, padding: 10, border: "1px solid var(--line)",
            background: sent === "thumbs_down" ? "var(--danger-soft)" : "var(--panel)",
            color: sent === "thumbs_down" ? "var(--danger)" : "var(--ink2)",
            borderRadius: 8, fontSize: 13, cursor: "pointer",
            fontFamily: "var(--font-sans)",
          }}
        >
          <ThumbsDown size={13} style={{ display: "inline", marginRight: 6 }} />
          Something's off
        </button>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {[
          { label: "This is wrong",    signal: "this_is_wrong" },
          { label: "Mark as verified", signal: "mark_as_verified" },
        ].map(({ label, signal }) => (
          <button
            key={signal}
            onClick={() => send(signal)}
            disabled={feedback.isPending}
            style={{
              flex: 1, padding: "8px", border: "1px solid var(--line)",
              background: "var(--panel)", color: "var(--ink2)",
              borderRadius: 999, fontSize: 12.5, cursor: "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ImpactPanel({ ruleId, view }: { ruleId: string; view: string }) {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useImpact(ruleId, view);

  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10 }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 18px", border: 0, background: "transparent", cursor: "pointer",
          fontFamily: "var(--font-sans)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 12, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Impact</span>
        </div>
        {open ? <ChevronDown size={14} color="var(--ink3)" /> : <ChevronRight size={14} color="var(--ink3)" />}
      </button>

      {open && (
        <div style={{ padding: "0 18px 18px", borderTop: "1px solid var(--line2)" }}>
          {isLoading && <p style={{ fontSize: 12, color: "var(--ink3)", marginTop: 12 }}>Loading impact…</p>}
          {data && (
            <>
              {data.summary && <p style={{ fontSize: 14, color: "var(--ink2)", marginTop: 12, lineHeight: 1.6 }}>{data.summary}</p>}
              {data.services.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 8 }}>
                    Affected Services
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {data.services.map((s, i) => (
                      <span key={i} style={{ padding: "4px 10px", borderRadius: 999, background: "var(--panel2)", fontFamily: "var(--font-mono)", fontSize: 11.5, color: "var(--ink2)" }}>
                        {s.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {data.rules.length > 0 && (
                <div style={{ marginTop: 12, borderTop: "1px solid var(--line2)", paddingTop: 10 }}>
                  <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 8 }}>
                    Related Rules
                  </div>
                  {data.rules.map((r, i) => (
                    <div key={i} style={{ padding: "4px 0", fontSize: 13 }}>
                      {r.id ? (
                        <Link to={`/rules/${r.id}`} style={{ color: "var(--accent)", fontWeight: 500, textDecoration: "none" }}>→ {r.title}</Link>
                      ) : (
                        <span style={{ color: "var(--ink2)" }}>→ {r.title}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function StatusActions({ rule }: { rule: { id: string; status: string } }) {
  const update = useUpdateRuleStatus();
  const { user } = useAuthStore();
  const canAct = user?.role === "admin" || user?.role === "tech_lead" || user?.role === "business_admin";
  if (!canAct) return null;

  const actions: { label: string; toStatus: string; bg: string }[] = [];
  if (rule.status === "proposed") {
    actions.push({ label: "Approve", toStatus: "approved", bg: "var(--ok)" });
  }
  if (rule.status === "approved") {
    actions.push({ label: "Mark Active", toStatus: "active", bg: "var(--accent)" });
  }
  if (rule.status !== "deprecated") {
    actions.push({ label: "Deprecate", toStatus: "deprecated", bg: "var(--ink3)" });
  }
  if (actions.length === 0) return null;

  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {actions.map(({ label, toStatus, bg }) => (
        <button
          key={toStatus}
          onClick={() => update.mutate({ id: rule.id, status: toStatus })}
          disabled={update.isPending}
          style={{
            padding: "8px 18px", borderRadius: 999, border: 0,
            background: bg, color: "#fff",
            fontSize: 13, fontWeight: 600, cursor: "pointer",
            fontFamily: "var(--font-sans)", opacity: update.isPending ? 0.6 : 1,
          }}
        >
          {label}
        </button>
      ))}
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
      {/* Breadcrumb */}
      <div style={{ fontSize: 12, color: "var(--ink3)", marginBottom: 10, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <Link to="/rules" style={{ color: "var(--ink3)", textDecoration: "none" }}>Rules</Link>
          {rule && <> · <span style={{ fontFamily: "var(--font-mono)" }}>{rule.id}</span></>}
        </div>
        {rule && ["active", "drift", "needs_update"].includes(rule.status) && (
          <Link
            to={`/wiki/${rule.id}`}
            style={{
              fontSize: 12, color: "var(--accent)", textDecoration: "none",
              fontWeight: 500, display: "flex", alignItems: "center", gap: 4,
            }}
          >
            View in Wiki →
          </Link>
        )}
      </div>

      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}
      {isError   && <div style={{ color: "var(--danger)", fontSize: 13 }}>Rule not found.</div>}

      {rule && (
        <>
          {/* Title row */}
          <div style={{ display: "flex", alignItems: "flex-end", gap: 14, marginBottom: 6, flexWrap: "wrap" }}>
            <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em" }}>
              {rule.title}
            </h1>
            <StatusBadge status={rule.status} />
            <div style={{ flex: 1 }} />
            <StatusActions rule={rule} />
            <SubscribeButton ruleId={rule.id} />
          </div>

          <div style={{ color: "var(--ink3)", fontSize: 13.5, marginBottom: 24 }}>
            {rule.source_type && <>{rule.source_type} · </>}
            {rule.created_at && <>Added {new Date(rule.created_at).toLocaleDateString()}</>}
          </div>

          {/* Compare view */}
          <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: 24, marginBottom: 14 }}>
            <CompareView rule={rule} />
          </div>

          {/* Details */}
          <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: 18, marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 12 }}>
              Details
            </div>
            <dl style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: "6px 0", fontSize: 13 }}>
              <dt style={{ color: "var(--ink3)" }}>ID</dt>
              <dd style={{ margin: 0, fontFamily: "var(--font-mono)", color: "var(--ink)", fontSize: 12 }}>{rule.id}</dd>
              <dt style={{ color: "var(--ink3)" }}>Source</dt>
              <dd style={{ margin: 0, color: "var(--ink2)" }}>{rule.source_type || "—"}</dd>
              {rule.source_file && (
                <>
                  <dt style={{ color: "var(--ink3)" }}>File</dt>
                  <dd style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink2)", wordBreak: "break-all" }}>{rule.source_file}</dd>
                </>
              )}
              {rule.extraction_confidence != null && (
                <>
                  <dt style={{ color: "var(--ink3)" }}>Confidence</dt>
                  <dd style={{ margin: 0, color: "var(--ink2)" }}>{Math.round(rule.extraction_confidence * 100)}%</dd>
                </>
              )}
              {rule.graph_quality_score != null && (
                <>
                  <dt style={{ color: "var(--ink3)" }}>Quality</dt>
                  <dd style={{ margin: 0, color: "var(--ink2)" }}>{Math.round(rule.graph_quality_score * 100)}%</dd>
                </>
              )}
              <dt style={{ color: "var(--ink3)" }}>Created</dt>
              <dd style={{ margin: 0, color: "var(--ink2)" }}>{rule.created_at ? new Date(rule.created_at).toLocaleString() : "—"}</dd>
            </dl>
          </div>

          {/* Feedback + Impact side by side */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <FeedbackPanel ruleId={rule.id} />
            <ImpactPanel ruleId={rule.id} view={view} />
          </div>
        </>
      )}
    </Layout>
  );
}
