import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import apiClient from "../../api/client";
import { AxiosError } from "axios";

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 12px",
  border: "1px solid var(--line)", borderRadius: 8,
  fontSize: 14, fontFamily: "var(--font-sans)",
  background: "var(--panel)", color: "var(--ink)",
  outline: "none",
};

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", email: "", name: "", password: "" });
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
    <div style={{ minHeight: "100vh", background: "var(--surface)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 380, background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, padding: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "center", marginBottom: 28 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--accent)", display: "grid", placeItems: "center" }}>
            <svg width="17" height="17" viewBox="0 0 16 16" fill="none">
              <circle cx="3.5" cy="3.5" r="2" fill="#fff" />
              <circle cx="12.5" cy="3.5" r="2" fill="#fff" opacity="0.7" />
              <circle cx="8" cy="12" r="2" fill="#fff" opacity="0.85" />
              <path d="M3.5 3.5L12.5 3.5M3.5 3.5L8 12M12.5 3.5L8 12" stroke="#fff" strokeWidth="0.9" opacity="0.4" />
            </svg>
          </div>
          <span style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.015em" }}>Create Account</span>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {[
            { key: "username", label: "Username", type: "text" },
            { key: "email",    label: "Email",    type: "email" },
            { key: "name",     label: "Full Name", type: "text" },
            { key: "password", label: "Password",  type: "password" },
          ].map(({ key, label, type }) => (
            <div key={key}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--ink)", marginBottom: 6 }}>{label}</label>
              <input
                name={key}
                type={type}
                value={form[key as keyof typeof form]}
                onChange={set(key)}
                required
                style={inputStyle}
              />
            </div>
          ))}

          {error && (
            <div
              role="alert"
              className="error"
              style={{
                fontSize: 13, color: "var(--danger)",
                background: "var(--danger-soft)",
                border: "1px solid var(--danger)",
                borderRadius: 8, padding: "8px 12px",
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%", padding: "10px 16px",
              background: loading ? "var(--accent-soft)" : "var(--accent)",
              color: loading ? "var(--accent-deep)" : "#fff",
              border: 0, borderRadius: 999,
              fontSize: 14, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
              fontFamily: "var(--font-sans)", transition: "background 150ms",
            }}
          >
            {loading ? "Creating…" : "Register"}
          </button>
        </form>

        <p style={{ marginTop: 20, textAlign: "center", fontSize: 13, color: "var(--ink3)" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
