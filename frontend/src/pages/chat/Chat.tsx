import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { Send } from "lucide-react";
import Layout from "../../components/Layout";
import StatusBadge from "../../components/StatusBadge";
import { useChat, useChatHistory } from "../../api/chat";
import type { ChatHistoryMessage, ChatSource } from "../../api/chat";
import { useViewStore } from "../../store/viewStore";
import { useCreateRule } from "../../api/rules";

function SourceLink({ source }: { source: ChatSource }) {
  if (source.type === "rule" && source.id) {
    return (
      <div
        style={{
          display: "flex", alignItems: "center", gap: 10, padding: "8px 12px",
          background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 8,
        }}
      >
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11.5, color: "var(--ink3)" }}>{source.id}</span>
        <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{source.title}</span>
        {(source as any).status && <StatusBadge status={(source as any).status} />}
        <Link to={`/rules/${source.id}`} style={{ color: "var(--accent)", fontWeight: 600, fontSize: 12.5, textDecoration: "none" }}>
          Open →
        </Link>
      </div>
    );
  }
  return <span style={{ fontSize: 13, color: "var(--ink3)" }}>{source.title}</span>;
}

function MessageBubble({ msg, userName }: { msg: ChatHistoryMessage; userName: string }) {
  const isUser = msg.role === "user";
  const initials = userName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div style={{ display: "flex", gap: 14, marginBottom: 22 }}>
      <div
        style={{
          width: 32, height: 32, borderRadius: 999, flexShrink: 0,
          background: isUser ? "var(--clay-soft)" : "var(--accent)",
          color: isUser ? "var(--clay)" : "#fff",
          display: "grid", placeItems: "center", fontWeight: 700, fontSize: 12,
        }}
      >
        {isUser ? initials : "RG"}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
          {isUser ? userName : "RuleGraph"}
          <span style={{ fontWeight: 400, color: "var(--ink3)", marginLeft: 8, fontSize: 12 }}>
            {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.65, color: "var(--ink)", whiteSpace: "pre-wrap" }}>
          {msg.content}
        </div>
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600, marginBottom: 8 }}>
              Sourced from
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {msg.sources.map((s, i) => <SourceLink key={i} source={s} />)}
            </div>
          </div>
        )}
        {!isUser && msg.confidence != null && (
          <div style={{ marginTop: 8, fontSize: 12, color: "var(--ink4)" }}>
            Confidence: {Math.round(msg.confidence * 100)}%
          </div>
        )}
      </div>
    </div>
  );
}

