"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/use-auth"
import { AuthPage } from "@/components/auth/auth-page"
import { chatApiService } from "@/lib/chat-api"

export default function HomePage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const hasRedirected = useRef(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const redirectToChat = async () => {
      if (!user?.id || hasRedirected.current) return
      
      hasRedirected.current = true // Prevent multiple redirects

      try {
        console.log('Home page: Loading conversations for user', user.id)
        // Get user's conversations
        const conversations = await chatApiService.getConversations(user.id)
        console.log('Home page: Found', conversations.length, 'conversations')
        
        if (conversations.length > 0) {
          // Redirect to the most recent conversation
          console.log('Home page: Redirecting to latest conversation', conversations[0].id)
          router.replace(`/chat/${conversations[0].id}`)
        } else {
          // No conversations exist - directly create one
          console.log('Home page: No conversations found, creating new one')
          const newConversation = await chatApiService.createConversation(user.id)
          console.log('Home page: Created conversation', newConversation.id)
          router.replace(`/chat/${newConversation.id}`)
        }
      } catch (error) {
        console.error('Home page: Failed to load conversations:', error)
        
        // Check if this is a database unavailable error
        if (error instanceof Error && error.message.includes('Database not available')) {
          console.warn('Home page: Database not available, showing error message')
          setError('Database not available. Please configure AWS credentials to enable chat functionality.')
          hasRedirected.current = false // Allow retry
          return
        }
        
        try {
          // Fallback: create a new conversation
          console.log('Home page: Fallback - creating new conversation')
          const newConversation = await chatApiService.createConversation(user.id)
          router.replace(`/chat/${newConversation.id}`)
        } catch (createError) {
          console.error('Home page: Failed to create conversation:', createError)
          
          // Check if this is also a database error
          if (createError instanceof Error && createError.message.includes('Database not available')) {
            console.warn('Home page: Database not available for conversation creation')
          }
          
          // Ultimate fallback: show error instead of redirecting
          hasRedirected.current = false // Allow retry
        }
      }
    }

    // Add a small delay to prevent race conditions
    const timeoutId = setTimeout(redirectToChat, 100)
    return () => clearTimeout(timeoutId)
  }, [user?.id, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!user) {
    return <AuthPage />
  }

  // Show error if database is not available
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md mx-auto p-6">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-destructive">Database Not Available</h2>
          <p className="text-muted-foreground">{error}</p>
          <button 
            onClick={() => {
              setError(null)
              hasRedirected.current = false
            }}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Retry
          </button>
          <div className="mt-4 p-4 bg-muted rounded-md text-left">
            <p className="text-sm font-medium mb-2">To fix this issue:</p>
            <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
              <li>Configure AWS credentials in your backend</li>
              <li>Set up DynamoDB tables as described in the setup guide</li>
              <li>Restart the backend server</li>
            </ol>
          </div>
        </div>
      </div>
    )
  }

  // Show loading while redirecting
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center space-y-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p className="text-sm text-muted-foreground">Setting up your chat...</p>
      </div>
    </div>
  )
}
