import { useNavigate } from "react-router-dom";
import { useCreateRule } from "../../api/rules";
import Layout from "../../components/Layout";
import WikiEditor from "../../components/WikiEditor";

export default function NewRule() {
  const navigate = useNavigate();
  const { mutate, isPending } = useCreateRule();

  const handleSubmit = (data: { title: string; definition: string }) => {
    mutate(
      { ...data, source_type: "manual" },
      {
        onSuccess: (rule) => navigate(`/rules/${rule.id}`),
      }
    );
  };

  return (
    <Layout>
      <div className="max-w-2xl">
        <div className="mb-6">
          <h1 className="text-xl font-serif text-bone-0">Propose New Rule</h1>
          <p className="text-sm text-bone-3 mt-1">
            Define a business rule. It will be sent to the review queue.
          </p>
        </div>
        <div className="bg-ink-2 border border-bone-4 rounded-lg p-6">
          <WikiEditor onSubmit={handleSubmit} loading={isPending} />
        </div>
      </div>
    </Layout>
  );
}
