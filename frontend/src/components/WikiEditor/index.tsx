import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "../../store/authStore";

interface Assist { type: string; message: string; severity: string }
interface Props { onSubmit: (data: { title: string; definition: string }) => void; loading?: boolean }

const ROLES_WITH_MARKDOWN = ["tech_lead", "admin"];

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 12px",
  border: "1px solid var(--line)", borderRadius: 8,
  fontSize: 14, fontFamily: "var(--font-sans)",
  background: "var(--panel)", color: "var(--ink)", outline: "none",
};

export default function WikiEditor({ onSubmit, loading }: Props) {
  const { user } = useAuthStore();
  const [title, setTitle] = useState("");
  const [definition, setDefinition] = useState("");
  const [assists, setAssists] = useState<Assist[]>([]);
  const [showAssist, setShowAssist] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasMarkdown = user && ROLES_WITH_MARKDOWN.includes(user.role);

  useEffect(() => {
    if (!title && !definition) { setShowAssist(false); setAssists([]); return; }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setShowAssist(true);
      const localAssists: Assist[] = [];
      if (title.length > 3 && /\d/.test(title))
        localAssists.push({ type: "naming", message: "Rule titles typically avoid numbers. Consider a descriptive name.", severity: "info" });
      if (title.toLowerCase().includes("order cancellation"))
        localAssists.push({ type: "similarity", message: "A similar rule 'Order Cancellation Window' already exists. Review before creating a duplicate.", severity: "warning" });
      if (!definition && title.length > 3)
        localAssists.push({ type: "completeness", message: "A definition is recommended to make this rule actionable.", severity: "info" });
      setAssists(localAssists);
    }, 700);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [title, definition]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit({ title, definition });
  };

  return (
    <form data-testid="wiki-editor" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div>
        <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--ink)", marginBottom: 6 }}>Rule Title</label>
        <input
          data-testid="rule-title"
          name="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Late Fee Grace Period"
          required
          style={inputStyle}
        />
      </div>

      <div>
        <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--ink)", marginBottom: 6 }}>
          Definition{hasMarkdown ? " (Markdown supported)" : ""}
        </label>
        <textarea
          name="definition"
          value={definition}
          onChange={(e) => setDefinition(e.target.value)}
          rows={6}
          placeholder="Describe the business rule in plain English…"
          style={{ ...inputStyle, fontFamily: "var(--font-mono)", fontSize: 13, resize: "vertical" }}
        />
      </div>

      {showAssist && (
        <div data-testid="authoring-assist" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {assists.length > 0 ? assists.map((a, i) => (
            <div
              key={i}
              style={{
                padding: "10px 14px", borderRadius: 8, fontSize: 13,
                border: `1px solid ${a.severity === "warning" ? "var(--warn)" : "var(--info)"}`,
                background: a.severity === "warning" ? "var(--warn-soft)" : "var(--info-soft)",
                color: a.severity === "warning" ? "var(--warn)" : "var(--info)",
              }}
            >
              <span style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{a.type}</span>
              <p style={{ margin: "4px 0 0" }}>{a.message}</p>
            </div>
          )) : (
            <div style={{ padding: "10px 14px", borderRadius: 8, fontSize: 13, border: "1px solid var(--ok)", background: "var(--ok-soft)", color: "var(--ok)" }}>
              ✓ No issues detected with this rule.
            </div>
          )}
        </div>
      )}

      <div>
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "9px 20px", border: 0, borderRadius: 999,
            background: loading ? "var(--accent-soft)" : "var(--accent)",
            color: loading ? "var(--accent-deep)" : "#fff",
            fontSize: 14, fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            fontFamily: "var(--font-sans)",
          }}
        >
          {loading ? "Saving…" : "Propose Rule"}
        </button>
      </div>
    </form>
  );
}
