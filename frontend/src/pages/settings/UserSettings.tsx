import { useAuthStore } from "../../store/authStore";
import Layout from "../../components/Layout";

export default function UserSettings() {
  const { user } = useAuthStore();

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">User Settings</h1>
      <div className="max-w-lg bg-ink-2 border border-bone-4 rounded-lg p-6 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-bone-2 mb-3">Profile</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-bone-3">Name</dt>
              <dd className="text-bone-0">{user?.name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-bone-3">Email</dt>
              <dd className="text-bone-0">{user?.email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-bone-3">Role</dt>
              <dd className="text-brass-0 capitalize">{user?.role?.replace("_", " ")}</dd>
            </div>
          </dl>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-bone-2 mb-2">Connected Accounts</h3>
          <p className="text-xs text-bone-3">
            No connected accounts. Connect Azure DevOps or GitHub to enable work item creation.
          </p>
          <button className="mt-2 px-3 py-1 text-xs border border-bone-4 text-bone-2 rounded hover:border-brass-0 hover:text-brass-0">
            + Connect ADO
          </button>
        </div>
      </div>
    </Layout>
  );
}
