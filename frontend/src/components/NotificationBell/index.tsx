import { useEffect } from "react";
import { useNotificationStore } from "../../store/notificationStore";
import { useNotifications, useMarkNotificationRead } from "../../api/chat";

export default function NotificationBell() {
  const { unreadCount, feedOpen, toggleFeed, notifications, closeFeed, setNotifications, markRead: markLocalRead } =
    useNotificationStore();

  const { data } = useNotifications(1, 50);
  const markReadMutation = useMarkNotificationRead();

  useEffect(() => {
    if (data?.items) setNotifications(data.items);
  }, [data]);

  const handleMarkRead = async (id: string) => {
    markLocalRead(id);
    await markReadMutation.mutateAsync(id);
  };

  return (
    <div style={{ position: "relative", flexShrink: 0 }}>
      <button
        data-testid="notification-bell"
        onClick={toggleFeed}
        aria-label="Notifications"
        style={{
          border: 0, background: "transparent", width: 32, height: 32,
          borderRadius: 999, display: "grid", placeItems: "center",
          position: "relative", cursor: "pointer",
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--ink2)" strokeWidth="1.6">
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute", top: 5, right: 6,
              width: 7, height: 7, borderRadius: 999,
              background: "var(--clay)", border: "2px solid var(--panel)",
            }}
          />
        )}
      </button>

      {feedOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={closeFeed} />
          <div
            data-testid="notification-feed"
            style={{
              position: "absolute", right: 0, top: "calc(100% + 8px)",
              width: 320, background: "var(--panel)", border: "1px solid var(--line)",
              borderRadius: 10, boxShadow: "0 8px 24px rgba(40,40,30,0.12)",
              zIndex: 30, maxHeight: 384, overflowY: "auto",
            }}
          >
            <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line2)" }}>
              <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Notifications</h3>
            </div>
            {notifications.length === 0 ? (
              <div style={{ padding: 16, fontSize: 13, color: "var(--ink3)", textAlign: "center" }}>
                No notifications
              </div>
            ) : (
              <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                {notifications.map((n) => (
                  <li
                    key={n.id}
                    style={{
                      padding: "12px 16px", borderBottom: "1px solid var(--line2)",
                      color: n.read ? "var(--ink3)" : "var(--ink)", fontSize: 13,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{n.type}</div>
                        <div style={{ fontSize: 12, marginTop: 2, color: "var(--ink3)" }}>{n.message}</div>
                      </div>
                      {!n.read && (
                        <button
                          onClick={() => handleMarkRead(n.id)}
                          style={{
                            border: 0, background: "none", cursor: "pointer",
                            fontSize: 12, color: "var(--accent)", fontWeight: 600,
                            flexShrink: 0, fontFamily: "var(--font-sans)",
                          }}
                        >
                          Mark read
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
