"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { type Message, type Conversation, chatApiService } from "@/lib/chat-api"
import { useAuth } from "./use-auth"

export interface UseChatApiOptions {
  enableConversationsLoad?: boolean
  enableCurrentLoad?: boolean
}

export function useChatApi(currentSessionId?: string | null, options?: UseChatApiOptions) {
  const { user } = useAuth()
  const router = useRouter()
  const { enableConversationsLoad = true, enableCurrentLoad = true } = options || {}
  
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingConversations, setIsLoadingConversations] = useState(false)

  // Load all conversations when user ID changes
  const loadConversations = useCallback(async () => {
    if (!user?.id) return

    setIsLoadingConversations(true)
    try {
      const userConversations = await chatApiService.getConversations(user.id)
      setConversations(userConversations)
    } catch (error) {
      console.error('Failed to load conversations:', error)
    } finally {
      setIsLoadingConversations(false)
    }
  }, [user?.id]) // Only depend on user.id, not the entire user object

  // Load conversations on user ID change
  useEffect(() => {
    if (!enableConversationsLoad) return
    loadConversations()
  }, [loadConversations, enableConversationsLoad])

  // Load current conversation and messages when currentSessionId changes
  useEffect(() => {
    if (!enableCurrentLoad) return
    const loadCurrentConversation = async () => {
      if (!user?.id || !currentSessionId || currentSessionId === 'new') {
        setCurrentConversation(null)
        setMessages([])
        return
      }

      try {
        // Load conversation details (skip last-message API since we'll fetch full messages next)
        const conversation = await chatApiService.getConversation(user.id, currentSessionId, { skipLastMessage: true })
        if (conversation) {
          setCurrentConversation(conversation)
          
          // Load messages for this conversation
          const conversationMessages = await chatApiService.getMessages(currentSessionId)
          setMessages(conversationMessages)
        } else {
          // Conversation not found, redirect to home instead of creating new chat
          console.warn(`Conversation ${currentSessionId} not found, redirecting to home`)
          router.push('/')
        }
      } catch (error) {
        console.error('Failed to load conversation:', error)
        // On error, redirect to home instead of creating new chat
        router.push('/')
      }
    }

    loadCurrentConversation()
  }, [user?.id, currentSessionId, router, enableCurrentLoad])

  // Create new conversation
  const createNewConversation = useCallback(async () => {
    if (!user) return

    try {
      const newConversation = await chatApiService.createConversation(user.id)
      
      // Navigate to the new conversation
      router.push(`/chat/${newConversation.id}`)
      
      // Update local state
      await loadConversations()
      
      return newConversation
    } catch (error) {
      console.error('Failed to create conversation:', error)
      throw error
    }
  }, [user, router, loadConversations])

  // Switch to a different conversation
  const switchConversation = useCallback((conversationId: string) => {
    router.push(`/chat/${conversationId}`)
  }, [router])

  // Delete conversation
  const deleteConversation = useCallback(async (conversationId: string) => {
    if (!user) return false

    try {
      const success = await chatApiService.deleteConversation(user.id, conversationId)
      
      if (success) {
        // Remove from local state
        setConversations(prev => prev.filter(conv => conv.id !== conversationId))
        
        // If we deleted the current conversation, navigate to new chat
        if (currentSessionId === conversationId) {
          router.push('/chat/new')
        }
        
        return true
      }
      
      return false
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      return false
    }
  }, [user, currentSessionId, router])

  // Update conversation title
  const updateConversationTitle = useCallback(async (conversationId: string, title: string) => {
    if (!user) return false

    try {
      const success = await chatApiService.updateConversation(user.id, conversationId, { title })
      
      if (success) {
        // Update local state
        setConversations(prev => 
          prev.map(conv => 
            conv.id === conversationId 
              ? { ...conv, title }
              : conv
          )
        )
        
        if (currentConversation?.id === conversationId) {
          setCurrentConversation(prev => prev ? { ...prev, title } : null)
        }
        
        return true
      }
      
      return false
    } catch (error) {
      console.error('Failed to update conversation title:', error)
      return false
    }
  }, [user, currentConversation])

  // Send message
  const sendMessage = useCallback(async (
    content: string,
    userContext?: Record<string, any>,
    onAIResponse?: (response: string) => void
  ) => {
    if (!currentConversation || !user) {
      throw new Error('No active conversation')
    }

    // Create user message immediately and add to UI
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content,
      isUser: true,
      timestamp: new Date(),
      conversationId: currentConversation.id,
      metadata: userContext
    }

    // Add user message to UI immediately
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      // Send message and get AI response
      const { userMessage: apiUserMessage, aiMessage } = await chatApiService.sendChatMessage(
        currentConversation.id,
        user.id,
        content,
        userContext
      )

      // Replace the temporary user message with the real one from API
      setMessages(prev => prev.map(msg => 
        msg.id === userMessage.id ? apiUserMessage : msg
      ))

      // Add AI response
      setMessages(prev => [...prev, aiMessage])

      // Update conversation title if this is the first message
      if (messages.length === 0) {
        const title = chatApiService.generateConversationTitle(content)
        await updateConversationTitle(currentConversation.id, title)
      }

      // Reload conversations to update last message (only when enabled)
      if (enableConversationsLoad) {
        await loadConversations()
      }

      if (onAIResponse) {
        onAIResponse(aiMessage.content)
      }

      return { userMessage: apiUserMessage, aiMessage }
    } catch (error) {
      console.error('Failed to send message:', error)
      
      // Add error message to local state
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        content: 'I apologize, but I encountered an error. Please try again.',
        isUser: false,
        timestamp: new Date(),
        conversationId: currentConversation.id,
        metadata: { error: true }
      }
      
      setMessages(prev => [...prev, errorMessage])
      throw error
    } finally {
      setIsLoading(false)
    }
  }, [currentConversation, user, messages.length, updateConversationTitle, loadConversations, enableConversationsLoad])

  // Refresh current conversation
  const refreshConversation = useCallback(async () => {
    if (!user || !currentSessionId) return

    try {
      const conversation = await chatApiService.getConversation(user.id, currentSessionId)
      if (conversation) {
        setCurrentConversation(conversation)
        const conversationMessages = await chatApiService.getMessages(currentSessionId)
        setMessages(conversationMessages)
      }
    } catch (error) {
      console.error('Failed to refresh conversation:', error)
    }
  }, [user, currentSessionId])

  return {
    // State
    conversations,
    currentConversation,
    messages,
    isLoading,
    isLoadingConversations,
    
    // Actions
    createNewConversation,
    switchConversation,
    deleteConversation,
    sendMessage,
    updateConversationTitle,
    refreshConversation,
    loadConversations,
  }
}
