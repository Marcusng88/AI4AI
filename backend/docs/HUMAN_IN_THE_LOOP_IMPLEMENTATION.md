# Human-in-the-Loop Implementation Guide

This document explains the complete human-in-the-loop (HITL) system implemented for your AI4AI project, enabling seamless interaction between browser automation agents and users through a web interface.

## Overview

The human-in-the-loop system allows the automation agent to pause execution and request human input when:
- Login credentials are needed
- The agent is unsure about account status (existing vs new account)
- Confirmation is needed for sensitive actions
- The agent encounters errors or gets stuck
- Progress updates need user guidance

## Architecture

```
Frontend (React)
    ↓ WebSocket
Backend WebSocket Manager
    ↓ Callback System
Browser Automation Agent
    ↓ CDP/WebSocket
HyperBrowser (Remote Browser)
    ↓ HTTP/HTTPS
Target Website (JPJ, LHDN, etc.)
```

## Components

### 1. Backend Components

#### WebSocket Human Tools (`websocket_human_tools.py`)
- Replaces console-based interaction with WebSocket communication
- Provides tools for: help, confirmation, choice, information, progress
- Uses async/await pattern for non-blocking execution

#### Human Interaction Manager (`human_interaction.py`)
- Manages WebSocket connections by session
- Handles request/response lifecycle
- Provides status and progress updates to frontend

#### WebSocket Router (`websocket.py`)
- WebSocket endpoints for real-time communication
- HTTP fallback for reliability
- Handles connection management and message routing

### 2. Frontend Components

#### Human Interaction Dialog (`human-interaction-dialog.tsx`)
- Modal dialog for different interaction types
- Handles sensitive information input
- Provides clear visual feedback

#### WebSocket Hook (`use-human-interaction.ts`)
- Manages WebSocket connection lifecycle
- Handles reconnection with exponential backoff
- Provides real-time updates

## Interaction Types

### 1. Help Request
**When**: Agent is stuck or unsure
**Example**: "I can't find the login button on this page. What should I do?"
```typescript
{
  type: "help",
  question: "Cannot locate login form on the page",
  context: "Looking for JPJ login page elements"
}
```

### 2. Confirmation Request
**When**: Sensitive actions need approval
**Example**: "Should I submit this form with your IC number?"
```typescript
{
  type: "confirmation",
  action_description: "Submit form with IC number 123456-78-9012",
  risk_level: "high"
}
```

### 3. Choice Request
**When**: Multiple options available
**Example**: "Do you have an account or need to create one?"
```typescript
{
  type: "choice",
  question: "Do you have an account for MySikap JPJ?",
  options: ["Yes, I have an account", "No, create new account", "I'm not sure"]
}
```

### 4. Information Request
**When**: Credentials or data needed
**Example**: "Please enter your IC number"
```typescript
{
  type: "information",
  information_type: "IC number",
  context: "Required to login to JPJ portal",
  is_sensitive: true
}
```

### 5. Progress Report
**When**: Status updates or direction needed
**Example**: "Successfully logged in. Should I continue to check summons?"
```typescript
{
  type: "progress",
  progress_description: "Successfully logged into JPJ portal",
  next_steps: "Navigate to summons check page"
}
```

## Implementation Flow

### 1. User Initiates Request
```typescript
// User: "Check if there are summons for my vehicle WAA1234"
const response = await fetch('/api/v1/chat', {
  method: 'POST',
  body: JSON.stringify({
    message: "Check vehicle summons for WAA1234",
    session_id: "user-session-123",
    user_context: {
      plate_number: "WAA1234"
    }
  })
})
```

### 2. Coordinator Processes Request
```python
# Coordinator analyzes request and prepares automation task
coordinator_result = await coordinator_agent.process_user_request(
    user_message="Check vehicle summons for WAA1234",
    user_context={"plate_number": "WAA1234"}
)

if coordinator_result["status"] == "ready_for_automation":
    # Pass to automation agent with session_id
    automation_result = await automation_agent.execute_automation_task(
        automation_task=coordinator_result["automation_task"],
        session_id="user-session-123"
    )
```

### 3. Automation Agent Sets Up Human Interaction
```python
# In automation_agent.py
def _setup_human_interaction_callback(self, session_id: str):
    from app.websocket.human_interaction import setup_human_interaction_callback
    setup_human_interaction_callback(session_id)
```

### 4. Browser Agent Executes with Human Tools
```python
# Create browser agent with human tools
browser_agent = BrowserAgent(
    task=enhanced_instructions,
    llm=self.llm,
    browser=self.browser,
    tools=human_tools  # WebSocket-enabled tools
)

# Execute with human intervention capability
result = await browser_agent.run(
    on_step_start=self.hooks.on_step_start,
    on_step_end=self.hooks.on_step_end,
    max_steps=20
)
```

### 5. Human Interaction Triggered
```python
# When agent needs help (in websocket_human_tools.py)
@tools.action(description='Ask human for help when stuck')
def ask_human_for_help(question: str) -> str:
    # Send request via WebSocket
    result = await send_human_interaction_request("help", {
        "question": question,
        "context": "Agent needs assistance to continue"
    })
    return f"Human assistance: {result}"
```

### 6. Frontend Receives Request
```typescript
// In use-human-interaction.ts hook
wsRef.current.onmessage = (event) => {
  const message = JSON.parse(event.data)
  
  if (message.type === "human_interaction_request") {
    const request: HumanInteractionRequest = {
      request_id: message.request_id,
      type: message.data.type,
      ...message.data
    }
    setCurrentRequest(request) // Shows dialog
  }
}
```

### 7. User Responds
```typescript
// User responds through dialog
const sendResponse = (requestId: string, response: string) => {
  wsRef.current?.send(JSON.stringify({
    type: "human_response",
    request_id: requestId,
    response: response
  }))
}
```

