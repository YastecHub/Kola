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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const source = new EventSource(_url);

    source.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    source.addEventListener("kola-events", (event) => {
      setEvents(JSON.parse(event.data) as KolaEvent[]);
    });

    source.addEventListener("kola-error", (event) => {
      const data = JSON.parse(event.data) as { message?: string };
      setError(data.message ?? "Unable to stream KOLA events");
    });

    source.onerror = () => {
      setIsConnected(false);
      setError("Reconnecting to KOLA event stream");
    };

    return () => {
      setIsConnected(false);
      source.close();
    };
  }, [_url]);

  return { events, isConnected, error };
}
