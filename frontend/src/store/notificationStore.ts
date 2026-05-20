import { create } from "zustand";

interface Notification {
  id: string;
  type: string;
  message: string;
  read: boolean;
  created_at: string | null;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  feedOpen: boolean;
  setNotifications: (n: Notification[]) => void;
  markRead: (id: string) => void;
  toggleFeed: () => void;
  closeFeed: () => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  feedOpen: false,
  setNotifications: (notifications) => {
    set({ notifications, unreadCount: notifications.filter((n) => !n.read).length });
  },
  markRead: (id) => {
    const updated = get().notifications.map((n) =>
      n.id === id ? { ...n, read: true } : n
    );
    set({ notifications: updated, unreadCount: updated.filter((n) => !n.read).length });
  },
  toggleFeed: () => set((s) => ({ feedOpen: !s.feedOpen })),
  closeFeed: () => set({ feedOpen: false }),
}));
