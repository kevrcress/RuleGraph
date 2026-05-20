import { useCoverage } from "../../api/admin";
import Layout from "../../components/Layout";

const STATUS_COLORS: Record<string, string> = {
  covered: "text-green-400",
  partial: "text-yellow-400",
  uncovered: "text-ember",
  coverage_gap: "text-orange-400",
  stale: "text-bone-3",
};

export default function Coverage() {
  const { data, isLoading } = useCoverage();

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">Coverage Report</h1>
      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}
      <ul className="space-y-2">
        {data?.items?.map((c: { id: string; rule_id?: string; rule_title?: string; status?: string; created_at?: string }) => (
          <li key={c.id} className="bg-ink-2 border border-bone-4 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-bone-0 text-sm font-medium">{c.rule_title || c.rule_id}</h3>
              <span className={`text-xs font-medium ${STATUS_COLORS[c.status || ""] || "text-bone-3"}`}>
                {c.status}
              </span>
            </div>
          </li>
        ))}
        {data?.items?.length === 0 && !isLoading && (
          <li className="text-bone-3 text-sm py-4 text-center">No coverage data available.</li>
        )}
      </ul>
    </Layout>
  );
}
