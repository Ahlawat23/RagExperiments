import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

export function ChatInput({ onSendMessage, disabled }) {
  const [message, setMessage] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="p-4 bg-white">
      <form onSubmit={handleSubmit}>
        <div className="relative flex items-down max-w-4xl mx-auto">
          <div className="relative flex items-down w-full bg-zinc-800 rounded-full border border-zinc-700 focus-within:border-zinc-600 transition-colors">
            {/* Input field */}
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask anything"
              className={cn(
                "flex-1 bg-transparent border-none text-white placeholder:text-zinc-400",
                "focus-visible:ring-0 focus-visible:ring-offset-0 px-0 py-3 h-auto"
              )}
              disabled={disabled}
            />
            
            {/* Send button - only visible when there's text */}
            {message.trim() && (
              <div className="mr-1">
                <Button
                  type="submit"
                  size="icon"
                  disabled={disabled}
                  className={cn(
                    "h-8 w-8 shrink-0 bg-message-user hover:bg-message-user/90",
                    "text-message-user-foreground rounded-full transition-all duration-200"
                  )}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
