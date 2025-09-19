# DynamoDB Setup Guide for Step 2.1

This guide will help you complete the DynamoDB setup for chat session management in your AI4AI application.

## 📋 Overview

You need to create two DynamoDB tables in the AWS Console and configure your environment with the proper credentials.

## 🔧 Prerequisites

1. **AWS Account** with DynamoDB access
2. **AWS CLI configured** (optional but recommended)
3. **IAM User/Role** with DynamoDB permissions

## 📊 Tables to Create

### Table 1: Chat Sessions (`ai4ai-chat-sessions`)

This table stores chat session metadata for each user.

#### AWS Console Steps:
1. Go to **AWS Console > DynamoDB > Tables**
2. Click **"Create table"**
3. Configure as follows:
   - **Table name**: `ai4ai-chat-sessions`
   - **Partition key**: `user_id` (String)
   - **Sort key**: `session_id` (String)
   - **Table settings**: Use default settings
   - **Read/write capacity**: On-demand
4. Click **"Create table"**

#### Table Schema:
```json
{
  "TableName": "ai4ai-chat-sessions",
  "KeySchema": [
    {"AttributeName": "user_id", "KeyType": "HASH"},
    {"AttributeName": "session_id", "KeyType": "RANGE"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "user_id", "AttributeType": "S"},
    {"AttributeName": "session_id", "AttributeType": "S"}
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### Table 2: Chat Messages (`ai4ai-chat-messages`)

This table stores individual messages within chat sessions.

#### AWS Console Steps:
1. Go to **AWS Console > DynamoDB > Tables**
2. Click **"Create table"**
3. Configure as follows:
   - **Table name**: `ai4ai-chat-messages`
   - **Partition key**: `session_id` (String)
   - **Sort key**: `timestamp` (Number)
   - **Table settings**: Use default settings
   - **Read/write capacity**: On-demand
4. Click **"Create table"**

#### Table Schema:
```json
{
  "TableName": "ai4ai-chat-messages",
  "KeySchema": [
    {"AttributeName": "session_id", "KeyType": "HASH"},
    {"AttributeName": "timestamp", "KeyType": "RANGE"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "session_id", "AttributeType": "S"},
    {"AttributeName": "timestamp", "AttributeType": "N"}
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

## 🔐 AWS Credentials Setup

### Method 1: Environment Variables (Recommended for Development)

Create a `.env` file in the `backend/` directory:

```bash
# Copy from env.example
cp env.example .env
```

Then edit `.env` with your AWS credentials:

```env
# AWS Configuration (Step 2.1 - DynamoDB Setup)
DEFAULT_AWS_REGION=ap-southeast-2
AWS_ACCESS_KEY_ID=your_actual_access_key_here
AWS_SECRET_ACCESS_KEY=your_actual_secret_key_here

# DynamoDB Configuration
DYNAMODB_CHAT_SESSIONS_TABLE=ai4ai-chat-sessions
DYNAMODB_CHAT_MESSAGES_TABLE=ai4ai-chat-messages
```

### Method 2: AWS CLI Configuration

```bash
aws configure
```

Enter:
- **AWS Access Key ID**: Your access key
- **AWS Secret Access Key**: Your secret key
- **Default region name**: `ap-southeast-2`
- **Default output format**: `json`

### Method 3: IAM Roles (Production)

For production deployment, use IAM roles instead of hardcoded credentials.

## 🔑 Required IAM Permissions

Your IAM user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-southeast-2:*:table/ai4ai-chat-sessions",
        "arn:aws:dynamodb:ap-southeast-2:*:table/ai4ai-chat-messages"
      ]
    }
  ]
}
```

## 🚀 Testing the Setup

### 1. Start the Backend Server

```bash
cd backend
python run.py
```

### 2. Check Logs

Look for these messages in the startup logs:

```
INFO: Creating sessions table: ai4ai-chat-sessions
INFO: Creating messages table: ai4ai-chat-messages
INFO: Sessions table ai4ai-chat-sessions created successfully
INFO: Messages table ai4ai-chat-messages created successfully
```

Or if tables already exist:

```
INFO: Sessions table ai4ai-chat-sessions already exists
INFO: Messages table ai4ai-chat-messages already exists
```

### 3. Test API Endpoints

#### Create a Session:
```bash
curl -X POST "http://localhost:8000/api/v1/sessions?user_id=test_user&title=Test Chat"
```

#### Get User Sessions:
```bash
curl "http://localhost:8000/api/v1/sessions/test_user"
```

#### Add a Message:
```bash
curl -X POST "http://localhost:8000/api/v1/sessions/{session_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Hello, this is a test message"}'
```

## 🔍 Troubleshooting

### Common Issues:

#### 1. "Could not initialize DynamoDB tables"
- **Cause**: AWS credentials not configured or incorrect
- **Solution**: Check your `.env` file or run `aws configure`

#### 2. "Access Denied" errors
- **Cause**: IAM permissions insufficient
- **Solution**: Add the required DynamoDB permissions to your IAM user/role

#### 3. "Table already exists" errors during manual creation
- **Cause**: Tables were created previously
- **Solution**: This is normal, you can skip the creation step

#### 4. Region mismatch
- **Cause**: Tables created in different region than configured
- **Solution**: Ensure all AWS resources are in `ap-southeast-2`

### Debug Commands:

#### Check if tables exist:
```bash
aws dynamodb list-tables --region ap-southeast-2
```

#### Describe a table:
```bash
aws dynamodb describe-table --table-name ai4ai-chat-sessions --region ap-southeast-2
```

#### Test AWS credentials:
```bash
aws sts get-caller-identity
```

## 📊 Monitoring

### AWS Console Monitoring:
1. Go to **AWS Console > DynamoDB > Tables**
2. Select your table
3. Click **"Metrics"** tab to view:
   - Read/Write capacity consumption
   - Throttled requests
   - Error rates

### Application Logs:
Check `backend/logs/app.log` for DynamoDB operation logs.

## 🎯 Next Steps

Once DynamoDB is working:

1. **✅ Mark Step 2.1 as Complete**
2. **➡️ Move to Step 2.2**: Backend DynamoDB service integration (already implemented)
3. **➡️ Move to Step 2.3**: Frontend integration to use DynamoDB instead of localStorage

## 🔗 API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Create new session |
| GET | `/api/v1/sessions/{user_id}` | Get user sessions |
| GET | `/api/v1/sessions/{user_id}/{session_id}` | Get specific session |
| PUT | `/api/v1/sessions/{user_id}/{session_id}` | Update session |
| DELETE | `/api/v1/sessions/{user_id}/{session_id}` | Delete session |
| GET | `/api/v1/sessions/{session_id}/messages` | Get session messages |
| POST | `/api/v1/sessions/{session_id}/messages` | Add message to session |

## 📝 Notes

- Tables use **pay-per-request** billing (no upfront costs)
- No session expiration implemented (as requested in requirements)
- All times stored in UTC
- Message timestamps use milliseconds for better sorting
- User sessions are completely isolated (no cross-user access)

---

**Status**: Ready for AWS Console configuration ✅
**Estimated Time**: 10-15 minutes for AWS setup
**Required**: AWS Console access + valid credentials
