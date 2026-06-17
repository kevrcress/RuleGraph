import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

export interface RuleListItem {
  id: string;
  title: string;
  definition: string;
  status: string;
  extraction_confidence: number | null;
  source_type: string | null;
  created_at: string | null;
}

export interface RuleDetail extends RuleListItem {
  owner_id: string | null;
  environment: string | null;
  source_file: string | null;
  graph_quality_score: number | null;
  cognee_node_id: string | null;
  workitem_id: string | null;
  workitem_url: string | null;
  coverage_status: string | null;
  code_behavior: string | null;
  updated_at: string | null;
  deprecated_at: string | null;
}

export interface PaginatedRules {
  items: RuleListItem[];
  total: number;
  page: number;
  limit: number;
}

export const useDriftRules = () =>
  useQuery({
    queryKey: ["rules", "drift"],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedRules>("/rules", { params: { status: "drift", limit: 200 } });
      return res.data.items as RuleDetail[];
    },
  });

export const useRules = (page = 1, limit = 200, search?: string, sort = "created_at", order = "desc") =>
  useQuery({
    queryKey: ["rules", page, limit, search, sort, order],
    queryFn: async () => {
      const params: Record<string, unknown> = { page, limit, sort, order };
      const res = await apiClient.get<PaginatedRules>("/rules", { params });
      let items = res.data.items;
      if (search) {
        const lower = search.toLowerCase();
        items = items.filter(
          (r) =>
            r.title.toLowerCase().includes(lower) ||
            (r.source_type?.toLowerCase().includes(lower) ?? false)
        );
      }
      return { ...res.data, items };
    },
  });

export const useRule = (id: string) =>
  useQuery({
    queryKey: ["rule", id],
    queryFn: async () => {
      const res = await apiClient.get<RuleDetail>(`/rules/${id}`);
      return res.data;
    },
    enabled: !!id,
  });

export const useUpdateRuleStatus = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const res = await apiClient.put(`/rules/${id}`, { status });
      return res.data;
    },
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ["rules"] });
      qc.invalidateQueries({ queryKey: ["rule", id] });
    },
  });
};

export const useCreateRule = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { title: string; definition: string; source_type?: string }) => {
      const res = await apiClient.post("/rules", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
};
