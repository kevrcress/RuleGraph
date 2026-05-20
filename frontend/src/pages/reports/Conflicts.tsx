import { Bell, BellOff } from "lucide-react";
import { useConflicts } from "../../api/admin";
import { useSubscriptions, useSubscribe, useUnsubscribe } from "../../api/chat";
import Layout from "../../components/Layout";

function ConflictSubscribeButton({ conflictId }: { conflictId: string }) {
  const { data: subs } = useSubscriptions();
  const subscribe = useSubscribe();
  const unsubscribe = useUnsubscribe();

  const existing = subs?.items.find(
    (s) => s.target_type === "conflict" && s.target_id === conflictId
  );

  if (existing) {
    return (
      <button
        onClick={() => unsubscribe.mutate(existing.id)}
        className="inline-flex items-center gap-1 text-xs text-bone-3 hover:text-ember border border-bone-4 rounded px-2 py-1"
      >
        <BellOff size={12} /> Unsubscribe
      </button>
    );
  }

  return (
    <button
      onClick={() => subscribe.mutate({ target_type: "conflict", target_id: conflictId })}
      className="inline-flex items-center gap-1 text-xs text-bone-2 hover:text-brass-0 border border-bone-4 rounded px-2 py-1"
    >
      <Bell size={12} /> Subscribe
    </button>
  );
}

export default function Conflicts() {
  const { data, isLoading } = useConflicts();

  return (
    <Layout>
      <h1 className="text-xl font-serif text-bone-0 mb-4">Conflicts</h1>
      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}
      <ul className="space-y-2">
        {data?.items?.map((c: { id: string; rule_a_title?: string; rule_b_title?: string; conflict_type?: string; description?: string; created_at?: string }) => (
          <li key={c.id} className="bg-ink-2 border border-bone-4 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-bone-0 text-sm font-medium">
                  {c.rule_a_title} ↔ {c.rule_b_title}
                </h3>
                <p className="text-xs text-bone-3 mt-1">{c.conflict_type}</p>
                {c.description && <p className="text-sm text-bone-2 mt-2">{c.description}</p>}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-ember">Conflict</span>
                <ConflictSubscribeButton conflictId={c.id} />
              </div>
            </div>
          </li>
        ))}
        {data?.items?.length === 0 && !isLoading && (
          <li className="text-bone-3 text-sm py-4 text-center">No conflicts detected.</li>
        )}
      </ul>
    </Layout>
  );
}
