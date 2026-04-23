"use client";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { Wifi, WifiOff } from "lucide-react";

export function OnlineIndicator() {
  const isOnline = useOnlineStatus();
  
  if (isOnline) return null;
  
  return (
    <div className="fixed bottom-4 left-4 z-[9998] flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg shadow-lg text-sm font-medium animate-pulse">
      <WifiOff className="w-4 h-4" />
      Sem conexão com a internet
    </div>
  );
}
