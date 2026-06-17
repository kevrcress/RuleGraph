import { useState } from "react";
import { Link } from "react-router-dom";
import { ThumbsUp, ThumbsDown, ChevronUp, ChevronDown, CheckSquare, Square } from "lucide-react";
import { useRules } from "../../api/rules";
import { useFeedback } from "../../api/feedback";
import { useBulkApproveRules } from "../../api/admin";
import { useAuthStore } from "../../store/authStore";
import Layout from "../../components/Layout";
import StatusBadge from "../../components/StatusBadge";

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value > 0.85 ? "var(--ok)" : value > 0.7 ? "var(--warn)" : "var(--danger)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ width: 80, height: 5, background: "var(--panel2)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 999 }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", fontVariantNumeric: "tabular-nums" }}>
        {pct}%
      </span>
    </div>
  );
}

function QuickFeedback({ ruleId }: { ruleId: string }) {
  const feedback = useFeedback();
  const [sent, setSent] = useState<string | null>(null);

  const send = (e: React.MouseEvent, signal_type: string) => {
    e.preventDefault();
    e.stopPropagation();
    feedback.mutate({ signal_type, rule_id: ruleId });
    setSent(signal_type);
  };

  const btnStyle = (active: boolean): React.CSSProperties => ({
    width: 32, height: 32, border: "1px solid var(--line)",
    background: "var(--panel)", borderRadius: 999,
    display: "grid", placeItems: "center", cursor: "pointer",
    color: active ? "var(--accent)" : "var(--ink3)",
    transition: "color 150ms",
  });

  return (
    <div style={{ display: "flex", gap: 4 }}>
      <button aria-label="Helpful" style={btnStyle(sent === "thumbs_up")} onClick={(e) => send(e, "thumbs_up")}>
        <ThumbsUp size={13} />
      </button>
      <button aria-label="Not helpful" style={btnStyle(sent === "thumbs_down")} onClick={(e) => send(e, "thumbs_down")}>
        <ThumbsDown size={13} />
      </button>
    </div>
  );
}

const STAT_CARDS = [
  { key: "verified",  label: "Verified",       color: "var(--ok)",     sub: "of catalog" },
  { key: "drift",     label: "Drift detected", color: "var(--warn)",   sub: "reviewing" },
  { key: "conflict",  label: "Conflicts",      color: "var(--danger)", sub: "high severity" },
  { key: "proposed",  label: "Proposed",       color: "var(--info)",   sub: "awaiting review" },
];

type SortKey = "created_at" | "title" | "confidence";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "created_at", label: "Date" },
  { key: "title",      label: "Name" },
  { key: "confidence", label: "Confidence" },
];