export default function Chat() {
  const sessionId = useRef(`session-${Date.now()}`).current;
  const [input, setInput] = useState("");
  const [localMessages, setLocalMessages] = useState<ChatHistoryMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { mode: view } = useViewStore();
  const chatMutation = useChat();
  const createRule = useCreateRule();
  const { data: history } = useChatHistory(sessionId);

  useEffect(() => {
    if (history?.messages && history.messages.length > localMessages.length) {
      setLocalMessages(history.messages);
    }
  }, [history]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localMessages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");

    const userMsg: ChatHistoryMessage = { role: "user", content: text, created_at: new Date().toISOString() };
    setLocalMessages((prev) => [...prev, userMsg]);

    try {
      const res = await chatMutation.mutateAsync({ message: text, session_id: sessionId, view });
      setLocalMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.message, confidence: res.confidence, sources: res.sources, created_at: new Date().toISOString() },
      ]);
    } catch {
      setLocalMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again.", created_at: new Date().toISOString() },
      ]);
    }
  };

  const handleSubmitAsSource = async () => {
    const transcript = localMessages
      .map((m) => `${m.role === "user" ? "User" : "Assistant"}: ${m.content}`)
      .join("\n\n");
    if (!transcript) return;
    await createRule.mutateAsync({ title: `Chat session ${new Date().toLocaleDateString()}`, definition: transcript, source_type: "chat" });
    alert("Chat submitted for BA review as a proposed rule source.");
  };

  const SUGGESTIONS = ["Which rules have no tests?", "Show conflicts in Payments", "What changed last week?"];

  return (
    <Layout>
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 0, height: "calc(100vh - 120px)", margin: "-28px -40px", overflow: "hidden" }}>
        {/* Sidebar */}
        <div style={{ borderRight: "1px solid var(--line)", padding: "20px 16px", background: "var(--panel2)", overflowY: "auto" }}>
          <button
            style={{
              width: "100%", background: "var(--accent)", color: "#fff",
              border: 0, borderRadius: 10, padding: "10px 14px",
              fontSize: 13, fontWeight: 600, marginBottom: 14, cursor: "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            + New conversation
          </button>
          <div style={{ fontSize: 11, color: "var(--ink3)", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600, margin: "8px 4px" }}>
            Today
          </div>
          {localMessages.length > 0 && (
            <div style={{ padding: "8px 12px", borderRadius: 8, background: "var(--panel)", color: "var(--ink)", fontSize: 13, fontWeight: 600 }}>
              {localMessages[0]?.content.slice(0, 40)}…
            </div>
          )}
          {localMessages.length === 0 && (
            <div style={{ padding: "8px 12px", color: "var(--ink3)", fontSize: 13 }}>No conversations yet</div>
          )}
        </div>

        {/* Main chat area */}
        <div style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {/* Header */}
          <div style={{ padding: "18px 32px 14px", borderBottom: "1px solid var(--line)", background: "var(--panel)" }}>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Knowledge Chat</h1>
            <div style={{ fontSize: 12.5, color: "var(--ink3)" }}>
              Ask questions about your business rules · grounded answers with citations
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "20px 32px" }}>
            {localMessages.length === 0 ? (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", color: "var(--ink3)" }}>
                <div>
                  <p style={{ marginBottom: 8, fontSize: 14 }}>Ask anything about your business rules.</p>
                  <p style={{ fontSize: 12 }}>
                    "How does order cancellation work?" · "Which rules have no tests?" · "What changed this month?"
                  </p>
                </div>
              </div>
            ) : (
              localMessages.map((msg, i) => <MessageBubble key={i} msg={msg} userName="You" />)
            )}
            {chatMutation.isPending && (
              <div style={{ display: "flex", gap: 14 }}>
                <div style={{ width: 32, height: 32, borderRadius: 999, background: "var(--accent)", display: "grid", placeItems: "center", color: "#fff", fontWeight: 700, fontSize: 12 }}>RG</div>
                <div style={{ fontSize: 14, color: "var(--ink3)", paddingTop: 6 }}>Thinking…</div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Composer */}
          <div style={{ padding: "14px 32px 24px", borderTop: "1px solid var(--line)", background: "var(--panel)" }}>
            <div
              style={{
                background: "var(--panel)", border: "1px solid var(--line)",
                borderRadius: 14, padding: "12px 14px",
                boxShadow: "0 1px 3px rgba(40,40,30,0.04)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  style={{
                    flex: 1, border: 0, outline: "none",
                    fontSize: 14, fontFamily: "var(--font-sans)",
                    background: "transparent", color: "var(--ink)",
                  }}
                  placeholder="Ask a question or paste a Slack thread…"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                />
                <button
                  onClick={handleSend}
                  disabled={chatMutation.isPending || !input.trim()}
                  style={{
                    border: 0, background: input.trim() ? "var(--accent)" : "var(--accent-soft)",
                    color: input.trim() ? "#fff" : "var(--accent-deep)",
                    padding: "6px 14px", borderRadius: 999,
                    fontSize: 12.5, fontWeight: 600, cursor: input.trim() ? "pointer" : "not-allowed",
                    fontFamily: "var(--font-sans)", display: "flex", alignItems: "center", gap: 6,
                  }}
                >
                  <Send size={13} /> Ask
                </button>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  style={{
                    border: "1px solid var(--line)", background: "var(--panel)",
                    padding: "5px 12px", borderRadius: 999, fontSize: 12,
                    color: "var(--ink2)", cursor: "pointer", fontFamily: "var(--font-sans)",
                  }}
                >
                  {s}
                </button>
              ))}
              {localMessages.length > 0 && (
                <button
                  onClick={handleSubmitAsSource}
                  style={{
                    border: "1px solid var(--accent)", background: "var(--accent-soft)",
                    color: "var(--accent)", padding: "5px 12px", borderRadius: 999,
                    fontSize: 12, cursor: "pointer", fontFamily: "var(--font-sans)", fontWeight: 600,
                  }}
                >
                  ↗ Submit as source
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
