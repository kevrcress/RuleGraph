import { useState, useEffect } from "react";
import { useSystemSettings, useUpdateSettings, useClearData } from "../../api/admin";
import Layout from "../../components/Layout";

export default function Settings() {
  const { data, isLoading } = useSystemSettings();
  const { mutate: save } = useUpdateSettings();
  const clearData = useClearData();
  const [form, setForm] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [preview, setPreview] = useState<Record<string, number> | null>(null);
  const [clearDone, setClearDone] = useState<string | null>(null);
  const [confirmStep, setConfirmStep] = useState(false);

  useEffect(() => {
    if (data?.settings) setForm(data.settings);
  }, [data]);

  const handleSave = () => {
    save(form, {
      onSuccess: () => {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      },
    });
  };

  const handlePreview = () => {
    clearData.mutate(true, {
      onSuccess: (d) => {
        setPreview(d.would_delete);
        setConfirmStep(true);
      },
    });
  };

  const handleClearConfirmed = () => {
    clearData.mutate(false, {
      onSuccess: (d) => {
        setClearDone(`Deleted ${d.total_rows} rows across ${Object.keys(d.deleted).length} tables.`);
        setPreview(null);
        setConfirmStep(false);
      },
    });
  };

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">System Settings</h1>
      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}

      <div className="max-w-lg bg-ink-2 border border-bone-4 rounded-lg p-6 space-y-4">
        {Object.entries(form).map(([key, val]) => (
          <div key={key}>
            <label className="block text-xs text-bone-3 mb-1 font-mono">{key}</label>
            <input
              value={val}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              className="w-full bg-ink-3 border border-bone-4 rounded px-3 py-2 text-sm text-bone-0 focus:outline-none focus:border-brass-0"
            />
          </div>
        ))}
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-brass-0 text-ink-0 rounded text-sm font-semibold hover:bg-brass-1"
        >
          {saved ? "Saved!" : "Save Settings"}
        </button>
      </div>

      {/* ── Danger zone ────────────────────────────────── */}
      <div className="max-w-lg mt-8 border border-ember/40 rounded-lg p-6">
        <h2 className="text-sm font-semibold text-ember mb-1">Danger Zone</h2>
        <p className="text-xs text-bone-3 mb-4">
          Clear all ingested data — rules, services, conflicts, terminology,
          feedback, documents, ingest history. Users, audit log, and settings
          are preserved.
        </p>

        {clearDone && (
          <div className="mb-4 p-3 bg-green-900/20 border border-green-500/30 rounded text-green-400 text-xs">
            {clearDone}
          </div>
        )}

        {!confirmStep ? (
          <button
            onClick={handlePreview}
            disabled={clearData.isPending}
            className="px-4 py-2 border border-ember text-ember rounded text-sm font-semibold hover:bg-ember/10 disabled:opacity-50"
          >
            {clearData.isPending ? "Checking…" : "Clear all data…"}
          </button>
        ) : (
          <div className="space-y-3">
            <div className="bg-ink-3 rounded p-3 text-xs space-y-1">
              {preview && Object.entries(preview).map(([table, count]) => (
                <div key={table} className="flex justify-between">
                  <span className="text-bone-3 font-mono">{table}</span>
                  <span className={count > 0 ? "text-ember" : "text-bone-4"}>{count} rows</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-ember font-semibold">This cannot be undone.</p>
            <div className="flex gap-3">
              <button
                onClick={handleClearConfirmed}
                disabled={clearData.isPending}
                className="px-4 py-2 bg-ember text-white rounded text-sm font-semibold hover:bg-red-700 disabled:opacity-50"
              >
                {clearData.isPending ? "Deleting…" : "Yes, delete everything"}
              </button>
              <button
                onClick={() => { setConfirmStep(false); setPreview(null); }}
                className="px-4 py-2 border border-bone-4 text-bone-2 rounded text-sm hover:border-bone-2"
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
