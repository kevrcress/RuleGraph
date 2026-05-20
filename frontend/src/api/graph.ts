import { useQuery } from "@tanstack/react-query";
import apiClient from "./client";

export interface GraphNode {
  id: string;
  type: string;
  data: {
    label: string;
    nodeType: string;
    status?: string;
    ruleId?: string;
  };
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  type?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export const useGraph = () =>
  useQuery({
    queryKey: ["graph"],
    queryFn: async () => {
      const res = await apiClient.get<GraphData>("/graph");
      return res.data;
    },
  });
