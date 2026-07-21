import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

export interface IngestRunInfo {
  id: string;
  source_name: string;
  status: string | null;
  batch_status: string | null;
  files_processed: number;
  files_errored: number;
  started_at: string | null;
}

export interface IngestFileCheckpointInfo {
  id: string;
  file_path: string;
  status: "pending" | "processing" | "done" | "error";
  error_message: string | null;
  processed_at: string | null;
}

export interface PaginatedCheckpointsResponse {
  items: IngestFileCheckpointInfo[];
  total: number;
  run: IngestRunInfo | null;
}

export const useSourceIngestStatus = (
  sourceId: string,
  page = 1,
  pageSize = 50
) =>
  useQuery({
    queryKey: ["ingest-runs", sourceId, "files", page, pageSize],
    queryFn: async () => {
      const res = await apiClient.get(
        `/admin/sources/${sourceId}/ingest-runs/latest/files`,
        { params: { page, page_size: pageSize } }
      );
      return res.data as PaginatedCheckpointsResponse;
    },
    refetchInterval: (query) => {
      const batch = query.state.data?.run?.batch_status;
      return batch === "running" ? 3000 : false;
    },
  });

export interface RetryErrorsResponse {
  status: string;
  source_name: string;
  message: string;
  run_id?: string;
}

export const useRetryErrors = (sourceId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/admin/sources/${sourceId}/retry-errors`);
      return res.data as RetryErrorsResponse;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sources"] });
      qc.invalidateQueries({ queryKey: ["ingest-runs", sourceId] });
    },
  });
};