### 8. Agent Continues
```python
# Response received and processed
def provide_human_response(request_id: str, response: str):
    _pending_responses[request_id] = response
    _pending_requests[request_id].set()  # Resume waiting agent
```

## HyperBrowser Integration

### Automatic Session Management
The system automatically manages HyperBrowser sessions:

```python
# Session created when automation starts
session = await hyperbrowser_client.sessions.create(
    CreateSessionParams(
        use_proxy=True,
        proxy_country="MY",  # Malaysia proxy for local sites
        use_stealth=True,
        solve_captchas=True,
        adblock=True
    )
)

# Browser-Use connects to HyperBrowser
browser = Browser(cdp_url=session.ws_endpoint)

# Session cleaned up when done
await hyperbrowser_client.sessions.stop(session.id)
```

### State Persistence
The browser state persists across human interactions:
- Cookies and login sessions maintained
- Page state preserved during pauses
- User can see what the agent is doing

## Example: Vehicle Summons Check Flow

### Step 1: User Request
```
User: "I want to check if there are any summons for my vehicle WAA1234"
```

### Step 2: Coordinator Processing
```python
# Coordinator determines this needs JPJ automation
automation_task = {
    "task_type": "malaysian_government_service",
    "service_name": "JPJ Vehicle Summons Check",
    "instructions": "Navigate to JPJ MySikap portal, login, and check summons for WAA1234",
    "user_context": {"plate_number": "WAA1234"}
}
```

### Step 3: Browser Automation Starts
```python
# Agent navigates to JPJ portal
await browser_agent.go_to_url("https://mysikap.jpj.gov.my")
```

### Step 4: Login Challenge
```python
# Agent detects login form but needs credentials
result = ask_user_has_account("JPJ MySikap", "check vehicle summons")
# WebSocket dialog: "Do you have an account for JPJ MySikap?"
# User responds: "Yes, I have an account"
```

### Step 5: Credential Request
```python
# Agent asks for login credentials
ic_number = ask_human_for_information("IC number", "Required to login to JPJ portal")
# WebSocket dialog: Sensitive input field for IC number
# User enters: "123456-78-9012"

password = ask_human_for_information("password", "Your JPJ portal password")
# WebSocket dialog: Password input field
# User enters their password
```

### Step 6: Login Confirmation
```python
# Agent asks before submitting login
confirmation = ask_human_confirmation(
    "Login to JPJ portal with your credentials",
    risk_level="medium"
)
# WebSocket dialog: "Proceed with login?"
# User confirms: "Yes, proceed"
```

### Step 7: Navigation and Results
```python
# Agent logs in, navigates to summons section
progress = report_progress_and_ask(
    "Successfully logged in. Found vehicle summons section.",
    "Will search for summons for vehicle WAA1234"
)
# WebSocket dialog: Progress update
# User responds: "Continue as planned"

# Agent completes the task and reports results
```

## Configuration

### Environment Variables
```bash
# Required for HyperBrowser
HYPERBROWSER_API_KEY=your_hyperbrowser_api_key

# Optional: Manual CDP URL
REMOTE_BROWSER_CDP_URL=wss://your-session.hyperbrowser.ai

# LLM Configuration
GEMINI_API_KEY=your_gemini_api_key
```

### Frontend Integration
```typescript
// In your main chat component
import { useHumanInteraction } from "@/hooks/use-human-interaction"
import { HumanInteractionDialog } from "@/components/human-interaction/human-interaction-dialog"

export function ChatArea() {
  const { currentRequest, sendResponse } = useHumanInteraction(sessionId)
  
  return (
    <>
      {/* Your existing chat UI */}
      
      <HumanInteractionDialog
        isOpen={!!currentRequest}
        request={currentRequest}
        onResponse={sendResponse}
        onClose={() => {/* handle close */}}
      />
    </>
  )
}
```

## Benefits

### 1. Seamless User Experience
- Real-time interaction without page refreshes
- Clear visual feedback for different interaction types
- Maintains context throughout the automation

### 2. Intelligent Automation
- LLM-based decisions on when to ask for help
- Context-aware questions and requests
- Fallback to console for development/testing

### 3. Security and Privacy
- Sensitive information handled securely
- Clear warnings for sensitive data
- Session-based isolation

### 4. Reliability
- WebSocket with HTTP fallback
- Automatic reconnection with exponential backoff
- Error handling and timeout management

### 5. Scalability
- Multiple concurrent sessions supported
- Session-based WebSocket management
- Efficient message routing

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   ```typescript
   // Check browser console for connection errors
   // Verify backend is running on correct port
   // Check CORS configuration
   ```

2. **Human Interaction Not Triggered**
   ```python
   # Verify callback is set up correctly
   # Check human_tools import in automation_agent
   # Ensure session_id is passed to automation_agent
   ```

3. **HyperBrowser Session Issues**
   ```python
   # Check API key is valid
   # Verify account credits
   # Check session creation logs
   ```

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger("app.websocket").setLevel(logging.DEBUG)
logging.getLogger("app.agents.automation").setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Multi-modal Interaction**
   - Voice input for accessibility
   - Image/screenshot sharing
   - Video calls for complex issues

2. **Smart Caching**
   - Remember user preferences
   - Cache credentials securely
   - Learn from user patterns

3. **Advanced UI**
   - Live browser viewport sharing
   - Step-by-step progress visualization
   - Automation recording/replay

4. **Analytics**
   - Track interaction patterns
   - Measure automation success rates
   - Optimize intervention triggers

This implementation provides a robust, user-friendly human-in-the-loop system that seamlessly integrates browser automation with real-time user interaction, specifically designed for Malaysian government service automation.
