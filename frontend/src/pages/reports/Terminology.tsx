import { useState, useMemo } from "react";
import {
  useTerminology,
  useInferDefinition,
  useUpdateDefinition,
  useRescanTerminology,
} from "../../api/admin";
import Layout from "../../components/Layout";

type Term = {
  id: string;
  canonical_term: string | null;
  variants: string[];
  services: string[];
  status: string | null;
  is_issue: boolean;
  definition: string | null;
  definition_confidence: number | null;
  definition_status: string | null; // draft | accepted | edited | null
};

const FILTERS = ["All", "Issues", "Clean"] as const;
type Filter = (typeof FILTERS)[number];

export default function Terminology() {
  const [filter, setFilter] = useState<Filter>("All");
  const [search, setSearch] = useState("");
  const [rescanResult, setRescanResult] = useState<{
    terms_added: number; services_scanned: number
  } | null>(null);

  const { data, isLoading } = useTerminology(1, false);
  const rescanMutation = useRescanTerminology();
  const items: Term[] = data?.items ?? [];
  const issueCount = items.filter((t) => t.is_issue).length;

  const filtered = useMemo(() => {
    let list = items;
    if (filter === "Issues") list = list.filter((t) => t.is_issue);
    if (filter === "Clean") list = list.filter((t) => !t.is_issue);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (t) =>
          t.canonical_term?.toLowerCase().includes(q) ||
          t.variants.some((v) => v.toLowerCase().includes(q)) ||
          t.services.some((s) => s.toLowerCase().includes(q))
      );
    }
    return list;
  }, [items, filter, search]);

  const grouped = useMemo(() => {
    const map = new Map<string, Term[]>();
    for (const t of filtered) {
      const letter = (t.canonical_term ?? t.variants[0] ?? "?")[0].toUpperCase();
      if (!map.has(letter)) map.set(letter, []);
      map.get(letter)!.push(t);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, gap: 12, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>
            Terminology
          </h1>
          {issueCount > 0 && (
            <span
              style={{
                fontSize: 12, fontWeight: 500,
                background: "rgba(239,68,68,0.1)", color: "#dc2626",
                borderRadius: 99, padding: "2px 10px",
              }}
            >
              {issueCount} {issueCount === 1 ? "issue" : "issues"}
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {rescanResult && (
            <span style={{ fontSize: 12, color: "var(--ink3)" }}>
              {rescanResult.terms_added > 0
                ? `+${rescanResult.terms_added} new term${rescanResult.terms_added !== 1 ? "s" : ""} found`
                : `No new terms found`}
              {" "}across {rescanResult.services_scanned} service{rescanResult.services_scanned !== 1 ? "s" : ""}
            </span>
          )}
          <ActionButton
            onClick={() =>
              rescanMutation.mutate(undefined, {
                onSuccess: (r) => setRescanResult(r),
              })
            }
            disabled={rescanMutation.isPending}
            variant="ghost"
          >
            {rescanMutation.isPending ? "Scanning…" : "Rescan"}
          </ActionButton>
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
        <input
          type="search"
          placeholder="Search terms, variants, services…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: "1 1 220px", padding: "7px 12px", borderRadius: 8,
            border: "1px solid var(--line)", background: "var(--panel)",
            color: "var(--ink1)", fontSize: 13, outline: "none",
          }}
        />
        <div style={{ display: "flex", gap: 6 }}>
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: "7px 14px", borderRadius: 8, border: "1px solid var(--line)",
                background: filter === f ? "var(--accent)" : "var(--panel)",
                color: filter === f ? "#fff" : "var(--ink2)",
                fontSize: 13, fontWeight: 500, cursor: "pointer",
              }}
            >
              {f}
              {f === "Issues" && issueCount > 0 && (
                <span style={{ marginLeft: 6, opacity: 0.85 }}>({issueCount})</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}

      {!isLoading && filtered.length === 0 && (
        <div style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: 48 }}>
          {search || filter !== "All"
            ? "No terms match your filter."
            : "No terminology found. Ingest some sources to populate the glossary."}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {grouped.map(([letter, terms]) => (
          <div key={letter}>
            <div
              style={{
                fontSize: 11, fontWeight: 600, letterSpacing: "0.08em",
                color: "var(--ink4)", textTransform: "uppercase",
                marginBottom: 8, paddingBottom: 4, borderBottom: "1px solid var(--line)",
              }}
            >
              {letter}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {terms.map((t) => <TermCard key={t.id} term={t} />)}
            </div>
          </div>
        ))}
      </div>
    </Layout>
  );
}

