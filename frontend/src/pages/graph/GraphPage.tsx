import Layout from "../../components/Layout";
import GraphVisualization from "../../components/GraphVisualization";
import { useGraph } from "../../api/graph";

export default function GraphPage() {
  const { data, isLoading, isError } = useGraph();

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Knowledge Graph</h1>
        {data && (
          <span style={{ fontSize: 13, color: "var(--ink3)" }}>
            {data.nodes.length} nodes · {data.edges.length} edges
          </span>
        )}
      </div>

      {isLoading && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 400, color: "var(--ink3)", fontSize: 13 }}>
          Loading graph…
        </div>
      )}
      {isError && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 400, color: "var(--danger)", fontSize: 13 }}>
          Failed to load graph data.
        </div>
      )}
      {data && data.nodes.length === 0 && (
        <div
          style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            height: 400, background: "var(--panel)", border: "1px solid var(--line)",
            borderRadius: 10, color: "var(--ink3)", fontSize: 13, textAlign: "center",
          }}
        >
          No data in graph yet. Ingest some source files to populate the graph.
        </div>
      )}
      {data && data.nodes.length > 0 && (
        <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, overflow: "hidden" }}>
          <GraphVisualization nodes={data.nodes} edges={data.edges} />
        </div>
      )}
    </Layout>
  );
}
