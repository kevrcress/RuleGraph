import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronUp, ChevronDown } from "lucide-react";
import { useWikiPages } from "../../api/wiki";
import Layout from "../../components/Layout";

type SortKey = "updated_at" | "title" | "last_generated_at";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "last_generated_at", label: "Generated" },
  { key: "title",             label: "Name" },
  { key: "updated_at",        label: "Updated" },
];

function ModuleChip({ module }: { module: string }) {
  const parts = module.split("/");
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
      {parts.map((p, i) => (
        <span key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {i > 0 && <span style={{ color: "var(--ink4)", fontSize: 11 }}>/</span>}
          <span style={{
            padding: "2px 8px", borderRadius: 999,
            background: i === 0 ? "var(--accent-soft)" : "var(--panel2)",
            border: `1px solid ${i === 0 ? "var(--accent-soft)" : "var(--line)"}`,
            fontSize: 11, fontFamily: "var(--font-mono)",
            color: i === 0 ? "var(--accent-deep)" : "var(--ink2)",
            fontWeight: i === 0 ? 600 : 400,
          }}>{p}</span>
        </span>
      ))}
    </div>
  );
}

function Snippet({ text }: { text: string }) {
  const plain = text.replace(/#{1,6}\s/g, "").replace(/\*\*/g, "").replace(/\*/g, "");
  const snippet = plain.length > 180 ? plain.slice(0, 177) + "…" : plain;
  return (
    <p style={{ margin: "8px 0 0", fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55 }}>
      {snippet}
    </p>
  );
}

export default function WikiBrowser() {
  const [search, setSearch] = useState("");
  const [page, setPage]     = useState(1);
  const [sort, setSort]     = useState<SortKey>("last_generated_at");
  const [order, setOrder]   = useState<"asc" | "desc">("desc");
  const limit = 50;

  const { data, isLoading, isError } = useWikiPages(page, limit, search, sort, order);

  const toggleSort = (key: SortKey) => {
    if (sort === key) setOrder(o => o === "desc" ? "asc" : "desc");
    else { setSort(key); setOrder(key === "title" ? "asc" : "desc"); }
    setPage(1);
  };

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 30, fontWeight: 600, letterSpacing: "-0.022em" }}>Wiki</h1>
          <p style={{ margin: "6px 0 0", fontSize: 14, color: "var(--ink2)" }}>
            Auto-generated documentation from the knowledge graph.
            {data && <> &nbsp;{data.total} {data.total === 1 ? "page" : "pages"}.</>}
          </p>
        </div>
      </div>

      {/* Search + sort */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 10, background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 999, padding: "10px 16px" }}>
          <svg width="15" height="15" viewBox="0 0 14 14" fill="none" stroke="var(--ink3)" strokeWidth="1.5">
            <circle cx="6" cy="6" r="4" /><path d="M9 9L12 12" />
          </svg>
          <input
            type="text" value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search modules, titles, and content…"
            style={{ flex: 1, border: 0, outline: "none", background: "transparent", color: "var(--ink)", fontSize: 14, fontFamily: "var(--font-sans)" }}
          />
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {SORT_OPTIONS.map(({ key, label }) => {
            const active = sort === key;
            return (
              <button key={key} onClick={() => toggleSort(key)} style={{ display: "flex", alignItems: "center", gap: 4, padding: "8px 13px", borderRadius: 999, border: "1px solid var(--line)", background: active ? "var(--panel2)" : "var(--panel)", color: active ? "var(--ink)" : "var(--ink3)", fontSize: 13, fontWeight: active ? 600 : 400, cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                {label}
                {active && (order === "desc" ? <ChevronDown size={12} /> : <ChevronUp size={12} />)}
              </button>
            );
          })}
        </div>
      </div>

      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading wiki…</div>}
      {isError   && <div style={{ color: "var(--danger)", fontSize: 13 }}>Failed to load wiki.</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {data?.items.map((entry) => (
          <Link key={entry.id} to={`/wiki/${entry.id}`} style={{ textDecoration: "none", color: "inherit" }}>
            <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "16px 20px", transition: "border-color 150ms" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4, flexWrap: "wrap" }}>
                <span style={{ fontSize: 15.5, fontWeight: 600, letterSpacing: "-0.01em" }}>{entry.title}</span>
                <div style={{ flex: 1 }} />
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, background: "var(--info-soft)", color: "var(--info)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>AI Generated</span>
                {entry.last_generated_at && (
                  <span style={{ fontSize: 11.5, color: "var(--ink3)" }}>
                    {new Date(entry.last_generated_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <ModuleChip module={entry.module} />
              <Snippet text={entry.content} />
              {entry.linked_rule_ids.length > 0 && (
                <div style={{ marginTop: 10, fontSize: 12, color: "var(--ink3)" }}>
                  {entry.linked_rule_ids.length} linked rule{entry.linked_rule_ids.length !== 1 ? "s" : ""}
                </div>
              )}
            </div>
          </Link>
        ))}

        {data?.items.length === 0 && !isLoading && (
          <div style={{ textAlign: "center", padding: "48px 24px", background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, color: "var(--ink3)", fontSize: 14 }}>
            {search
              ? `No wiki pages match "${search}".`
              : "No wiki pages yet. Ingest a repository to auto-generate documentation, or use Admin → Settings → Regenerate wiki."}
          </div>
        )}
      </div>

      {data && data.total > limit && (
        <div style={{ marginTop: 18, display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ padding: "7px 14px", borderRadius: 999, border: "1px solid var(--line)", background: "var(--panel)", color: page === 1 ? "var(--ink4)" : "var(--ink2)", fontSize: 13, cursor: page === 1 ? "default" : "pointer", fontFamily: "var(--font-sans)" }}>← Prev</button>
          <span style={{ fontSize: 13, color: "var(--ink3)" }}>Page {page} of {Math.ceil(data.total / limit)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page * limit >= data.total} style={{ padding: "7px 14px", borderRadius: 999, border: "1px solid var(--line)", background: "var(--panel)", color: page * limit >= data.total ? "var(--ink4)" : "var(--ink2)", fontSize: 13, cursor: page * limit >= data.total ? "default" : "pointer", fontFamily: "var(--font-sans)" }}>Next →</button>
        </div>
      )}
    </Layout>
  );
}
