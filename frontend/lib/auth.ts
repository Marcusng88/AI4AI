/**
 * AWS Cognito authentication service for AI4AI frontend
 * Integrates with AWS Cognito using Amplify Auth
 */

import { getCurrentUser, signOut, signInWithRedirect, fetchAuthSession } from 'aws-amplify/auth'
import './amplify-config' // Initialize Amplify configuration

export interface User {
  id: string
  email: string
  name: string
  emailVerified?: boolean
  phoneNumber?: string
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
}

export interface AuthTokens {
  accessToken: string
  idToken: string
}

export const authService = {
  /**
   * Sign in using Cognito hosted UI
   */
  signIn: async (): Promise<void> => {
    try {
      console.log('Initiating sign in with redirect...')
      await signInWithRedirect()
    } catch (error) {
      console.error('Sign in error:', error)
      throw new Error(`Failed to initiate sign in: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  },

  /**
   * Sign out current user
   */
  signOut: async (): Promise<void> => {
    try {
      await signOut({ global: true })
    } catch (error) {
      console.error('Sign out error:', error)
      throw new Error('Failed to sign out')
    }
  },

  /**
   * Get current authenticated user
   */
  getCurrentUser: async (): Promise<User | null> => {
    try {
      const user = await getCurrentUser()
      
      return {
        id: user.userId,
        email: user.signInDetails?.loginId || '',
        name: user.signInDetails?.loginId?.split('@')[0] || 'User',
        emailVerified: true // Assuming verified since they got through Cognito
      }
    } catch (error) {
      // User is not authenticated
      return null
    }
  },

  /**
   * Get authentication tokens
   */
  getTokens: async (): Promise<AuthTokens | null> => {
    try {
      const session = await fetchAuthSession()
      
      if (!session.tokens) {
        return null
      }

      return {
        accessToken: session.tokens.accessToken.toString(),
        idToken: session.tokens.idToken?.toString() || ''
      }
    } catch (error) {
      console.error('Error fetching tokens:', error)
      return null
    }
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated: async (): Promise<boolean> => {
    try {
      await getCurrentUser()
      return true
    } catch {
      return false
    }
  },

  /**
   * Get access token for API calls
   */
  getAccessToken: async (): Promise<string | null> => {
    try {
      const tokens = await authService.getTokens()
      return tokens?.accessToken || null
    } catch (error) {
      console.error('Error getting access token:', error)
      return null
    }
  }
}
