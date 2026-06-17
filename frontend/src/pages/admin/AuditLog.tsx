import { useAuditLog } from "../../api/admin";
import Layout from "../../components/Layout";

export default function AuditLog() {
  const { data, isLoading } = useAuditLog();

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Audit Log</h1>
      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}

      <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, overflow: "hidden" }}>
        <table data-testid="audit-log-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--panel2)", borderBottom: "1px solid var(--line)" }}>
              {["Action", "Target", "IP", "When"].map((h) => (
                <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11, color: "var(--ink3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.items?.map((log: any) => (
              <tr key={log.id} style={{ borderBottom: "1px solid var(--line2)" }}>
                <td style={{ padding: "10px 16px", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink)" }}>{log.action}</td>
                <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--ink2)" }}>{log.target_type}</td>
                <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--ink3)", fontFamily: "var(--font-mono)" }}>{log.ip_address || "—"}</td>
                <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--ink3)" }}>
                  {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.items?.length === 0 && !isLoading && (
          <p style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: 24 }}>No audit events yet.</p>
        )}
      </div>
    </Layout>
  );
}
