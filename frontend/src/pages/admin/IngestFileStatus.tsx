import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Layout from "../../components/Layout";
import { useSource } from "../../api/sources";
import { useSourceIngestStatus, useRetryErrors } from "../../api/ingestRuns";
import type { IngestFileCheckpointInfo } from "../../api/ingestRuns";

function formatAge(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  pending:    { background: "var(--panel2)", color: "var(--ink3)" },
  processing: { background: "var(--accent-soft, #e8f0fe)", color: "var(--accent)" },
  done:       { background: "var(--ok-soft)", color: "var(--ok)" },
  error:      { background: "var(--danger-soft, #fde8e8)", color: "var(--danger)" },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  return (
    <span style={{
      ...style,
      fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 999,
      display: "inline-flex", alignItems: "center", gap: 4,
    }}>
      {status === "processing" && (
        <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--accent)", animation: "pulse 1.2s ease-in-out infinite" }} />
      )}
      {status}
    </span>
  );
}

function FileRow({ file }: { file: IngestFileCheckpointInfo }) {
  const [expanded, setExpanded] = useState(false);
  const err = file.error_message;
  const shortErr = err && err.length > 80 ? err.slice(0, 80) + "…" : err;

  return (
    <tr>
      <td style={{ padding: "8px 12px", fontFamily: "var(--font-mono)", fontSize: 12, maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        <span title={file.file_path}>{file.file_path}</span>
      </td>
      <td style={{ padding: "8px 12px", whiteSpace: "nowrap" }}>
        <StatusBadge status={file.status} />
      </td>
      <td style={{ padding: "8px 12px", fontSize: 12, color: "var(--ink3)", maxWidth: 280 }}>
        {err ? (
          <span>
            {expanded ? err : shortErr}
            {err.length > 80 && (
              <button onClick={() => setExpanded(!expanded)} style={{ marginLeft: 4, fontSize: 11, color: "var(--accent)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                {expanded ? "less" : "more"}
              </button>
            )}
          </span>
        ) : "—"}
      </td>
      <td style={{ padding: "8px 12px", fontSize: 12, color: "var(--ink3)", whiteSpace: "nowrap" }}>
        {formatAge(file.processed_at)}
      </td>
    </tr>
  );
}

const PAGE_SIZES = [25, 50, 100];

export default function IngestFileStatus() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [retryMessage, setRetryMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const retryErrors = useRetryErrors(sourceId ?? "");

  const sourceQuery = useSource(sourceId ?? "");
  const statusQuery = useSourceIngestStatus(sourceId ?? "", page, pageSize);

  const src = sourceQuery.data;
  const { items, total, run } = statusQuery.data ?? { items: [], total: 0, run: null };
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const batchBadgeStyle = run?.batch_status
    ? (STATUS_STYLES[run.batch_status] ?? STATUS_STYLES.pending)
    : STATUS_STYLES.pending;

  return (
    <Layout>
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
        {/* Back */}
        <button
          onClick={() => navigate("/admin/sources")}
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--accent)", fontSize: 13, marginBottom: 16, padding: 0, display: "flex", alignItems: "center", gap: 4 }}
        >
          ← Back to Sources
        </button>

        {/* Title */}
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20, color: "var(--ink)" }}>
          Ingest Status{src ? ` — ${src.name}` : ""}
        </h1>

        {/* Run header */}
        {run ? (
          <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: "16px 20px", marginBottom: 20, display: "flex", flexWrap: "wrap", gap: 24 }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--ink3)", marginBottom: 4 }}>Run status</div>
              <span style={{ ...batchBadgeStyle, fontSize: 12, fontWeight: 600, padding: "3px 10px", borderRadius: 999 }}>
                {run.batch_status ?? "unknown"}
              </span>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--ink3)", marginBottom: 4 }}>Progress</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>
                {run.files_processed} done / {run.files_errored} errors / {total} total
              </div>
            </div>
            {run.started_at && (
              <div>
                <div style={{ fontSize: 11, color: "var(--ink3)", marginBottom: 4 }}>Started</div>
                <div style={{ fontSize: 13, color: "var(--ink)" }}>{formatAge(run.started_at)}</div>
              </div>
            )}
            {run.files_errored > 0 && src?.ingest_status !== "ingesting" && (
              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center" }}>
                <button
                  onClick={() =>
                    retryErrors.mutate(undefined, {
                      onSuccess: (data) =>
                        setRetryMessage({ type: "ok", text: data.message }),
                      onError: (err: unknown) => {
                        const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
                        setRetryMessage({ type: "err", text: detail ?? "Retry failed — check the console for details." });
                      },
                    })
                  }
                  disabled={retryErrors.isPending}
                  style={{
                    padding: "6px 16px",
                    borderRadius: 6,
                    border: "1px solid var(--danger)",
                    background: "transparent",
                    color: "var(--danger)",
                    cursor: retryErrors.isPending ? "not-allowed" : "pointer",
                    opacity: retryErrors.isPending ? 0.5 : 1,
                    fontSize: 13,
                    fontWeight: 600,
                  }}
                >
                  {retryErrors.isPending ? "Retrying…" : `Retry ${run.files_errored} error${run.files_errored !== 1 ? "s" : ""}`}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: "32px 20px", textAlign: "center", color: "var(--ink3)", fontSize: 14, background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, marginBottom: 20 }}>
            No ingest run found for this source.
          </div>
        )}

        {/* File table */}
        {run && (
          <>
            {retryMessage && (
              <div style={{
                marginBottom: 12,
                padding: "10px 14px",
                borderRadius: 8,
                background: retryMessage.type === "ok" ? "var(--ok-soft)" : "var(--danger-soft, #fde8e8)",
                color: retryMessage.type === "ok" ? "var(--ok)" : "var(--danger)",
                fontSize: 13,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}>
                <span>{retryMessage.text}</span>
                <button
                  onClick={() => setRetryMessage(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", fontSize: 16, lineHeight: 1 }}
                >
                  ×
                </button>
              </div>
            )}
            <div style={{ overflowX: "auto", border: "1px solid var(--line)", borderRadius: 10, background: "var(--panel)" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--line)", background: "var(--panel2)" }}>
                    <th style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, color: "var(--ink3)", fontWeight: 600 }}>File Path</th>
                    <th style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, color: "var(--ink3)", fontWeight: 600 }}>Status</th>
                    <th style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, color: "var(--ink3)", fontWeight: 600 }}>Error</th>
                    <th style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, color: "var(--ink3)", fontWeight: 600 }}>Processed</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={4} style={{ padding: "24px 12px", textAlign: "center", color: "var(--ink3)" }}>No files on this page.</td>
                    </tr>
                  ) : (
                    items.map((file) => <FileRow key={file.id} file={file} />)
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--panel)", color: "var(--ink)", cursor: page <= 1 ? "not-allowed" : "pointer", opacity: page <= 1 ? 0.5 : 1, fontSize: 13 }}
              >
                ← Prev
              </button>
              <span style={{ fontSize: 13, color: "var(--ink3)" }}>Page {page} of {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--panel)", color: "var(--ink)", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.5 : 1, fontSize: 13 }}
              >
                Next →
              </button>
              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 12, color: "var(--ink3)" }}>Rows:</span>
                {PAGE_SIZES.map((sz) => (
                  <button
                    key={sz}
                    onClick={() => { setPageSize(sz); setPage(1); }}
                    style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid var(--line)", background: sz === pageSize ? "var(--accent)" : "var(--panel)", color: sz === pageSize ? "#fff" : "var(--ink)", cursor: "pointer", fontSize: 12 }}
                  >
                    {sz}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
