type RuleStatus =
  | "active" | "verified" | "drift" | "conflict" | "needs_update"
  | "proposed" | "under_review" | "deprecated" | "undocumented"
  | "match" | "missing" | "approved";

const STATUS_CONFIG: Record<RuleStatus, { fg: string; bg: string; label: string }> = {
  active:       { fg: "var(--ok)",     bg: "var(--ok-soft)",      label: "Active" },
  verified:     { fg: "var(--ok)",     bg: "var(--ok-soft)",      label: "Verified" },
  approved:     { fg: "var(--ok)",     bg: "var(--ok-soft)",      label: "Approved" },
  match:        { fg: "var(--ok)",     bg: "var(--ok-soft)",      label: "Match" },
  drift:        { fg: "var(--warn)",   bg: "var(--warn-soft)",    label: "Drift" },
  needs_update: { fg: "var(--warn)",   bg: "var(--warn-soft)",    label: "Needs update" },
  conflict:     { fg: "var(--danger)", bg: "var(--danger-soft)",  label: "Conflict" },
  undocumented: { fg: "var(--danger)", bg: "var(--danger-soft)",  label: "Undocumented" },
  missing:      { fg: "var(--danger)", bg: "var(--danger-soft)",  label: "Missing" },
  proposed:     { fg: "var(--info)",   bg: "var(--info-soft)",    label: "Proposed" },
  under_review: { fg: "var(--info)",   bg: "var(--info-soft)",    label: "Under review" },
  deprecated:   { fg: "var(--ink3)",   bg: "#eeeae0",             label: "Deprecated" },
};

export default function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status as RuleStatus] ?? {
    fg: "var(--ink3)", bg: "#eeeae0", label: status,
  };
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", gap: 5,
        fontSize: 11.5, color: cfg.fg, background: cfg.bg,
        padding: "2px 9px", borderRadius: 999, fontWeight: 500,
        letterSpacing: "0.005em", whiteSpace: "nowrap",
      }}
    >
      <span style={{ width: 5, height: 5, borderRadius: 999, background: cfg.fg, flexShrink: 0 }} />
      {cfg.label}
    </span>
  );
}
