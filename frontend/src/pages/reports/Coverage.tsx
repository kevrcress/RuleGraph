import { useCoverage } from "../../api/admin";
import Layout from "../../components/Layout";

const STATUS_STYLE: Record<string, { color: string; label: string }> = {
  covered:      { color: "var(--ok)",     label: "Covered" },
  partial:      { color: "var(--warn)",   label: "Partial" },
  uncovered:    { color: "var(--danger)", label: "Uncovered" },
  coverage_gap: { color: "var(--warn)",   label: "Coverage gap" },
  stale:        { color: "var(--ink3)",   label: "Stale" },
};

export default function Coverage() {
  const { data, isLoading } = useCoverage();
  const items = data?.items ?? [];

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Coverage</h1>
      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {items.map((c: any) => {
          const s = STATUS_STYLE[c.coverage_status ?? ""] ?? { color: "var(--ink3)", label: c.coverage_status };
          return (
            <div
              key={c.id}
              style={{
                background: "var(--panel)", border: "1px solid var(--line)",
                borderRadius: 10, padding: "14px 18px",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}
            >
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>{c.title || c.id}</h3>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, color: s.color, fontWeight: 500 }}>
                <span style={{ width: 5, height: 5, borderRadius: 999, background: s.color }} />
                {s.label}
              </span>
            </div>
          );
        })}
        {items.length === 0 && !isLoading && (
          <div style={{ color: "var(--ink3)", fontSize: 13, textAlign: "center", padding: 32 }}>
            No coverage data available.
          </div>
        )}
      </div>
    </Layout>
  );
}
