"use client"

import { MessageSquare, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Conversation } from "@/lib/chat-api"
import { cn } from "@/lib/utils"

interface ConversationListProps {
  conversations: Conversation[]
  currentConversationId?: string
  onSelectConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => void
  isCollapsed?: boolean
}

export function ConversationList({
  conversations,
  currentConversationId,
  onSelectConversation,
  onDeleteConversation,
  isCollapsed = false,
}: ConversationListProps) {
  const formatTime = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    } else if (days === 1) {
      return "Yesterday"
    } else if (days < 7) {
      return `${days} days ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  return (
    <ScrollArea className="h-full px-2">
      <div className="space-y-1">
        {conversations.map((conversation) => (
          <div
            key={conversation.id}
            className={cn(
              "group flex items-center rounded-lg cursor-pointer hover:bg-accent transition-colors",
              currentConversationId === conversation.id && "bg-accent",
              isCollapsed ? "p-2 justify-center" : "p-3"
            )}
            onClick={() => onSelectConversation(conversation.id)}
            title={isCollapsed ? conversation.title : undefined}
          >
            <MessageSquare className={cn(
              "h-4 w-4 text-muted-foreground flex-shrink-0",
              isCollapsed ? "" : "mr-3"
            )} />
            {!isCollapsed && (
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{conversation.title}</p>
                  <p className="text-xs text-muted-foreground truncate">{conversation.lastMessage}</p>
                  <p className="text-xs text-muted-foreground">{formatTime(conversation.lastMessageTime)}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteConversation(conversation.id)
                  }}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </>
            )}
          </div>
        ))}
        {conversations.length === 0 && !isCollapsed && (
          <div className="text-center py-8 text-muted-foreground">
            <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No conversations yet</p>
          </div>
        )}
        {conversations.length === 0 && isCollapsed && (
          <div className="text-center py-8 text-muted-foreground">
            <MessageSquare className="h-6 w-6 mx-auto opacity-50" />
          </div>
        )}
      </div>
    </ScrollArea>
  )
}
