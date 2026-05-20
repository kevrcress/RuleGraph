import { useQuery } from "@tanstack/react-query";
import apiClient from "./client";

export interface DiffItem {
  rule_id: string;
  title: string;
  status: string;
  change_type: string;
  changed_at: string;
}

export interface PaginatedDiff {
  items: DiffItem[];
  total: number;
  page: number;
  limit: number;
}

export interface DiffVersion {
  definition: string | null;
  status: string | null;
  changed_at: string;
  change_note: string | null;
}

export interface DiffDetail {
  rule_id: string;
  rule_title: string;
  before: DiffVersion | null;
  after: DiffVersion | null;
  versions: DiffVersion[];
}

export const useDiffList = (page = 1) =>
  useQuery({
    queryKey: ["diff", page],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedDiff>("/diff", { params: { page } });
      return res.data;
    },
  });

export const useRuleDiff = (ruleId: string) =>
  useQuery({
    queryKey: ["diff", ruleId],
    queryFn: async () => {
      const res = await apiClient.get<DiffDetail>(`/diff/${ruleId}`);
      return res.data;
    },
    enabled: !!ruleId,
  });