export default function RuleBrowser() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<SortKey>("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkFeedback, setBulkFeedback] = useState<string | null>(null);
  const limit = 200;

  const { data, isLoading, isError } = useRules(page, limit, search, sort, order);
  const bulkApprove = useBulkApproveRules();
  const { user } = useAuthStore();
  const canApprove = user?.role === "admin" || user?.role === "business_admin";

  const toggleSort = (key: SortKey) => {
    if (sort === key) {
      setOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSort(key);
      setOrder(key === "title" ? "asc" : "desc");
    }
    setPage(1);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllVisible = () => {
    setSelectedIds(new Set(data?.items.map((r) => r.id) ?? []));
  };

  const selectAllProposed = () => {
    setSelectedIds(new Set((data?.items ?? []).filter((r) => r.status === "proposed").map((r) => r.id)));
  };

  const clearSelection = () => setSelectedIds(new Set());

  const handleBulkApprove = (which: "selected" | "all") => {
    const ids = which === "all" ? "all" : Array.from(selectedIds);
    bulkApprove.mutate(ids, {
      onSuccess: (res) => {
        setBulkFeedback(`${res.approved} rule${res.approved !== 1 ? "s" : ""} approved`);
        clearSelection();
        setTimeout(() => setBulkFeedback(null), 3000);
      },
    });
  };

  const counts = {
    verified: data?.items.filter((r) => r.status === "verified" || r.status === "approved").length ?? 0,
    drift:    data?.items.filter((r) => r.status === "drift").length ?? 0,
    conflict: data?.items.filter((r) => r.status === "conflict").length ?? 0,
    proposed: data?.items.filter((r) => r.status === "proposed").length ?? 0,
  };

  const allVisibleSelected = !!data?.items.length && data.items.every((r) => selectedIds.has(r.id));
  const someSelected = selectedIds.size > 0;

  return (
    <Layout>
      {/* Hero */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 30, fontWeight: 600, letterSpacing: "-0.022em" }}>
            Business rules
          </h1>
          {data && (
            <div style={{ color: "var(--ink2)", marginTop: 6, fontSize: 14 }}>
              {data.total} rules in catalog
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {canApprove && counts.proposed > 0 && (
            <button
              onClick={() => handleBulkApprove("all")}
              disabled={bulkApprove.isPending}
              style={{
                border: "1px solid var(--ok)", background: "var(--ok-soft)", color: "var(--ok)",
                padding: "8px 16px", borderRadius: 999, fontSize: 13, fontWeight: 600,
                cursor: "pointer", fontFamily: "var(--font-sans)",
                opacity: bulkApprove.isPending ? 0.6 : 1,
              }}
            >
              Approve all proposed ({counts.proposed})
            </button>
          )}
          <Link
            to="/rules/new"
            style={{
              border: 0, background: "var(--accent)", color: "#fff",
              padding: "8px 16px", borderRadius: 999, fontSize: 13, fontWeight: 600,
              textDecoration: "none", display: "inline-block",
            }}
          >
            + Propose a rule
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 22 }}>
        {STAT_CARDS.map((s) => (
          <div
            key={s.key}
            style={{
              background: "var(--panel)", border: "1px solid var(--line)",
              borderRadius: 10, padding: "16px 18px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: s.color }} />
              <span style={{ fontSize: 13, color: "var(--ink2)", fontWeight: 500 }}>{s.label}</span>
            </div>
            <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.025em" }}>
              {counts[s.key as keyof typeof counts]}
            </div>
            <div style={{ fontSize: 12, color: "var(--ink3)", marginTop: 2 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Search + sort */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <div
          style={{
            flex: 1, display: "flex", alignItems: "center", gap: 10,
            background: "var(--panel)", border: "1px solid var(--line)",
            borderRadius: 999, padding: "10px 16px",
          }}
        >
          <svg width="15" height="15" viewBox="0 0 14 14" fill="none" stroke="var(--ink3)" strokeWidth="1.5">
            <circle cx="6" cy="6" r="4" />
            <path d="M9 9L12 12" />
          </svg>
          <input
            data-testid="search-input"
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Ask a question or search for a rule…"
            style={{
              flex: 1, border: 0, outline: "none",
              background: "transparent", color: "var(--ink)",
              fontSize: 14, fontFamily: "var(--font-sans)",
            }}
          />
          <span style={{ color: "var(--ink4)", fontSize: 11, fontFamily: "var(--font-mono)", background: "var(--panel2)", padding: "2px 7px", borderRadius: 4 }}>⌘K</span>
        </div>

        {/* Sort controls */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {SORT_OPTIONS.map(({ key, label }) => {
            const active = sort === key;
            return (
              <button
                key={key}
                onClick={() => toggleSort(key)}
                style={{
                  display: "flex", alignItems: "center", gap: 4,
                  padding: "8px 13px", borderRadius: 999,
                  border: "1px solid var(--line)",
                  background: active ? "var(--panel2)" : "var(--panel)",
                  color: active ? "var(--ink)" : "var(--ink3)",
                  fontSize: 13, fontWeight: active ? 600 : 400,
                  cursor: "pointer", fontFamily: "var(--font-sans)",
                }}
              >
                {label}
                {active && (order === "desc"
                  ? <ChevronDown size={12} />
                  : <ChevronUp size={12} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Bulk action bar */}
      {canApprove && (someSelected || data?.items.length) && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          background: "var(--panel)", border: "1px solid var(--line)",
          borderRadius: 8, padding: "9px 14px", marginBottom: 12,
        }}>
          {/* Select-all toggle */}
          <button
            onClick={allVisibleSelected ? clearSelection : selectAllVisible}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              background: "transparent", border: 0, cursor: "pointer",
              color: "var(--ink2)", fontSize: 13, fontFamily: "var(--font-sans)", padding: 0,
            }}
          >
            {allVisibleSelected
              ? <CheckSquare size={15} color="var(--accent)" />
              : <Square size={15} color="var(--ink3)" />
            }
            {allVisibleSelected ? "Deselect all" : "Select all"}
          </button>

          {someSelected && (
            <>
              <span style={{ color: "var(--line)", userSelect: "none" }}>|</span>
              <span style={{ fontSize: 13, color: "var(--ink2)" }}>
                {selectedIds.size} selected
              </span>
              <button
                onClick={() => selectAllProposed()}
                style={{
                  background: "transparent", border: "1px solid var(--line)",
                  borderRadius: 999, padding: "4px 10px",
                  fontSize: 12, color: "var(--ink3)", cursor: "pointer",
                  fontFamily: "var(--font-sans)",
                }}
              >
                Select all proposed
              </button>
              <button
                onClick={() => handleBulkApprove("selected")}
                disabled={bulkApprove.isPending}
                style={{
                  background: "var(--ok)", border: 0, borderRadius: 999,
                  padding: "5px 12px", fontSize: 12, fontWeight: 600,
                  color: "#fff", cursor: "pointer", fontFamily: "var(--font-sans)",
                  opacity: bulkApprove.isPending ? 0.6 : 1,
                }}
              >
                Approve selected
              </button>
              <button
                onClick={clearSelection}
                style={{
                  background: "transparent", border: 0,
                  fontSize: 12, color: "var(--ink3)", cursor: "pointer",
                  fontFamily: "var(--font-sans)", padding: "4px 6px",
                }}
              >
                Clear
              </button>
            </>
          )}

          {bulkFeedback && (
            <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--ok)", fontWeight: 600 }}>
              {bulkFeedback}
            </span>
          )}
        </div>
      )}

      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading rules…</div>}
      {isError  && <div style={{ color: "var(--danger)", fontSize: 13 }}>Failed to load rules.</div>}

      {/* Rule cards */}
      <div data-testid="rule-list" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {data?.items.map((rule) => {
          const isSelected = selectedIds.has(rule.id);
          return (
            <div
              key={rule.id}
              data-testid="rule-item"
              style={{
                background: isSelected ? "var(--accent-soft, color-mix(in srgb, var(--accent) 8%, var(--panel)))" : "var(--panel)",
                border: `1px solid ${isSelected ? "var(--accent)" : "var(--line)"}`,
                borderRadius: 10,
                display: "flex", alignItems: "center",
                transition: "border-color 150ms, background 150ms",
              }}
            >
              {/* Checkbox */}
              <div
                onClick={() => toggleSelect(rule.id)}
                style={{
                  padding: "14px 4px 14px 14px",
                  cursor: "pointer", flexShrink: 0,
                  display: "flex", alignItems: "center",
                }}
              >
                {isSelected
                  ? <CheckSquare size={16} color="var(--accent)" />
                  : <Square size={16} color="var(--ink4)" />
                }
              </div>

              {/* Main content (navigates to rule) */}
              <Link
                to={`/rules/${rule.id}`}
                style={{ flex: 1, textDecoration: "none", color: "inherit", display: "flex", alignItems: "center", gap: 18, padding: "14px 10px 14px 10px" }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-0.01em" }}>{rule.title}</span>
                    <StatusBadge status={rule.status} />
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--ink3)", display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--ink2)", fontSize: 12 }}>{rule.id}</span>
                    {rule.source_type && (
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 11.5 }}>{rule.source_type}</span>
                    )}
                    {rule.created_at && (
                      <span>{new Date(rule.created_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>

                {rule.extraction_confidence != null && (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                    <div style={{ fontSize: 11, color: "var(--ink3)" }}>Confidence</div>
                    <ConfidenceBar value={rule.extraction_confidence} />
                  </div>
                )}
              </Link>

              {/* Feedback (outside link to prevent nav on click) */}
              <div style={{ padding: "0 14px" }}>
                <QuickFeedback ruleId={rule.id} />
              </div>
            </div>
          );
        })}
        {data?.items.length === 0 && !isLoading && (
          <div style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: 24 }}>
            No rules found.
          </div>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > limit && (
        <div style={{ marginTop: 18, display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{
              padding: "7px 14px", borderRadius: 999, border: "1px solid var(--line)",
              background: "var(--panel)", color: page === 1 ? "var(--ink4)" : "var(--ink2)",
              fontSize: 13, cursor: page === 1 ? "default" : "pointer", fontFamily: "var(--font-sans)",
            }}
          >
            ← Prev
          </button>
          <span style={{ fontSize: 13, color: "var(--ink3)" }}>
            Page {page} of {Math.ceil(data.total / limit)} · {data.total} rules
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * limit >= data.total}
            style={{
              padding: "7px 14px", borderRadius: 999, border: "1px solid var(--line)",
              background: "var(--panel)", color: page * limit >= data.total ? "var(--ink4)" : "var(--ink2)",
              fontSize: 13, cursor: page * limit >= data.total ? "default" : "pointer", fontFamily: "var(--font-sans)",
            }}
          >
            Next →
          </button>
        </div>
      )}
      {data && data.total <= limit && data.total > 0 && (
        <div style={{ marginTop: 14, fontSize: 12, color: "var(--ink3)", textAlign: "center" }}>
          {data.total} rule{data.total !== 1 ? "s" : ""} total
        </div>
      )}
    </Layout>
  );
}
