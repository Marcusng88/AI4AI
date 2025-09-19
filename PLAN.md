# AI4AI Implementation Plan

## Overview
This plan outlines the implementation strategy for integrating AWS Cognito authentication, DynamoDB chat storage, and deploying the coordinator agent to AWS Bedrock AgentCore Runtime while maintaining the automation agent in FastAPI with human-in-the-loop capabilities.

## 1. Authentication with AWS Cognito

### 1.1 AWS Cognito Setup
**Status**: Manual AWS Console Configuration Required

#### Prerequisites:
- AWS Account with appropriate permissions
- AWS CLI configured for ap-southeast-2 region

#### Cognito User Pool Configuration:
1. **Create User Pool** in AWS Console (ap-southeast-2)
   - Pool name: `ai4ai-user-pool`
   - Username attributes: `email`
   - Password policy: As per requirements
   - MFA: Optional (recommended)

2. **App Client Configuration**:
   - App client name: `ai4ai-frontend`
   - **Client secret**: DISABLED (SPA requirement)
   - **Allowed callback URLs**: 
     - `http://localhost:3000/authorize` (development)
     - `https://yourdomain.com/authorize` (production)
   - **Allowed sign-out URLs**:
     - `http://localhost:3000/` (development)
     - `https://yourdomain.com/` (production)
   - **Scopes**: `phone`, `openid`, `email`, `profile`

3. **Domain Configuration**:
   - Create Cognito domain for hosted UI (optional)

### 1.2 Backend Integration

#### Dependencies Installation:
```bash
pip install authlib werkzeug flask requests boto3
```

#### Implementation Strategy:
- **Replace existing auth system** in `backend/app/lib/auth.py`
- **Create new Cognito service** at `backend/app/services/cognito_service.py`
- **Update FastAPI routes** to use Cognito JWT validation
- **Integrate with existing user session management**

#### Key Changes:
1. OAuth2 integration using authlib
2. JWT token validation middleware
3. User session management with Cognito user ID
4. Maintain existing WebSocket authentication for human-in-the-loop

### 1.3 Frontend Integration

#### Dependencies Installation:
```bash
npm install @aws-amplify/auth aws-amplify
```

#### Implementation Strategy:
- **Replace** `frontend/lib/auth.ts` with Cognito integration
- **Update** `frontend/hooks/use-auth.tsx` to use Amplify Auth
- **Modify** authentication components to use Cognito flows
- **Maintain** existing authentication context patterns

## 2. Chat Session Management with DynamoDB

### 2.1 DynamoDB Setup
**Status**: Manual AWS Console Configuration Required

