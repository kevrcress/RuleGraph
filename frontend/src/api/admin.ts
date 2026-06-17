import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

export const useReviewQueue = (page = 1) =>
  useQuery({
    queryKey: ["review-queue", page],
    queryFn: async () => {
      const res = await apiClient.get("/admin/review-queue", { params: { page } });
      return res.data;
    },
  });

export const useApproveRule = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ruleId: string) => {
      const res = await apiClient.put(`/admin/review-queue/${ruleId}/approve`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["rules"] });
    },
  });
};

export const useBulkApproveRules = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ruleIds: string[] | "all") => {
      const res = await apiClient.post("/admin/review-queue/bulk-approve", {
        rule_ids: ruleIds === "all" ? ["all"] : ruleIds,
      });
      return res.data as { approved: number; message: string };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["rules"] });
    },
  });
};

export const useRejectRule = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ruleId, note }: { ruleId: string; note: string }) => {
      const res = await apiClient.put(`/admin/review-queue/${ruleId}/reject`, {
        rejection_note: note,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["rules"] });
    },
  });
};

export const useTLDashboard = (page = 1) =>
  useQuery({
    queryKey: ["tl-dashboard", page],
    queryFn: async () => {
      const res = await apiClient.get("/admin/tech-lead-dashboard", { params: { page } });
      return res.data;
    },
  });

export const useAuditLog = (page = 1) =>
  useQuery({
    queryKey: ["audit-log", page],
    queryFn: async () => {
      const res = await apiClient.get("/admin/audit-log", { params: { page } });
      return res.data;
    },
  });

export const useUsers = (page = 1) =>
  useQuery({
    queryKey: ["admin-users", page],
    queryFn: async () => {
      const res = await apiClient.get("/admin/users", { params: { page } });
      return res.data;
    },
  });

export const useIngestErrors = (page = 1) =>
  useQuery({
    queryKey: ["ingest-errors", page],
    queryFn: async () => {
      const res = await apiClient.get("/admin/ingest-errors", { params: { page } });
      return res.data;
    },
  });

export const useSystemSettings = () =>
  useQuery({
    queryKey: ["system-settings"],
    queryFn: async () => {
      const res = await apiClient.get("/admin/settings");
      return res.data;
    },
  });

export const useUpdateSettings = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (updates: Record<string, string>) => {
      const res = await apiClient.put("/admin/settings", updates);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["system-settings"] }),
  });
};

export const useConflicts = (page = 1) =>
  useQuery({
    queryKey: ["conflicts", page],
    queryFn: async () => {
      const res = await apiClient.get("/conflicts", { params: { page } });
      return res.data;
    },
  });

export const useCoverage = (page = 1) =>
  useQuery({
    queryKey: ["coverage", page],
    queryFn: async () => {
      const res = await apiClient.get("/coverage", { params: { page } });
      return res.data;
    },
  });

export const useTerminology = (page = 1, issuesOnly = false) =>
  useQuery({
    queryKey: ["terminology", page, issuesOnly],
    queryFn: async () => {
      const res = await apiClient.get("/terminology", {
        params: { page, issues_only: issuesOnly },
      });
      return res.data;
    },
  });

export const useRescanTerminology = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/terminology/rescan");
      return res.data as {
        services_scanned: number;
        terms_before: number;
        terms_after: number;
        terms_added: number;
      };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["terminology"] }),
  });
};

export const useInferDefinition = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (termId: string) => {
      const res = await apiClient.post(`/terminology/${termId}/infer`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["terminology"] }),
  });
};

export const useUpdateDefinition = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      termId,
      definition,
      definition_status,
    }: {
      termId: string;
      definition?: string;
      definition_status?: string;
    }) => {
      const res = await apiClient.patch(`/terminology/${termId}`, {
        definition,
        definition_status,
      });
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["terminology"] }),
  });
};

export const useClearData = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (preview: boolean) => {
      const res = await apiClient.delete(
        `/admin/data${preview ? "" : "?confirm=true"}`
      );
      return res.data;
    },
    onSuccess: (_data, preview) => {
      if (!preview) {
        qc.invalidateQueries();
      }
    },
  });
};

export const useExportSnapshot = () =>
  useMutation({
    mutationFn: async () => {
      const res = await apiClient.get("/admin/export", { responseType: "blob" });
      const cd = res.headers["content-disposition"] as string | undefined;
      const filename = cd?.match(/filename="(.+)"/)?.[1] ?? "rulegraph_export.zip";
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

export const useRunImprove = () =>
  useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/improve");
      return res.data as { rules_updated: number; message: string };
    },
  });

export const useRunLint = () =>
  useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/lint");
      return res.data as { message: string; warnings?: string[] };
    },
  });

export const useRegenerateWiki = () =>
  useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/wiki/regenerate");
      return res.data as { status: string; message: string };
    },
  });

export const useImportSnapshot = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await apiClient.post("/admin/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data as { status: string; total_rows: number; tables: Record<string, number> };
    },
    onSuccess: () => qc.invalidateQueries(),
  });
};
