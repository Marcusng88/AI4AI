# AWS Cognito Setup Guide for ap-southeast-5

## Step-by-Step Cognito Configuration

### 🎯 **Overview**
We'll create a new Cognito User Pool in `ap-southeast-5` to match your backend region.

## **Step 1: Create User Pool**

### 1.1 Navigate to Cognito
1. Go to AWS Console → **Cognito** service
2. **Select Region**: `ap-southeast-5` (Singapore)
3. Click **"Create user pool"**

### 1.2 Configure User Pool
```
Step 1: Configure sign-in experience
├── Cognito user pool sign-in options:
    ☑️ Email
    ☐ Username
    ☐ Phone number
    ☐ Preferred username

├── User name requirements:
    ☐ Allow users to sign in with an email address, phone number, or username
    ☑️ Allow users to sign in with preferred username
    ☑️ Allow users to sign in with an email address

Step 2: Configure security requirements
├── Password policy:
    ☑️ Use the Cognito defaults

├── Multi-factor authentication:
    ☐ Required
    ☑️ Optional (Recommended for better UX)

├── User account recovery:
    ☑️ Enable self-service account recovery
    ☑️ Email only

Step 3: Configure sign-up experience
├── Self-service sign-up:
    ☑️ Enable self-registration

├── Attribute verification and user account confirmation:
    ☑️ Send email message to verify new accounts
    ☐ Send SMS message to verify new accounts

├── Required attributes:
    ☑️ email
    ☐ phone_number
    ☐ given_name
    ☐ family_name
    ☐ address
    ☐ birthdate
    ☐ gender
    ☐ locale
    ☐ middle_name
    ☐ name
    ☐ nickname
    ☐ picture
    ☐ preferred_username
    ☐ profile
    ☐ updated_at
    ☐ website

Step 4: Configure message delivery
├── Email:
    ☑️ Send email with Cognito
    ☐ Send email with Amazon SES

Step 5: Integrate your app
├── User pool name:
    `ai4ai-government-services`

├── Use the Cognito Hosted UI:
    ☑️ Use the Cognito Hosted UI

├── Domain:
    ☑️ Use a Cognito domain
    Domain prefix: `ai4ai-gov-services-ap5`
    (This will create: ai4ai-gov-services-ap5.auth.ap-southeast-5.amazoncognito.com)

├── Initial app client:
    App client name: `ai4ai-frontend-spa`
    App client type: ☑️ Public client (no client secret)
    Authentication flows:
        ☑️ ALLOW_USER_PASSWORD_AUTH
        ☑️ ALLOW_USER_SRP_AUTH
        ☑️ ALLOW_REFRESH_TOKEN_AUTH
        ☑️ ALLOW_CUSTOM_AUTH
    OAuth 2.0 grant types:
        ☑️ Authorization code grant
        ☑️ Implicit grant
    OAuth scopes:
        ☑️ openid
        ☑️ email
        ☑️ profile
        ☑️ aws.cognito.signin.user.admin

├── Hosted authentication pages:
    ☑️ Use the Cognito Hosted UI
    ☑️ Use the Cognito Hosted UI for the OAuth 2.0 flow

├── OAuth 2.0 settings:
    Callback URL(s):
        http://localhost:3000/auth/callback
        https://yourdomain.com/auth/callback (add your production domain later)
    
    Sign out URL(s):
        http://localhost:3000
        https://yourdomain.com (add your production domain later)

    OAuth 2.0 grant types:
        ☑️ Authorization code grant
        ☑️ Implicit grant

Step 6: Review and create
├── Review all settings
├── Click "Create user pool"
```

## **Step 2: Get Configuration Details**

After creation, you'll get these details:

### 2.1 User Pool Information
```
User Pool ID: ap-southeast-5_XXXXXXXXX
ARN: arn:aws:cognito-idp:ap-southeast-5:ACCOUNT_ID:userpool/ap-southeast-5_XXXXXXXXX
```

### 2.2 App Client Information
```
App Client ID: XXXXXXXXXXXXXXX
App Client Secret: (None - it's a public client)
```

### 2.3 Domain Information
```
Domain: ai4ai-gov-services-ap5.auth.ap-southeast-5.amazoncognito.com
```

## **Step 3: Update Frontend Configuration**

