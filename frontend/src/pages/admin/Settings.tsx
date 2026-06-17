import { useState, useEffect, useRef } from "react";
import { useSystemSettings, useUpdateSettings, useClearData, useExportSnapshot, useImportSnapshot, useRunImprove, useRunLint, useRegenerateWiki } from "../../api/admin";
import Layout from "../../components/Layout";

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "9px 12px",
  border: "1px solid var(--line)", borderRadius: 8,
  fontSize: 13, fontFamily: "var(--font-sans)",
  background: "var(--panel)", color: "var(--ink)", outline: "none",
};

const sectionStyle: React.CSSProperties = {
  background: "var(--panel)", border: "1px solid var(--line)",
  borderRadius: 10, padding: 24, maxWidth: 680, marginBottom: 20,
};

const FEATURE_FLAG_KEYS = ["claude_enabled"] as const;
const SENSITIVE_KEYS = ["anthropic_api_key"] as const;
const MASKED = "***SET***";

export default function Settings() {
  const { data, isLoading } = useSystemSettings();
  const { mutate: save } = useUpdateSettings();
  const clearData = useClearData();
  const exportSnapshot = useExportSnapshot();
  const importSnapshot = useImportSnapshot();
  const runImprove = useRunImprove();
  const runLint = useRunLint();
  const regenerateWiki = useRegenerateWiki();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [improveResult, setImproveResult] = useState<string | null>(null);
  const [lintResult, setLintResult] = useState<string | null>(null);
  const [wikiResult, setWikiResult] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [flagSaved, setFlagSaved] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeySet, setApiKeySet] = useState(false);
  const [apiKeySaved, setApiKeySaved] = useState(false);
  const [preview, setPreview] = useState<Record<string, number> | null>(null);
  const [clearDone, setClearDone] = useState<string | null>(null);
  const [confirmStep, setConfirmStep] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);

  useEffect(() => {
    if (data?.settings) {
      const defaults: Record<string, string> = { claude_enabled: "true" };
      setForm({ ...defaults, ...data.settings });
      setApiKeySet(data.settings["anthropic_api_key"] === MASKED);
    }
  }, [data]);

  const handleSave = () => {
    const nonFlags = Object.fromEntries(
      Object.entries(form).filter(([k]) =>
        !FEATURE_FLAG_KEYS.includes(k as typeof FEATURE_FLAG_KEYS[number]) &&
        !SENSITIVE_KEYS.includes(k as typeof SENSITIVE_KEYS[number])
      )
    );
    save(nonFlags, {
      onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); },
    });
  };

  const handleSaveApiKey = () => {
    if (!apiKeyInput.trim()) return;
    save({ anthropic_api_key: apiKeyInput.trim() }, {
      onSuccess: () => {
        setApiKeyInput("");
        setShowApiKey(false);
        setApiKeySet(true);
        setApiKeySaved(true);
        setTimeout(() => setApiKeySaved(false), 2000);
      },
    });
  };

  const handlePreview = () => {
    clearData.mutate(true, {
      onSuccess: (d) => { setPreview(d.would_delete); setConfirmStep(true); },
    });
  };

  const handleClearConfirmed = () => {
    clearData.mutate(false, {
      onSuccess: (d) => {
        setClearDone(`Deleted ${d.total_rows} rows across ${Object.keys(d.deleted).length} tables.`);
        setPreview(null); setConfirmStep(false);
      },
    });
  };

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Settings</h1>
      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}

      {/* API Keys */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 600 }}>API Keys</h2>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--ink3)" }}>
          The Anthropic API key is stored encrypted in the database. It is never returned in plaintext.
          Leave blank to fall back to the <code style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>ANTHROPIC_API_KEY</code> environment variable.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <label style={{ fontSize: 12, color: "var(--ink3)", fontFamily: "var(--font-mono)" }}>anthropic_api_key</label>
          {apiKeySet && !apiKeyInput && (
            <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", border: "1px solid var(--line)", borderRadius: 8, background: "var(--bg)", fontSize: 13, color: "var(--ink3)" }}>
              <span>●●●●●●●●●●●●●●●●</span>
              <span style={{ flex: 1, color: "var(--ok)", fontSize: 12 }}>Key is configured</span>
              <button
                onClick={() => setApiKeyInput(" ")}
                style={{ padding: "4px 12px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 12, cursor: "pointer", fontFamily: "var(--font-sans)" }}
              >
                Replace
              </button>
            </div>
          )}
          {(!apiKeySet || apiKeyInput) && (
            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ position: "relative", flex: 1 }}>
                <input
                  type={showApiKey ? "text" : "password"}
                  value={apiKeyInput.trim() === "" && apiKeySet ? "" : apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder={apiKeySet ? "Enter new key to replace…" : "sk-ant-…"}
                  style={{ ...inputStyle, paddingRight: 40 }}
                  autoComplete="off"
                />
                <button
                  onClick={() => setShowApiKey((v) => !v)}
                  style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", background: "none", border: 0, cursor: "pointer", color: "var(--ink3)", fontSize: 13, padding: 0 }}
                  title={showApiKey ? "Hide" : "Show"}
                >
                  {showApiKey ? "🙈" : "👁"}
                </button>
              </div>
              <button
                onClick={handleSaveApiKey}
                disabled={!apiKeyInput.trim()}
                style={{ padding: "9px 18px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: apiKeyInput.trim() ? "pointer" : "not-allowed", fontFamily: "var(--font-sans)", opacity: apiKeyInput.trim() ? 1 : 0.5 }}
              >
                Save key
              </button>
              {apiKeySet && (
                <button
                  onClick={() => { setApiKeyInput(""); setShowApiKey(false); }}
                  style={{ padding: "9px 14px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 13, cursor: "pointer", fontFamily: "var(--font-sans)" }}
                >
                  Cancel
                </button>
              )}
            </div>
          )}
          {apiKeySaved && <div style={{ fontSize: 12, color: "var(--ok)" }}>API key saved and encrypted.</div>}
        </div>
      </div>

      {/* Feature Flags */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 600 }}>Feature Flags</h2>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--ink3)" }}>
          Kill switches for external API calls. Disabling Claude stops all LLM extraction, definition inference, and graph enrichment.
        </p>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "var(--bg)", border: "1px solid var(--line)", borderRadius: 8 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, fontFamily: "var(--font-mono)" }}>claude_enabled</div>
            <div style={{ fontSize: 12, color: "var(--ink3)", marginTop: 2 }}>
              {form["claude_enabled"] === "false"
                ? "Claude API calls are blocked — ingest and inference will fail gracefully."
                : "Claude API calls are allowed."}
            </div>
          </div>
          <button
            onClick={() => {
              const next = form["claude_enabled"] === "false" ? "true" : "false";
              const updated = { ...form, claude_enabled: next };
              setForm(updated);
              save(updated, {
                onSuccess: () => { setFlagSaved(true); setTimeout(() => setFlagSaved(false), 2000); },
              });
            }}
            style={{
              flexShrink: 0,
              marginLeft: 24,
              width: 48,
              height: 26,
              borderRadius: 999,
              border: 0,
              cursor: "pointer",
              background: form["claude_enabled"] === "false" ? "var(--ink4)" : "var(--accent)",
              position: "relative",
              transition: "background 0.15s",
            }}
            title={form["claude_enabled"] === "false" ? "Enable Claude" : "Disable Claude"}
          >
            <span style={{
              position: "absolute",
              top: 3,
              left: form["claude_enabled"] === "false" ? 4 : 22,
              width: 20,
              height: 20,
              borderRadius: "50%",
              background: "#fff",
              transition: "left 0.15s",
            }} />
          </button>
        </div>
        {flagSaved && <div style={{ marginTop: 10, fontSize: 12, color: "var(--ok)" }}>Saved!</div>}
      </div>

      {/* Config */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>System Configuration</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {Object.entries(form).filter(([key]) =>
            !FEATURE_FLAG_KEYS.includes(key as typeof FEATURE_FLAG_KEYS[number]) &&
            !SENSITIVE_KEYS.includes(key as typeof SENSITIVE_KEYS[number])
          ).map(([key, val]) => (
            <div key={key}>
              <label style={{ display: "block", fontSize: 12, color: "var(--ink3)", fontFamily: "var(--font-mono)", marginBottom: 6 }}>{key}</label>
              <input value={val} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} style={inputStyle} />
            </div>
          ))}
        </div>
        {Object.keys(form).some((k) =>
          !FEATURE_FLAG_KEYS.includes(k as typeof FEATURE_FLAG_KEYS[number]) &&
          !SENSITIVE_KEYS.includes(k as typeof SENSITIVE_KEYS[number])
        ) && (
          <button
            onClick={handleSave}
            style={{ marginTop: 20, padding: "9px 20px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "var(--font-sans)" }}
          >
            {saved ? "Saved!" : "Save Settings"}
          </button>
        )}
      </div>

      {/* Snapshot */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 6px", fontSize: 15, fontWeight: 600 }}>Data Snapshot</h2>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--ink3)" }}>
          Export the current graph to a ZIP, or restore from a previous export without re-running ingestion.
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            onClick={() => exportSnapshot.mutate()}
            disabled={exportSnapshot.isPending}
            style={{ padding: "9px 18px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: exportSnapshot.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)" }}
          >
            {exportSnapshot.isPending ? "Exporting…" : "Export snapshot"}
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importSnapshot.isPending}
            style={{ padding: "9px 18px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 13, cursor: importSnapshot.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)" }}
          >
            {importSnapshot.isPending ? "Importing…" : "Import snapshot"}
          </button>
          <input ref={fileInputRef} type="file" accept=".zip" style={{ display: "none" }} onChange={(e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            e.target.value = "";
            importSnapshot.mutate(f, { onSuccess: (d) => setImportResult(`Imported ${d.total_rows} rows.`) });
          }} />
        </div>
        {exportSnapshot.isError && <p style={{ marginTop: 12, fontSize: 12, color: "var(--danger)" }}>Export failed. Check server logs.</p>}
        {importResult && <div style={{ marginTop: 12, padding: "10px 14px", background: "var(--ok-soft)", border: "1px solid var(--ok)", borderRadius: 8, color: "var(--ok)", fontSize: 13 }}>{importResult}</div>}
        {importSnapshot.isError && <p style={{ marginTop: 12, fontSize: 12, color: "var(--danger)" }}>Import failed. Make sure the file is a valid snapshot ZIP.</p>}
      </div>

      {/* Graph Maintenance */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 600 }}>Graph Maintenance</h2>
        <p style={{ margin: "0 0 18px", fontSize: 13, color: "var(--ink3)" }}>
          Improve graph quality scores from feedback, re-enrich the knowledge graph structure, or regenerate all wiki pages from current rules.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Improve */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "var(--bg)", border: "1px solid var(--line)", borderRadius: 8 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>Improve graph</div>
              <div style={{ fontSize: 12, color: "var(--ink3)", marginTop: 2 }}>Aggregate feedback signals and update quality scores on all rules.</div>
            </div>
            <button
              onClick={() => runImprove.mutate(undefined, {
                onSuccess: (d) => setImproveResult(d.message ?? "Done"),
                onError: () => setImproveResult("Failed — check server logs."),
              })}
              disabled={runImprove.isPending}
              style={{ flexShrink: 0, marginLeft: 24, padding: "7px 16px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: runImprove.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)", opacity: runImprove.isPending ? 0.6 : 1 }}
            >
              {runImprove.isPending ? "Running…" : "Run"}
            </button>
          </div>
          {improveResult && <div style={{ fontSize: 12, color: "var(--ok)", paddingLeft: 4 }}>{improveResult}</div>}

          {/* Lint */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "var(--bg)", border: "1px solid var(--line)", borderRadius: 8 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>Re-enrich graph</div>
              <div style={{ fontSize: 12, color: "var(--ink3)", marginTop: 2 }}>Re-ingest Cognee skills and re-cognify the knowledge graph structure.</div>
            </div>
            <button
              onClick={() => runLint.mutate(undefined, {
                onSuccess: (d) => setLintResult(d.warnings?.length ? `Done (warnings: ${d.warnings.join(", ")})` : d.message),
                onError: () => setLintResult("Failed — check server logs."),
              })}
              disabled={runLint.isPending}
              style={{ flexShrink: 0, marginLeft: 24, padding: "7px 16px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: runLint.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)", opacity: runLint.isPending ? 0.6 : 1 }}
            >
              {runLint.isPending ? "Running…" : "Run"}
            </button>
          </div>
          {lintResult && <div style={{ fontSize: 12, color: "var(--ok)", paddingLeft: 4 }}>{lintResult}</div>}

          {/* Regenerate wiki */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "var(--bg)", border: "1px solid var(--line)", borderRadius: 8 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>Regenerate wiki</div>
              <div style={{ fontSize: 12, color: "var(--ink3)", marginTop: 2 }}>Re-generate all wiki pages from current rules. Runs in the background.</div>
            </div>
            <button
              onClick={() => regenerateWiki.mutate(undefined, {
                onSuccess: (d) => setWikiResult(d.message),
                onError: () => setWikiResult("Failed — check server logs."),
              })}
              disabled={regenerateWiki.isPending}
              style={{ flexShrink: 0, marginLeft: 24, padding: "7px 16px", border: 0, borderRadius: 999, background: "var(--accent)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: regenerateWiki.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)", opacity: regenerateWiki.isPending ? 0.6 : 1 }}
            >
              {regenerateWiki.isPending ? "Starting…" : "Run"}
            </button>
          </div>
          {wikiResult && <div style={{ fontSize: 12, color: "var(--ok)", paddingLeft: 4 }}>{wikiResult}</div>}
        </div>
      </div>

      {/* Danger zone */}
      <div style={{ ...sectionStyle, border: "1px solid var(--danger)", background: "var(--danger-soft)" }}>
        <h2 style={{ margin: "0 0 6px", fontSize: 15, fontWeight: 600, color: "var(--danger)" }}>Danger Zone</h2>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--ink2)" }}>
          Clear all ingested data — rules, services, conflicts, terminology, feedback, documents, ingest history.
          Users, audit log, settings, and ingest sources are preserved.
        </p>

        {clearDone && (
          <div style={{ marginBottom: 16, padding: "10px 14px", background: "var(--ok-soft)", border: "1px solid var(--ok)", borderRadius: 8, color: "var(--ok)", fontSize: 13 }}>
            {clearDone}
          </div>
        )}

        {!confirmStep ? (
          <button
            onClick={handlePreview}
            disabled={clearData.isPending}
            style={{ padding: "9px 18px", border: "1px solid var(--danger)", borderRadius: 999, background: "transparent", color: "var(--danger)", fontSize: 13, fontWeight: 600, cursor: clearData.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)" }}
          >
            {clearData.isPending ? "Checking…" : "Clear all data…"}
          </button>
        ) : (
          <div>
            <div style={{ background: "var(--panel)", borderRadius: 8, padding: "12px 14px", marginBottom: 12 }}>
              {preview && Object.entries(preview).map(([table, count]) => (
                <div key={table} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "3px 0" }}>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--ink3)" }}>{table}</span>
                  <span style={{ color: count > 0 ? "var(--danger)" : "var(--ink4)", fontWeight: count > 0 ? 600 : 400 }}>{count} rows</span>
                </div>
              ))}
            </div>
            <p style={{ fontSize: 12, color: "var(--danger)", fontWeight: 600, marginBottom: 12 }}>This cannot be undone.</p>
            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={handleClearConfirmed}
                disabled={clearData.isPending}
                style={{ padding: "9px 18px", border: 0, borderRadius: 999, background: "var(--danger)", color: "#fff", fontSize: 13, fontWeight: 600, cursor: clearData.isPending ? "not-allowed" : "pointer", fontFamily: "var(--font-sans)" }}
              >
                {clearData.isPending ? "Deleting…" : "Yes, delete everything"}
              </button>
              <button
                onClick={() => { setConfirmStep(false); setPreview(null); }}
                style={{ padding: "9px 18px", border: "1px solid var(--line)", borderRadius: 999, background: "var(--panel)", color: "var(--ink2)", fontSize: 13, cursor: "pointer", fontFamily: "var(--font-sans)" }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
