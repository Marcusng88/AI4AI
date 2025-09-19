# Step 2.3: Frontend Implementation - DynamoDB Integration

This document outlines the implementation of frontend updates to integrate with the DynamoDB backend for chat session management.

## 🎯 Overview

Step 2.3 replaces the localStorage-based chat system with a full API-based solution that integrates with the DynamoDB backend implemented in Step 2.1.

## 📁 Files Created/Modified

### New Files Created:

1. **`lib/api-client.ts`** - API client for DynamoDB endpoints
2. **`lib/chat-api.ts`** - Chat service using API instead of localStorage  
3. **`hooks/use-chat-api.ts`** - Updated hook for API-based chat management
4. **`app/chat/[sessionId]/page.tsx`** - Dynamic route for chat sessions
5. **`docs/STEP_2_3_IMPLEMENTATION.md`** - This documentation

### Modified Files:

1. **`components/chat/chat-layout.tsx`** - Updated to use API-based hooks
2. **`components/chat/chat-area.tsx`** - Modified to accept session props
3. **`app/page.tsx`** - Updated to redirect to proper chat routes

## 🏗️ Architecture Changes

### Before (localStorage):
```
Frontend Components → localStorage → Local State
```

### After (DynamoDB API):
```
Frontend Components → API Client → Backend API → DynamoDB
```

## 🔄 URL Routing Implementation

### Route Structure:
- **`/`** - Home page (redirects to latest chat or new chat)
- **`/chat/new`** - Creates new chat session
- **`/chat/[sessionId]`** - Specific chat session

### Dynamic Routing Benefits:
- ✅ **Shareable URLs** - Users can bookmark specific conversations
- ✅ **Browser Navigation** - Back/forward buttons work correctly
- ✅ **Direct Access** - Can navigate directly to any conversation
- ✅ **SEO Friendly** - Better for search engines

## 📡 API Integration

### API Client (`lib/api-client.ts`)

The API client provides a clean interface to interact with the DynamoDB backend:

```typescript
// Session Management
await apiClient.createSession(userId, title)
await apiClient.getUserSessions(userId) 
await apiClient.getSession(userId, sessionId)
await apiClient.updateSession(userId, sessionId, title)
await apiClient.deleteSession(userId, sessionId)

// Message Management  
await apiClient.getSessionMessages(sessionId)
await apiClient.addMessage(sessionId, messageData)
await apiClient.sendChatMessage(sessionId, userId, content)
```

### Environment Configuration

The API client uses environment variables for configuration:

