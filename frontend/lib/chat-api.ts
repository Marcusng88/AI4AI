/**
 * Chat service that integrates with DynamoDB backend
 * Replaces localStorage-based chat.ts with API-based implementation
 */

import { apiClient, type ApiSession, type ApiMessage } from './api-client'

export interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  conversationId: string
  metadata?: Record<string, any>
}

export interface Conversation {
  id: string
  title: string
  lastMessage: string
  lastMessageTime: Date
  userId: string
  messageCount: number
}

/**
 * Convert API session to frontend conversation format
 */
function apiSessionToConversation(session: ApiSession): Conversation {
  return {
    id: session.session_id,
    title: session.title,
    lastMessage: '', // Will be populated when loading messages
    lastMessageTime: new Date(session.updated_at),
    userId: session.user_id,
    messageCount: session.message_count,
  }
}

/**
 * Convert API message to frontend message format
 */
function apiMessageToMessage(apiMessage: ApiMessage): Message {
  return {
    id: apiMessage.message_id,
    content: apiMessage.content,
    isUser: apiMessage.role === 'user',
    timestamp: new Date(apiMessage.timestamp),
    conversationId: apiMessage.session_id,
    metadata: apiMessage.metadata,
  }
}

// Simple cache to prevent duplicate conversation creation
const creationCache = new Map<string, Promise<Conversation>>()

// Clean up old cache entries periodically
setInterval(() => {
  const now = Date.now()
  for (const [key] of creationCache.entries()) {
    const timestamp = parseInt(key.split('_')[2])
    if (now - timestamp > 10000) { // Remove entries older than 10 seconds
      creationCache.delete(key)
    }
  }
}, 5000) // Run every 5 seconds

