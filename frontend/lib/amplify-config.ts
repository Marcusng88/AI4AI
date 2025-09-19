/**
 * AWS Amplify configuration for Cognito authentication
 * Based on your NEW Cognito setup:
 * - User Pool ID: ap-southeast-2_KbRSvyt1T
 * - Client ID: 25de8c235cphr8mqqoenamc6dn (SPA - no client secret)
 * - Domain: ap-southeast-2kbrsvyt1t.auth.ap-southeast-2.amazoncognito.com
 * - Region: ap-southeast-2
 */

import { Amplify } from 'aws-amplify'

// Determine if we're running locally
const isLocalhost = typeof window !== 'undefined' && (
  window.location.hostname === 'localhost' ||
  window.location.hostname === '[::1]' ||
  window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
)

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'ap-southeast-2_KbRSvyt1T',
      // New public client ID (no client secret - perfect for SPAs)
      userPoolClientId: '25de8c235cphr8mqqoenamc6dn',
      loginWith: {
        oauth: {
          domain: 'ap-southeast-2kbrsvyt1t.auth.ap-southeast-2.amazoncognito.com',
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

// Configure Amplify with error handling
try {
  Amplify.configure(amplifyConfig)
  console.log('Amplify configured successfully')
} catch (error) {
  console.error('Error configuring Amplify:', error)
}

export { amplifyConfig }
