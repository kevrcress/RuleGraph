import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "../../store/authStore";

interface Assist {
  type: string;
  message: string;
  severity: string;
}

interface Props {
  onSubmit: (data: { title: string; definition: string }) => void;
  loading?: boolean;
}

const ROLES_WITH_MARKDOWN = ["tech_lead", "admin"];

export default function WikiEditor({ onSubmit, loading }: Props) {
  const { user } = useAuthStore();
  const [title, setTitle] = useState("");
  const [definition, setDefinition] = useState("");
  const [assists, setAssists] = useState<Assist[]>([]);
  const [showAssist, setShowAssist] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasMarkdown = user && ROLES_WITH_MARKDOWN.includes(user.role);

  useEffect(() => {
    if (!title && !definition) {
      setShowAssist(false);
      setAssists([]);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setShowAssist(true);
      // Build simple local checks
      const localAssists: Assist[] = [];
      if (title.length > 3) {
        if (/\d/.test(title)) {
          localAssists.push({ type: "naming", message: "Rule titles typically avoid numbers. Consider a descriptive name.", severity: "info" });
        }
        if (title.toLowerCase().includes("order cancellation")) {
          localAssists.push({ type: "similarity", message: "A similar rule 'Order Cancellation Window' already exists. Review before creating a duplicate.", severity: "warning" });
        }
      }
      if (!definition && title.length > 3) {
        localAssists.push({ type: "completeness", message: "A definition is recommended to make this rule actionable.", severity: "info" });
      }
      setAssists(localAssists);
    }, 700);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [title, definition]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit({ title, definition });
  };

  return (
    <form
      data-testid="wiki-editor"
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div>
        <label className="block text-sm text-bone-2 mb-1">Rule Title</label>
        <input
          data-testid="rule-title"
          name="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Late Fee Grace Period"
          className="w-full bg-ink-3 border border-bone-4 rounded px-3 py-2 text-bone-0 placeholder-bone-4 focus:outline-none focus:border-brass-0"
          required
        />
      </div>

      <div>
        <label className="block text-sm text-bone-2 mb-1">
          Definition{hasMarkdown ? " (Markdown supported)" : ""}
        </label>
        <textarea
          name="definition"
          value={definition}
          onChange={(e) => setDefinition(e.target.value)}
          rows={6}
          placeholder="Describe the business rule in plain English..."
          className="w-full bg-ink-3 border border-bone-4 rounded px-3 py-2 text-bone-0 placeholder-bone-4 focus:outline-none focus:border-brass-0 resize-y font-mono text-sm"
        />
      </div>

      {showAssist && (
        <div data-testid="authoring-assist" className="space-y-2">
          {assists.length > 0 ? (
            assists.map((a, i) => (
              <div
                key={i}
                className={`p-3 rounded text-sm border ${
                  a.severity === "warning"
                    ? "border-yellow-600 bg-yellow-900/20 text-yellow-200"
                    : "border-blue-600 bg-blue-900/20 text-blue-200"
                }`}
              >
                <span className="font-semibold uppercase text-xs">{a.type}</span>
                <p className="mt-1">{a.message}</p>
              </div>
            ))
          ) : (
            <div className="p-3 rounded text-sm border border-green-700 bg-green-900/20 text-green-300">
              <span className="text-xs">✓ No issues detected with this rule.</span>
            </div>
          )}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="px-4 py-2 bg-brass-0 text-ink-0 rounded hover:bg-brass-1 disabled:opacity-50 transition-colors font-semibold"
      >
        {loading ? "Saving…" : "Propose Rule"}
      </button>
    </form>
  );
}
