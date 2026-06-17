import { useState, useRef } from "react";
import { useDocuments, useUploadDocument } from "../../api/documents";
import Layout from "../../components/Layout";

const ALLOWED_EXTS = [".pdf", ".docx", ".txt", ".md", ".eml", ".msg"];
const MAX_SIZE_MB = 25;

function validateFile(file: File): string | null {
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ALLOWED_EXTS.includes(ext))
    return `File type ${ext} is not allowed. Allowed: ${ALLOWED_EXTS.join(", ")}`;
  if (file.size > MAX_SIZE_MB * 1024 * 1024)
    return `File exceeds ${MAX_SIZE_MB}MB limit.`;
  return null;
}

const STATUS_COLORS: Record<string, string> = {
  ready:      "var(--ok)",
  processing: "var(--warn)",
  error:      "var(--danger)",
  pending:    "var(--info)",
};

export default function DocumentLibrary() {
  const { data, isLoading } = useDocuments();
  const { mutate: upload, isPending: uploading } = useUploadDocument();
  const [uploadError, setUploadError] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError("");
    setUploadSuccess("");

    const err = validateFile(file);
    if (err) { setUploadError(err); e.target.value = ""; return; }

    upload(file, {
      onSuccess: () => {
        setUploadSuccess(`${file.name} uploaded successfully.`);
        if (fileRef.current) fileRef.current.value = "";
      },
      onError: (err: unknown) => {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed";
        setUploadError(msg);
      },
    });
  };

  return (
    <Layout>
      <div data-testid="document-library" style={{ maxWidth: 800 }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 24 }}>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Documents</h1>
        </div>

        {/* Upload card */}
        <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: 20, marginBottom: 20 }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>Upload Document</h3>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,.md,.eml,.msg"
            onChange={handleFileChange}
            disabled={uploading}
            style={{ display: "block", fontSize: 13, color: "var(--ink2)", marginBottom: 8 }}
          />
          <p style={{ fontSize: 12, color: "var(--ink3)", margin: 0 }}>
            PDF, DOCX, TXT, MD, EML, MSG — max {MAX_SIZE_MB}MB
          </p>
          {uploadError && <p style={{ color: "var(--danger)", fontSize: 13, marginTop: 8 }}>{uploadError}</p>}
          {uploadSuccess && <p style={{ color: "var(--ok)", fontSize: 13, marginTop: 8 }}>{uploadSuccess}</p>}
        </div>

        {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading documents…</div>}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {data?.items.map((doc) => (
            <div
              key={doc.id}
              style={{
                background: "var(--panel)", border: "1px solid var(--line)",
                borderRadius: 10, padding: "14px 18px",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}
            >
              <div>
                <p style={{ margin: 0, fontSize: 14, fontWeight: 500, color: "var(--ink)" }}>{doc.filename}</p>
                <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--ink3)" }}>
                  {doc.content_type} · {Math.round(doc.size_bytes / 1024)}KB
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 12, color: STATUS_COLORS[doc.status] ?? "var(--ink3)", fontWeight: 500 }}>
                  {doc.status}
                </span>
                <span style={{ fontSize: 12, color: "var(--ink4)" }}>
                  {new Date(doc.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
          {data?.items.length === 0 && !isLoading && (
            <div style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: 32 }}>
              No documents uploaded yet.
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
