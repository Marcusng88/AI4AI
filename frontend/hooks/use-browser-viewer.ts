import { useState, useEffect, useCallback } from 'react';

interface BrowserViewerState {
  isVisible: boolean;
  liveUrl?: string;
  sessionId?: string;
  isBrowserActive: boolean;
  userHasControl: boolean;
}

export function useBrowserViewer() {
  const [state, setState] = useState<BrowserViewerState>({
    isVisible: false,
    isBrowserActive: false,
    userHasControl: false,
  });

  // Listen for browser live URL updates from the backend
  useEffect(() => {
    const handleLiveUrlUpdate = (event: CustomEvent) => {
      const { liveUrl } = event.detail;
      if (liveUrl) {
        setState(prev => ({
          ...prev,
          liveUrl,
          isVisible: true,
          isBrowserActive: true,
        }));
      }
    };

    const handleBrowserViewerReady = (event: CustomEvent) => {
      const { live_url, browser_connected, hyperbrowser_session_active } = event.detail;
      if (live_url) {
        setState(prev => ({
          ...prev,
          liveUrl: live_url,
          isVisible: true,
          isBrowserActive: browser_connected || hyperbrowser_session_active,
        }));
      }
    };

    window.addEventListener('browser-live-url-updated', handleLiveUrlUpdate as EventListener);
    window.addEventListener('browser-viewer-ready', handleBrowserViewerReady as EventListener);
    
    return () => {
      window.removeEventListener('browser-live-url-updated', handleLiveUrlUpdate as EventListener);
      window.removeEventListener('browser-viewer-ready', handleBrowserViewerReady as EventListener);
    };
  }, []);

  const showBrowserViewer = useCallback((sessionId: string, liveUrl?: string) => {
    setState(prev => ({
      ...prev,
      isVisible: true,
      sessionId,
      liveUrl,
      isBrowserActive: !!liveUrl,
    }));
  }, []);

  const hideBrowserViewer = useCallback(() => {
    setState(prev => ({
      ...prev,
      isVisible: false,
      userHasControl: false,
    }));
  }, []);

  const updateLiveUrl = useCallback((liveUrl: string) => {
    setState(prev => ({
      ...prev,
      liveUrl,
      isBrowserActive: true,
    }));
  }, []);

  const setBrowserActive = useCallback((isActive: boolean) => {
    setState(prev => ({
      ...prev,
      isBrowserActive: isActive,
    }));
  }, []);

  const setUserControl = useCallback((hasControl: boolean) => {
    setState(prev => ({
      ...prev,
      userHasControl: hasControl,
    }));
  }, []);

  return {
    ...state,
    showBrowserViewer,
    hideBrowserViewer,
    updateLiveUrl,
    setBrowserActive,
    setUserControl,
  };
}
