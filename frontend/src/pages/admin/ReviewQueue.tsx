import { useState } from "react";
import { useReviewQueue, useApproveRule, useRejectRule, useBulkApproveRules } from "../../api/admin";
import Layout from "../../components/Layout";

export default function ReviewQueue() {
  const { data, isLoading } = useReviewQueue();
  const { mutate: approve } = useApproveRule();
  const { mutate: reject } = useRejectRule();
  const bulkApprove = useBulkApproveRules();
  const [rejecting, setRejecting] = useState<string | null>(null);
  const [rejectNote, setRejectNote] = useState("");
  const [bulkFeedback, setBulkFeedback] = useState<string | null>(null);

  return (
    <Layout>
      <div data-testid="review-queue" style={{ maxWidth: 800 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Review Queue</h1>
          {data?.items?.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {bulkFeedback && (
                <span style={{ fontSize: 12, color: "var(--ok)", fontWeight: 600 }}>{bulkFeedback}</span>
              )}
              <button
                onClick={() =>
                  bulkApprove.mutate("all", {
                    onSuccess: (res) => {
                      setBulkFeedback(`${res.approved} rule${res.approved !== 1 ? "s" : ""} approved`);
                      setTimeout(() => setBulkFeedback(null), 3000);
                    },
                  })
                }
                disabled={bulkApprove.isPending}
                style={{
                  padding: "8px 16px", border: "1px solid var(--ok)",
                  background: "var(--ok-soft)", color: "var(--ok)",
                  borderRadius: 999, fontSize: 13, fontWeight: 600,
                  cursor: "pointer", fontFamily: "var(--font-sans)",
                  opacity: bulkApprove.isPending ? 0.6 : 1,
                }}
              >
                Approve all ({data.items.length})
              </button>
            </div>
          )}
        </div>
        {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}
        {data?.items?.length === 0 && !isLoading && (
          <p style={{ color: "var(--ink3)", fontSize: 13 }}>No rules pending review.</p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {data?.items?.map((rule: any) => (
            <div key={rule.id} style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "18px 20px" }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>{rule.title}</h3>
                  {rule.definition && (
                    <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--ink2)", lineHeight: 1.5 }}>
                      {rule.definition.slice(0, 200)}{rule.definition.length > 200 ? "…" : ""}
                    </p>
                  )}
                  <p style={{ margin: "6px 0 0", fontSize: 12, color: "var(--ink3)" }}>
                    Proposed {new Date(rule.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8, marginLeft: 16 }}>
                  <button
                    onClick={() => approve(rule.id)}
                    style={{
                      padding: "7px 14px", border: 0, borderRadius: 999,
                      background: "var(--accent)", color: "#fff",
                      fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "var(--font-sans)",
                    }}
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => setRejecting(rule.id)}
                    style={{
                      padding: "7px 14px", border: "1px solid var(--danger)",
                      borderRadius: 999, background: "var(--danger-soft)",
                      color: "var(--danger)", fontSize: 13, cursor: "pointer", fontFamily: "var(--font-sans)",
                    }}
                  >
                    Reject
                  </button>
                </div>
              </div>

              {rejecting === rule.id && (
                <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                  <input
                    value={rejectNote}
                    onChange={(e) => setRejectNote(e.target.value)}
                    placeholder="Rejection reason…"
                    style={{
                      flex: 1, padding: "8px 12px", border: "1px solid var(--line)",
                      borderRadius: 8, fontSize: 13, fontFamily: "var(--font-sans)",
                      background: "var(--panel)", color: "var(--ink)", outline: "none",
                    }}
                  />
                  <button
                    onClick={() => { reject({ ruleId: rule.id, note: rejectNote }); setRejecting(null); setRejectNote(""); }}
                    style={{ padding: "7px 14px", border: 0, borderRadius: 999, background: "var(--danger)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "var(--font-sans)" }}
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setRejecting(null)}
                    style={{ padding: "7px 14px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 13, cursor: "pointer", fontFamily: "var(--font-sans)" }}
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
