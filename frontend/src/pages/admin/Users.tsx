import { useUsers } from "../../api/admin";
import Layout from "../../components/Layout";

const ROLE_COLORS: Record<string, string> = {
  admin:          "var(--info)",
  tech_lead:      "var(--ok)",
  business_admin: "var(--clay)",
  user:           "var(--ink3)",
};

export default function Users() {
  const { data, isLoading } = useUsers();

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.022em" }}>Users</h1>
      {isLoading && <div style={{ color: "var(--ink3)", fontSize: 13 }}>Loading…</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data?.items?.map((u: any) => (
          <div
            key={u.id}
            style={{
              background: "var(--panel)", border: "1px solid var(--line)",
              borderRadius: 10, padding: "14px 18px",
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div
                style={{
                  width: 32, height: 32, borderRadius: 999,
                  background: (ROLE_COLORS[u.role] ?? "var(--ink3)") + "22",
                  color: ROLE_COLORS[u.role] ?? "var(--ink3)",
                  display: "grid", placeItems: "center",
                  fontSize: 12, fontWeight: 700,
                }}
              >
                {u.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
              </div>
              <div>
                <p style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>{u.name}</p>
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--ink3)" }}>{u.email} · {u.username}</p>
              </div>
            </div>
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                fontSize: 12, color: ROLE_COLORS[u.role] ?? "var(--ink3)",
                background: (ROLE_COLORS[u.role] ?? "var(--ink3)") + "18",
                padding: "3px 10px", borderRadius: 999, fontWeight: 500,
              }}
            >
              {u.role.replace("_", " ")}
            </span>
          </div>
        ))}
      </div>
    </Layout>
  );
}
