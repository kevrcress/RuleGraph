import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

export interface ChatSource {
  type: string;
  id: string | null;
  title: string;
}

export interface ChatResponse {
  message: string;
  confidence: number;
  sources: ChatSource[];
  session_id: string;
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
  confidence?: number;
  sources?: ChatSource[];
  created_at: string;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatHistoryMessage[];
}

export interface Subscription {
  id: string;
  user_id: string | null;
  target_type: string;
  target_id: string;
  created_at: string | null;
}

export interface Notification {
  id: string;
  user_id: string | null;
  type: string;
  rule_id: string | null;
  message: string;
  read: boolean;
  created_at: string | null;
}

export interface PaginatedNotifications {
  items: Notification[];
  total: number;
  page: number;
  limit: number;
}

export interface PaginatedSubscriptions {
  items: Subscription[];
  total: number;
  page: number;
  limit: number;
}

export const useChat = () =>
  useMutation({
    mutationFn: async (data: { message: string; session_id: string; view: string }) => {
      const res = await apiClient.post<ChatResponse>("/chat", data);
      return res.data;
    },
  });

export const useChatHistory = (sessionId: string) =>
  useQuery({
    queryKey: ["chat-history", sessionId],
    queryFn: async () => {
      const res = await apiClient.get<ChatHistoryResponse>(`/chat/history?session_id=${sessionId}`);
      return res.data;
    },
    enabled: !!sessionId,
  });

export const useNotifications = (page = 1, limit = 50) =>
  useQuery({
    queryKey: ["notifications", page, limit],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedNotifications>("/notifications", {
        params: { page, limit },
      });
      return res.data;
    },
    refetchInterval: 30_000,
  });

export const useMarkNotificationRead = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.put<Notification>(`/notifications/${id}/read`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
};

export const useSubscriptions = () =>
  useQuery({
    queryKey: ["subscriptions"],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedSubscriptions>("/subscriptions");
      return res.data;
    },
  });

export const useSubscribe = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { target_type: string; target_id: string }) => {
      const res = await apiClient.post<Subscription>("/subscriptions", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  });
};

export const useUnsubscribe = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/subscriptions/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  });
};