#### Table Structure:
```json
{
  "TableName": "ai4ai-chat-sessions",
  "KeySchema": [
    {
      "AttributeName": "user_id",
      "KeyType": "HASH"
    },
    {
      "AttributeName": "session_id", 
      "KeyType": "RANGE"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "user_id",
      "AttributeType": "S"
    },
    {
      "AttributeName": "session_id",
      "AttributeType": "S"
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

#### Messages Table:
```json
{
  "TableName": "ai4ai-chat-messages",
  "KeySchema": [
    {
      "AttributeName": "session_id",
      "KeyType": "HASH"
    },
    {
      "AttributeName": "timestamp",
      "KeyType": "RANGE"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "session_id",
      "AttributeType": "S"
    },
    {
      "AttributeName": "timestamp",
      "AttributeType": "N"
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### 2.2 Backend Implementation

#### Dependencies:
```bash
pip install boto3 aioboto3
```

#### Implementation Strategy:
1. **Create DynamoDB service** at `backend/app/services/dynamodb_service.py`
2. **Replace localStorage-based chat** in `frontend/lib/chat.ts`
3. **Add session API endpoints** in `backend/app/routers/chat.py`
4. **Maintain user-scoped sessions** with no collaboration
5. **No session expiration** as requested

#### Key Features:
- User-scoped session isolation
- Real-time session creation
- Message persistence
- Session history retrieval

### 2.3 Frontend Updates

#### Implementation Strategy:
1. **Replace localStorage calls** with API calls
2. **Update chat service** to use backend endpoints
3. **Maintain existing UI patterns**
4. **Add error handling** for network issues

## 3. AgentCore Runtime Deployment

### 3.1 Coordinator Agent Migration

#### Analysis Based on Context7 Documentation:
✅ **SUPPORTED**: Coordinator agent can be deployed to AgentCore
- Strands/CrewAI agents are fully supported
- Session management available via `RequestContext`
- Memory integration supported
- Async operations supported

#### Implementation Strategy:

```python
# coordinator_agentcore.py
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.context import RequestContext
from app.agents.coordinator.coordinator_agent import CoordinatorAgent

app = BedrockAgentCoreApp()
coordinator = CoordinatorAgent()

@app.entrypoint
def coordinator_entrypoint(payload, context: RequestContext):
    """Main coordinator entry point for AgentCore"""
    user_message = payload.get("prompt", "")
    session_id = context.session_id or "default"
    user_id = payload.get("user_id", "anonymous")
    
    # Process with existing coordinator logic
    result = coordinator.process_message(
        message=user_message,
        session_id=session_id,
        user_id=user_id
    )
    
    return {
        "message": result.get("response", ""),
        "session_id": session_id,
        "status": result.get("status", "completed")
    }

if __name__ == "__main__":
    app.run()
```

#### Deployment Process:
```bash
# Install AgentCore SDK
pip install bedrock-agentcore-starter-toolkit

# Configure deployment
agentcore configure --entrypoint coordinator_agentcore.py --region ap-southeast-2

# Deploy to AgentCore Runtime
agentcore launch --region ap-southeast-2
```

### 3.2 Automation Agent Considerations

#### Analysis Based on Research:
✅ **BROWSER AUTOMATION SUPPORTED**: AgentCore has built-in browser support
- **Browser sessions** available via `bedrock_agentcore.tools.browser_client`
- **WebSocket connections** supported for browser automation
- **Playwright integration** documented and supported
- **Session persistence** across human interactions

#### Critical Finding:
AgentCore **DOES SUPPORT** browser automation with:
- Built-in browser session management
- WebSocket connectivity for CDP
- Integration with Playwright/Nova Act
- Session state persistence

#### Recommended Architecture:
1. **Deploy automation agent to AgentCore** (POSSIBLE AND RECOMMENDED)
2. **Maintain human-in-the-loop via FastAPI WebSocket proxy**
3. **Use AgentCore browser tools** instead of HyperBrowser

#### Implementation Strategy:

```python
# automation_agentcore.py
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.tools.browser_client import browser_session
from bedrock_agentcore.context import RequestContext

app = BedrockAgentCoreApp()

@app.entrypoint
def automation_entrypoint(payload, context: RequestContext):
    """Browser automation entry point"""
    task = payload.get("automation_task", {})
    session_id = context.session_id
    
    # Use AgentCore browser tools
    with browser_session("ap-southeast-2") as browser_client:
        ws_url, headers = browser_client.generate_ws_headers()
        
        # Connect existing Browser-Use agent
        result = execute_browser_automation(
            task=task,
            session_id=session_id,
            cdp_url=ws_url,
            cdp_headers=headers
        )
    
    return result
```

### 3.3 Human-in-the-Loop Integration

#### Challenge: WebSocket Support in AgentCore
**Research Result**: AgentCore does NOT natively support WebSocket servers for human interaction.

#### Solution: Hybrid Architecture
1. **AgentCore agents** for AI processing
2. **FastAPI WebSocket proxy** for human interaction
3. **Message routing** between AgentCore and FastAPI

#### Architecture:
```
Frontend WebSocket ↔ FastAPI WebSocket ↔ AgentCore HTTP API
```

#### Implementation:
```python
# FastAPI WebSocket Proxy
@router.websocket("/ws/human-interaction/{session_id}")
async def human_interaction_proxy(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    # Forward to AgentCore when needed
    async def forward_to_agentcore(message):
        # Call AgentCore HTTP endpoint
        response = await agentcore_client.invoke({
            "prompt": message,
            "session_id": session_id
        })
        return response
    
    # Handle WebSocket messages
    async for message in websocket.iter_text():
        if needs_agentcore_processing(message):
            result = await forward_to_agentcore(message)
            await websocket.send_text(json.dumps(result))
```

## 4. Final Architecture

### 4.1 Deployment Strategy

#### AgentCore Agents:
1. **Coordinator Agent**: Deployed to AgentCore Runtime
2. **Automation Agent**: Deployed to AgentCore Runtime with browser tools

#### FastAPI Services:
1. **WebSocket proxy** for human-in-the-loop
2. **Authentication endpoints** for Cognito integration
3. **Chat session management** APIs
4. **Health monitoring** and status endpoints

### 4.2 Component Integration

```
Frontend (Next.js + Cognito)
    ↓ HTTP/WebSocket
FastAPI Backend
    ↓ HTTP API
AgentCore Runtime (ap-southeast-2)
    ├─ Coordinator Agent
    ├─ Automation Agent (with browser tools)
    └─ Memory/Session Management
    ↓ 
AWS Services
    ├─ DynamoDB (Chat Storage)
    ├─ Cognito (Authentication)  
    └─ CloudWatch (Monitoring)
```

## 5. Implementation Order

### Phase 1: Authentication Migration
1. Set up AWS Cognito User Pool
2. Implement backend Cognito integration
3. Update frontend authentication
4. Test authentication flow

### Phase 2: DynamoDB Integration  
1. Create DynamoDB tables
2. Implement backend DynamoDB service
3. Update frontend chat service
4. Test chat session management

### Phase 3: AgentCore Deployment
1. Deploy coordinator agent to AgentCore
2. Deploy automation agent to AgentCore with browser tools
3. Implement WebSocket proxy in FastAPI
4. Test human-in-the-loop functionality

### Phase 4: Integration Testing
1. End-to-end testing
2. Performance optimization
3. Security validation
4. Production deployment

## 6. Critical Considerations

### 6.1 Browser Automation in AgentCore
✅ **CONFIRMED SUPPORTED**: AgentCore has built-in browser automation
- Use `bedrock_agentcore.tools.browser_client` instead of HyperBrowser
- Maintain existing Browser-Use agent logic
- Session persistence handled by AgentCore

### 6.2 Human-in-the-Loop Compatibility
⚠️ **HYBRID APPROACH REQUIRED**: 
- AgentCore for AI processing
- FastAPI for WebSocket human interaction
- Message routing between systems

### 6.3 Session State Management
✅ **AGENTCORE MEMORY SUPPORTED**:
- Use AgentCore memory for conversation context
- Integrate with DynamoDB for long-term storage
- Session-aware processing with `RequestContext`

## 7. AWS Resource Requirements

### 7.1 Required AWS Services:
- **Cognito User Pool** (Authentication)
- **DynamoDB** (Chat storage)
- **Bedrock AgentCore** (Agent runtime)
- **IAM Roles** (Service permissions)
- **CloudWatch** (Monitoring)

### 7.2 Region: ap-southeast-2 (Sydney)
All resources will be deployed in the specified region.

## 8. Next Steps

1. **AWS Console Setup**: Create Cognito User Pool and DynamoDB tables
2. **Gather AWS Credentials**: IAM user/role for AgentCore deployment
3. **Install Dependencies**: AgentCore SDK and required packages
4. **Begin Implementation**: Start with Phase 1 (Authentication)

This plan ensures a smooth migration to AWS services while maintaining existing functionality and adding the requested features.
