import { useNavigate, Link } from "react-router-dom";
import { useCreateRule } from "../../api/rules";
import Layout from "../../components/Layout";
import WikiEditor from "../../components/WikiEditor";

export default function NewRule() {
  const navigate = useNavigate();
  const { mutate, isPending } = useCreateRule();

  const handleSubmit = (data: { title: string; definition: string }) => {
    mutate(
      { ...data, source_type: "manual" },
      { onSuccess: (rule) => navigate(`/rules/${rule.id}`) }
    );
  };

  return (
    <Layout>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div style={{ fontSize: 12, color: "var(--ink3)", marginBottom: 10 }}>
          <Link to="/rules" style={{ color: "var(--ink3)", textDecoration: "none" }}>Rules</Link>
          {" · Propose"}
        </div>
        <h1 style={{ margin: "0 0 6px", fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em" }}>
          Propose a new rule
        </h1>
        <p style={{ color: "var(--ink2)", fontSize: 14, marginBottom: 28 }}>
          Drafted rules go to a Business Admin for review before being added to the catalog.
        </p>

        <div style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 12, padding: 24 }}>
          <WikiEditor onSubmit={handleSubmit} loading={isPending} />
        </div>
      </div>
    </Layout>
  );
}
