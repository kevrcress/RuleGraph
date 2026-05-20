import { useIngestErrors } from "../../api/admin";
import Layout from "../../components/Layout";

export default function IngestErrors() {
  const { data, isLoading } = useIngestErrors();

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">Ingest Errors</h1>
      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}

      <ul className="space-y-2">
        {data?.items?.map((e: { id: string; error_type?: string; message?: string; source_name?: string; created_at?: string; resolved_at?: string }) => (
          <li key={e.id} className="bg-ink-2 border border-bone-4 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-ember text-sm font-medium">{e.error_type}</p>
                <p className="text-bone-2 text-xs mt-1">{e.message}</p>
                {e.source_name && (
                  <p className="text-xs text-bone-3 mt-1">Source: {e.source_name}</p>
                )}
              </div>
              <div className="text-right text-xs text-bone-4">
                <p>{e.created_at ? new Date(e.created_at).toLocaleDateString() : ""}</p>
                {e.resolved_at && <p className="text-green-400">Resolved</p>}
              </div>
            </div>
          </li>
        ))}
        {data?.items?.length === 0 && !isLoading && (
          <p className="text-bone-3 text-sm py-4 text-center">No ingest errors.</p>
        )}
      </ul>
    </Layout>
  );
}
