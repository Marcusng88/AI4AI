"use client"

import 'aws-amplify/auth/enable-oauth-listener'
import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from "react"
import { type User, authService } from "@/lib/auth"
import { Hub } from 'aws-amplify/utils'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  signIn: () => Promise<void>
  signOut: () => Promise<void>
  isAuthenticated: boolean
  checkAuthState: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const checkAuthState = useCallback(async (): Promise<boolean> => {
    try {
      setIsLoading(true)
      console.log('Checking authentication state...')
      const currentUser = await authService.getCurrentUser()
      console.log('Current user:', currentUser)
      setUser(currentUser)
      return currentUser !== null
    } catch (error) {
      console.log('No authenticated user:', error)
      setUser(null)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Check authentication status on mount
  useEffect(() => {
    checkAuthState()
  }, [checkAuthState])

  // Listen for auth events
  useEffect(() => {
    const hubListenerCancelToken = Hub.listen('auth', ({ payload }) => {
      console.log('Auth Hub event received:', payload.event, payload)
      
      switch (payload.event) {
        case 'signInWithRedirect':
          console.log('SignInWithRedirect event - checking auth state')
          checkAuthState()
          break
        case 'signInWithRedirect_failure':
          console.error('Sign in failed:', payload.data)
          setIsLoading(false)
          break
        case 'signedOut':
          console.log('User signed out')
          setUser(null)
          setIsLoading(false)
          break
        case 'tokenRefresh':
          console.log('Token refreshed - checking auth state')
          checkAuthState()
          break
        case 'tokenRefresh_failure':
          console.error('Token refresh failed:', payload.data)
          break
      }
    })

    return () => hubListenerCancelToken()
  }, [checkAuthState])

  const signIn = async () => {
    try {
      setIsLoading(true)
      await authService.signIn()
      // Note: User will be set via Hub listener after redirect
    } catch (error) {
      console.error('Sign in error:', error)
      setIsLoading(false)
      throw error
    }
  }

  const signOut = async () => {
    try {
      setIsLoading(true)
      await authService.signOut()
      setUser(null)
    } catch (error) {
      console.error('Sign out error:', error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const isAuthenticated = user !== null

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signOut, isAuthenticated, checkAuthState }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
