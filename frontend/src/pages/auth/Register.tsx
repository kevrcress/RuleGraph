import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import apiClient from "../../api/client";
import { AxiosError } from "axios";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    email: "",
    name: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await apiClient.post("/auth/register", { ...form, role: "user" });
      navigate("/login");
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>;
      setError(axiosErr.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink-0 flex items-center justify-center">
      <div className="w-full max-w-sm bg-ink-1 border border-bone-4 rounded-lg p-8">
        <h1 className="text-2xl font-serif text-brass-0 mb-6 text-center">Create Account</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: "username", label: "Username", type: "text" },
            { key: "email", label: "Email", type: "email" },
            { key: "name", label: "Full Name", type: "text" },
            { key: "password", label: "Password", type: "password" },
          ].map(({ key, label, type }) => (
            <div key={key}>
              <label className="block text-sm text-bone-2 mb-1">{label}</label>
              <input
                name={key}
                type={type}
                value={form[key as keyof typeof form]}
                onChange={set(key)}
                required
                className="w-full bg-ink-3 border border-bone-4 rounded px-3 py-2 text-bone-0 focus:outline-none focus:border-brass-0"
              />
            </div>
          ))}
          {error && (
            <div role="alert" className="error text-ember text-sm bg-ember/10 border border-ember/30 rounded p-2">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brass-0 text-ink-0 py-2 rounded font-semibold hover:bg-brass-1 disabled:opacity-50 transition-colors"
          >
            {loading ? "Creating…" : "Register"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-bone-3">
          Already have an account?{" "}
          <Link to="/login" className="text-brass-0 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
