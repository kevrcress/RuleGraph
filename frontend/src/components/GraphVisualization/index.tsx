import { useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
} from "reactflow";
import type { Node, Edge, NodeTypes } from "reactflow";
import "reactflow/dist/style.css";
import { useNavigate } from "react-router-dom";
import type { GraphNode, GraphEdge } from "../../api/graph";

// Custom node: Service
function ServiceNode({ data }: { data: { label: string } }) {
  return (
    <div className="px-3 py-2 rounded border-2 border-brass-0 bg-ink-1 text-bone-0 text-xs font-semibold min-w-[120px] text-center shadow">
      <Handle type="target" position={Position.Top} className="!bg-brass-0" />
      <div className="text-brass-0 text-[10px] uppercase tracking-wide mb-0.5">Service</div>
      <div>{data.label}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-brass-0" />
    </div>
  );
}

// Custom node: Rule
function RuleNode({ data }: { data: { label: string; status: string } }) {
  const statusColor: Record<string, string> = {
    active: "border-green-500",
    drift: "border-ember",
    proposed: "border-bone-3",
    under_review: "border-yellow-500",
    approved: "border-blue-400",
    deprecated: "border-bone-4",
    needs_update: "border-orange-400",
  };
  const border = statusColor[data.status] ?? "border-bone-4";

  return (
    <div
      className={`px-3 py-2 rounded border-2 ${border} bg-ink-2 text-bone-0 text-xs min-w-[140px] max-w-[200px] text-center shadow cursor-pointer hover:bg-ink-1 transition-colors`}
    >
      <Handle type="target" position={Position.Top} />
      <div className="text-bone-3 text-[10px] uppercase tracking-wide mb-0.5">Rule</div>
      <div className="font-medium leading-snug">{data.label}</div>
      <div className="text-[10px] mt-1 text-bone-3">{data.status}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  service: ServiceNode,
  rule: RuleNode,
};

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export default function GraphVisualization({ nodes, edges }: Props) {
  const navigate = useNavigate();

  const rfNodes: Node[] = nodes.map((n) => ({
    id: n.id,
    type: n.type,
    data: n.data,
    position: n.position,
  }));

  const rfEdges: Edge[] = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    type: e.type ?? "default",
    animated: e.label === "IMPLEMENTS",
    style: { stroke: "#7a5f1a", strokeWidth: 1.5 },
    labelStyle: { fontSize: 9, fill: "#7a756e" },
  }));

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const ruleId = node.data?.ruleId;
      if (ruleId) navigate(`/rules/${ruleId}`);
    },
    [navigate]
  );

  return (
    <div
      data-testid="graph-visualization"
      style={{ width: "100%", height: "600px" }}
      className="rounded-lg border border-bone-4 bg-ink-1 overflow-hidden"
    >
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={2}
        attributionPosition="bottom-right"
      >
        <Background color="#b0aaa3" gap={16} size={0.5} />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            if (n.type === "service") return "#7a5f1a";
            return "#5a554f";
          }}
          maskColor="rgba(240,237,232,0.6)"
        />
      </ReactFlow>
    </div>
  );
}
