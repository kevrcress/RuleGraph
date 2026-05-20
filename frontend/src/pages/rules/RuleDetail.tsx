import { useParams, Link } from "react-router-dom";
import { useRule } from "../../api/rules";
import Layout from "../../components/Layout";
import CompareView from "../../components/CompareView";

export default function RuleDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: rule, isLoading, isError } = useRule(id || "");

  return (
    <Layout>
      <div className="mb-4">
        <Link to="/rules" className="text-sm text-bone-3 hover:text-bone-1">
          ← Back to Rules
        </Link>
      </div>

      {isLoading && <div className="text-bone-3 text-sm">Loading…</div>}
      {isError && <div className="text-ember text-sm">Rule not found.</div>}

      {rule && (
        <div className="max-w-3xl">
          <div className="bg-ink-2 border border-bone-4 rounded-lg p-6">
            <CompareView rule={rule} />
          </div>

          <div className="mt-4 bg-ink-2 border border-bone-4 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-bone-2 mb-2">Details</h4>
            <dl className="grid grid-cols-2 gap-2 text-xs text-bone-3">
              <dt>ID</dt>
              <dd className="font-mono">{rule.id}</dd>
              <dt>Source</dt>
              <dd>{rule.source_type || "—"}</dd>
              {rule.extraction_confidence != null && (
                <>
                  <dt>Confidence</dt>
                  <dd>{Math.round(rule.extraction_confidence * 100)}%</dd>
                </>
              )}
              <dt>Created</dt>
              <dd>{rule.created_at ? new Date(rule.created_at).toLocaleString() : "—"}</dd>
            </dl>
          </div>
        </div>
      )}
    </Layout>
  );
}
