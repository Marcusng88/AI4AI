/**
 * API Client for DynamoDB Chat Services
 * Handles all communication with the backend DynamoDB endpoints
 */

import { authService } from './auth'

export interface ApiSession {
  session_id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ApiMessage {
  message_id: string
  session_id: string
  timestamp: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  metadata?: Record<string, any>
}

export interface CreateSessionRequest {
  user_id: string
  title?: string
}

export interface AddMessageRequest {
  role: 'user' | 'assistant' | 'system'
  content: string
  metadata?: Record<string, any>
}

export interface ApiResponse<T = any> {
  status: 'success' | 'error'
  timestamp: string
  data?: T
  // Backend specific response fields
  session?: ApiSession
  sessions?: ApiSession[]
  message?: ApiMessage
  messages?: ApiMessage[]
  count?: number
}

class ApiClient {
  private baseUrl: string

  constructor() {
    // Default to localhost for development, can be configured via env
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}/api/v1${endpoint}`
    
    // Get authentication token
    const accessToken = await authService.getAccessToken()
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken && { 'Authorization': `Bearer ${accessToken}` }),
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`
        
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorData.message || errorMessage
        } catch (jsonError) {
          // If we can't parse JSON, use the status text
          console.warn('Could not parse error response as JSON:', jsonError)
        }
        
        // Check if this is a DynamoDB unavailable error
        if (errorMessage.includes('DynamoDB not available') || errorMessage.includes('AWS credentials not configured')) {
          throw new Error('Database not available. Please configure AWS credentials to enable chat persistence.')
        }
        
        // Check if this is an authentication error
        if (response.status === 401) {
          throw new Error('Authentication required. Please sign in to continue.')
        }
        
        // Log the full error for debugging
        console.error(`API Error [${response.status}]:`, errorMessage)
        throw new Error(errorMessage)
      }

      return await response.json()
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  // Session Management

  /**
   * Create a new chat session
   */
  async createSession(userId: string, title?: string): Promise<ApiSession> {
    const params = new URLSearchParams({ user_id: userId })
    if (title) {
      params.append('title', title)
    }

    const response = await this.request<ApiResponse<ApiSession>>(
      `/sessions?${params.toString()}`,
      { method: 'POST' }
    )
    
    if (!response.session) {
      throw new Error('No session data received from server')
    }
    
    return response.session
  }

  /**
   * Get all sessions for a user
   */
  async getUserSessions(userId: string): Promise<ApiSession[]> {
    const response = await this.request<ApiResponse<ApiSession[]>>(
      `/sessions/${encodeURIComponent(userId)}`
    )
    
    return response.sessions || []
  }

  /**
   * Get a specific session
   */
  async getSession(userId: string, sessionId: string): Promise<ApiSession | null> {
    try {
      const response = await this.request<ApiResponse<ApiSession>>(
        `/sessions/${encodeURIComponent(userId)}/${encodeURIComponent(sessionId)}`
      )
      
      return response.session || null
    } catch (error) {
      // If session not found, return null instead of throwing
      if (error instanceof Error && error.message.includes('404')) {
        return null
      }
      throw error
    }
  }

  /**
   * Update session information
   */
  async updateSession(userId: string, sessionId: string, title: string): Promise<boolean> {
    const params = new URLSearchParams({ title })
    
    try {
      await this.request<ApiResponse>(
        `/sessions/${encodeURIComponent(userId)}/${encodeURIComponent(sessionId)}?${params.toString()}`,
        { method: 'PUT' }
      )
      return true
    } catch (error) {
      console.error('Failed to update session:', error)
      return false
    }
  }

  /**
   * Delete a session and all its messages
   */
  async deleteSession(userId: string, sessionId: string): Promise<boolean> {
    try {
      await this.request<ApiResponse>(
        `/sessions/${encodeURIComponent(userId)}/${encodeURIComponent(sessionId)}`,
        { method: 'DELETE' }
      )
      return true
    } catch (error) {
      console.error('Failed to delete session:', error)
      return false
    }
  }

  // Message Management

  /**
   * Get all messages for a session
   */
  async getSessionMessages(sessionId: string, limit: number = 100): Promise<ApiMessage[]> {
    const params = new URLSearchParams({ limit: limit.toString() })
    
    const response = await this.request<ApiResponse<ApiMessage[]>>(
      `/sessions/${encodeURIComponent(sessionId)}/messages?${params.toString()}`
    )
    
    return response.messages || []
  }

  /**
   * Add a message to a session
   */
  async addMessage(sessionId: string, message: AddMessageRequest): Promise<ApiMessage> {
    const response = await this.request<ApiResponse<ApiMessage>>(
      `/sessions/${encodeURIComponent(sessionId)}/messages`,
      {
        method: 'POST',
        body: JSON.stringify(message),
      }
    )
    
    if (!response.message) {
      throw new Error('No message data received from server')
    }
    
    return response.message
  }

  // Chat Integration

  /**
   * Send a chat message and get AI response
   */
  async sendChatMessage(
    sessionId: string,
    userId: string,
    content: string,
    userContext?: Record<string, any>
  ): Promise<{ userMessage: ApiMessage; aiResponse: ApiMessage }> {
    // First, add the user message
    const userMessage = await this.addMessage(sessionId, {
      role: 'user',
      content,
      metadata: userContext,
    })

    // Then call the chat endpoint for AI response
    const chatResponse = await this.request<any>('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: content,
        session_id: sessionId,
        user_id: userId,
        user_context: userContext,
      }),
    })

    // Add the AI response as a message
    const aiMessage = await this.addMessage(sessionId, {
      role: 'assistant',
      content: chatResponse.message || 'I apologize, but I encountered an issue generating a response.',
      metadata: {
        chat_response: chatResponse,
        status: chatResponse.status,
        // Pass tutorial content if present
        ...(chatResponse.tutorial && { tutorial: chatResponse.tutorial }),
        // Pass any other response fields that might be useful
        ...(chatResponse.requires_human !== undefined && { requires_human: chatResponse.requires_human }),
        ...(chatResponse.details && { details: chatResponse.details }),
        ...(chatResponse.error && { error: chatResponse.error }),
      },
    })

    return {
      userMessage,
      aiResponse: aiMessage,
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient()
