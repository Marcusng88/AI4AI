"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/use-auth"
import { AuthPage } from "@/components/auth/auth-page"
import { ChatLayout } from "@/components/chat/chat-layout"
import { ChatArea } from "@/components/chat/chat-area"
import { chatApiService } from "@/lib/chat-api"

interface ChatPageProps {
  params: Promise<{ sessionId: string }>
}

export default function ChatPage({ params }: ChatPageProps) {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Extract sessionId from params
  useEffect(() => {
    const getSessionId = async () => {
      const resolvedParams = await params
      setSessionId(resolvedParams.sessionId)
    }
    getSessionId()
  }, [params])

  // Load conversation when user and sessionId are available
  useEffect(() => {
    const loadConversation = async () => {
      if (!user || !sessionId) return

      setIsLoading(true)
      setError(null)

      try {
        // Check if this is a "new" session request
        if (sessionId === 'new') {
          // Create a new conversation
          const newConversation = await chatApiService.createConversation(user.id)
          // Redirect to the new conversation URL
          router.replace(`/chat/${newConversation.id}`)
          return
        }

        // Validate existing conversation
        const exists = await chatApiService.conversationExists(user.id, sessionId)
        if (!exists) {
          setError('Conversation not found')
          return
        }
      } catch (err) {
        console.error('Failed to load conversation:', err)
        setError('Failed to load conversation')
      } finally {
        setIsLoading(false)
      }
    }

    loadConversation()
  }, [user, sessionId, router])

  // Show loading state during auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  // Show auth page if not logged in
  if (!user) {
    return <AuthPage />
  }

  // Show loading state while loading conversation
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="text-sm text-muted-foreground">Loading conversation...</p>
        </div>
      </div>
    )
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <h2 className="text-xl font-semibold text-destructive">Error</h2>
          <p className="text-muted-foreground">{error}</p>
          <button 
            onClick={() => router.push('/chat/new')}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Start New Chat
          </button>
        </div>
      </div>
    )
  }

  // Render the chat interface
  return (
    <ChatLayout currentSessionId={sessionId}>
      <ChatArea sessionId={sessionId!} />
    </ChatLayout>
  )
}
