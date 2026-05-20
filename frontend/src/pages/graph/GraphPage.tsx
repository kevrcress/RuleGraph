import Layout from "../../components/Layout";
import GraphVisualization from "../../components/GraphVisualization";
import { useGraph } from "../../api/graph";

export default function GraphPage() {
  const { data, isLoading, isError } = useGraph();

  return (
    <Layout>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-bone-0">
          Knowledge Graph
        </h1>
        <span className="text-xs text-bone-3">
          {data
            ? `${data.nodes.length} nodes · ${data.edges.length} edges`
            : ""}
        </span>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-64 text-bone-3 text-sm">
          Loading graph…
        </div>
      )}

      {isError && (
        <div className="flex items-center justify-center h-64 text-ember text-sm">
          Failed to load graph data.
        </div>
      )}

      {data && data.nodes.length === 0 && (
        <div className="flex items-center justify-center h-64 bg-ink-1 rounded-lg border border-bone-4 text-bone-3 text-sm">
          No data in graph yet. Ingest some source files to populate the graph.
        </div>
      )}

      {data && data.nodes.length > 0 && (
        <GraphVisualization nodes={data.nodes} edges={data.edges} />
      )}
    </Layout>
  );
}