### 3.1 Update Amplify Config
```typescript
// frontend/lib/amplify-config.ts
const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'ap-southeast-5_XXXXXXXXX', // Your new User Pool ID
      userPoolClientId: 'XXXXXXXXXXXXXXX', // Your new App Client ID
      loginWith: {
        oauth: {
          domain: 'ai4ai-gov-services-ap5.auth.ap-southeast-5.amazoncognito.com', // Your new domain
          scopes: ['openid', 'email', 'profile', 'aws.cognito.signin.user.admin'],
          redirectSignIn: [
            'http://localhost:3000/auth/callback'
          ],
          redirectSignOut: [
            'http://localhost:3000'
          ],
          responseType: 'code' as const
        }
      }
    }
  }
}
```

### 3.2 Update Backend Cognito Service
```python
# backend/app/services/cognito_service.py
class CognitoService:
    def __init__(self):
        # Updated configuration for ap-southeast-5
        self.region = "ap-southeast-5"
        self.user_pool_id = "ap-southeast-5_XXXXXXXXX"  # Your new User Pool ID
        self.client_id = "XXXXXXXXXXXXXXX"  # Your new App Client ID
        self.client_secret = None  # SPA client doesn't have a secret
        
        # OAuth URLs
        self.authority = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        self.oauth_base_url = f"https://ai4ai-gov-services-ap5.auth.{self.region}.amazoncognito.com"
        
        # JWT verification
        self.jwks_url = f"{self.authority}/.well-known/jwks.json"
        self.jwks_client = None
        self._jwks_cache = None
        self._jwks_cache_time = None
        
        logger.info(f"Initialized Cognito service for region {self.region}")
```

## **Step 4: Test the Setup**

### 4.1 Test Frontend
```bash
cd frontend
npm run dev
# Navigate to http://localhost:3000
# Click "Sign in with AWS Cognito"
# Should redirect to your new Cognito hosted UI
```

### 4.2 Test Backend
```bash
cd backend
python -c "
from app.services.cognito_service import cognito_service
print('Cognito region:', cognito_service.region)
print('User Pool ID:', cognito_service.user_pool_id)
print('OAuth URL:', cognito_service.oauth_base_url)
"
```

## **Step 5: Create Test User**

### 5.1 Create User via AWS Console
1. Go to your new User Pool
2. Click **"Users"** tab
3. Click **"Create user"**
4. Fill in:
   ```
   Username: testuser
   Email: your-email@example.com
   Temporary password: TempPass123!
   ☑️ Mark email as verified
   ```
5. Click **"Create user"**

### 5.2 Test Sign In
1. Go to your frontend
2. Click "Sign in with AWS Cognito"
3. Use the test user credentials
4. Should work seamlessly!

## **Step 6: Clean Up Old Cognito (Optional)**

After confirming everything works:
1. Go to old Cognito User Pool (ap-southeast-2)
2. Delete the User Pool
3. This will clean up any unused resources

## **Important Notes**

### ✅ **What This Setup Gives You:**
- **Region Alignment**: Backend (ap-southeast-5) + Cognito (ap-southeast-5)
- **SPA-Optimized**: Public client (no client secret needed)
- **OAuth 2.0**: Authorization code flow for security
- **Hosted UI**: Professional sign-in experience
- **Email Verification**: Automatic email verification
- **Self-Service**: Users can sign up themselves

### 🔒 **Security Features:**
- **HTTPS Only**: All OAuth flows use HTTPS
- **CSRF Protection**: Built-in state parameter handling
- **Token Validation**: JWT tokens with proper expiration
- **Scope Limitation**: Only necessary OAuth scopes

### 🚀 **Production Considerations:**
- Add production callback URLs
- Consider using Amazon SES for emails
- Enable MFA for enhanced security
- Set up proper logging and monitoring

## **Quick Reference**

After setup, you'll have:
```
Region: ap-southeast-5
User Pool ID: ap-southeast-5_XXXXXXXXX
App Client ID: XXXXXXXXXXXXXXX
Domain: ai4ai-gov-services-ap5.auth.ap-southeast-5.amazoncognito.com
Callback URL: http://localhost:3000/auth/callback
Sign Out URL: http://localhost:3000
```

This configuration will perfectly align with your backend region and resolve all authentication issues!
