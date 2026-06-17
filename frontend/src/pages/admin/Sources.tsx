import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../../components/Layout";
import { useSources, useCreateSource, useUpdateSource, useDeleteSource, useTriggerIngest, type IngestSource } from "../../api/sources";

const BLANK = { name: "", repo_url: "", branch: "main", pat: "", paths: "", test_paths: "" };

function formatAge(iso: string | null) {
  if (!iso) return "Never";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "9px 12px",
  border: "1px solid var(--line)", borderRadius: 8,
  fontSize: 13, fontFamily: "var(--font-sans)",
  background: "var(--panel)", color: "var(--ink)", outline: "none",
};

function IngestStatusBadge({ source }: { source: IngestSource }) {
  if (source.ingest_status === "ingesting") {
    return (
      <div>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, padding: "2px 9px", borderRadius: 999, background: "var(--accent-soft, #e8f0fe)", color: "var(--accent)", fontWeight: 600 }}>
          <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: "var(--accent)", animation: "pulse 1.2s ease-in-out infinite" }} />
          Ingesting…
        </span>
        {source.ingest_progress && (
          <div style={{ fontSize: 11, color: "var(--ink3)", marginTop: 4, maxWidth: 220, lineHeight: 1.4 }}>
            {source.ingest_progress}
          </div>
        )}
      </div>
    );
  }
  if (source.ingest_status === "error") {
    return (
      <div>
        <span style={{ fontSize: 12, padding: "2px 9px", borderRadius: 999, background: "var(--danger-soft, #fde8e8)", color: "var(--danger)", fontWeight: 600 }}>
          Error
        </span>
        {source.ingest_error && (
          <div style={{ fontSize: 11, color: "var(--danger)", marginTop: 4, maxWidth: 220, lineHeight: 1.4, wordBreak: "break-word" }}>
            {source.ingest_error}
          </div>
        )}
      </div>
    );
  }
  return (
    <span style={{ fontSize: 12, padding: "2px 9px", borderRadius: 999, background: source.status === "active" ? "var(--ok-soft)" : "var(--panel2)", color: source.status === "active" ? "var(--ok)" : "var(--ink3)", fontWeight: 500 }}>
      {source.status}
    </span>
  );
}

