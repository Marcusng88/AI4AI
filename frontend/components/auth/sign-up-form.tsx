"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/hooks/use-auth"
import { useToast } from "@/hooks/use-toast"

interface SignUpFormProps {
  onToggleMode: () => void
}

export function SignUpForm({ onToggleMode }: SignUpFormProps) {
  const { signIn, isLoading } = useAuth()
  const { toast } = useToast()

  const handleCognitoSignUp = async () => {
    try {
      await signIn() // Same flow - Cognito hosted UI handles both sign in and sign up
      toast({
        title: "Redirecting...",
        description: "You will be redirected to sign up with AWS Cognito.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to initiate sign up",
        variant: "destructive",
      })
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl font-bold">Create account</CardTitle>
        <CardDescription>Sign up to start chatting with AI</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Button 
            onClick={handleCognitoSignUp} 
            className="w-full" 
            disabled={isLoading}
            size="lg"
          >
            {isLoading ? "Redirecting..." : "Sign up with AWS Cognito"}
          </Button>
          
          <div className="text-center text-sm text-muted-foreground">
            Create your account securely with AWS Cognito
          </div>
        </div>
        
        <div className="mt-6 text-center text-sm">
          Already have an account?{" "}
          <button type="button" onClick={onToggleMode} className="text-primary hover:underline font-medium">
            Sign in
          </button>
        </div>
      </CardContent>
    </Card>
  )
}
