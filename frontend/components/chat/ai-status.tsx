"use client"

import { Badge } from "@/components/ui/badge"
import { Bot } from "lucide-react"

export function AIStatus() {
  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-muted/30">
      <Bot className="h-4 w-4 text-primary" />
      <span className="text-sm text-muted-foreground">AI Assistant</span>
    </div>
  )
}