function SourceRow({ source, onIngest, onDelete, onSaved }: { source: IngestSource; onIngest: (id: string) => void; onDelete: (id: string) => void; onSaved: () => void }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: source.name, branch: source.branch, repo_url: source.repo_url, paths: (source.paths ?? []).join(", "), test_paths: (source.test_paths ?? []).join(", "), pat: "" });
  const [editError, setEditError] = useState<string | null>(null);
  const updateSource = useUpdateSource();
  const isIngesting = source.ingest_status === "ingesting";

  const openEdit = () => {
    setEditForm({ name: source.name, branch: source.branch, repo_url: source.repo_url, paths: (source.paths ?? []).join(", "), test_paths: (source.test_paths ?? []).join(", "), pat: "" });
    setEditError(null);
    setEditing(true);
  };

  const handleSave = () => {
    setEditError(null);
    if (!editForm.name || !editForm.repo_url) { setEditError("Name and Repository URL are required."); return; }
    const payload: Parameters<typeof updateSource.mutate>[0]["payload"] = {
      name: editForm.name,
      branch: editForm.branch || "main",
      paths: editForm.paths.trim() ? editForm.paths.split(",").map((p) => p.trim()).filter(Boolean) : [],
      test_paths: editForm.test_paths.trim() ? editForm.test_paths.split(",").map((p) => p.trim()).filter(Boolean) : [],
    };
    if (editForm.pat) payload.pat = editForm.pat;
    updateSource.mutate({ id: source.id, payload }, {
      onSuccess: () => { setEditing(false); onSaved(); },
      onError: (err: any) => setEditError(err?.response?.data?.detail ?? "Failed to save."),
    });
  };

  return (
    <>
      <tr style={{ borderBottom: editing ? "none" : "1px solid var(--line2)" }}>
        <td style={{ padding: "12px 16px" }}>
          <div style={{ fontSize: 14, fontWeight: 500 }}>{source.name}</div>
          <div style={{ fontSize: 12, color: "var(--ink3)", fontFamily: "var(--font-mono)" }}>{source.repo_url}</div>
        </td>
        <td style={{ padding: "12px 16px", fontSize: 13, color: "var(--ink2)" }}>{source.branch}</td>
        <td style={{ padding: "12px 16px" }}>
          <span style={{ fontSize: 12, padding: "2px 9px", borderRadius: 999, background: source.has_pat ? "var(--ok-soft)" : "var(--panel2)", color: source.has_pat ? "var(--ok)" : "var(--ink3)", fontWeight: 500 }}>
            {source.has_pat ? "Private" : "Public"}
          </span>
        </td>
        <td style={{ padding: "12px 16px", fontSize: 12, color: "var(--ink3)" }}>
          <div>{formatAge(source.last_ingested_at)}</div>
          {source.last_commit_sha && (
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink4)", marginTop: 2 }}>
              {source.last_commit_sha.slice(0, 7)}
            </div>
          )}
        </td>
        <td style={{ padding: "12px 16px" }}>
          <IngestStatusBadge source={source} />
        </td>
        <td style={{ padding: "12px 16px", textAlign: "right" }}>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              onClick={() => onIngest(source.id)}
              disabled={isIngesting}
              style={{ padding: "6px 14px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 12, fontWeight: 600, cursor: isIngesting ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)", opacity: isIngesting ? 0.6 : 1, whiteSpace: "nowrap" }}
            >
              {isIngesting ? "Running…" : "Ingest Now"}
            </button>
            <button
              onClick={openEdit}
              style={{ padding: "6px 14px", border: "1px solid var(--line)", borderRadius: 999, background: editing ? "var(--panel2)" : "var(--panel)", color: "var(--ink2)", fontSize: 12, cursor: "pointer", fontFamily: "var(--font-sans)" }}
            >
              Edit
            </button>
            {confirmDelete ? (
              <>
                <button onClick={() => onDelete(source.id)} style={{ padding: "6px 14px", border: 0, borderRadius: 999, background: "var(--danger)", color: "#fff", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                  Confirm
                </button>
                <button onClick={() => setConfirmDelete(false)} style={{ padding: "6px 14px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 12, cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                  Cancel
                </button>
              </>
            ) : (
              <button onClick={() => setConfirmDelete(true)} style={{ padding: "6px 14px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink3)", fontSize: 12, cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                Delete
              </button>
            )}
          </div>
        </td>
      </tr>
      {editing && (
        <tr style={{ borderBottom: "1px solid var(--line2)" }}>
          <td colSpan={6} style={{ padding: "0 16px 16px" }}>
            <div style={{ background: "var(--panel2)", border: "1px solid var(--line)", borderRadius: 10, padding: 20 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
                <div>
                  <label style={{ display: "block", fontSize: 11, color: "var(--ink3)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.05em" }}>Source name</label>
                  <input value={editForm.name} onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 11, color: "var(--ink3)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.05em" }}>Branch</label>
                  <input value={editForm.branch} onChange={(e) => setEditForm((f) => ({ ...f, branch: e.target.value }))} style={inputStyle} />
                </div>
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 11, color: "var(--ink3)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.05em" }}>Repository URL</label>
                <input value={editForm.repo_url} onChange={(e) => setEditForm((f) => ({ ...f, repo_url: e.target.value }))} style={inputStyle} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
                <div>
                  <label style={{ display: "block", fontSize: 11, color: "var(--ink3)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.05em" }}>Paths <span style={{ fontWeight: 400, textTransform: "none" }}>(comma-separated)</span></label>
                  <input value={editForm.paths} onChange={(e) => setEditForm((f) => ({ ...f, paths: e.target.value }))} placeholder="src/, lib/" style={inputStyle} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 11, color: "var(--ink3)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.05em" }}>Test paths <span style={{ fontWeight: 400, textTransform: "none" }}>(comma-separated)</span></label>
                  <input value={editForm.test_paths} onChange={(e) => setEditForm((f) => ({ ...f, test_paths: e.target.value }))} placeholder="tests/" style={inputStyle} />
                </div>
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 11, color: "var(--ink3)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.05em" }}>New PAT <span style={{ fontWeight: 400, textTransform: "none" }}>(leave blank to keep existing)</span></label>
                <input type="password" value={editForm.pat} onChange={(e) => setEditForm((f) => ({ ...f, pat: e.target.value }))} placeholder="ghp_…" style={inputStyle} />
              </div>
              {editError && <p style={{ color: "var(--danger)", fontSize: 12, margin: "0 0 10px" }}>{editError}</p>}
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={handleSave} disabled={updateSource.isPending} style={{ padding: "7px 18px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 12, fontWeight: 600, cursor: updateSource.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)" }}>
                  {updateSource.isPending ? "Saving…" : "Save"}
                </button>
                <button onClick={() => setEditing(false)} style={{ padding: "7px 18px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 12, cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                  Cancel
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function Sources() {
  const navigate = useNavigate();
  const { data, isLoading, refetch } = useSources();
  const createSource = useCreateSource();
  const deleteSource = useDeleteSource();
  const triggerIngest = useTriggerIngest();
  // useUpdateSource is called per-row inside SourceRow

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(BLANK);
  const [formError, setFormError] = useState<string | null>(null);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);

  const handleCreate = async () => {
    setFormError(null);
    if (!form.name || !form.repo_url) { setFormError("Name and Repository URL are required."); return; }

    const payload: Parameters<typeof createSource.mutate>[0] = { name: form.name, repo_url: form.repo_url, branch: form.branch || "main" };
    if (form.pat) payload.pat = form.pat;
    if (form.paths.trim()) payload.paths = form.paths.split(",").map((p) => p.trim()).filter(Boolean);
    if (form.test_paths.trim()) payload.test_paths = form.test_paths.split(",").map((p) => p.trim()).filter(Boolean);

    createSource.mutate(payload, {
      onSuccess: () => { setForm(BLANK); setShowForm(false); },
      onError: (err: any) => setFormError(err?.response?.data?.detail ?? "Failed to create source."),
    });
  };

  const handleIngest = (id: string) => {
    setIngestMessage(null);
    triggerIngest.mutate(id, {
      onSuccess: (data) => { setIngestMessage(data.message); refetch(); },
      onError: (err: any) => setIngestMessage(err?.response?.data?.detail ?? "Ingest trigger failed."),
    });
  };

  const sources = data?.items ?? [];

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Sources</h1>
          <p style={{ margin: "6px 0 0", fontSize: 14, color: "var(--ink3)" }}>
            GitHub repositories ingested into RuleGraph.
          </p>
        </div>
        <button
          onClick={() => { setShowForm(!showForm); setFormError(null); }}
          style={{ padding: "8px 16px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "var(--font-sans)" }}
        >
          {showForm ? "Cancel" : "+ Add Repository"}
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: 24, marginBottom: 24, maxWidth: 720 }}>
          <h2 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>Add a GitHub Repository</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "var(--ink3)", fontWeight: 600, marginBottom: 6 }}>Source name *</label>
              <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="e.g. ordering-service" style={inputStyle} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "var(--ink3)", fontWeight: 600, marginBottom: 6 }}>Branch</label>
              <input value={form.branch} onChange={(e) => setForm((f) => ({ ...f, branch: e.target.value }))} placeholder="main" style={inputStyle} />
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 12, color: "var(--ink3)", fontWeight: 600, marginBottom: 6 }}>Repository URL *</label>
            <input value={form.repo_url} onChange={(e) => setForm((f) => ({ ...f, repo_url: e.target.value }))} placeholder="https://github.com/org/repo" style={inputStyle} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 12, color: "var(--ink3)", fontWeight: 600, marginBottom: 6 }}>
              GitHub PAT <span style={{ fontWeight: 400, color: "var(--ink4)" }}>(optional — private repos)</span>
            </label>
            <input type="password" value={form.pat} onChange={(e) => setForm((f) => ({ ...f, pat: e.target.value }))} placeholder="ghp_…" style={inputStyle} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "var(--ink3)", fontWeight: 600, marginBottom: 6 }}>Paths to ingest <span style={{ fontWeight: 400, color: "var(--ink4)" }}>(comma-separated)</span></label>
              <input value={form.paths} onChange={(e) => setForm((f) => ({ ...f, paths: e.target.value }))} placeholder="src/, lib/" style={inputStyle} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "var(--ink3)", fontWeight: 600, marginBottom: 6 }}>Test paths <span style={{ fontWeight: 400, color: "var(--ink4)" }}>(comma-separated)</span></label>
              <input value={form.test_paths} onChange={(e) => setForm((f) => ({ ...f, test_paths: e.target.value }))} placeholder="tests/, __tests__/" style={inputStyle} />
            </div>
          </div>
          {formError && <p style={{ color: "var(--danger)", fontSize: 13, margin: "0 0 12px" }}>{formError}</p>}
          <button
            onClick={handleCreate}
            disabled={createSource.isPending}
            style={{ padding: "9px 20px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: createSource.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)" }}
          >
            {createSource.isPending ? "Saving…" : "Save Source"}
          </button>
        </div>
      )}

      {/* Ingest banner */}
      {ingestMessage && (
        <div style={{ background: "var(--ok-soft)", border: "1px solid var(--ok)", borderRadius: 10, padding: "12px 16px", marginBottom: 16, fontSize: 13, color: "var(--accent-deep)" }}>
          <p style={{ margin: 0 }}>{ingestMessage}</p>
          <button onClick={() => navigate("/rules")} style={{ border: 0, background: "none", color: "var(--accent)", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "var(--font-sans)", marginTop: 4, padding: 0 }}>
            View rules →
          </button>
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <p style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</p>
      ) : sources.length === 0 ? (
        <div style={{ textAlign: "center", padding: "48px 0", color: "var(--ink3)" }}>
          <p style={{ fontSize: 15, margin: "0 0 6px" }}>No sources configured yet.</p>
          <p style={{ fontSize: 13, margin: 0 }}>Click "+ Add Repository" to connect a GitHub repo.</p>
        </div>
      ) : (
        <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--panel2)", borderBottom: "1px solid var(--line)" }}>
                {["Repository", "Branch", "Auth", "Last Ingested", "Status", ""].map((h) => (
                  <th key={h} style={{ padding: "10px 16px", textAlign: h === "" ? "right" : "left", fontSize: 11, color: "var(--ink3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sources.map((src) => (
                <SourceRow key={src.id} source={src} onIngest={handleIngest} onDelete={(id) => deleteSource.mutate(id)} onSaved={refetch} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
