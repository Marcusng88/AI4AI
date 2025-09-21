"use client";

import React, { useEffect, useRef, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Video, AlertCircle, Loader2 } from 'lucide-react';

interface DCVViewerProps {
  liveViewUrl: string;
  sessionId: string;
  className?: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: string) => void;
}

export function DCVViewer({ 
  liveViewUrl, 
  sessionId, 
  className = "",
  onConnect,
  onDisconnect,
  onError 
}: DCVViewerProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!liveViewUrl || !containerRef.current) return;

    const initializeDCV = async () => {
      try {
        setIsConnecting(true);
        setError(null);

        // Create iframe for DCV viewer
        const iframe = document.createElement('iframe');
        iframe.src = liveViewUrl;
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.allow = 'camera; microphone; clipboard-read; clipboard-write';
        iframe.sandbox = 'allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox';

        iframe.onload = () => {
          setIsConnected(true);
          setIsConnecting(false);
          onConnect?.();
        };

        iframe.onerror = () => {
          const errorMsg = 'Failed to load DCV viewer';
          setError(errorMsg);
          setIsConnecting(false);
          onError?.(errorMsg);
        };

        // Clear container and add iframe
        if (containerRef.current) {
          containerRef.current.innerHTML = '';
          containerRef.current.appendChild(iframe);
        }

      } catch (err) {
        const errorMsg = `DCV initialization error: ${err}`;
        setError(errorMsg);
        setIsConnecting(false);
        onError?.(errorMsg);
      }
    };

    initializeDCV();

    // Cleanup on unmount
    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
      setIsConnected(false);
      onDisconnect?.();
    };
  }, [liveViewUrl, sessionId, onConnect, onDisconnect, onError]);

  const retryConnection = () => {
    setError(null);
    setIsConnecting(false);
    // Trigger re-initialization
    if (containerRef.current) {
      containerRef.current.innerHTML = '';
    }
  };

  return (
    <div className={`relative w-full h-full bg-black ${className}`}>
      {/* Connection Status */}
      <div className="absolute top-2 right-2 z-10">
        {isConnecting && (
          <Badge variant="secondary" className="flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Connecting...
          </Badge>
        )}
        {isConnected && (
          <Badge variant="default" className="flex items-center gap-1">
            <Video className="h-3 w-3" />
            Live Streaming
          </Badge>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-75">
          <div className="text-center text-white p-4">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 text-red-400" />
            <p className="text-sm mb-2">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={retryConnection}
              className="text-white border-white hover:bg-white hover:text-black"
            >
              Retry Connection
            </Button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isConnecting && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black">
          <div className="text-center text-white">
            <Loader2 className="h-8 w-8 mx-auto mb-2 animate-spin" />
            <p className="text-sm">Initializing live view...</p>
          </div>
        </div>
      )}

      {/* DCV Container */}
      <div 
        ref={containerRef}
        className="w-full h-full"
        style={{ minHeight: '400px' }}
      />
    </div>
  );
}