```bash
# Default: http://localhost:8000 (development)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🔗 Frontend Service Layer

### Chat API Service (`lib/chat-api.ts`)

Provides a compatibility layer between the old localStorage interface and the new API:

```typescript
// Maintains same interface as old localStorage service
export const chatApiService = {
  getConversations,
  createConversation, 
  getConversation,
  updateConversation,
  deleteConversation,
  getMessages,
  addMessage,
  sendChatMessage,
  generateConversationTitle,
  conversationExists
}
```

### Data Transformation

The service handles transformation between API responses and frontend models:

- **API Session** → **Frontend Conversation**
- **API Message** → **Frontend Message**
- **Timestamps** → **Date objects**
- **Role mapping** → **isUser boolean**

## 🎣 React Hooks

### Updated Hook (`hooks/use-chat-api.ts`)

The new hook integrates with Next.js routing and API services:

```typescript
const {
  conversations,
  currentConversation, 
  messages,
  isLoading,
  createNewConversation,
  switchConversation,
  deleteConversation,
  sendMessage,
  updateConversationTitle
} = useChatApi(currentSessionId)
```

### Key Features:
- **URL-aware** - Syncs with current route parameter
- **Async operations** - Handles loading states
- **Error handling** - Graceful fallbacks
- **Navigation integration** - Uses Next.js router

## 🎨 Component Updates

### ChatLayout Component

Updated to work with URL routing:

```typescript
interface ChatLayoutProps {
  children: React.ReactNode
  currentSessionId?: string | null  // NEW: Session from URL
}
```

### ChatArea Component

Now accepts session props instead of using global state:

```typescript
interface ChatAreaProps {
  sessionId: string                 // NEW: Specific session
  conversation: Conversation | null // NEW: Conversation data  
}
```

### Dynamic Page Component

Handles URL parameters and loading states:

```typescript
// app/chat/[sessionId]/page.tsx
export default function ChatPage({ params }: { params: Promise<{ sessionId: string }> })
```

## 🔄 Migration Benefits

### Performance Improvements:
- **Server-side persistence** - Data survives browser refreshes
- **Selective loading** - Only load needed conversations/messages
- **Real-time sync** - Multiple devices can sync (future enhancement)

### User Experience:
- **Bookmarkable chats** - Direct URL access to conversations
- **Browser integration** - Back/forward navigation works
- **Loading states** - Clear feedback during operations
- **Error handling** - Graceful degradation on failures

### Developer Experience:
- **Type safety** - Full TypeScript integration
- **Error boundaries** - Proper error handling
- **Testing friendly** - Mockable API layer
- **Scalable** - Ready for production deployment

## 🚀 Usage Instructions

### 1. Start Backend Server
```bash
cd backend
python run.py
```

### 2. Start Frontend Server
```bash
cd frontend
npm run dev
```

### 3. Navigation Flow
1. User visits `/` (home page)
2. System checks for existing conversations
3. Redirects to latest conversation or `/chat/new`
4. User can navigate between chats via sidebar
5. Each chat has unique URL: `/chat/{sessionId}`

## 🔧 Configuration

### Environment Variables:

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Backend (.env):**
```bash
DEFAULT_AWS_REGION=ap-southeast-2
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

## 🧪 Testing

### Manual Testing Checklist:

- [ ] Home page redirects correctly
- [ ] Can create new conversations via `/chat/new`
- [ ] Can access specific conversations via `/chat/{id}`
- [ ] Sidebar shows all user conversations
- [ ] Can send messages and receive AI responses
- [ ] Can delete conversations
- [ ] Browser back/forward navigation works
- [ ] Page refresh preserves conversation state
- [ ] Error handling works when backend is down

### API Endpoint Testing:
```bash
# Test session creation
curl -X POST "http://localhost:8000/api/v1/sessions?user_id=test_user"

# Test message addition
curl -X POST "http://localhost:8000/api/v1/sessions/{sessionId}/messages" \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Hello"}'
```

## 🐛 Troubleshooting

### Common Issues:

1. **"Failed to load conversations"**
   - Check backend server is running
   - Verify API URL in environment variables
   - Check AWS credentials are configured

2. **"Conversation not found" errors**
   - Ensure sessionId in URL is valid
   - Check user has access to the conversation
   - Verify DynamoDB tables exist

3. **Infinite loading states**
   - Check network tab for failed requests
   - Verify backend API responses match expected format
   - Check for JavaScript errors in console

### Debug Commands:
```bash
# Check backend health
curl http://localhost:8000/api/v1/health

# List user sessions
curl "http://localhost:8000/api/v1/sessions/{userId}"

# Get session messages  
curl "http://localhost:8000/api/v1/sessions/{sessionId}/messages"
```

## ✅ Success Criteria

Step 2.3 is successfully implemented when:

- [ ] Home page redirects to appropriate chat route
- [ ] Dynamic chat routes work: `/chat/[sessionId]`
- [ ] All chat functionality works with DynamoDB backend
- [ ] URL sharing works (can bookmark specific chats)
- [ ] Browser navigation works correctly
- [ ] Error states are handled gracefully
- [ ] Loading states provide good UX
- [ ] No localStorage dependencies remain

## 🔮 Future Enhancements

- **Real-time sync** across multiple devices
- **Conversation sharing** between users
- **Advanced search** across all conversations
- **Conversation folders/tags** for organization
- **Export/import** functionality
- **Offline support** with sync when online

---

**Implementation Status**: ✅ Complete
**Dependencies**: Step 2.1 (DynamoDB Setup) must be completed first
**Testing**: Manual testing required with backend running
