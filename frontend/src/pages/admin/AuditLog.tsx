import { useAuditLog } from "../../api/admin";
import Layout from "../../components/Layout";

export default function AuditLog() {
  const { data, isLoading } = useAuditLog();

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">Audit Log</h1>
      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}

      <div className="overflow-x-auto">
        <table data-testid="audit-log-table" className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-bone-3 border-b border-bone-4">
              <th className="pb-2 pr-4">Action</th>
              <th className="pb-2 pr-4">Target</th>
              <th className="pb-2 pr-4">IP</th>
              <th className="pb-2">When</th>
            </tr>
          </thead>
          <tbody>
            {data?.items?.map((log: { id: string; action: string; target_type?: string; target_id?: string; ip_address?: string; created_at?: string }) => (
              <tr key={log.id} className="border-b border-bone-4/30 text-bone-2">
                <td className="py-2 pr-4 font-mono text-xs">{log.action}</td>
                <td className="py-2 pr-4 text-xs">
                  {log.target_type && <span>{log.target_type}</span>}
                </td>
                <td className="py-2 pr-4 text-xs text-bone-3">{log.ip_address || "—"}</td>
                <td className="py-2 text-xs text-bone-3">
                  {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.items?.length === 0 && !isLoading && (
          <p className="text-bone-3 text-sm py-4 text-center">No audit events yet.</p>
        )}
      </div>
    </Layout>
  );
}