// ─── Term card ───────────────────────────────────────────────────────────────

function TermCard({ term }: { term: Term }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(term.definition ?? "");

  const inferMutation = useInferDefinition();
  const updateMutation = useUpdateDefinition();

  const displayName = term.canonical_term ?? term.variants[0] ?? "(unnamed)";
  const isPending = inferMutation.isPending || updateMutation.isPending;

  function handleAccept() {
    updateMutation.mutate({ termId: term.id, definition_status: "accepted" });
  }

  function handleSaveEdit() {
    updateMutation.mutate(
      { termId: term.id, definition: draft, definition_status: "edited" },
      { onSuccess: () => setEditing(false) }
    );
  }

  function handleInfer() {
    inferMutation.mutate(term.id, {
      onSuccess: () => setEditing(false),
    });
  }

  return (
    <div
      style={{
        background: "var(--panel)",
        border: `1px solid ${term.is_issue ? "rgba(239,68,68,0.3)" : "var(--line)"}`,
        borderRadius: 10,
        padding: "12px 16px",
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
      }}
    >
      {/* Issue accent bar */}
      <div
        style={{
          width: 4, borderRadius: 99, alignSelf: "stretch", flexShrink: 0,
          background: term.is_issue ? "#ef4444" : "var(--line)",
        }}
      />

      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Title row */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink1)" }}>
            {displayName}
          </span>
          {term.is_issue && (
            <Badge color="red" label="CONFLICT" />
          )}
          {term.definition_status === "accepted" && (
            <Badge color="green" label="accepted" />
          )}
          {term.definition_status === "edited" && (
            <Badge color="blue" label="edited" />
          )}
          {term.definition_status === "draft" && (
            <Badge color="gray" label="draft" />
          )}
        </div>

        {/* Variants */}
        {term.variants.length > 0 && (
          <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 4 }}>
            {term.variants.map((v) => (
              <span
                key={v}
                style={{
                  fontSize: 12, background: "var(--surface)",
                  border: "1px solid var(--line)", borderRadius: 6,
                  padding: "1px 8px", color: "var(--ink2)", fontFamily: "monospace",
                }}
              >
                {v}
              </span>
            ))}
          </div>
        )}

        {/* Services */}
        {term.services.length > 0 && (
          <div style={{ marginTop: 5, display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "var(--ink4)", marginRight: 2 }}>in</span>
            {term.services.map((s) => (
              <span
                key={s}
                style={{
                  fontSize: 11, fontWeight: 500,
                  background: "rgba(99,102,241,0.08)", color: "var(--accent)",
                  borderRadius: 6, padding: "1px 7px",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        )}

        {/* Definition section */}
        <div style={{ marginTop: 10 }}>
          {editing ? (
            <EditDefinition
              value={draft}
              onChange={setDraft}
              onSave={handleSaveEdit}
              onCancel={() => { setEditing(false); setDraft(term.definition ?? ""); }}
              saving={isPending}
            />
          ) : term.definition ? (
            <ExistingDefinition
              definition={term.definition}
              confidence={term.definition_confidence}
              status={term.definition_status}
              onAccept={term.definition_status !== "accepted" ? handleAccept : undefined}
              onEdit={() => { setDraft(term.definition ?? ""); setEditing(true); }}
              onReInfer={handleInfer}
              busy={isPending}
            />
          ) : (
            <NoDefinition onInfer={handleInfer} busy={inferMutation.isPending} />
          )}
          {inferMutation.isError && (
            <p style={{ margin: "4px 0 0", fontSize: 11, color: "#dc2626" }}>
              Inference failed — check API key or try again.
            </p>
          )}
        </div>

        {term.is_issue && term.variants.length > 1 && (
          <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--ink3)" }}>
            Different names for the same concept across services — consider standardising on one term.
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Badge({
  label,
  color,
}: {
  label: string;
  color: "red" | "green" | "blue" | "gray";
}) {
  const colors = {
    red: { bg: "rgba(239,68,68,0.1)", text: "#dc2626" },
    green: { bg: "rgba(34,197,94,0.12)", text: "#16a34a" },
    blue: { bg: "rgba(59,130,246,0.12)", text: "#2563eb" },
    gray: { bg: "rgba(107,114,128,0.1)", text: "var(--ink3)" },
  };
  const { bg, text } = colors[color];
  return (
    <span
      style={{
        fontSize: 11, fontWeight: 600,
        background: bg, color: text,
        borderRadius: 6, padding: "1px 7px", letterSpacing: "0.03em",
      }}
    >
      {label.toUpperCase()}
    </span>
  );
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 75 ? "#16a34a" : pct >= 50 ? "#d97706" : "#dc2626";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div
        style={{
          width: 64, height: 4, borderRadius: 99,
          background: "var(--line)", overflow: "hidden",
        }}
      >
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 99 }} />
      </div>
      <span style={{ fontSize: 11, color: "var(--ink3)" }}>{pct}% confidence</span>
    </div>
  );
}

function ExistingDefinition({
  definition,
  confidence,
  status,
  onAccept,
  onEdit,
  onReInfer,
  busy,
}: {
  definition: string;
  confidence: number | null;
  status: string | null;
  onAccept?: () => void;
  onEdit: () => void;
  onReInfer: () => void;
  busy: boolean;
}) {
  return (
    <div>
      <p
        style={{
          margin: 0, fontSize: 13, color: "var(--ink2)", lineHeight: 1.55,
          fontStyle: status === "draft" ? "italic" : "normal",
        }}
      >
        {definition}
      </p>
      <div
        style={{
          marginTop: 8, display: "flex", alignItems: "center",
          gap: 10, flexWrap: "wrap",
        }}
      >
        {confidence !== null && status === "draft" && (
          <ConfidenceBar confidence={confidence} />
        )}
        <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
          {onAccept && (
            <ActionButton onClick={onAccept} disabled={busy} variant="accept">
              Accept
            </ActionButton>
          )}
          <ActionButton onClick={onEdit} disabled={busy} variant="ghost">
            Edit
          </ActionButton>
          <ActionButton onClick={onReInfer} disabled={busy} variant="ghost">
            ↺ Re-infer
          </ActionButton>
        </div>
      </div>
    </div>
  );
}

function NoDefinition({ onInfer, busy }: { onInfer: () => void; busy: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ fontSize: 12, color: "var(--ink4)", fontStyle: "italic" }}>
        No definition yet
      </span>
      <ActionButton onClick={onInfer} disabled={busy} variant="primary">
        {busy ? "Generating…" : "Get definition"}
      </ActionButton>
    </div>
  );
}

function EditDefinition({
  value,
  onChange,
  onSave,
  onCancel,
  saving,
}: {
  value: string;
  onChange: (v: string) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        style={{
          width: "100%", padding: "8px 10px", borderRadius: 8,
          border: "1px solid var(--accent)", background: "var(--surface)",
          color: "var(--ink1)", fontSize: 13, resize: "vertical",
          outline: "none", boxSizing: "border-box",
        }}
      />
      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
        <ActionButton onClick={onCancel} disabled={saving} variant="ghost">
          Cancel
        </ActionButton>
        <ActionButton onClick={onSave} disabled={saving || !value.trim()} variant="accept">
          {saving ? "Saving…" : "Save"}
        </ActionButton>
      </div>
    </div>
  );
}

function ActionButton({
  children,
  onClick,
  disabled,
  variant,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  variant: "primary" | "accept" | "ghost";
}) {
  const styles: Record<string, React.CSSProperties> = {
    primary: {
      background: "var(--accent)", color: "#fff",
      border: "1px solid transparent",
    },
    accept: {
      background: "rgba(34,197,94,0.12)", color: "#16a34a",
      border: "1px solid rgba(34,197,94,0.25)",
    },
    ghost: {
      background: "transparent", color: "var(--ink3)",
      border: "1px solid var(--line)",
    },
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "4px 10px", borderRadius: 6, fontSize: 12,
        fontWeight: 500, cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        ...styles[variant],
      }}
    >
      {children}
    </button>
  );
}
