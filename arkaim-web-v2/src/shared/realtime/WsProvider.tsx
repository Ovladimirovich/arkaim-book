/**
 * WsProvider — жизненный цикл WS-соединения на уровне приложения (F1_SPEC §9).
 * F1 использует соединение только для индикатора онлайн в Topbar;
 * доменные подписки (уведомления/предложения) — F4/F5.
 */
'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { wsClient } from './ws-client';

interface WsStatus {
  connected: boolean;
}

const WsContext = createContext<WsStatus>({ connected: false });

export function useWsStatus(): WsStatus {
  return useContext(WsContext);
}

/** Подписка на любое WS-событие (для доменных потребителей F4+). */
export function useWsEvent(event: Parameters<typeof wsClient.on>[0], handler: (data: Record<string, unknown>) => void) {
  useEffect(() => {
    const off = wsClient.on(event, handler);
    return off;
  }, [event, handler]);
}

export function WsProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const offConn = wsClient.on('_connected', () => setConnected(true));
    const offDisc = wsClient.on('_disconnected', () => setConnected(false));
    wsClient.connect();
    return () => {
      offConn();
      offDisc();
      wsClient.disconnect();
    };
  }, []);

  return <WsContext.Provider value={{ connected }}>{children}</WsContext.Provider>;
}
