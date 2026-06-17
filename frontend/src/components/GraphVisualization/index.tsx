import { useCallback } from "react";
import ReactFlow, { Background, Controls, MiniMap, Handle, Position } from "reactflow";
import type { Node, Edge, NodeTypes } from "reactflow";
import "reactflow/dist/style.css";
import { useNavigate } from "react-router-dom";
import type { GraphNode, GraphEdge } from "../../api/graph";

const STATUS_BORDER: Record<string, string> = {
  active:       "#4d7a5f",
  verified:     "#4d7a5f",
  approved:     "#4d7a5f",
  drift:        "#b87a2a",
  needs_update: "#b87a2a",
  conflict:     "#b1493b",
  proposed:     "#3a6a8e",
  under_review: "#3a6a8e",
  deprecated:   "#aaa9a0",
};

function ServiceNode({ data }: { data: { label: string } }) {
  return (
    <div style={{ padding: "8px 14px", borderRadius: 8, border: "2px solid var(--accent)", background: "var(--accent-soft)", color: "var(--accent-deep)", fontSize: 12, fontWeight: 600, minWidth: 120, textAlign: "center" }}>
      <Handle type="target" position={Position.Top} style={{ background: "var(--accent)" }} />
      <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2, opacity: 0.7 }}>Service</div>
      <div>{data.label}</div>
      <Handle type="source" position={Position.Bottom} style={{ background: "var(--accent)" }} />
    </div>
  );
}

function RuleNode({ data }: { data: { label: string; status: string } }) {
  const border = STATUS_BORDER[data.status] ?? "var(--line)";
  return (
    <div style={{ padding: "8px 14px", borderRadius: 8, border: `2px solid ${border}`, background: "var(--panel)", color: "var(--ink)", fontSize: 12, minWidth: 140, maxWidth: 200, textAlign: "center", cursor: "pointer" }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--ink3)", marginBottom: 2 }}>Rule</div>
      <div style={{ fontWeight: 500, lineHeight: 1.3 }}>{data.label}</div>
      <div style={{ fontSize: 10, marginTop: 4, color: "var(--ink3)" }}>{data.status}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes: NodeTypes = { service: ServiceNode, rule: RuleNode };

export default function GraphVisualization({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const navigate = useNavigate();

  const rfNodes: Node[] = nodes.map((n) => ({ id: n.id, type: n.type, data: n.data, position: n.position }));
  const rfEdges: Edge[] = edges.map((e) => ({
    id: e.id, source: e.source, target: e.target, label: e.label,
    type: e.type ?? "default", animated: e.label === "IMPLEMENTS",
    style: { stroke: "var(--accent)", strokeWidth: 1.5 },
    labelStyle: { fontSize: 9, fill: "var(--ink3)" },
  }));

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const ruleId = node.data?.ruleId;
      if (ruleId) navigate(`/rules/${ruleId}`);
    },
    [navigate]
  );

  return (
    <div data-testid="graph-visualization" style={{ width: "100%", height: 600 }}>
      <ReactFlow
        nodes={rfNodes} edges={rfEdges} nodeTypes={nodeTypes}
        onNodeClick={onNodeClick} fitView fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3} maxZoom={2} attributionPosition="bottom-right"
      >
        <Background color="var(--line)" gap={16} size={0.5} />
        <Controls />
        <MiniMap
          nodeColor={(n) => n.type === "service" ? "var(--accent)" : "var(--ink3)"}
          maskColor="rgba(250,248,244,0.6)"
        />
      </ReactFlow>
    </div>
  );
}
