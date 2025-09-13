import { cn } from "@/lib/utils";
import { User } from "lucide-react";

export function ChatMessage({ message, isUser, timestamp }) {
  return (
    <div
      className={cn(
        "flex w-full gap-3 p-4 animate-in slide-in-from-bottom-2 duration-300",
        isUser ? "justify-end" : "justify-center"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 transition-all duration-200",
          isUser
            ? "bg-message-user text-message-user-foreground ml-auto"
            : "text-message-ai-foreground"
        )}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{message}</p>
        {timestamp && (
          <span className="text-xs opacity-70 mt-1 block">{timestamp}</span>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-message-user flex items-center justify-center">
          <User className="w-4 h-4 text-message-user-foreground" />
        </div>
      )}
    </div>
  );
}
