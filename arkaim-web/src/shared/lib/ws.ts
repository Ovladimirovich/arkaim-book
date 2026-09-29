/**
 * ws.ts — WebSocket клиент для real-time уведомлений.
 * Поддерживает аутентификацию, reconnect, event routing.
 */

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8642';

type WsEvent = 'pulse_beat' | 'new_suggestion' | 'service_status' |
  'new_question' | 'your_question_answered' | 'chat_response' |
  'crowdfunding_milestone' | '_connected' | '_disconnected' |
  'exploration_started' | 'exploration_progress' | 'exploration_complete';

type WsMessage = { event: WsEvent; data: Record<string, unknown> };
type WsHandler = (data: Record<string, unknown>) => void;

class WsClient {
  private ws: WebSocket | null = null;
  private handlers: Map<WsEvent | string, Set<WsHandler>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private token: string | null = null;
  private connected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;

  connect(token?: string) {
    if (typeof window === 'undefined') return;
    this.token = token || this.getTokenFromCookie();
    const url = this.token
      ? `${WS_BASE}/ws?token=${encodeURIComponent(this.token)}`
      : `${WS_BASE}/ws`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectAttempts = 0;
      this.emit('_connected', {});
    };

    this.ws.onmessage = (e) => {
      try {
        const msg: WsMessage = JSON.parse(e.data);
        this.emit(msg.event, msg.data);
      } catch {}
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.emit('_disconnected', {});
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    this.connected = false;
    this.reconnectAttempts = 0;
  }

  reconnect() {
    this.disconnect();
    this.connect(this.token || undefined);
  }

  on(event: WsEvent | string, handler: WsHandler) {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(handler);
    return () => this.handlers.get(event)?.delete(handler);
  }

  private emit(event: WsEvent | string, data: Record<string, unknown>) {
    this.handlers.get(event)?.forEach(h => h(data));
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectAttempts++;
    // Exponential backoff with jitter: 1s, 2s, 4s, 8s, 16s, 32s, 60s max
    const baseDelay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 60000);
    const jitter = Math.random() * 1000;
    const delay = baseDelay + jitter;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private getTokenFromCookie(): string | null {
    if (typeof document === 'undefined') return null;
    const match = document.cookie.split('; ').find(c => c.startsWith('arkaim_session='));
    return match ? match.split('=')[1] : null;
  }

  get isConnected() {
    return this.connected;
  }
}

export const wsClient = new WsClient();
export type { WsEvent, WsMessage, WsHandler };
