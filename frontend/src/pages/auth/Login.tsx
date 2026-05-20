import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import apiClient from "../../api/client";
import { useAuthStore } from "../../store/authStore";
import { useViewStore } from "../../store/viewStore";
import { AxiosError } from "axios";

export default function Login() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const { setMode } = useViewStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const loginRes = await apiClient.post("/auth/login", { email, password });
      const token = loginRes.data.access_token;

      // Decode JWT (base64url → base64 → JSON)
      const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
      const payload = JSON.parse(atob(padded));

      const user = {
        id: payload.sub,
        username: payload.username || email.split("@")[0],
        email,
        name: payload.name || email,
        role: payload.role || "user",
      };

      setAuth(token, user);

      // Set default view based on role
      const technicalRoles = ["tech_lead", "admin"];
      setMode(technicalRoles.includes(user.role) ? "technical" : "business");

      navigate("/rules");
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>;
      setError(axiosErr.response?.data?.detail || "Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink-0 flex items-center justify-center">
      <div className="w-full max-w-sm bg-ink-1 border border-bone-4 rounded-lg p-8">
        <h1 className="text-2xl font-serif text-brass-0 mb-6 text-center">RuleGraph</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-bone-2 mb-1">Email</label>
            <input
              name="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-ink-3 border border-bone-4 rounded px-3 py-2 text-bone-0 focus:outline-none focus:border-brass-0"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-bone-2 mb-1">Password</label>
            <input
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-ink-3 border border-bone-4 rounded px-3 py-2 text-bone-0 focus:outline-none focus:border-brass-0"
            />
          </div>
          {error && (
            <div
              data-testid="error"
              role="alert"
              className="error text-ember text-sm bg-ember/10 border border-ember/30 rounded p-2"
            >
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brass-0 text-ink-0 py-2 rounded font-semibold hover:bg-brass-1 disabled:opacity-50 transition-colors"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-bone-3">
          No account?{" "}
          <Link to="/register" className="text-brass-0 hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
