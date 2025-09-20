# Memory System Setup for Phase 1 Implementation

## Current Memory System Status

The Phase 1 implementation includes a **basic DynamoDB-based memory system** that is already functional. However, there are some optional enhancements you can add for better performance.

## What's Already Working ✅

### 1. **DynamoDB Memory Manager** (Currently Implemented)
- **Location**: `backend/app/agents/coordinator/coordinator_agent.py` (lines 204-393)
- **Features**:
  - Conversation history storage
  - User entity memory
  - Session-based memory
  - TTL (Time To Live) support
- **Dependencies**: Already installed (`boto3`, `botocore`)

### 2. **Memory Integration Points**
- Conversation history retrieval
- User entity memory storage
- Context building for chain-of-thought prompting
- Memory persistence across sessions

## What You Need to Set Up 🔧

### 1. **AWS DynamoDB Tables** (Required)

You need to create two DynamoDB tables in your AWS account:

#### Table 1: `crewai-memory`
```bash
aws dynamodb create-table \
    --table-name crewai-memory \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --time-to-live-specification AttributeName=ttl,Enabled=true
```

#### Table 2: `ai4ai-chat-messages`
```bash
aws dynamodb create-table \
    --table-name ai4ai-chat-messages \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
        AttributeName=created_at,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST
```

### 2. **Environment Variables** (Already Required)
Make sure these are set in your `.env` file:
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-southeast-2
```

### 3. **AWS IAM Permissions**
Your AWS user/role needs these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/crewai-memory",
                "arn:aws:dynamodb:*:*:table/ai4ai-chat-messages"
            ]
        }
    ]
}
```

## Optional Enhancements 🚀

### 1. **Mem0 Long-Term Memory** (Optional)
For advanced long-term memory capabilities, you can add Mem0 integration:

```bash
pip install mem0ai
```

Then set these environment variables:
```bash
MEM0_API_KEY=your_mem0_key
```

### 2. **AgentScope Memory Integration** (Optional)
For more sophisticated memory management:

```bash
pip install agentscope
```

### 3. **ChromaDB for Vector Memory** (Optional)
For semantic memory search:

```bash
pip install chromadb
```

## Testing the Memory System 🧪

### 1. **Test DynamoDB Connection**
```python
# Run this test to verify DynamoDB setup
import boto3
from backend.app.agents.coordinator.coordinator_agent import DynamoDBMemoryManager

async def test_memory():
    memory_manager = DynamoDBMemoryManager()
    
    # Test saving memory
    success = await memory_manager.save_conversation_memory(
        session_id="test_session",
        user_id="test_user",
        user_message="Hello",
        agent_response="Hi there!",
        context={"test": True}
    )
    print(f"Memory save: {'✅ Success' if success else '❌ Failed'}")
    
    # Test retrieving memory
    history = await memory_manager.get_conversation_history("test_session")
    print(f"Memory retrieval: {'✅ Success' if history else '❌ Failed'}")

# Run the test
import asyncio
asyncio.run(test_memory())
```

### 2. **Test with Phase 1 Implementation**
The memory system is automatically used when you run the coordinator agent. You can test it by running:

```bash
cd backend
python test_phase1_implementation.py
```

## Current Memory Flow 📊

```
User Request → Coordinator Agent → Memory Manager → DynamoDB
     ↓
1. Save conversation to DynamoDB
2. Retrieve conversation history
3. Build context for chain-of-thought prompting
4. Update user entity memory
```

## Memory Data Structure 📋

### Conversation Memory
```json
{
    "session_id": "session_123",
    "timestamp": "2025-01-20T10:30:00Z",
    "user_id": "user_456",
    "user_message": "I want to pay summons",
    "agent_response": "I'll help you with that...",
    "context": {"ic_number": "123456789012"},
    "memory_id": "uuid-1234",
    "ttl": 1737384600
}
```

### User Entity Memory
```json
{
    "session_id": "user_entity_user_456",
    "timestamp": "metadata",
    "user_id": "user_456",
    "memory_data": {
        "preferences": {"language": "en"},
        "service_history": ["summons_payment"],
        "credentials_template": {"portal": "myeg"}
    },
    "last_updated": "2025-01-20T10:30:00Z",
    "ttl": 1737384600
}
```

## Troubleshooting 🔧

### Common Issues:

1. **DynamoDB Table Not Found**
   - Error: `ResourceNotFoundException`
   - Solution: Create the tables using the AWS CLI commands above

2. **Permission Denied**
   - Error: `AccessDeniedException`
   - Solution: Check IAM permissions and AWS credentials

3. **Region Mismatch**
   - Error: `UnrecognizedClientException`
   - Solution: Ensure `AWS_DEFAULT_REGION` matches your DynamoDB region

4. **Memory Not Persisting**
   - Check TTL settings
   - Verify table creation was successful
   - Check AWS CloudWatch logs

## Summary 📝

**For Phase 1, you only need to:**
1. ✅ Create two DynamoDB tables (commands provided above)
2. ✅ Ensure AWS credentials are configured
3. ✅ Test the memory system with the provided test script

**The memory system is already integrated and working** - no additional Python dependencies needed for basic functionality!

**Optional enhancements** can be added later for more advanced memory capabilities, but the current DynamoDB-based system is sufficient for Phase 1 implementation.
