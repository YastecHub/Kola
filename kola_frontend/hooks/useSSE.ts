"use client";

import { useEffect, useState } from "react";

export interface KolaEvent {
  id: string;
  title: string;
  amount: string;
  meta: string;
}

export function useSSE(_url: string) {
  const [events, setEvents] = useState<KolaEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    setIsConnected(true);
    const timer = window.setInterval(() => {
      setEvents((current) => [
        {
          id: crypto.randomUUID(),
          title: "Live Week Contribution",
          amount: "N5,000",
          meta: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        },
        ...current
      ].slice(0, 3));
    }, 9000);
    return () => {
      setIsConnected(false);
      window.clearInterval(timer);
    };
  }, []);

  return { events, isConnected, error: null };
}
