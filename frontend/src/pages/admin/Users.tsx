import { useUsers } from "../../api/admin";
import Layout from "../../components/Layout";

export default function Users() {
  const { data, isLoading } = useUsers();

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">User Management</h1>
      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}

      <ul className="space-y-2">
        {data?.items?.map((u: { id: string; username: string; email: string; name: string; role: string; created_at: string }) => (
          <li key={u.id} className="bg-ink-2 border border-bone-4 rounded-lg p-4 flex items-center justify-between">
            <div>
              <p className="text-bone-0 font-medium">{u.name}</p>
              <p className="text-xs text-bone-3">{u.email} · {u.username}</p>
            </div>
            <span className="text-xs text-brass-0 capitalize">{u.role.replace("_", " ")}</span>
          </li>
        ))}
      </ul>
    </Layout>
  );
}
