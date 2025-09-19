"use client"

import { useRef, useEffect } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageBubble } from "./message-bubble"
import { ChatInput } from "./chat-input"
import { AIStatus } from "./ai-status"
import { useChatApi } from "@/hooks/use-chat-api"
// Removed human interaction - using simple chat-based approach
import { type Conversation } from "@/lib/chat-api"

interface ChatAreaProps {
  sessionId: string
}

export function ChatArea({ sessionId }: ChatAreaProps) {
  // Only this component loads current conversation/messages. It should not load the conversation list.
  const { messages, isLoading, sendMessage, currentConversation } = useChatApi(sessionId, { enableConversationsLoad: false, enableCurrentLoad: true })
  
  // Removed human interaction - using simple chat-based approach
  
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = (content: string) => {
    sendMessage(content)
  }

  if (!currentConversation) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-muted-foreground">Select a conversation or create a new one to start chatting</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <AIStatus />

      <ScrollArea className="flex-1 min-h-0" ref={scrollAreaRef}>
        <div className="space-y-0">
          {messages.length === 0 && (
            <div className="flex items-center justify-center min-h-[400px] p-4">
              <div className="text-center">
                <h2 className="text-xl font-semibold mb-2">Start a conversation</h2>
                <p className="text-muted-foreground">Send a message to begin chatting with AI</p>
              </div>
            </div>
          )}
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message.content}
              isUser={message.isUser}
              timestamp={message.timestamp}
              metadata={message.metadata}
            />
          ))}
          {isLoading && (
            <div className="flex gap-3 p-4">
              <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
                <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
              </div>
              <div className="bg-muted rounded-lg px-4 py-3 flex-1">
                <div className="flex items-center gap-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <p className="text-sm text-muted-foreground">AI is thinking...</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
      <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
    </div>
  )
}
