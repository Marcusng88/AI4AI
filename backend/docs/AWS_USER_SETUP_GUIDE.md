# AWS User Setup Guide for Memory System

## Using Your Existing `agentcore-browser` User

You **don't need to create a new user**! Your existing `agentcore-browser` user can be used for the memory system, but you need to ensure it has the right DynamoDB permissions.

## Step 1: Check Current Permissions

First, let's check what permissions your `agentcore-browser` user currently has:

```bash
# Check current user policies
aws iam list-attached-user-policies --user-name agentcore-browser
aws iam list-user-policies --user-name agentcore-browser
```

## Step 2: Add DynamoDB Permissions

Your `agentcore-browser` user needs these additional permissions for the memory system:

### Option A: Attach AWS Managed Policy (Recommended)
```bash
# Attach the AWS managed DynamoDB read/write policy
aws iam attach-user-policy \
    --user-name agentcore-browser \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
```

### Option B: Create Custom Policy (More Secure)
Create a custom policy with only the permissions needed:

```bash
# Create custom policy file
cat > dynamodb-memory-policy.json << 'EOF'
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
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:DeleteItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/crewai-memory",
                "arn:aws:dynamodb:*:*:table/ai4ai-chat-messages",
                "arn:aws:dynamodb:*:*:table/crewai-memory/*",
                "arn:aws:dynamodb:*:*:table/ai4ai-chat-messages/*"
            ]
        }
    ]
}
EOF

# Create the policy
aws iam create-policy \
    --policy-name DynamoDBMemoryAccess \
    --policy-document file://dynamodb-memory-policy.json

# Attach the policy to your user
aws iam attach-user-policy \
    --user-name agentcore-browser \
    --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/DynamoDBMemoryAccess
```

## Step 3: Get Access Keys (If Needed)

If you don't have access keys for your `agentcore-browser` user, create them:

```bash
# Create access keys
aws iam create-access-key --user-name agentcore-browser
```

**Important**: Save the access key ID and secret access key securely!

## Step 4: Update Your Environment Variables

Update your `.env` file with the credentials:

```bash
# In your .env file
AWS_ACCESS_KEY_ID=AKIA...your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_DEFAULT_REGION=ap-southeast-5
```

## Step 5: Test the Setup

Run the setup script to test everything:

```bash
cd backend
python setup_memory_system.py
```

## Alternative: Use AWS CLI Profile

If you prefer to use AWS CLI profiles instead of environment variables:

### 1. Configure AWS CLI Profile
```bash
aws configure --profile agentcore-browser
# Enter your access key ID, secret key, and region
```

### 2. Update the Setup Script
Modify `setup_memory_system.py` to use the profile:

```python
# In setup_memory_system.py, change the boto3 client initialization:
dynamodb = boto3.client(
    'dynamodb',
    profile_name='agentcore-browser'  # Use profile instead of env vars
)
```

## Troubleshooting

### Issue 1: "Access Denied" Error
```bash
# Check if the policy is attached
aws iam list-attached-user-policies --user-name agentcore-browser

# If not attached, attach it:
aws iam attach-user-policy \
    --user-name agentcore-browser \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
```

### Issue 2: "Invalid Credentials" Error
```bash
# Test your credentials
aws sts get-caller-identity --profile agentcore-browser
```

### Issue 3: "Region Mismatch" Error
Make sure your region in `.env` matches where you want to create the tables:
```bash
AWS_DEFAULT_REGION=ap-southeast-5  # or your preferred region
```

## Summary

**You don't need a new user!** Just:

1. ✅ Add DynamoDB permissions to your existing `agentcore-browser` user
2. ✅ Use the existing access keys (or create new ones if needed)
3. ✅ Update your `.env` file with the credentials
4. ✅ Run the setup script

The memory system will work with your existing AWS user once you add the DynamoDB permissions.
