import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageMarkdownProps {
  content: string;
  role: "user" | "assistant";
}

export function ChatMessageMarkdown({ content, role }: ChatMessageMarkdownProps) {
  const toneClass = role === "user" ? "chat-md-user" : "chat-md-assistant";

  return (
    <div className={`chat-markdown ${toneClass}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ ...props }) => (
            <a
              {...props}
              target="_blank"
              rel="noreferrer noopener"
              className="font-medium text-accent underline decoration-accent/40 underline-offset-2 transition hover:text-[#7dffd1]"
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
