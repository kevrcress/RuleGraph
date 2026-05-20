import { useState } from "react";
import { Link } from "react-router-dom";
import { useRules } from "../../api/rules";
import Layout from "../../components/Layout";

const STATUS_COLORS: Record<string, string> = {
  active: "text-green-400",
  approved: "text-blue-400",
  proposed: "text-yellow-400",
  drift: "text-orange-400",
  needs_update: "text-orange-400",
  deprecated: "text-bone-4",
  under_review: "text-purple-400",
};

export default function RuleBrowser() {
  const [search, setSearch] = useState("");
  const [page] = useState(1);
  const { data, isLoading, isError } = useRules(page, 50, search);

  return (
    <Layout>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-serif text-bone-0">Business Rules</h1>
        <Link
          to="/rules/new"
          className="px-3 py-1 bg-brass-0 text-ink-0 rounded text-sm font-semibold hover:bg-brass-1"
        >
          + Propose Rule
        </Link>
      </div>

      <div className="mb-4">
        <input
          data-testid="search-input"
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search rules…"
          className="w-full max-w-md bg-ink-2 border border-bone-4 rounded px-3 py-2 text-bone-0 placeholder-bone-4 focus:outline-none focus:border-brass-0 text-sm"
        />
      </div>

      {isLoading && (
        <div className="text-bone-3 text-sm">Loading rules…</div>
      )}

      {isError && (
        <div className="text-ember text-sm">Failed to load rules.</div>
      )}

      <ul data-testid="rule-list" className="space-y-2">
        {data?.items.map((rule) => (
          <li
            key={rule.id}
            data-testid="rule-item"
            className="bg-ink-2 border border-bone-4 rounded-lg p-4 hover:border-brass-1 transition-colors"
          >
            <Link to={`/rules/${rule.id}`} className="block">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-bone-0 font-medium">{rule.title}</h3>
                  {rule.source_type && (
                    <span className="text-xs text-bone-3 mt-0.5 block">{rule.source_type}</span>
                  )}
                </div>
                <span
                  className={`text-xs font-medium ${STATUS_COLORS[rule.status] || "text-bone-3"}`}
                >
                  {rule.status}
                </span>
              </div>
              <div className="mt-2 flex items-center gap-4 text-xs text-bone-3">
                {rule.extraction_confidence != null && (
                  <span>Confidence: {Math.round(rule.extraction_confidence * 100)}%</span>
                )}
                {rule.created_at && (
                  <span>{new Date(rule.created_at).toLocaleDateString()}</span>
                )}
              </div>
            </Link>
          </li>
        ))}
        {data?.items.length === 0 && !isLoading && (
          <li className="text-bone-3 text-sm py-4 text-center">No rules found.</li>
        )}
      </ul>

      {data && data.total > 50 && (
        <div className="mt-4 text-xs text-bone-3">
          Showing {data.items.length} of {data.total} rules
        </div>
      )}
    </Layout>
  );
}
