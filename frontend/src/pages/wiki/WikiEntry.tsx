import { useParams, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { useWikiPage } from "../../api/wiki";
import Layout from "../../components/Layout";
import StatusBadge from "../../components/StatusBadge";

function ModuleChip({ module }: { module: string }) {
  const parts = module.split("/");
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
      {parts.map((p, i) => (
        <span key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {i > 0 && <span style={{ color: "var(--ink4)", fontSize: 12 }}>/</span>}
          <span style={{
            padding: "3px 9px", borderRadius: 999,
            background: i === 0 ? "var(--accent-soft)" : "var(--panel2)",
            border: `1px solid ${i === 0 ? "var(--accent-soft)" : "var(--line)"}`,
            fontSize: 12, fontFamily: "var(--font-mono)",
            color: i === 0 ? "var(--accent-deep)" : "var(--ink2)",
            fontWeight: i === 0 ? 600 : 400,
          }}>{p}</span>
        </span>
      ))}
    </div>
  );
}

const proseStyle: React.CSSProperties = {
  fontSize: 14.5,
  lineHeight: 1.75,
  color: "var(--ink)",
};

export default function WikiEntry() {
  const { id } = useParams<{ id: string }>();
  const { data: page, isLoading, isError } = useWikiPage(id || "");

  return (
    <Layout>
      {/* Breadcrumb */}
      <div style={{ fontSize: 12, color: "var(--ink3)", marginBottom: 14 }}>
        <Link to="/wiki" style={{ color: "var(--ink3)", textDecoration: "none" }}>Wiki</Link>
        {page && <> · <span style={{ color: "var(--ink2)" }}>{page.title}</span></>}
      </div>

      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}
      {isError   && <div style={{ color: "var(--danger)", fontSize: 13 }}>Page not found.</div>}

      {page && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 20, alignItems: "start" }}>

          {/* Main content */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Header */}
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
                <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em" }}>
                  {page.title}
                </h1>
                <span style={{ padding: "3px 10px", borderRadius: 999, fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", background: "var(--info-soft)", color: "var(--info)" }}>
                  AI Generated
                </span>
              </div>
              <ModuleChip module={page.module} />
            </div>

            {/* Markdown content */}
            <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "24px 28px" }}>
              <div style={proseStyle} className="wiki-prose">
                <ReactMarkdown>{page.content}</ReactMarkdown>
              </div>
            </div>

            {/* Footer links */}
            <div style={{ fontSize: 13, color: "var(--ink3)" }}>
              <Link to="/wiki" style={{ color: "var(--accent)", fontWeight: 500, textDecoration: "none" }}>← Back to wiki</Link>
            </div>
          </div>

          {/* Sidebar */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Metadata */}
            <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "16px 18px" }}>
              <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 14 }}>Details</div>
              <dl style={{ margin: 0, display: "flex", flexDirection: "column", gap: 10 }}>
                <div>
                  <dt style={{ fontSize: 11.5, color: "var(--ink3)", marginBottom: 2 }}>Module</dt>
                  <dd style={{ margin: 0, fontSize: 12.5, fontFamily: "var(--font-mono)", color: "var(--ink2)", wordBreak: "break-all" }}>{page.module}</dd>
                </div>
                <div>
                  <dt style={{ fontSize: 11.5, color: "var(--ink3)", marginBottom: 2 }}>Last generated</dt>
                  <dd style={{ margin: 0, fontSize: 13, color: "var(--ink2)" }}>
                    {page.last_generated_at ? new Date(page.last_generated_at).toLocaleString() : "—"}
                  </dd>
                </div>
                <div>
                  <dt style={{ fontSize: 11.5, color: "var(--ink3)", marginBottom: 2 }}>Rules covered</dt>
                  <dd style={{ margin: 0, fontSize: 13, color: "var(--ink2)" }}>{page.linked_rule_ids.length}</dd>
                </div>
              </dl>
            </div>

            {/* Linked rules */}
            {page.linked_rules.length > 0 && (
              <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "16px 18px" }}>
                <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 10 }}>
                  Linked rules
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {page.linked_rules.map((rule) => (
                    <div key={rule.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                      <Link
                        to={`/rules/${rule.id}`}
                        style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none", fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                        title={rule.title}
                      >
                        {rule.title}
                      </Link>
                      <StatusBadge status={rule.status} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}
