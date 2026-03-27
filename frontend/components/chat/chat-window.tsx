import { useEffect, useRef } from "react";

import { ChatMessageMarkdown } from "@/components/chat/chat-message-markdown";
import { ChatMessage } from "@/types";

interface ChatWindowProps {
  messages: ChatMessage[];
  isTyping?: boolean;
}

export function ChatWindow({ messages, isTyping = false }: ChatWindowProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) {
      return;
    }
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, isTyping]);

  return (
    <div
      ref={containerRef}
      className="panel-glass h-[65vh] space-y-3 overflow-y-auto rounded-2xl border border-white/10 bg-panel/80 p-4 shadow-card"
    >
      {messages.map((message) => {
        const isUser = message.role === "user";

        return (
          <div key={message.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[84%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm transition-all duration-300 ease-smooth ${
                isUser
                  ? "border border-[#7dffd1]/45 bg-gradient-to-br from-[#5dffd0] to-[#00d186] text-[#032117] shadow-[0_0_24px_rgba(0,255,163,0.32)]"
                  : "border border-white/10 bg-panelAlt/95 text-text"
              }`}
            >
              <ChatMessageMarkdown content={message.content} role={message.role} />
              <p className={`mt-1 text-[10px] ${isUser ? "text-[#073624]" : "text-muted/70"}`}>
                {new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
          </div>
        );
      })}

      {isTyping ? (
        <div className="flex justify-start">
          <div className="rounded-2xl border border-white/10 bg-panelAlt/90 px-4 py-3">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 animate-bounce rounded-full bg-accent/70 [animation-delay:0ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-accent/70 [animation-delay:140ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-accent/70 [animation-delay:280ms]" />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
