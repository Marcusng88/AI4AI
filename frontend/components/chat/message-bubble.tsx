"use client"

import { cn } from "@/lib/utils"
import { User, Bot, Monitor } from "lucide-react"
import { useBrowserViewer } from "@/hooks/use-browser-viewer"

interface MessageBubbleProps {
  message: string
  isUser: boolean
  timestamp?: Date
  metadata?: Record<string, any>
}

export function MessageBubble({ message, isUser, timestamp, metadata }: MessageBubbleProps) {
  const { showBrowserViewer } = useBrowserViewer()
  
  // Check if this message contains browser viewer information
  const browserViewer = metadata?.browser_viewer
  const hasBrowserViewer = browserViewer?.is_available && browserViewer?.live_url

  // Check if this message contains tutorial content
  const tutorial = metadata?.tutorial
  const hasTutorial = tutorial && tutorial.length > 0

  const handleShowBrowser = () => {
    if (browserViewer?.live_url) {
      // Dispatch event to show browser panel instead of using the hook directly
      window.dispatchEvent(new CustomEvent('show-browser-panel', {
        detail: { liveUrl: browserViewer.live_url }
      }));
    }
  }

  return (
    <div className={cn("flex gap-3 p-4", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
          <Bot className="h-4 w-4 text-primary-foreground" />
        </div>
      )}

      <div
        className={cn(
          "max-w-[70%] rounded-lg px-4 py-2",
          isUser ? "bg-primary text-primary-foreground ml-auto" : "bg-muted text-foreground",
        )}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{message}</p>
        
        {/* Tutorial Content */}
        {!isUser && hasTutorial && (
          <div className="mt-3 pt-3 border-t border-border">
            <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-4">
              <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">📚 Tutorial Guide</h4>
              <div 
                className="text-sm text-blue-800 dark:text-blue-200 prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ 
                  __html: tutorial.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>')
                }}
              />
            </div>
          </div>
        )}
        
        {/* Browser Viewer Button */}
        {!isUser && hasBrowserViewer && (
          <div className="mt-3 pt-3 border-t border-border">
            <button
              onClick={handleShowBrowser}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-md transition-colors"
            >
              <Monitor className="h-4 w-4" />
              View Live Browser
            </button>
            <p className="text-xs text-muted-foreground mt-1">
              Click to view the browser automation in real-time
            </p>
          </div>
        )}
        
        {timestamp && (
          <p className={cn("text-xs mt-1", isUser ? "text-primary-foreground/70" : "text-muted-foreground")}>
            {timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 bg-secondary rounded-full flex items-center justify-center flex-shrink-0">
          <User className="h-4 w-4 text-secondary-foreground" />
        </div>
      )}
    </div>
  )
}
