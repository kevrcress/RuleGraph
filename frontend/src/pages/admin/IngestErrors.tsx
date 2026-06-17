import { useState } from "react";
import { useIngestErrors } from "../../api/admin";
import Layout from "../../components/Layout";

function formatTs(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "numeric", day: "numeric", year: "numeric" })
    + " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function ErrorRow({ e }: { e: any }) {
  const [open, setOpen] = useState(false);
  const hasDetails = e.stack_trace || e.raw_content || e.resolution_note;

  return (
    <div
      style={{
        background: "var(--panel)", border: "1px solid var(--line)",
        borderRadius: 10, overflow: "hidden",
      }}
    >
      {/* Summary row */}
      <div
        onClick={() => setOpen((o) => !o)}
        style={{
          padding: "14px 18px", display: "flex", alignItems: "flex-start",
          justifyContent: "space-between", cursor: "pointer",
          userSelect: "none",
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: 999, background: e.resolved_at ? "var(--ok)" : "var(--danger)", flexShrink: 0 }} />
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {e.error_source ?? "error"}
            </span>
            {e.resolved_at && (
              <span style={{ fontSize: 11, padding: "1px 7px", borderRadius: 999, background: "var(--ok-soft)", color: "var(--ok)", fontWeight: 600 }}>
                Resolved
              </span>
            )}
          </div>
          <p style={{ margin: "0 0 6px", fontSize: 13, color: "var(--ink)", fontFamily: "var(--font-mono)", wordBreak: "break-word" }}>
            {e.error_message ?? "No message recorded"}
          </p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {e.source_name && (
              <span style={{ fontSize: 12, color: "var(--ink3)" }}>
                Source: <span style={{ fontFamily: "var(--font-mono)" }}>{e.source_name}</span>
              </span>
            )}
            {e.file_path && (
              <span style={{ fontSize: 12, color: "var(--ink3)", fontFamily: "var(--font-mono)" }}>{e.file_path}</span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0, marginLeft: 20 }}>
          <span style={{ fontSize: 12, color: "var(--ink4)", whiteSpace: "nowrap" }}>{formatTs(e.created_at)}</span>
          {hasDetails && (
            <span style={{ fontSize: 12, color: "var(--ink3)", transition: "transform 150ms", display: "inline-block", transform: open ? "rotate(180deg)" : "none" }}>
              ▾
            </span>
          )}
        </div>
      </div>

      {/* Expandable details */}
      {open && hasDetails && (
        <div style={{ borderTop: "1px solid var(--line2)", padding: "14px 18px", display: "flex", flexDirection: "column", gap: 14, background: "var(--panel2)" }}>
          {e.stack_trace && (
            <div>
              <p style={{ margin: "0 0 6px", fontSize: 11, fontWeight: 700, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Stack Trace</p>
              <pre style={{ margin: 0, fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--danger)", background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 6, padding: "10px 12px", overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {e.stack_trace}
              </pre>
            </div>
          )}
          {e.raw_content && (
            <div>
              <p style={{ margin: "0 0 6px", fontSize: 11, fontWeight: 700, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Raw Content</p>
              <pre style={{ margin: 0, fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--ink2)", background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 6, padding: "10px 12px", overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 300, overflow: "auto" }}>
                {e.raw_content}
              </pre>
            </div>
          )}
          {e.resolution_note && (
            <div>
              <p style={{ margin: "0 0 6px", fontSize: 11, fontWeight: 700, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Resolution Note</p>
              <p style={{ margin: 0, fontSize: 13, color: "var(--ink2)" }}>{e.resolution_note}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function IngestErrors() {
  const { data, isLoading } = useIngestErrors();

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Ingest Errors</h1>
      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data?.items?.map((e: any) => <ErrorRow key={e.id} e={e} />)}
        {data?.items?.length === 0 && !isLoading && (
          <div style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: 32 }}>
            No ingest errors.
          </div>
        )}
      </div>
    </Layout>
  );
}
