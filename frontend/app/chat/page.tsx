"use client";

import { SendHorizontal } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";

import { ChatWindow } from "@/components/chat/chat-window";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { sendMessage, getChatHistory } from "@/services/chatService";
import type { ChatMessage } from "@/types";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const temporaryIdRef = useRef<number>(Date.now());

  useEffect(() => {
    async function loadHistory() {
      try {
        const history = await getChatHistory();
        setMessages([...history].reverse());
      } catch {
        toast.error("Unable to load chat history");
      }
    }

    loadHistory();
  }, []);

  const onSend = async () => {
    const normalizedQuery = query.trim();
    if (!normalizedQuery || loading) {
      return;
    }

    temporaryIdRef.current += 2;

    const userMessage: ChatMessage = {
      id: temporaryIdRef.current,
      role: "user",
      content: normalizedQuery,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentQuery = normalizedQuery;
    setQuery("");

    try {
      setLoading(true);
      const response = await sendMessage(currentQuery);

      const assistantMessage: ChatMessage = {
        id: temporaryIdRef.current + 1,
        role: "assistant",
        content: response.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      toast.error("Message failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page-enter mx-auto w-full max-w-4xl px-4 py-8">
      <header className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-semibold">Mentor Chat</h1>
          <p className="text-sm text-muted">Your AI finance co-pilot with contextual guidance.</p>
        </div>
        <Link href="/dashboard" className="text-sm text-accent transition hover:text-[#7dffd1]">
          Back to dashboard
        </Link>
      </header>

      <ChatWindow messages={messages} isTyping={loading} />

      <div className="panel-glass mt-4 rounded-2xl border border-white/10 p-2">
        <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about SIP, EMI, savings rate, or car affordability..."
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              void onSend();
            }
          }}
        />
        <Button
          className="min-w-[140px] gap-2"
          onClick={() => void onSend()}
          isLoading={loading}
          disabled={!query.trim()}
        >
          <SendHorizontal className="h-4 w-4" />
          Send Message
        </Button>
        </div>
        <p className="px-2 pt-2 text-xs text-muted/80">Press Enter to send instantly</p>
      </div>
    </main>
  );
}
