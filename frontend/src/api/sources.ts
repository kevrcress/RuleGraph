import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

export interface IngestSource {
  id: string;
  name: string;
  source_type: string;
  repo_url: string;
  branch: string;
  paths: string[] | null;
  exclude: string[] | null;
  test_paths: string[] | null;
  has_pat: boolean;
  created_at: string | null;
  last_ingested_at: string | null;
  status: string;
  ingest_status: string;
  ingest_error: string | null;
  ingest_progress: string | null;
  last_commit_sha: string | null;
  run_status: string | null;
  done_file_count: number;
  total_file_count: number;
  run_is_stale: boolean;
  can_resume: boolean;
}

export interface CreateSourcePayload {
  name: string;
  source_type?: string;
  repo_url: string;
  branch?: string;
  paths?: string[];
  exclude?: string[];
  test_paths?: string[];
  pat?: string;
}

export const useSources = () =>
  useQuery({
    queryKey: ["sources"],
    queryFn: async () => {
      const res = await apiClient.get("/admin/sources");
      return res.data as { items: IngestSource[]; total: number };
    },
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      return items.some((s) => s.ingest_status === "ingesting") ? 3000 : false;
    },
  });

export const useSource = (id: string) =>
  useQuery({
    queryKey: ["sources", id],
    queryFn: async () => {
      const res = await apiClient.get(`/admin/sources/${id}`);
      return res.data as IngestSource;
    },
    refetchInterval: (query) => {
      // Stop polling once we have a last_ingested_at value recorded after trigger
      return query.state.data ? false : 3000;
    },
  });

export interface UpdateSourcePayload {
  name?: string;
  branch?: string;
  paths?: string[];
  exclude?: string[];
  test_paths?: string[];
  pat?: string;
  status?: string;
}

export const useUpdateSource = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: UpdateSourcePayload }) => {
      const res = await apiClient.put(`/admin/sources/${id}`, payload);
      return res.data as IngestSource;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });
};

export const useCreateSource = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateSourcePayload) => {
      const res = await apiClient.post("/admin/sources", payload);
      return res.data as IngestSource;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });
};

export const useDeleteSource = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/admin/sources/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });
};

export const useTriggerIngest = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (sourceId: string) => {
      const res = await apiClient.post(`/admin/sources/${sourceId}/ingest`);
      return res.data as { status: string; source_name: string; message: string; run_id?: string };
    },
    onSuccess: () => {
      // Invalidate sources so last_ingested_at refreshes
      qc.invalidateQueries({ queryKey: ["sources"] });
    },
  });
};

export const useResumeSource = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (sourceId: string) => {
      const res = await apiClient.post(`/admin/sources/${sourceId}/resume`);
      return res.data as { status: string; source_name: string; message: string; run_id?: string };
    },
    onSuccess: () => {
      // Invalidate sources so progress fields refresh
      qc.invalidateQueries({ queryKey: ["sources"] });
    },
  });
};
