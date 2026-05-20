import { useState, useEffect } from "react";
import { useSystemSettings, useUpdateSettings } from "../../api/admin";
import Layout from "../../components/Layout";

export default function Settings() {
  const { data, isLoading } = useSystemSettings();
  const { mutate: save } = useUpdateSettings();
  const [form, setForm] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

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
    </Layout>
  );
}
