"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Monitor, 
  Play, 
  Pause, 
  RotateCcw, 
  Maximize2, 
  Minimize2,
  X,
  ExternalLink,
  MousePointer,
  Bot
} from 'lucide-react';

interface BrowserViewerProps {
  sessionId: string;
  liveUrl?: string;
  isVisible: boolean;
  onClose: () => void;
  onTakeControl?: () => void;
  onReleaseControl?: () => void;
}

interface BrowserStatus {
  status: string;
  browser_connected: boolean;
  hyperbrowser_session_active: boolean;
  hyperbrowser_live_url?: string;
}

export function BrowserViewer({ 
  sessionId, 
  liveUrl, 
  isVisible, 
  onClose,
  onTakeControl,
  onReleaseControl 
}: BrowserViewerProps) {
  const [browserStatus, setBrowserStatus] = useState<BrowserStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [userHasControl, setUserHasControl] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket connection management
  useEffect(() => {
    if (!isVisible || !sessionId) return;

    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/browser-viewer/${sessionId}`;
        
        wsRef.current = new WebSocket(wsUrl);
        
        wsRef.current.onopen = () => {
          console.log('Browser viewer WebSocket connected');
          setIsConnected(true);
          setError(null);
          setIsLoading(false);
          
          // Request initial browser status
          wsRef.current?.send(JSON.stringify({
            type: 'request_browser_status'
          }));
        };
        
        wsRef.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
          } catch (err) {
            console.error('Error parsing WebSocket message:', err);
          }
        };
        
        wsRef.current.onclose = () => {
          console.log('Browser viewer WebSocket disconnected');
          setIsConnected(false);
          
          // Attempt to reconnect after 3 seconds
          if (isVisible) {
            reconnectTimeoutRef.current = setTimeout(() => {
              connectWebSocket();
            }, 3000);
          }
        };
        
        wsRef.current.onerror = (error) => {
          console.error('Browser viewer WebSocket error:', error);
          setError('Connection error. Attempting to reconnect...');
        };
        
      } catch (err) {
        console.error('Error connecting to browser viewer WebSocket:', err);
        setError('Failed to connect to browser viewer');
        setIsLoading(false);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isVisible, sessionId]);

  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'browser_status':
        setBrowserStatus(message.status);
        if (message.live_url && !liveUrl) {
          // Update live URL if not already set
          window.dispatchEvent(new CustomEvent('browser-live-url-updated', {
            detail: { liveUrl: message.live_url }
          }));
        }
        break;
        
      case 'browser_viewer_ready':
        // Handle browser viewer ready event from backend
        const { live_url, browser_connected, hyperbrowser_session_active } = message;
        if (live_url) {
          window.dispatchEvent(new CustomEvent('browser-viewer-ready', {
            detail: { 
              live_url, 
              browser_connected, 
              hyperbrowser_session_active 
            }
          }));
        }
        break;
        
      case 'control_taken':
        setUserHasControl(true);
        break;
        
      case 'control_released':
        setUserHasControl(false);
        break;
        
      case 'browser_viewer_connected':
        console.log('Browser viewer connected:', message.message);
        break;
        
      case 'error':
        setError(message.message);
        break;
        
      default:
        console.log('Unknown browser viewer message:', message);
    }
  };

  const handleTakeControl = () => {
    wsRef.current?.send(JSON.stringify({
      type: 'take_control'
    }));
    onTakeControl?.();
  };

  const handleReleaseControl = () => {
    wsRef.current?.send(JSON.stringify({
      type: 'release_control'
    }));
    onReleaseControl?.();
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const refreshBrowser = () => {
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  const openInNewTab = () => {
    if (liveUrl || browserStatus?.hyperbrowser_live_url) {
      window.open(liveUrl || browserStatus?.hyperbrowser_live_url, '_blank');
    }
  };

  if (!isVisible) return null;

  const currentLiveUrl = liveUrl || browserStatus?.hyperbrowser_live_url;
  const isBrowserActive = browserStatus?.browser_connected || false;

  return (
    <Card className={`browser-viewer ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Monitor className="h-5 w-5" />
          <CardTitle className="text-lg">Live Browser</CardTitle>
          <Badge variant={isBrowserActive ? "default" : "secondary"}>
            {isBrowserActive ? "Active" : "Inactive"}
          </Badge>
          {userHasControl && (
            <Badge variant="destructive" className="flex items-center gap-1">
              <MousePointer className="h-3 w-3" />
              User Control
            </Badge>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {isBrowserActive && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleTakeControl}
                disabled={userHasControl}
                className="flex items-center gap-1"
              >
                <MousePointer className="h-3 w-3" />
                Take Control
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleReleaseControl}
                disabled={!userHasControl}
                className="flex items-center gap-1"
              >
                <Bot className="h-3 w-3" />
                Release Control
              </Button>
            </>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={refreshBrowser}
            disabled={!isBrowserActive}
          >
            <RotateCcw className="h-3 w-3" />
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={openInNewTab}
            disabled={!currentLiveUrl}
          >
            <ExternalLink className="h-3 w-3" />
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={toggleFullscreen}
          >
            {isFullscreen ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        {isLoading && (
          <div className="flex items-center justify-center h-64 bg-gray-50">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-sm text-gray-600">Connecting to browser...</p>
            </div>
          </div>
        )}
        
        {error && (
          <div className="flex items-center justify-center h-64 bg-red-50">
            <div className="text-center">
              <div className="text-red-600 mb-2">⚠️</div>
              <p className="text-sm text-red-600">{error}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.location.reload()}
                className="mt-2"
              >
                Retry
              </Button>
            </div>
          </div>
        )}
        
        {!isLoading && !error && !isBrowserActive && (
          <div className="flex items-center justify-center h-64 bg-gray-50">
            <div className="text-center">
              <Monitor className="h-12 w-12 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600">Browser not initialized</p>
              <p className="text-xs text-gray-500 mt-1">
                The browser will appear here when automation starts
              </p>
            </div>
          </div>
        )}
        
        {!isLoading && !error && isBrowserActive && currentLiveUrl && (
          <div className="relative">
            <iframe
              ref={iframeRef}
              src={currentLiveUrl}
              className="w-full h-96 border-0"
              style={{ minHeight: isFullscreen ? 'calc(100vh - 120px)' : '384px' }}
              allow="camera; microphone; clipboard-read; clipboard-write"
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
            />
            
            {userHasControl && (
              <div className="absolute top-2 left-2 bg-red-600 text-white px-2 py-1 rounded text-xs font-medium">
                You have control
              </div>
            )}
          </div>
        )}
        
        {!isLoading && !error && isBrowserActive && !currentLiveUrl && (
          <div className="flex items-center justify-center h-64 bg-yellow-50">
            <div className="text-center">
              <div className="text-yellow-600 mb-2">⚠️</div>
              <p className="text-sm text-yellow-600">Browser active but live URL not available</p>
              <p className="text-xs text-yellow-500 mt-1">
                This may be a local browser session
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
