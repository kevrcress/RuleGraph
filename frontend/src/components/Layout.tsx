import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import ViewToggle from "./ViewToggle";
import NotificationBell from "./NotificationBell";

interface Props {
  children: React.ReactNode;
}

export default function Layout({ children }: Props) {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  const isAdmin = user?.role === "admin";
  const isTL = user?.role === "tech_lead";
  const isBA = user?.role === "business_admin";

  return (
    <div className="min-h-screen bg-ink-0 text-bone-0 font-sans">
      <nav className="bg-ink-1 border-b border-bone-4 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-brass-0 font-serif font-semibold text-lg">
              RuleGraph
            </Link>
            <Link to="/rules" className="text-sm text-bone-2 hover:text-bone-0">Rules</Link>
            <Link to="/chat" className="text-sm text-bone-2 hover:text-bone-0">Chat</Link>
            <Link to="/documents" className="text-sm text-bone-2 hover:text-bone-0">Documents</Link>
            <Link to="/diff" className="text-sm text-bone-2 hover:text-bone-0">Diff</Link>
            {(isBA || isAdmin) && (
              <Link to="/admin/review-queue" className="text-sm text-bone-2 hover:text-bone-0">Review Queue</Link>
            )}
            {(isTL || isAdmin) && (
              <Link to="/admin/tech-lead-dashboard" className="text-sm text-bone-2 hover:text-bone-0">TL Dashboard</Link>
            )}
            {isAdmin && (
              <Link to="/admin/users" className="text-sm text-bone-2 hover:text-bone-0">Admin</Link>
            )}
          </div>
          <div className="flex items-center gap-4">
            <ViewToggle />
            <NotificationBell />
            <span className="text-xs text-bone-3">{user?.name}</span>
            <button
              onClick={handleLogout}
              className="text-xs text-bone-3 hover:text-bone-1"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
