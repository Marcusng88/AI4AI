"use client"

import 'aws-amplify/auth/enable-oauth-listener'
import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/hooks/use-auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'
import { Hub } from 'aws-amplify/utils'
import { getCurrentUser, fetchUserAttributes } from 'aws-amplify/auth'

export default function AuthCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { checkAuthState } = useAuth()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    let hubUnsubscribe: (() => void) | null = null

    const handleCallback = async () => {
      try {
        // Check for error parameters from OAuth provider
        const errorParam = searchParams.get('error')
        const errorDescription = searchParams.get('error_description')
        
        if (errorParam) {
          if (mounted) {
            setError(errorDescription || errorParam)
            setStatus('error')
          }
          return
        }

        // Check for authorization code
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        
        if (!code) {
          if (mounted) {
            setError('No authorization code received')
            setStatus('error')
          }
          return
        }

        console.log('OAuth callback received with code:', code, 'state:', state)

        // Listen for Amplify Hub authentication events
        hubUnsubscribe = Hub.listen('auth', async ({ payload }) => {
          console.log('Auth Hub event:', payload.event, payload)
          
          switch (payload.event) {
            case 'signInWithRedirect':
              console.log('SignInWithRedirect successful')
              if (mounted) {
                try {
                  // Get user information after successful OAuth
                  const user = await getCurrentUser()
                  const userAttributes = await fetchUserAttributes()
                  console.log('OAuth user authenticated:', { user, userAttributes })
                  
                  setStatus('success')
                  // Redirect to main app after successful authentication
                  setTimeout(() => {
                    router.push('/')
                  }, 1000)
                } catch (err) {
                  console.error('Error getting user after OAuth:', err)
                  setError('Failed to get user information after authentication')
                  setStatus('error')
                }
              }
              break
            case 'signInWithRedirect_failure':
              console.error('SignInWithRedirect failed:', payload.data)
              if (mounted) {
                let errorMessage = 'Authentication failed during redirect'
                
                // Handle specific error types
                if (payload.data?.error) {
                  const errorData = payload.data.error
                  if (errorData.name === 'OAuthSignInException') {
                    if (errorData.message?.includes('invalid_client')) {
                      errorMessage = 'Invalid client configuration. The Cognito client needs to be configured as a public client (without client secret) for frontend applications.'
                    } else {
                      errorMessage = `OAuth error: ${errorData.message || 'Unknown OAuth error'}`
                    }
                  } else {
                    errorMessage = String(errorData.message || errorData)
                  }
                } else if (payload.data && typeof payload.data === 'object' && 'message' in payload.data) {
                  errorMessage = String(payload.data.message)
                }
                
                setError(errorMessage)
                setStatus('error')
              }
              break
            case 'customOAuthState':
              console.log('Custom OAuth state:', payload.data)
              break
            case 'tokenRefresh_failure':
              console.error('Token refresh failed:', payload.data)
              if (mounted) {
                setError('Token refresh failed')
                setStatus('error')
              }
              break
          }
        })

        // Try to check authentication state after a brief delay
        // This gives Amplify time to process the OAuth callback
        setTimeout(async () => {
          if (!mounted) return
          
          try {
            const isAuthenticated = await checkAuthState()
            console.log('Authentication state checked:', isAuthenticated)
            
            if (isAuthenticated) {
              setStatus('success')
              setTimeout(() => {
                if (mounted) {
                  router.push('/')
                }
              }, 1000)
            } else {
              // If not authenticated after 5 seconds, show error
              setTimeout(() => {
                if (mounted && status === 'processing') {
                  setError('Authentication timeout - please try again')
                  setStatus('error')
                }
              }, 3000)
            }
          } catch (err) {
            console.error('Error checking auth state:', err)
            if (mounted) {
              setError('Error checking authentication state')
              setStatus('error')
            }
          }
        }, 1000)

      } catch (err) {
        console.error('Auth callback error:', err)
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Authentication failed')
          setStatus('error')
        }
      }
    }

    handleCallback()

    return () => {
      mounted = false
      if (hubUnsubscribe) {
        hubUnsubscribe()
      }
    }
  }, [searchParams, checkAuthState, router, status])

  if (status === 'processing') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="flex items-center justify-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Processing Authentication
            </CardTitle>
            <CardDescription>
              Please wait while we complete your sign-in...
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-red-600">Authentication Failed</CardTitle>
            <CardDescription>
              {error || 'An error occurred during authentication'}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <button
              onClick={() => router.push('/auth')}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Try Again
            </button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-green-600">Success!</CardTitle>
            <CardDescription>
              You have been successfully authenticated. Redirecting...
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return null
}
