# Fix for Cognito OAuth `invalid_client` Error

## Problem
Your current Cognito User Pool Client (`35n2siagsdvuhoomfuat2jmkum`) has a **client secret** configured, but frontend Single Page Applications (SPAs) should use **public clients** without secrets for security reasons.

## Root Cause
- **Current Client**: Has client secret → Expects client authentication during OAuth
- **Frontend (Amplify)**: Cannot securely store client secrets → Sends unauthenticated requests
- **Result**: `invalid_client` error (400 Bad Request)

## ✅ Solution: Create a New Public Cognito Client

### Step 1: Create New Public Client

1. **Go to AWS Cognito Console**:
   - Region: `ap-southeast-2`
   - User Pool: `ap-southeast-2_EqqfWNKNE`

2. **Navigate to**: App integration → App clients and analytics → **Create app client**

3. **Configure the New Client**:
   ```
   App client name: ai4ai-frontend-public
   
   ❌ Generate client secret: UNCHECKED (Critical!)
   
   Auth flows:
   ✅ ALLOW_USER_SRP_AUTH
   ✅ ALLOW_REFRESH_TOKEN_AUTH
   
   OAuth 2.0 grant types:
   ✅ Authorization code grant
   
   OAuth 2.0 scopes:
   ✅ openid
   ✅ email  
   ✅ profile
   ✅ phone
   
   Callback URLs:
   - http://localhost:3000/auth/callback
   - https://d84l1y8p4kdic.cloudfront.net/auth/callback
   
   Sign out URLs:
   - http://localhost:3000
   - https://d84l1y8p4kdic.cloudfront.net
   ```

4. **Save** and note the new **Client ID**

### Step 2: Update Frontend Configuration

Replace the client ID in `frontend/lib/amplify-config.ts`:

```typescript
// Current (has secret - causes error)
userPoolClientId: '35n2siagsdvuhoomfuat2jmkum', 

// Replace with new public client ID
userPoolClientId: 'YOUR_NEW_PUBLIC_CLIENT_ID', 
```

### Step 3: Update Backend (Optional)

Keep your current backend client for server-to-server authentication:

```python
# backend/app/services/cognito_service.py
# Keep this for backend API authentication
self.client_id = "35n2siagsdvuhoomfuat2jmkum"  # With secret
self.client_secret = "1q2n4b2clkerphpdv1f28kahcm4gcamkl4q1m82m6j008sft8k26"
```

## 🔧 Alternative Quick Fix - Remove Client Secret (Recommended)

Since you have access to the client secret (`1q2n4b2clkerphpdv1f28kahcm4gcamkl4q1m82m6j008sft8k26`), you can modify your existing client:

1. Go to AWS Cognito Console → Your User Pool → App clients
2. Select your existing client: `35n2siagsdvuhoomfuat2jmkum`
3. Edit the client settings
4. **Uncheck "Generate client secret"** or remove the existing secret
5. Save changes

This will immediately fix the OAuth flow for your frontend while maintaining the same client ID.

⚠️ **Important**: Update your backend service to not use the client secret after this change.

## ✅ Verification

After implementing the fix:

1. Clear browser cache/localStorage
2. Try OAuth login again
3. You should see successful authentication without `invalid_client` errors

## 📝 Security Best Practices

- ✅ **Frontend**: Public clients (no secrets)
- ✅ **Backend**: Confidential clients (with secrets)
- ✅ **Mobile**: Public clients (no secrets)
- ✅ **Server-to-Server**: Confidential clients (with secrets)

## 🆘 If Still Having Issues

1. Check CloudWatch logs for detailed error messages
2. Verify redirect URLs match exactly (including protocol)
3. Ensure OAuth scopes are properly configured
4. Check browser network tab for the exact error response

---

**Note**: This follows AWS security best practices where frontend applications use public OAuth clients and backend services use confidential clients with secrets.
