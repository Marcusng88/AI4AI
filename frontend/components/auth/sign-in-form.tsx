"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/hooks/use-auth"
import { useToast } from "@/hooks/use-toast"

interface SignInFormProps {
  onToggleMode: () => void
}

export function SignInForm({ onToggleMode }: SignInFormProps) {
  const { signIn, isLoading } = useAuth()
  const { toast } = useToast()

  const handleCognitoSignIn = async () => {
    try {
      await signIn()
      toast({
        title: "Redirecting...",
        description: "You will be redirected to sign in with AWS Cognito.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to initiate sign in",
        variant: "destructive",
      })
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl font-bold">Welcome back</CardTitle>
        <CardDescription>Sign in to your account to continue</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Button 
            onClick={handleCognitoSignIn} 
            className="w-full" 
            disabled={isLoading}
            size="lg"
          >
            {isLoading ? "Redirecting..." : "Sign in with AWS Cognito"}
          </Button>
          
          <div className="text-center text-sm text-muted-foreground">
            Secure authentication powered by AWS Cognito
          </div>
        </div>
        
        <div className="mt-6 text-center text-sm">
          {"Don't have an account? "}
          <button type="button" onClick={onToggleMode} className="text-primary hover:underline font-medium">
            Sign up
          </button>
        </div>
      </CardContent>
    </Card>
  )
}
