import { useState, useRef } from "react";
import { useDocuments, useUploadDocument } from "../../api/documents";
import Layout from "../../components/Layout";

const ALLOWED_EXTS = [".pdf", ".docx", ".txt", ".md", ".eml", ".msg"];
const MAX_SIZE_MB = 25;

function validateFile(file: File): string | null {
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ALLOWED_EXTS.includes(ext)) {
    return `File type ${ext} is not allowed. Allowed: ${ALLOWED_EXTS.join(", ")}`;
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return `File exceeds ${MAX_SIZE_MB}MB limit.`;
  }
  return null;
}

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
    if (err) {
      setUploadError(err);
      e.target.value = "";
      return;
    }

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
      <div data-testid="document-library" className="max-w-4xl">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-serif text-bone-0">Document Library</h1>
        </div>

        <div className="bg-ink-2 border border-bone-4 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-bone-2 mb-3">Upload Document</h3>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,.md,.eml,.msg"
            onChange={handleFileChange}
            disabled={uploading}
            className="block text-sm text-bone-2 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:bg-brass-0 file:text-ink-0 file:cursor-pointer hover:file:bg-brass-1"
          />
          <p className="text-xs text-bone-3 mt-2">
            Allowed: PDF, DOCX, TXT, MD, EML, MSG. Max {MAX_SIZE_MB}MB.
          </p>
          {uploadError && (
            <p className="text-ember text-sm mt-2">{uploadError}</p>
          )}
          {uploadSuccess && (
            <p className="text-green-400 text-sm mt-2">{uploadSuccess}</p>
          )}
        </div>

        {isLoading && <div className="text-bone-3 text-sm">Loading documents…</div>}

        <ul className="space-y-2">
          {data?.items.map((doc) => (
            <li
              key={doc.id}
              className="bg-ink-2 border border-bone-4 rounded-lg p-4 flex items-center justify-between"
            >
              <div>
                <p className="text-bone-0 text-sm font-medium">{doc.filename}</p>
                <p className="text-xs text-bone-3 mt-0.5">
                  {doc.content_type} · {Math.round(doc.size_bytes / 1024)}KB · {doc.status}
                </p>
              </div>
              <span className="text-xs text-bone-4">
                {new Date(doc.created_at).toLocaleDateString()}
              </span>
            </li>
          ))}
          {data?.items.length === 0 && !isLoading && (
            <li className="text-bone-3 text-sm py-4 text-center">No documents uploaded yet.</li>
          )}
        </ul>
      </div>
    </Layout>
  );
}
