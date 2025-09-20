# AWS Region Mismatch Diagnosis

## Current Configuration Analysis

### 🔍 **The Problem**
Your system has a **region mismatch** that can cause authentication and service connectivity issues:

- **Backend AWS Region**: `ap-southeast-5` (DynamoDB, Bedrock, etc.)
- **Cognito Region**: `ap-southeast-2` (User Pool, OAuth)
- **Frontend Cognito Config**: `ap-southeast-2` (matches Cognito)

## 🚨 **Impact Analysis**

### 1. **Authentication Flow Issues**
```
User clicks "Sign In" → Frontend redirects to Cognito (ap-southeast-2) → 
User authenticates → Cognito redirects back → 
Backend tries to verify tokens using ap-southeast-5 region → ❌ MISMATCH
```

### 2. **Specific Problems This Causes**

#### A. **Token Verification Failures**
- **JWT Verification**: Backend tries to fetch JWKS from wrong region
- **User Info API**: Backend calls Cognito APIs in wrong region
- **Token Refresh**: Backend attempts token refresh in wrong region

#### B. **Service Connectivity Issues**
- **DynamoDB**: Backend creates tables in ap-southeast-5, but user data might be expected in ap-southeast-2
- **Bedrock**: Backend uses ap-southeast-5, but if user permissions are tied to ap-southeast-2, this could cause issues
- **Cross-region latency**: Increased latency between services

#### C. **User Experience Problems**
- Sign-in appears to work but backend authentication fails
- Users get authenticated but can't access protected resources
- Token refresh failures leading to unexpected logouts

## 🔧 **Solutions**

### **Option 1: Move Backend to ap-southeast-2 (Recommended)**

This is the **easiest and most reliable** solution:

#### 1. Update Backend Environment Variables
```bash
# In your .env file
AWS_DEFAULT_REGION=ap-southeast-2
```

#### 2. Update Backend Configuration Files
- `backend/app/config.py`: Change default region to `ap-southeast-2`
- `backend/setup_memory_system.py`: Update region references
- `backend/check_aws_setup.py`: Update region references

#### 3. Recreate DynamoDB Tables
Since you'll be moving regions, you'll need to recreate your tables:
```bash
# Delete existing tables in ap-southeast-5
aws dynamodb delete-table --table-name crewai-memory --region ap-southeast-5
aws dynamodb delete-table --table-name ai4ai-chat-messages --region ap-southeast-5

# Recreate in ap-southeast-2
cd backend
python setup_memory_system.py
```

### **Option 2: Move Cognito to ap-southeast-5 (Complex)**

This requires recreating your entire Cognito setup:

#### 1. Create New Cognito User Pool in ap-southeast-5
- Create new User Pool in ap-southeast-5
- Create new App Client
- Configure OAuth settings
- Update all redirect URLs

#### 2. Update Frontend Configuration
```typescript
// frontend/lib/amplify-config.ts
const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'ap-southeast-5_NEW_POOL_ID',
      userPoolClientId: 'NEW_CLIENT_ID',
      loginWith: {
        oauth: {
          domain: 'NEW_DOMAIN.auth.ap-southeast-5.amazoncognito.com',
          // ... other config
        }
      }
    }
  }
}
```

#### 3. Update Backend Cognito Service
```python
# backend/app/services/cognito_service.py
self.region = "ap-southeast-5"
self.user_pool_id = "NEW_POOL_ID"
self.client_id = "NEW_CLIENT_ID"
self.oauth_base_url = f"https://NEW_DOMAIN.auth.ap-southeast-5.amazoncognito.com"
```

### **Option 3: Cross-Region Setup (Advanced)**

Keep both regions but handle cross-region communication properly:

#### 1. Update Backend to Use Correct Cognito Region
```python
# backend/app/services/cognito_service.py
class CognitoService:
    def __init__(self):
        # Keep DynamoDB in ap-southeast-5
        self.dynamodb_region = "ap-southeast-5"
        
        # Use Cognito in ap-southeast-2
        self.cognito_region = "ap-southeast-2"
        self.user_pool_id = "ap-southeast-2_KbRSvyt1T"
        # ... rest of config
```

#### 2. Use Region-Specific AWS Clients
```python
# Create separate clients for different regions
self.dynamodb_client = boto3.client('dynamodb', region_name=self.dynamodb_region)
self.cognito_client = boto3.client('cognito-idp', region_name=self.cognito_region)
```

## 🎯 **Recommended Action Plan**

### **Step 1: Choose Option 1 (Move Backend to ap-southeast-2)**

This is the simplest solution because:
- ✅ No need to recreate Cognito setup
- ✅ Frontend already configured correctly
- ✅ Minimal code changes required
- ✅ Better performance (same region)

### **Step 2: Implementation**

1. **Update Environment Variables**:
   ```bash
   # In your .env file
   AWS_DEFAULT_REGION=ap-southeast-2
   ```

2. **Update Configuration Files**:
   ```python
   # backend/app/config.py
   aws_region: Optional[str] = os.getenv("DEFAULT_AWS_REGION", "ap-southeast-2")
   ```

3. **Recreate Memory System Tables**:
   ```bash
   cd backend
   python setup_memory_system.py
   ```

4. **Test Authentication Flow**:
   ```bash
   # Start backend
   python run.py
   
   # Start frontend
   cd ../frontend
   npm run dev
   
   # Test sign-in flow
   ```

### **Step 3: Verify Fix**

After implementing the fix, test:

1. **Sign In Flow**: User can sign in successfully
2. **Token Verification**: Backend can verify Cognito tokens
3. **Memory System**: DynamoDB operations work correctly
4. **API Calls**: Authenticated API calls work properly

## 🔍 **Current Status**

- ❌ **Backend Region**: ap-southeast-5 (causing issues)
- ✅ **Cognito Region**: ap-southeast-2 (working)
- ✅ **Frontend Config**: ap-southeast-2 (correct)
- ❌ **Region Alignment**: MISMATCHED (needs fixing)

## 📋 **Quick Fix Commands**

```bash
# 1. Update your .env file
echo "AWS_DEFAULT_REGION=ap-southeast-2" >> backend/.env

# 2. Recreate memory system in correct region
cd backend
python setup_memory_system.py

# 3. Test the fix
python check_aws_setup.py
```

**Bottom Line**: The region mismatch is definitely causing authentication issues. Moving your backend to ap-southeast-2 is the quickest fix that will resolve all authentication problems.
