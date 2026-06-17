import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { useViewStore } from "../store/viewStore";
import NotificationBell from "./NotificationBell";

interface NavItem { label: string; path: string }

const BASE_NAV: NavItem[] = [
  { label: "Rules",       path: "/rules" },
  { label: "Wiki",        path: "/wiki" },
  { label: "Chat",        path: "/chat" },
  { label: "Documents",   path: "/documents" },
  { label: "Diff",        path: "/diff" },
  { label: "Conflicts",   path: "/reports/conflicts" },
  { label: "Coverage",    path: "/reports/coverage" },
  { label: "Terminology", path: "/reports/terminology" },
];

const GRAPH_NAV: NavItem = { label: "Graph", path: "/graph" };

const ADMIN_SUBNAV: Record<string, NavItem[]> = {
  business_admin: [
    { label: "Review Queue", path: "/admin/review-queue" },
  ],
  tech_lead: [
    { label: "TL Dashboard",   path: "/admin/tech-lead-dashboard" },
    { label: "Wiki Promotion", path: "/admin/wiki-promotion" },
  ],
  admin: [
    { label: "Sources",       path: "/admin/sources" },
    { label: "Users",         path: "/admin/users" },
    { label: "Audit Log",     path: "/admin/audit-log" },
    { label: "Ingest Errors", path: "/admin/ingest-errors" },
    { label: "Settings",      path: "/admin/settings" },
  ],
};

function RoleAvatar({ name, role }: { name: string; role: string }) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const colors: Record<string, string> = {
    user:           "#6f87b6",
    business_admin: "#b8704a",
    tech_lead:      "#4d7a5f",
    admin:          "#7a5a9f",
  };
  const color = colors[role] ?? "#6f87b6";
  return (
    <span
      style={{
        width: 22, height: 22, borderRadius: 999,
        background: color + "22", color,
        display: "grid", placeItems: "center",
        fontSize: 10.5, fontWeight: 700, flexShrink: 0,
      }}
    >
      {initials}
    </span>
  );
}

function RoleLabel(role: string) {
  const map: Record<string, string> = {
    user: "User",
    business_admin: "Business Admin",
    tech_lead: "Tech Lead",
    admin: "Admin",
  };
  return map[role] ?? role;
}

interface Props { children: React.ReactNode }

export default function Layout({ children }: Props) {
  const { user, clearAuth } = useAuthStore();
  const { mode, toggle } = useViewStore();
  const location = useLocation();
  const navigate = useNavigate();

  const role = user?.role ?? "user";
  const showGraph = role === "tech_lead" || role === "admin";
  const primaryNav = showGraph ? [...BASE_NAV, GRAPH_NAV] : BASE_NAV;
  const subNav = ADMIN_SUBNAV[role] ?? [];

  const isActive = (path: string) =>
    location.pathname === path ||
    (path !== "/rules" && location.pathname.startsWith(path));

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  const showViewToggle = role === "tech_lead" || role === "admin";

  return (
    <div className="min-h-screen bg-surface text-ink font-sans">
      {/* Top bar */}
      <header
        style={{
          height: 60, background: "var(--panel)",
          borderBottom: "1px solid var(--line)",
          display: "flex", alignItems: "center",
          padding: "0 28px", gap: 24, position: "sticky", top: 0, zIndex: 40,
        }}
      >
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div
            style={{
              width: 28, height: 28, borderRadius: 8, background: "var(--accent)",
              display: "grid", placeItems: "center",
            }}
          >
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <circle cx="3.5" cy="3.5" r="2" fill="#fff" />
              <circle cx="12.5" cy="3.5" r="2" fill="#fff" opacity="0.7" />
              <circle cx="8" cy="12" r="2" fill="#fff" opacity="0.85" />
              <path d="M3.5 3.5L12.5 3.5M3.5 3.5L8 12M12.5 3.5L8 12" stroke="#fff" strokeWidth="0.9" opacity="0.4" />
            </svg>
          </div>
          <span style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-0.015em", color: "var(--ink)" }}>
            RuleGraph
          </span>
        </div>

        {/* Primary nav pills */}
        <nav style={{ display: "flex", alignItems: "center", gap: 2, marginLeft: 16 }}>
          {primaryNav.map((item) => {
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  padding: "7px 14px", borderRadius: 999,
                  color: active ? "var(--accent-deep)" : "var(--ink2)",
                  background: active ? "var(--accent-soft)" : "transparent",
                  textDecoration: "none", fontSize: 14,
                  fontWeight: active ? 600 : 500,
                  whiteSpace: "nowrap",
                  transition: "background 150ms, color 150ms",
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div style={{ flex: 1 }} />

        {/* Production chip */}
        <div
          style={{
            display: "inline-flex", alignItems: "center", gap: 7,
            padding: "5px 12px", background: "var(--ok-soft)", borderRadius: 999,
            fontSize: 12.5, color: "var(--accent-deep)", fontWeight: 500, flexShrink: 0,
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: 999, background: "var(--ok)" }} />
          Production
        </div>

        {/* Business / Technical toggle */}
        {showViewToggle && (
          <div
            style={{
              display: "flex", background: "var(--panel2)", borderRadius: 999,
              padding: 3, fontSize: 12.5, flexShrink: 0,
            }}
          >
            {(["business", "technical"] as const).map((m) => (
              <button
                key={m}
                onClick={() => mode !== m && toggle()}
                style={{
                  padding: "4px 12px", borderRadius: 999, border: 0, cursor: "pointer",
                  color: mode === m ? "var(--ink)" : "var(--ink3)",
                  background: mode === m ? "var(--panel)" : "transparent",
                  fontWeight: mode === m ? 600 : 400,
                  boxShadow: mode === m ? "0 1px 2px rgba(0,0,0,0.04)" : "none",
                  fontFamily: "var(--font-sans)", fontSize: 12.5,
                  transition: "background 150ms",
                }}
              >
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
        )}

        {/* Notification bell */}
        <NotificationBell />

        {/* User chip */}
        {user && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
            <div
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "4px 10px 4px 4px", border: "1px solid var(--line)",
                borderRadius: 999, fontSize: 12.5, color: "var(--ink2)",
              }}
            >
              <RoleAvatar name={user.name} role={user.role} />
              <span style={{ fontWeight: 600, color: "var(--ink)" }}>
                {RoleLabel(user.role)}
              </span>
              <span style={{ color: "var(--ink3)", fontSize: 11 }}>{user.name}</span>
            </div>
            <button
              onClick={handleLogout}
              style={{
                border: "1px solid var(--line)", background: "var(--panel)",
                padding: "5px 12px", borderRadius: 999, fontSize: 12.5,
                color: "var(--ink2)", cursor: "pointer", fontFamily: "var(--font-sans)",
              }}
            >
              Logout
            </button>
          </div>
        )}
      </header>

      {/* Admin sub-nav */}
      {subNav.length > 0 && (
        <div
          style={{
            background: "var(--panel)", borderBottom: "1px solid var(--line)",
            padding: "0 44px", display: "flex", gap: 2,
          }}
        >
          {subNav.map((item) => {
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  padding: "8px 14px",
                  borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
                  color: active ? "var(--accent-deep)" : "var(--ink3)",
                  textDecoration: "none", fontSize: 13,
                  fontWeight: active ? 600 : 500,
                  whiteSpace: "nowrap",
                  transition: "color 150ms, border-color 150ms",
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}

      <main style={{ padding: "28px 40px", maxWidth: 1280, margin: "0 auto" }}>
        {children}
      </main>
    </div>
  );
}
