interface DiffPanelProps {
  before: string | null;
  after: string | null;
  title?: string;
}

function highlight(text: string, tone: "remove" | "add") {
  const styles: React.CSSProperties = {
    whiteSpace: "pre-wrap", fontSize: 13, padding: "12px 14px",
    borderRadius: 8, fontFamily: "var(--font-mono)", minHeight: 80,
    background: tone === "remove" ? "var(--danger-soft)" : "var(--ok-soft)",
    color: tone === "remove" ? "var(--danger)" : "var(--ok)",
    border: `1px solid ${tone === "remove" ? "var(--danger)" : "var(--ok)"}`,
    opacity: 0.85,
  };
  return <pre style={styles}>{text}</pre>;
}

export default function RuleDiff({ before, after, title }: DiffPanelProps) {
  return (
    <div data-testid="diff-panel" style={{ width: "100%" }}>
      {title && <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>{title}</h3>}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div>
          <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 8 }}>Before</div>
          <div data-testid="diff-before">
            {before ? highlight(before, "remove") : (
              <div style={{ color: "var(--ink4)", fontSize: 13, fontStyle: "italic", padding: 12 }}>No previous version</div>
            )}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 8 }}>After</div>
          <div data-testid="diff-after">
            {after ? highlight(after, "add") : (
              <div style={{ color: "var(--ink4)", fontSize: 13, fontStyle: "italic", padding: 12 }}>No current version</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
