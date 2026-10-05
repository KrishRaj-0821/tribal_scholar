import React, { useState, useEffect } from 'react';
import { WifiOff, Download, X } from 'lucide-react';

export const PwaOfflineBanner: React.FC = () => {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [installPrompt, setInstallPrompt] = useState<any>(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    const handleBeforeInstall = (e: any) => {
      e.preventDefault();
      setInstallPrompt(e);
      setShowInstallBanner(true);
    };

    const handleAppInstalled = () => {
      setShowInstallBanner(false);
      setInstallPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!installPrompt) return;
    try {
      await installPrompt.prompt();
      const choiceResult = await installPrompt.userChoice;
      if (choiceResult?.outcome === 'accepted') {
        setShowInstallBanner(false);
      }
    } catch (err) {
      console.warn('PWA install prompt error:', err);
    } finally {
      setInstallPrompt(null);
      setShowInstallBanner(false);
    }
  };

  return (
    <>
      {/* 1. Offline Mode Indicator Ribbon */}
      {isOffline && (
        <div 
          className="bg-[#C85A17] text-white py-2 px-4 text-xs font-semibold flex items-center justify-between sticky top-0 z-50 shadow-md"
          role="status"
          aria-live="polite"
        >
          <div className="gov-container flex items-center gap-2">
            <WifiOff className="w-4 h-4 flex-shrink-0 animate-pulse" />
            <span>
              <strong>You are working offline.</strong> Any entered scholarship application data is safely preserved in local offline storage and will sync automatically when connectivity returns.
            </span>
          </div>
        </div>
      )}

      {/* 2. PWA App Install Banner */}
      {showInstallBanner && !isOffline && (
        <div className="bg-[#1D0A69] text-white border-b-2 border-[#FFC107] py-2 px-4 text-xs select-none">
          <div className="gov-container flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Download className="w-4 h-4 text-[#FFC107] flex-shrink-0" />
              <span>
                <strong>Install Tribal Scholar App:</strong> Add to device home screen for faster access, offline form drafts, and SMS/push notifications.
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleInstallClick}
                className="bg-[#FFC107] hover:bg-[#FFB300] text-[#150202] font-bold px-3 py-1 rounded text-xs transition-colors shadow-xs"
              >
                Install App
              </button>
              <button
                onClick={() => setShowInstallBanner(false)}
                className="text-white/70 hover:text-white p-1"
                aria-label="Dismiss install banner"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
