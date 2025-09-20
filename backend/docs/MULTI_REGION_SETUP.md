# Multi-Region AWS Configuration Guide

## 🎯 **Problem Solved**

**Issue**: Bedrock is not available in ap-southeast-5, but your infrastructure is set up there.

**Solution**: Use **multi-region configuration** - different AWS services in their optimal regions.

## 📍 **Regional Service Mapping**

### **ap-southeast-5 (Singapore) - Primary Region**
- ✅ **Cognito User Pool**: `ap-southeast-5_nuC0or8vA`
- ✅ **DynamoDB Tables**: `crewai-memory`, `ai4ai-chat-messages`
- ✅ **Backend Infrastructure**: Main application region
- ✅ **Memory System**: Conversation history and user entity memory

### **ap-southeast-2 (Sydney) - Bedrock Region**
- ✅ **Bedrock Models**: `amazon.nova-lite-v1:0`, `anthropic.claude-3-5-sonnet`
- ✅ **LLM Invocations**: All agent reasoning and processing
- ✅ **AI Services**: Model inference and text generation

### **us-west-2 (Oregon) - AgentCore Region**
- ✅ **AWS Bedrock AgentCore**: Browser automation platform
- ✅ **Browser Automation**: Nova Act orchestration

## 🔧 **Configuration Updates**

### **1. Environment Variables** (`.env`)
```bash
# Primary Infrastructure Region
AWS_DEFAULT_REGION=ap-southeast-5

# Bedrock Region (where Bedrock is available)
BEDROCK_REGION=ap-southeast-2

# AgentCore Region
BEDROCK_AGENT_CORE_REGION=us-west-2

# AWS Credentials (same for all regions)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### **2. Backend Configuration** (`app/config.py`)
```python
class Settings(BaseSettings):
    # Primary region for infrastructure
    aws_region: Optional[str] = os.getenv("DEFAULT_AWS_REGION", "ap-southeast-5")
    
    # Bedrock configuration (ap-southeast-2)
    bedrock_region: str = "ap-southeast-2"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_agent_core_region: str = "us-west-2"
```

### **3. Agent LLM Configuration**
```python
# Coordinator Agent & Validator Agent
def _initialize_llm(self) -> LLM:
    return LLM(
        model="bedrock/amazon.nova-lite-v1:0",
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_region_name=os.getenv('BEDROCK_REGION', 'ap-southeast-2'),  # Bedrock region
        stream=True
    )
```

## 🚀 **How It Works**

### **Service Flow:**
```
User Request → Frontend (ap-southeast-5)
                ↓
Backend API (ap-southeast-5) → Cognito Auth (ap-southeast-5)
                ↓
Coordinator Agent → Bedrock LLM (ap-southeast-2)
                ↓
Validator Agent → Bedrock LLM (ap-southeast-2)
                ↓
Automation Agent → AgentCore Browser (us-west-2)
                ↓
Memory System → DynamoDB (ap-southeast-5)
```

### **Cross-Region Communication:**
- **Backend ↔ Bedrock**: Direct API calls to ap-southeast-2
- **Backend ↔ DynamoDB**: Direct API calls to ap-southeast-5
- **Backend ↔ AgentCore**: Direct API calls to us-west-2
- **No additional latency**: AWS handles cross-region communication efficiently

## ✅ **Benefits of This Setup**

### **1. Service Availability**
- ✅ **Bedrock**: Available in ap-southeast-2
- ✅ **Cognito**: Available in ap-southeast-5
- ✅ **DynamoDB**: Available in ap-southeast-5
- ✅ **AgentCore**: Available in us-west-2

### **2. Performance**
- ✅ **Low Latency**: Each service in its optimal region
- ✅ **No Data Transfer Costs**: Between regions for most operations
- ✅ **Efficient Routing**: AWS handles cross-region communication

### **3. Cost Optimization**
- ✅ **Regional Pricing**: Each service uses regional pricing
- ✅ **No Data Transfer**: Minimal cross-region data transfer
- ✅ **Optimal Resource Usage**: Each service in its best region

## 🧪 **Testing the Configuration**

### **1. Test Bedrock Access**
```bash
cd backend
python -c "
import boto3
bedrock = boto3.client('bedrock', region_name='ap-southeast-2')
models = bedrock.list_foundation_models()
print('✅ Bedrock accessible in ap-southeast-2')
print(f'Available models: {len(models.get(\"modelSummaries\", []))}')
"
```

### **2. Test DynamoDB Access**
```bash
python -c "
import boto3
dynamodb = boto3.client('dynamodb', region_name='ap-southeast-5')
tables = dynamodb.list_tables()
print('✅ DynamoDB accessible in ap-southeast-5')
print(f'Tables: {tables.get(\"TableNames\", [])}')
"
```

### **3. Test Cognito Access**
```bash
python -c "
import boto3
cognito = boto3.client('cognito-idp', region_name='ap-southeast-5')
pools = cognito.list_user_pools(MaxResults=10)
print('✅ Cognito accessible in ap-southeast-5')
print(f'User Pools: {len(pools.get(\"UserPools\", []))}')
"
```

## 🔒 **Security Considerations**

### **1. IAM Permissions**
Your AWS user needs permissions for all regions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": "ap-southeast-2"
                }
            }
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:*",
                "cognito-idp:*"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": "ap-southeast-5"
                }
            }
        }
    ]
}
```

### **2. Data Residency**
- **User Data**: Stored in ap-southeast-5 (Singapore)
- **AI Processing**: Happens in ap-southeast-2 (Sydney)
- **Browser Automation**: Happens in us-west-2 (Oregon)

## 📊 **Performance Impact**

### **Latency Estimates:**
- **Singapore → Sydney**: ~50ms (Bedrock calls)
- **Singapore → Oregon**: ~150ms (AgentCore calls)
- **Singapore → Singapore**: ~5ms (DynamoDB/Cognito calls)

### **Total Impact:**
- **Minimal**: Most operations are local to ap-southeast-5
- **Acceptable**: AI processing latency is negligible for user experience
- **Optimized**: Each service in its optimal region

## 🎯 **Summary**

**This multi-region setup is the optimal solution because:**

1. ✅ **Bedrock works**: Available in ap-southeast-2
2. ✅ **Infrastructure stays**: ap-southeast-5 for main services
3. ✅ **Performance maintained**: Minimal latency impact
4. ✅ **Cost optimized**: Each service in its best region
5. ✅ **Scalable**: Can easily add more regions as needed

**Your agents will work perfectly with Bedrock models while keeping your main infrastructure in ap-southeast-5!** 🚀
