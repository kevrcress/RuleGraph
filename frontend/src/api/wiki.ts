import { useQuery } from "@tanstack/react-query";
import apiClient from "./client";

export interface WikiPageItem {
  id: string;
  module: string;
  title: string;
  content: string;
  linked_rule_ids: string[];
  last_generated_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface LinkedRule {
  id: string;
  title: string;
  status: string;
}

export interface WikiPageDetail extends WikiPageItem {
  linked_rules: LinkedRule[];
}

export interface PaginatedWikiPages {
  items: WikiPageItem[];
  total: number;
  page: number;
  limit: number;
}

export const useWikiPages = (
  page = 1,
  limit = 50,
  search = "",
  sort = "updated_at",
  order: "asc" | "desc" = "desc"
) =>
  useQuery({
    queryKey: ["wiki", page, limit, search, sort, order],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedWikiPages>("/wiki", {
        params: { page, limit, search, sort, order },
      });
      return res.data;
    },
  });

export const useWikiPage = (id: string) =>
  useQuery({
    queryKey: ["wiki", id],
    queryFn: async () => {
      const res = await apiClient.get<WikiPageDetail>(`/wiki/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
