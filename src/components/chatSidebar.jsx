import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, MessageSquare, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

export function ChatSidebar({ chats, currentChatId, onNewChat, onSelectChat }) {
  return (
    <div className="w-64 bg-chat-sidebar border-r border-border flex flex-col h-full">
      {/* New Chat Button */}
      <div className="p-3 border-b border-border">
        <Button
          onClick={onNewChat}
          className={cn(
            "w-full justify-start gap-2 bg-message-user hover:bg-message-user/90",
            "text-message-user-foreground font-medium"
          )}
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Chat History */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {chats.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No chats yet</p>
              <p className="text-xs">Start a new conversation</p>
            </div>
          ) : (
            chats.map((chat) => (
              <button
                key={chat.id}
                onClick={() => onSelectChat(chat.id)}
                className={cn(
                  "w-full text-left p-3 rounded-lg transition-all duration-200",
                  "hover:bg-chat-sidebar-hover group relative",
                  currentChatId === chat.id && "bg-chat-sidebar-hover"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-sm truncate mb-1">
                      {chat.title}
                    </h3>
                    {chat.lastMessage && (
                      <p className="text-xs text-muted-foreground truncate">
                        {chat.lastMessage}
                      </p>
                    )}
                  </div>
                  <button className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-muted rounded">
                    <MoreHorizontal className="h-3 w-3" />
                  </button>
                </div>
                {chat.timestamp && (
                  <span className="text-xs text-muted-foreground mt-1 block">
                    {chat.timestamp}
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
