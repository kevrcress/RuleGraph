import { useTerminology } from "../../api/admin";
import Layout from "../../components/Layout";

export default function Terminology() {
  const { data, isLoading } = useTerminology();

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">Terminology Inconsistencies</h1>
      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}
      <ul className="space-y-2">
        {data?.items?.map((t: { id: string; canonical_term?: string; variants?: string[]; services?: string[]; status?: string }) => (
          <li key={t.id} className="bg-ink-2 border border-bone-4 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-bone-0 text-sm font-medium">
                  Canonical: <span className="text-brass-0">{t.canonical_term}</span>
                </h3>
                {t.variants && (
                  <p className="text-xs text-bone-3 mt-1">
                    Variants: {t.variants.join(", ")}
                  </p>
                )}
                {t.services && (
                  <p className="text-xs text-bone-3">Services: {t.services.join(", ")}</p>
                )}
              </div>
              <span className="text-xs text-bone-4">{t.status}</span>
            </div>
          </li>
        ))}
        {data?.items?.length === 0 && !isLoading && (
          <li className="text-bone-3 text-sm py-4 text-center">No terminology issues detected.</li>
        )}
      </ul>
    </Layout>
  );
}
