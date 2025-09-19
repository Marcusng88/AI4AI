"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/use-auth"
import { useChatApi } from "@/hooks/use-chat-api"
import { useBrowserViewer } from "@/hooks/use-browser-viewer"
import { ConversationList } from "./conversation-list"
import { BrowserPanel } from "@/components/browser/browser-panel"
import { Plus, Settings, LogOut, Menu, X, Eye, ChevronLeft, ChevronRight } from "lucide-react"

interface ChatLayoutProps {
  children: React.ReactNode
  currentSessionId?: string | null
}

export function ChatLayout({ children, currentSessionId }: ChatLayoutProps) {
  const { user, signOut } = useAuth()
  const { 
    conversations, 
    createNewConversation, 
    switchConversation, 
    deleteConversation,
    isLoadingConversations
  } = useChatApi(undefined, { enableConversationsLoad: true, enableCurrentLoad: false })
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isBrowserPanelOpen, setIsBrowserPanelOpen] = useState(false)
  
  const { 
    isVisible: isBrowserVisible, 
    liveUrl, 
    showBrowserViewer, 
    hideBrowserViewer,
    userHasControl,
    setUserControl 
  } = useBrowserViewer()

  // Listen for browser panel show events from message bubbles
  useEffect(() => {
    const handleShowBrowserPanel = (event: CustomEvent) => {
      const { liveUrl: eventLiveUrl } = event.detail;
      if (eventLiveUrl && currentSessionId) {
        showBrowserViewer(currentSessionId, eventLiveUrl);
        setIsBrowserPanelOpen(true);
      }
    };

    window.addEventListener('show-browser-panel', handleShowBrowserPanel as EventListener);
    
    return () => {
      window.removeEventListener('show-browser-panel', handleShowBrowserPanel as EventListener);
    };
  }, [currentSessionId, showBrowserViewer]);

  const handleSignOut = async () => {
    await signOut()
  }

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed)
  }

  const handleToggleBrowserPanel = () => {
    setIsBrowserPanelOpen(!isBrowserPanelOpen)
    if (!isBrowserPanelOpen && currentSessionId) {
      showBrowserViewer(currentSessionId, liveUrl)
    } else {
      hideBrowserViewer()
    }
  }

  const handleTakeControl = () => {
    setUserControl(true)
  }

  const handleReleaseControl = () => {
    setUserControl(false)
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Mobile sidebar overlay */}
      {isSidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setIsSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <div
        className={`
        fixed lg:static inset-y-0 left-0 z-50 bg-card border-r border-border
        transform transition-all duration-300 ease-in-out lg:translate-x-0
        ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}
        ${isSidebarCollapsed ? "w-16" : "w-64"}
        flex flex-col h-screen overflow-hidden flex-shrink-0
      `}
      >
        {/* Header - Fixed */}
        <div className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
          {!isSidebarCollapsed && (
            <h1 className="text-lg font-semibold">AI Chat</h1>
          )}
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={handleToggleSidebar}
              className="hidden lg:flex"
            >
              {isSidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setIsSidebarOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* New Chat Button - Fixed */}
        <div className="p-4 flex-shrink-0">
          <Button 
            className={`w-full bg-transparent ${isSidebarCollapsed ? "justify-center px-2" : "justify-start"}`} 
            variant="outline" 
            onClick={createNewConversation}
            title={isSidebarCollapsed ? "New Chat" : undefined}
          >
            <Plus className="h-4 w-4" />
            {!isSidebarCollapsed && <span className="ml-2">New Chat</span>}
          </Button>
        </div>

        {/* Chat History - Scrollable */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {isLoadingConversations ? (
            <div className="flex items-center justify-center p-4">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
            </div>
          ) : (
            <ConversationList
              conversations={conversations}
              currentConversationId={currentSessionId || undefined}
              onSelectConversation={switchConversation}
              onDeleteConversation={deleteConversation}
              isCollapsed={isSidebarCollapsed}
            />
          )}
        </div>

        {/* User Menu - Fixed */}
        <div className="p-4 border-t border-border flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-medium text-primary-foreground">
                  {user?.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              {!isSidebarCollapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user?.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                </div>
              )}
            </div>
            {!isSidebarCollapsed && (
              <div className="flex space-x-1">
                <Button variant="ghost" size="sm" title="Settings">
                  <Settings className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={handleSignOut} title="Sign Out">
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex h-screen overflow-hidden min-w-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Mobile Header */}
          <div className="lg:hidden flex items-center justify-between p-4 border-b border-border flex-shrink-0">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setIsSidebarOpen(true)}>
                <Menu className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={handleToggleSidebar}>
                {isSidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
              </Button>
            </div>
            <h1 className="text-lg font-semibold">{conversations.find(c => c.id === currentSessionId)?.title || "AI Chat"}</h1>
            <Button variant="ghost" size="sm" onClick={handleToggleBrowserPanel}>
              <Eye className="h-4 w-4" />
            </Button>
          </div>

          {/* Desktop Header */}
          <div className="hidden lg:flex items-center justify-between p-4 border-b border-border flex-shrink-0">
            <h1 className="text-lg font-semibold">{conversations.find(c => c.id === currentSessionId)?.title || "AI Chat"}</h1>
            <Button variant="ghost" size="sm" onClick={handleToggleBrowserPanel}>
              <Eye className="h-4 w-4" />
              {isBrowserPanelOpen ? "Hide" : "Show"} Live View
            </Button>
          </div>

          {/* Chat Area */}
          <div className="flex-1 min-h-0 overflow-hidden">{children}</div>
        </div>

        {/* Browser Panel */}
        {isBrowserPanelOpen && currentSessionId && (
          <BrowserPanel
            sessionId={currentSessionId}
            liveUrl={liveUrl}
            isVisible={isBrowserVisible}
            onToggle={handleToggleBrowserPanel}
            onTakeControl={handleTakeControl}
            onReleaseControl={handleReleaseControl}
          />
        )}
      </div>
    </div>
  )
}
