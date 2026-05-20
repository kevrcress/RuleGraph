import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { Send, ExternalLink } from "lucide-react";
import Layout from "../../components/Layout";
import { useChat, useChatHistory } from "../../api/chat";
import type { ChatHistoryMessage, ChatSource } from "../../api/chat";
import { useViewStore } from "../../store/viewStore";
import { useCreateRule } from "../../api/rules";

function SourceLink({ source }: { source: ChatSource }) {
  if (source.type === "rule" && source.id) {
    return (
      <Link
        to={`/rules/${source.id}`}
        className="inline-flex items-center gap-1 text-xs text-brass-0 hover:text-brass-1 underline underline-offset-2"
      >
        {source.title}
        <ExternalLink size={10} />
      </Link>
    );
  }
  return <span className="text-xs text-bone-3">{source.title}</span>;
}

function MessageBubble({ msg }: { msg: ChatHistoryMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-xl rounded-lg p-3 text-sm ${
          isUser
            ? "bg-brass-2 text-bone-0 ml-8"
            : "bg-ink-3 border border-bone-4 text-bone-1 mr-8"
        }`}
      >
        <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-bone-4">
            <span className="text-xs text-bone-3 mr-1">Sources:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {msg.sources.map((s, i) => (
                <SourceLink key={i} source={s} />
              ))}
            </div>
          </div>
        )}
        {!isUser && msg.confidence != null && (
          <div className="mt-1 text-xs text-bone-4">
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

    const userMsg: ChatHistoryMessage = {
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setLocalMessages((prev) => [...prev, userMsg]);

    try {
      const res = await chatMutation.mutateAsync({
        message: text,
        session_id: sessionId,
        view,
      });
      const assistantMsg: ChatHistoryMessage = {
        role: "assistant",
        content: res.message,
        confidence: res.confidence,
        sources: res.sources,
        created_at: new Date().toISOString(),
      };
      setLocalMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setLocalMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Something went wrong. Please try again.",
          created_at: new Date().toISOString(),
        },
      ]);
    }
  };

  const handleSubmitAsSource = async () => {
    const transcript = localMessages
      .map((m) => `${m.role === "user" ? "User" : "Assistant"}: ${m.content}`)
      .join("\n\n");
    if (!transcript) return;
    await createRule.mutateAsync({
      title: `Chat session ${new Date().toLocaleDateString()}`,
      definition: transcript,
      source_type: "chat",
    });
    alert("Chat submitted for BA review as a proposed rule source.");
  };

  return (
    <Layout>
      <div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-8rem)]">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-semibold text-bone-0">Knowledge Chat</h1>
          {localMessages.length > 0 && (
            <button
              onClick={handleSubmitAsSource}
              className="text-xs text-bone-3 hover:text-brass-0 border border-bone-4 rounded px-2 py-1"
            >
              Submit as source
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto bg-ink-2 border border-bone-4 rounded-lg p-4 mb-3">
          {localMessages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-bone-3 text-sm text-center">
              <div>
                <p className="mb-2">Ask anything about your business rules.</p>
                <p className="text-xs">
                  "How does order cancellation work?" • "Which rules have no tests?" •
                  "What changed this month?"
                </p>
              </div>
            </div>
          ) : (
            localMessages.map((msg, i) => <MessageBubble key={i} msg={msg} />)
          )}
          {chatMutation.isPending && (
            <div className="flex justify-start mb-4">
              <div className="bg-ink-3 border border-bone-4 rounded-lg p-3 text-bone-3 text-sm">
                Thinking…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="flex gap-2">
          <input
            className="flex-1 bg-ink-2 border border-bone-4 rounded-lg px-3 py-2 text-sm text-bone-0 placeholder-bone-4 focus:outline-none focus:border-brass-0"
            placeholder="Ask a question…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          />
          <button
            onClick={handleSend}
            disabled={chatMutation.isPending || !input.trim()}
            className="bg-brass-0 hover:bg-brass-1 disabled:opacity-40 text-ink-0 rounded-lg px-3 py-2 transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </Layout>
  );
}
