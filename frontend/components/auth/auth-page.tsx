"use client"

import { useState } from "react"
import { SignInForm } from "./sign-in-form"
import { SignUpForm } from "./sign-up-form"

export function AuthPage() {
  const [isSignIn, setIsSignIn] = useState(true)

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-md">
        {isSignIn ? (
          <SignInForm onToggleMode={() => setIsSignIn(false)} />
        ) : (
          <SignUpForm onToggleMode={() => setIsSignIn(true)} />
        )}
      </div>
    </div>
  )
}
