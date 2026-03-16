"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { sendMessage } from "@/lib/api";
import type { DraftCard } from "@/lib/api";
import DraftCardView from "@/components/DraftCard";

interface Message {
  role: "user" | "assistant";
  content: string;
  draft_card?: DraftCard | null;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleDraftConfirmed = useCallback(
    (msgIndex: number, confirmMessage: string) => {
      setMessages((prev) =>
        prev.map((m, i) =>
          i === msgIndex ? { ...m, draft_card: null } : m
        )
      );
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: confirmMessage },
      ]);
    },
    []
  );

  const handleDraftCancelled = useCallback((msgIndex: number) => {
    setMessages((prev) =>
      prev.map((m, i) =>
        i === msgIndex ? { ...m, draft_card: null } : m
      )
    );
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "Draft cancelled." },
    ]);
  }, []);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      const trimmed = input.trim();
      if (!trimmed || loading) return;

      const userMsg: Message = { role: "user", content: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);

      try {
        const res = await sendMessage({
          conversation_id: conversationId,
          message: trimmed,
        });
        setConversationId(res.conversation_id);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: res.reply,
            draft_card: res.draft_card,
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
          },
        ]);
      } finally {
        setLoading(false);
        inputRef.current?.focus();
      }
    },
    [input, loading, conversationId],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Chat toolbar */}
      <div className="flex shrink-0 items-center justify-end border-b border-slate-700 px-6 py-2">
        <button
          onClick={() => {
            setMessages([]);
            setConversationId(null);
          }}
          className="rounded-md px-3 py-1.5 text-sm text-slate-400 transition-colors hover:bg-slate-800"
        >
          New chat
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-2xl px-4 py-6">
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center pt-32 text-center text-slate-500">
              <p>Ask about your training — e.g. &quot;What was my last activity?&quot;</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className="mb-4">
              <div
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] whitespace-pre-wrap px-4 py-2.5 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "rounded-2xl rounded-br-sm bg-emerald-700 text-white"
                      : "rounded-2xl rounded-bl-sm bg-slate-800 text-slate-100"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
              {msg.draft_card && (
                <div className="mt-2 max-w-[85%]">
                  <DraftCardView
                    draft={msg.draft_card}
                    onConfirmed={(confirmMsg) =>
                      handleDraftConfirmed(i, confirmMsg)
                    }
                    onCancelled={() => handleDraftCancelled(i)}
                  />
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="mb-4 flex justify-start">
              <div className="rounded-2xl rounded-bl-sm bg-slate-800 px-4 py-2.5 text-sm text-slate-400">
                <span className="inline-flex gap-1">
                  <span className="animate-bounce">.</span>
                  <span className="animate-bounce [animation-delay:0.15s]">.</span>
                  <span className="animate-bounce [animation-delay:0.3s]">.</span>
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-slate-700 bg-slate-900 px-4 py-3">
        <form
          onSubmit={handleSubmit}
          className="mx-auto flex max-w-2xl items-end gap-2"
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none focus:ring-2 focus:ring-emerald-600"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-600 disabled:opacity-40"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
