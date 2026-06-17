import { useAuthStore } from "../../store/authStore";
import Layout from "../../components/Layout";

const ROLE_LABELS: Record<string, string> = {
  user: "User",
  business_admin: "Business Admin",
  tech_lead: "Tech Lead",
  admin: "Admin",
};

export default function UserSettings() {
  const { user } = useAuthStore();

  const initials = user?.name
    ? user.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
    : "?";

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Your Settings</h1>

      <div style={{ maxWidth: 560, display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Profile card */}
        <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
            <div
              style={{
                width: 48, height: 48, borderRadius: 999,
                background: "var(--accent-soft)", color: "var(--accent-deep)",
                display: "grid", placeItems: "center",
                fontSize: 18, fontWeight: 700,
              }}
            >
              {initials}
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{user?.name}</div>
              <div style={{ fontSize: 13, color: "var(--ink3)" }}>{ROLE_LABELS[user?.role ?? "user"] ?? user?.role}</div>
            </div>
          </div>

          <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 12 }}>
            Profile
          </div>
          <dl style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 0", fontSize: 13 }}>
            {[
              { label: "Name",     value: user?.name },
              { label: "Email",    value: user?.email },
              { label: "Username", value: user?.username },
              { label: "Role",     value: ROLE_LABELS[user?.role ?? ""] ?? user?.role },
            ].map(({ label, value }) => (
              <>
                <dt key={label + "-dt"} style={{ color: "var(--ink3)" }}>{label}</dt>
                <dd key={label + "-dd"} style={{ margin: 0, color: "var(--ink)" }}>{value || "—"}</dd>
              </>
            ))}
          </dl>
        </div>

        {/* Connected accounts */}
        <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: 24 }}>
          <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 12 }}>
            Connected Accounts
          </div>
          <p style={{ fontSize: 13, color: "var(--ink3)", margin: "0 0 12px" }}>
            No connected accounts. Connect Azure DevOps or GitHub to enable work item creation.
          </p>
          <button
            style={{
              padding: "7px 14px", border: "1px solid var(--line)",
              borderRadius: 999, background: "var(--panel)",
              color: "var(--ink2)", fontSize: 13, cursor: "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            + Connect ADO
          </button>
        </div>
      </div>
    </Layout>
  );
}
