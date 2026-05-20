import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

export interface DocumentItem {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: string;
  owner_id: string | null;
  created_at: string;
}

export interface PaginatedDocuments {
  items: DocumentItem[];
  total: number;
  page: number;
  limit: number;
}

export const useDocuments = (page = 1, limit = 50) =>
  useQuery({
    queryKey: ["documents", page, limit],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedDocuments>("/documents", {
        params: { page, limit },
      });
      return res.data;
    },
  });

export const useUploadDocument = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await apiClient.post("/documents", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });
};
