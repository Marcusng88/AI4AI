export interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  conversationId: string
}

export interface Conversation {
  id: string
  title: string
  lastMessage: string
  lastMessageTime: Date
  userId: string
}

export const chatService = {
  // Conversation management
  getConversations: (userId: string): Conversation[] => {
    const conversations = JSON.parse(localStorage.getItem(`conversations_${userId}`) || "[]")
    return conversations.map((conv: any) => ({
      ...conv,
      lastMessageTime: new Date(conv.lastMessageTime),
    }))
  },

  createConversation: (userId: string, title = "New Chat"): Conversation => {
    const conversations = chatService.getConversations(userId)
    const newConversation: Conversation = {
      id: Date.now().toString(),
      title,
      lastMessage: "",
      lastMessageTime: new Date(),
      userId,
    }

    conversations.unshift(newConversation)
    localStorage.setItem(`conversations_${userId}`, JSON.stringify(conversations))
    return newConversation
  },

  updateConversation: (userId: string, conversationId: string, updates: Partial<Conversation>) => {
    const conversations = chatService.getConversations(userId)
    const index = conversations.findIndex((conv) => conv.id === conversationId)

    if (index !== -1) {
      conversations[index] = { ...conversations[index], ...updates }
      localStorage.setItem(`conversations_${userId}`, JSON.stringify(conversations))
    }
  },

  deleteConversation: (userId: string, conversationId: string) => {
    const conversations = chatService.getConversations(userId)
    const filtered = conversations.filter((conv) => conv.id !== conversationId)
    localStorage.setItem(`conversations_${userId}`, JSON.stringify(filtered))

    // Also delete messages for this conversation
    localStorage.removeItem(`messages_${conversationId}`)
  },

  // Message management
  getMessages: (conversationId: string): Message[] => {
    const messages = JSON.parse(localStorage.getItem(`messages_${conversationId}`) || "[]")
    return messages.map((msg: any) => ({
      ...msg,
      timestamp: new Date(msg.timestamp),
    }))
  },

  addMessage: (message: Omit<Message, "id" | "timestamp">): Message => {
    const newMessage: Message = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date(),
    }

    const messages = chatService.getMessages(message.conversationId)
    messages.push(newMessage)
    localStorage.setItem(`messages_${message.conversationId}`, JSON.stringify(messages))

    return newMessage
  },

  generateConversationTitle: (firstMessage: string): string => {
    // Simple title generation from first message
    const words = firstMessage.split(" ").slice(0, 4)
    return words.join(" ") + (firstMessage.split(" ").length > 4 ? "..." : "")
  },
}
