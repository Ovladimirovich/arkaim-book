'use client';

import { useState, useEffect, useCallback, createContext, useContext, useMemo } from 'react';
import { wsClient, type WsEvent, type WsMessage, type WsHandler } from './ws';

type WsContextType = {
  connected: boolean;
  lastEvent: WsMessage | null;
  on: (event: WsEvent, handler: WsHandler) => () => void;
};

const WsContext = createContext<WsContextType>({
  connected: false,
  lastEvent: null,
  on: () => () => {},
});

export const useWsContext = () => useContext(WsContext);

export function WsProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WsMessage | null>(null);

  useEffect(() => {
    wsClient.connect();
    const unsub1 = wsClient.on('_connected', () => setConnected(true));
    const unsub2 = wsClient.on('_disconnected', () => setConnected(false));
    return () => {
      unsub1();
      unsub2();
      wsClient.disconnect();
    };
  }, []);

  const on = useCallback((event: WsEvent, handler: WsHandler) => {
    return wsClient.on(event, (data) => {
      setLastEvent({ event, data });
      handler(data);
    });
  }, []);

  const value = useMemo(() => ({ connected, lastEvent, on }), [connected, lastEvent, on]);
  return <WsContext.Provider value={value}>{children}</WsContext.Provider>;
}

export function useWsEvent(event: WsEvent, handler: WsHandler) {
  useEffect(() => {
    const unsub = wsClient.on(event, handler);
    return () => { unsub(); };
  }, [event, handler]);
}
