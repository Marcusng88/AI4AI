export interface AIProvider {
  name: string
  generateResponse: (
    message: string,
    conversationHistory?: Array<{ role: "user" | "assistant"; content: string }>,
  ) => Promise<string>
}

export interface ChatRequest {
  message: string
  language: "en" | "ms"
  session_id?: string
  user_id?: string
}

export interface ChatResponse {
  message: string
  session_id: string
  status: "success" | "error"
  metadata?: {
    intent?: string
    service?: string
    next_action?: string
    required_info?: string[]
    agency?: string
    timestamp?: string
    agent?: string
  }
  payment_links?: string[]
  screenshots?: string[]
}

// Mock AI responses with different patterns to simulate various AI behaviors
const mockResponses = {
  greeting: [
    "Hello! I'm here to help you with any questions or tasks you have. What would you like to discuss?",
    "Hi there! I'm your AI assistant. How can I assist you today?",
    "Greetings! I'm ready to help you with whatever you need. What's on your mind?",
  ],
  question: [
    "That's an interesting question! Let me think about that...",
    "Great question! Here's what I think about that topic:",
    "I'd be happy to help you understand that better. Here's my perspective:",
  ],
  help: [
    "I'm here to help! I can assist with a wide variety of tasks including answering questions, helping with analysis, creative writing, coding, and much more.",
    "I can help you with many things! Feel free to ask me about any topic, request explanations, or get assistance with tasks.",
    "I'm designed to be helpful across many domains. What specific area would you like assistance with?",
  ],
  creative: [
    "I love creative challenges! Let me put together something interesting for you.",
    "Creative tasks are some of my favorites. Here's what I came up with:",
    "That sounds like a fun creative project! Let me work on that for you.",
  ],
  technical: [
    "Let me break down the technical aspects of that for you:",
    "From a technical perspective, here's how I'd approach that:",
    "That's a good technical question. Here's my analysis:",
  ],
  default: [
    "I understand what you're asking about. Let me provide you with a helpful response.",
    "That's an interesting point. Here's my take on it:",
    "I see what you mean. Let me share some thoughts on that:",
  ],
}

const getResponseCategory = (message: string): keyof typeof mockResponses => {
  const lowerMessage = message.toLowerCase()

  if (lowerMessage.includes("hello") || lowerMessage.includes("hi") || lowerMessage.includes("hey")) {
    return "greeting"
  }
  if (
    lowerMessage.includes("?") ||
    lowerMessage.includes("what") ||
    lowerMessage.includes("how") ||
    lowerMessage.includes("why")
  ) {
    return "question"
  }
  if (lowerMessage.includes("help") || lowerMessage.includes("assist") || lowerMessage.includes("support")) {
    return "help"
  }
  if (
    lowerMessage.includes("create") ||
    lowerMessage.includes("write") ||
    lowerMessage.includes("story") ||
    lowerMessage.includes("poem")
  ) {
    return "creative"
  }
  if (
    lowerMessage.includes("code") ||
    lowerMessage.includes("program") ||
    lowerMessage.includes("technical") ||
    lowerMessage.includes("algorithm")
  ) {
    return "technical"
  }

  return "default"
}

const generateMockResponse = (message: string): string => {
  const category = getResponseCategory(message)
  const responses = mockResponses[category]
  const baseResponse = responses[Math.floor(Math.random() * responses.length)]

  // Add some context-aware content
  const contextualContent = generateContextualContent(message, category)

  return `${baseResponse}\n\n${contextualContent}`
}

const generateContextualContent = (message: string, category: keyof typeof mockResponses): string => {
  switch (category) {
    case "greeting":
      return "I'm ready to help you with questions, creative tasks, analysis, coding, or just have a conversation. What interests you today?"

    case "question":
      return `Regarding your question about "${message.slice(0, 50)}${message.length > 50 ? "..." : ""}", this is a mock response that demonstrates how the AI would provide detailed, helpful information. In a real implementation, this would be powered by an actual language model.`

    case "help":
      return "Some things I can help with include:\n• Answering questions on various topics\n• Writing and editing text\n• Code assistance and debugging\n• Creative projects like stories or brainstorming\n• Analysis and problem-solving\n• General conversation and advice"

    case "creative":
      return `For your creative request about "${message.slice(0, 50)}${message.length > 50 ? "..." : ""}", I would normally generate original content tailored to your needs. This mock response shows where that creative output would appear.`

    case "technical":
      return `For the technical topic you mentioned, I would provide detailed explanations, code examples if relevant, and step-by-step guidance. This mock response represents where that technical content would be generated.`

    default:
      return `I've processed your message: "${message.slice(0, 100)}${message.length > 100 ? "..." : ""}". This is a simulated response that demonstrates the AI's ability to understand context and provide relevant information. In production, this would be replaced with actual AI-generated content.`
  }
}

// Mock AI Provider
export const mockAIProvider: AIProvider = {
  name: "Mock AI",
  generateResponse: async (message: string, conversationHistory = []) => {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 800 + Math.random() * 1200))

    // Consider conversation history for more contextual responses
    if (conversationHistory.length > 0) {
      const lastUserMessage = conversationHistory[conversationHistory.length - 1]
      if (lastUserMessage && lastUserMessage.role === "user") {
        // Add some continuity to the conversation
        const continuityPhrases = [
          "Building on our previous discussion, ",
          "Following up on what we talked about, ",
          "Continuing from your last question, ",
          "As we were discussing, ",
        ]

        if (Math.random() > 0.7 && conversationHistory.length > 2) {
          const phrase = continuityPhrases[Math.floor(Math.random() * continuityPhrases.length)]
          return phrase + generateMockResponse(message).toLowerCase()
        }
      }
    }

    return generateMockResponse(message)
  },
}

// Real AI provider that connects to the backend coordinator agent
export const coordinatorAIProvider: AIProvider = {
  name: "Malaysian Government Coordinator Agent",
  generateResponse: async (message: string, conversationHistory = []) => {
    try {
      // Import auth service dynamically to avoid circular dependencies
      const { authService } = await import('@/lib/auth')
      
      // Get access token for authenticated requests
      const accessToken = await authService.getAccessToken()
      
      if (!accessToken) {
        return "Please sign in to use the AI chat service."
      }

      const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '')
      const response = await fetch(`${backendUrl}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          message,
          language: 'en', // Default to English, can be made dynamic
          session_id: `session_${Date.now()}`,
          user_id: `user_${Date.now()}`
        } as ChatRequest),
      })

      if (!response.ok) {
        if (response.status === 401) {
          return "Your session has expired. Please sign in again."
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: ChatResponse = await response.json()
      return data.message
    } catch (error) {
      console.error('Error calling coordinator agent:', error)
      return "I apologize, but I'm having trouble connecting to the government services system. Please try again later."
    }
  },
}

// Future: Real AI providers can be added here
// export const openAIProvider: AIProvider = { ... }
// export const claudeProvider: AIProvider = { ... }

export const aiService = {
  currentProvider: coordinatorAIProvider, // Use the real coordinator agent by default

  async generateResponse(
    message: string,
    conversationHistory?: Array<{ role: "user" | "assistant"; content: string }>,
  ) {
    return await this.currentProvider.generateResponse(message, conversationHistory)
  },

  setProvider(provider: AIProvider) {
    this.currentProvider = provider
  },
}
