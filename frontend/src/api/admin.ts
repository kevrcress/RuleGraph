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

export const useTerminology = (page = 1) =>
  useQuery({
    queryKey: ["terminology", page],
    queryFn: async () => {
      const res = await apiClient.get("/terminology", { params: { page } });
      return res.data;
    },
  });

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