export const chatApiService = {
  // Conversation management

  /**
   * Get all conversations for a user
   */
  getConversations: async (userId: string): Promise<Conversation[]> => {
    try {
      const sessions = await apiClient.getUserSessions(userId)
      const conversations = sessions.map(apiSessionToConversation)

      // Sort by last message time (newest first)
      conversations.sort((a, b) => b.lastMessageTime.getTime() - a.lastMessageTime.getTime())

      // Only load last message for conversations that have messages
      const conversationsWithMessages = await Promise.all(
        conversations.map(async (conv) => {
          // Skip loading messages if the conversation has 0 messages
          if (conv.messageCount === 0) {
            return conv
          }
          
          try {
            const messages = await apiClient.getSessionMessages(conv.id, 1)
            if (messages.length > 0) {
              const lastMessage = messages[messages.length - 1]
              return {
                ...conv,
                lastMessage: lastMessage.content.substring(0, 50) + (lastMessage.content.length > 50 ? '...' : ''),
              }
            }
            return conv
          } catch (error) {
            // Silently handle 404s for sessions without messages
            if (error instanceof Error && error.message.includes('404')) {
              return conv
            }
            console.warn(`Failed to load last message for conversation ${conv.id}:`, error)
            return conv
          }
        })
      )

      return conversationsWithMessages
    } catch (error) {
      console.error('Failed to load conversations:', error)
      
      // Check if this is a DynamoDB unavailable error
      if (error instanceof Error && error.message.includes('Database not available')) {
        console.warn('DynamoDB not available, falling back to localStorage')
        // Return empty array for now - could implement localStorage fallback here
        return []
      }
      
      throw new Error('Failed to load conversations')
    }
  },

  /**
   * Create a new conversation
   */
  createConversation: async (userId: string, title = "New Chat"): Promise<Conversation> => {
    // Use a simpler cache key based on user and title only
    const simpleCacheKey = `${userId}_${title}`
    
    // Check if there's already a creation in progress for this user with same title
    const existingCreation = Array.from(creationCache.entries()).find(([key]) => {
      const [cachedUserId, cachedTitle] = key.split('_')
      const timestamp = parseInt(key.split('_')[2])
      return cachedUserId === userId && 
             cachedTitle === title && 
             Date.now() - timestamp < 3000 // Within 3 seconds
    })
    
    if (existingCreation) {
      console.log('Chat API: Reusing existing conversation creation for user:', userId)
      return existingCreation[1]
    }

    const cacheKey = `${userId}_${title}_${Date.now()}`
    
    const creationPromise = (async () => {
      try {
        console.log('Chat API: Creating new conversation for user:', userId)
        const session = await apiClient.createSession(userId, title)
        const conversation = apiSessionToConversation(session)
        console.log('Chat API: Successfully created conversation:', conversation.id)
        creationCache.delete(cacheKey) // Clean up cache
        return conversation
      } catch (error) {
        creationCache.delete(cacheKey) // Clean up cache on error
        console.error('Chat API: Failed to create conversation:', error)
        
        // Check if this is a DynamoDB unavailable error
        if (error instanceof Error && error.message.includes('Database not available')) {
          throw new Error('Database not available. Please configure AWS credentials to enable chat persistence.')
        }
        
        throw new Error('Failed to create conversation')
      }
    })()

    creationCache.set(cacheKey, creationPromise)
    return creationPromise
  },

  /**
   * Get a specific conversation
   */
  getConversation: async (
    userId: string,
    conversationId: string,
    options?: { skipLastMessage?: boolean }
  ): Promise<Conversation | null> => {
    try {
      const session = await apiClient.getSession(userId, conversationId)
      if (!session) return null
      
      const conversation = apiSessionToConversation(session)
      
      if (!options?.skipLastMessage) {
        // Load last message
        try {
          const messages = await apiClient.getSessionMessages(conversationId, 1)
          if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1]
            conversation.lastMessage = lastMessage.content.substring(0, 50) + (lastMessage.content.length > 50 ? '...' : '')
          }
        } catch (error) {
          console.warn(`Failed to load last message for conversation ${conversationId}:`, error)
        }
      }
      
      return conversation
    } catch (error) {
      console.error('Failed to get conversation:', error)
      return null
    }
  },

  /**
   * Update conversation information
   */
  updateConversation: async (
    userId: string,
    conversationId: string,
    updates: Partial<Pick<Conversation, 'title'>>
  ): Promise<boolean> => {
    try {
      if (updates.title) {
        return await apiClient.updateSession(userId, conversationId, updates.title)
      }
      return true
    } catch (error) {
      console.error('Failed to update conversation:', error)
      return false
    }
  },

  /**
   * Delete a conversation
   */
  deleteConversation: async (userId: string, conversationId: string): Promise<boolean> => {
    try {
      return await apiClient.deleteSession(userId, conversationId)
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      return false
    }
  },

  // Message management

  /**
   * Get all messages for a conversation
   */
  getMessages: async (conversationId: string): Promise<Message[]> => {
    try {
      const apiMessages = await apiClient.getSessionMessages(conversationId)
      return apiMessages.map(apiMessageToMessage)
    } catch (error) {
      console.error('Failed to load messages:', error)
      throw new Error('Failed to load messages')
    }
  },

  /**
   * Add a message to a conversation
   */
  addMessage: async (message: Omit<Message, "id" | "timestamp">): Promise<Message> => {
    try {
      const apiMessage = await apiClient.addMessage(message.conversationId, {
        role: message.isUser ? 'user' : 'assistant',
        content: message.content,
        metadata: message.metadata,
      })
      
      return apiMessageToMessage(apiMessage)
    } catch (error) {
      console.error('Failed to add message:', error)
      
      // Provide more specific error messages
      if (error instanceof Error) {
        if (error.message.includes('Authentication required')) {
          throw new Error('Please sign in to add messages.')
        } else if (error.message.includes('Database not available')) {
          throw new Error('Database not available. Please configure AWS credentials to enable chat persistence.')
        } else if (error.message.includes('422')) {
          throw new Error('Invalid message format. Please try again.')
        } else if (error.message.includes('500')) {
          throw new Error('Server error. Please try again later.')
        } else if (error.message.includes('404')) {
          throw new Error('Session not found. Please refresh the page.')
        } else {
          throw new Error(`Failed to add message: ${error.message}`)
        }
      }
      
      throw new Error('Failed to add message')
    }
  },

  /**
   * Send a chat message and get AI response
   */
  sendChatMessage: async (
    conversationId: string,
    userId: string,
    content: string,
    userContext?: Record<string, any>
  ): Promise<{ userMessage: Message; aiMessage: Message }> => {
    try {
      const { userMessage: apiUserMessage, aiResponse: apiAiMessage } = 
        await apiClient.sendChatMessage(conversationId, userId, content, userContext)
      
      return {
        userMessage: apiMessageToMessage(apiUserMessage),
        aiMessage: apiMessageToMessage(apiAiMessage),
      }
    } catch (error) {
      console.error('Failed to send chat message:', error)
      
      // Provide more specific error messages
      if (error instanceof Error) {
        if (error.message.includes('Authentication required')) {
          throw new Error('Please sign in to send messages.')
        } else if (error.message.includes('Database not available')) {
          throw new Error('Database not available. Please configure AWS credentials to enable chat persistence.')
        } else if (error.message.includes('422')) {
          throw new Error('Invalid message format. Please try again.')
        } else if (error.message.includes('500')) {
          throw new Error('Server error. Please try again later.')
        } else if (error.message.includes('404')) {
          throw new Error('Session not found. Please refresh the page.')
        } else {
          throw new Error(`Failed to send message: ${error.message}`)
        }
      }
      
      throw new Error('Failed to send message')
    }
  },

  /**
   * Generate conversation title from first message
   */
  generateConversationTitle: (firstMessage: string): string => {
    // Simple title generation from first message
    const words = firstMessage.split(" ").slice(0, 4)
    return words.join(" ") + (firstMessage.split(" ").length > 4 ? "..." : "")
  },

  /**
   * Check if a conversation exists
   */
  conversationExists: async (userId: string, conversationId: string): Promise<boolean> => {
    try {
      // Lightweight check that avoids loading messages
      const session = await apiClient.getSession(userId, conversationId)
      return session !== null
    } catch (error) {
      return false
    }
  },
}

// Export for backward compatibility and easy migration
export const chatService = chatApiService
