import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

export interface ServiceImpact {
  id?: string;
  name: string;
}

export interface RuleImpact {
  id?: string;
  title: string;
  status: string;
}

export interface ImpactResponse {
  rule_id: string;
  summary?: string;
  services: ServiceImpact[];
  rules: RuleImpact[];
  tests: Array<{ name?: string; status: string }>;
  documents: Array<{ id?: string; filename: string }>;
  subscribed_count: number;
}

export interface ReverseImpactResponse {
  rule_id: string;
  upstream_services: ServiceImpact[];
  upstream_rules: RuleImpact[];
}

export interface FeedbackRequest {
  signal_type: string;
  rule_id: string;
}

export const useImpact = (ruleId: string, view = "technical") =>
  useQuery({
    queryKey: ["impact", ruleId, view],
    queryFn: async () => {
      const res = await apiClient.get<ImpactResponse>(
        `/rules/${ruleId}/impact`,
        { params: { view } }
      );
      return res.data;
    },
    enabled: !!ruleId,
  });

export const useReverseImpact = (ruleId: string, view = "technical") =>
  useQuery({
    queryKey: ["reverse-impact", ruleId, view],
    queryFn: async () => {
      const res = await apiClient.get<ReverseImpactResponse>(
        `/rules/${ruleId}/impact/reverse`,
        { params: { view } }
      );
      return res.data;
    },
    enabled: !!ruleId,
  });

export const useFeedback = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: FeedbackRequest) => {
      const res = await apiClient.post("/feedback", data);
      return res.data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["rule", vars.rule_id] });
    },
  });
};

export const useImprove = () =>
  useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/improve");
      return res.data;
    },
  });

export const useWikiPromote = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { change_ids: string[] }) => {
      const res = await apiClient.post("/wiki/promote", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
};
