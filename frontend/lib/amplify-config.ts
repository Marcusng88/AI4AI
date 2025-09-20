/**
 * AWS Amplify configuration for Cognito authentication
 * Updated for ap-southeast-5 region:
 * - User Pool ID: ap-southeast-5_nuC0or8vA
 * - Client ID: 1djcgis021homk7vjhaoamfuek (SPA - no client secret)
 * - Domain: ap-southeast-5nuc0or8va.auth.ap-southeast-5.amazoncognito.com
 * - Region: ap-southeast-5
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
      userPoolId: 'ap-southeast-5_nuC0or8vA',
      // New public client ID (no client secret - perfect for SPAs)
      userPoolClientId: '1djcgis021homk7vjhaoamfuek',
      loginWith: {
        oauth: {
          domain: 'ap-southeast-5nuc0or8va.auth.ap-southeast-5.amazoncognito.com',
          scopes: ['email','openid', 'profile'],
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
