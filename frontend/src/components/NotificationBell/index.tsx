import { Bell } from "lucide-react";
import { useNotificationStore } from "../../store/notificationStore";

export default function NotificationBell() {
  const { unreadCount, feedOpen, toggleFeed, notifications, closeFeed } =
    useNotificationStore();

  return (
    <div className="relative">
      <button
        data-testid="notification-bell"
        onClick={toggleFeed}
        className="relative p-2 text-bone-1 hover:text-brass-0 transition-colors"
        aria-label="Notifications"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-ember text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>

      {feedOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={closeFeed}
          />
          <div
            data-testid="notification-feed"
            className="absolute right-0 top-10 w-80 bg-ink-2 border border-bone-4 rounded-lg shadow-xl z-20 max-h-96 overflow-y-auto"
          >
            <div className="p-3 border-b border-bone-4">
              <h3 className="text-sm font-semibold text-bone-0">Notifications</h3>
            </div>
            {notifications.length === 0 ? (
              <div className="p-4 text-sm text-bone-3 text-center">
                No notifications
              </div>
            ) : (
              <ul>
                {notifications.map((n) => (
                  <li
                    key={n.id}
                    className={`p-3 border-b border-bone-4 text-sm ${
                      n.read ? "text-bone-3" : "text-bone-0"
                    }`}
                  >
                    <div className="font-medium">{n.type}</div>
                    <div className="text-xs mt-1">{n.message}</div>
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
