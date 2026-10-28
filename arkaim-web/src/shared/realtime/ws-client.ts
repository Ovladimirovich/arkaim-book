/**
 * shared/realtime/ws-client.ts — WS-клиент существующего контракта /ws (F1_SPEC §9).
 *
 * Контракт backend (runtime/core/websocket.py):
 *   GET /ws?token=<JWT>  — токен из cookie arkaim_session (query-param аутентификация)
 *   Сообщения: {"event": "...", "data": {...}}
 *   События: pulse_beat, new_suggestion, service_status, new_question,
 *            your_question_answered (user), chat_response (user),
 *            crowdfunding_milestone
 * Перенесено из legacy ws.ts (class A forensic) — reconnect/backoff/jitter.
 * Это одно из двух разрешённых мест сетевых вызовов (eslint).
 */
'use client';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8642';

export type WsEvent =
  | 'pulse_beat'
  | 'new_suggestion'
  | 'service_status'
  | 'new_question'
  | 'your_question_answered'
  | 'chat_response'
  | 'crowdfunding_milestone';

export interface WsMessage {
  event: WsEvent | string;
  data: Record<string, unknown>;
}

type WsHandler = (data: Record<string, unknown>) => void;

/** Внутренние события жизненного цикла соединения. */
export type WsLifecycle = '_connected' | '_disconnected';

export class WsClient {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<WsHandler>>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private token: string | null = null;
  /**
   * B1 (F1-аудит §6): disconnect() — намеренное закрытие. Асинхронный onclose
   * приходит ПОСЛЕ disconnect и не должен порождать reconnect.
   */
  private intentionalClose = false;
  connected = false;
  private attempts = 0;
  private maxAttempts = 10;

  connect(token?: string | null) {
    if (typeof window === 'undefined') return;
    this.token = token ?? this.token ?? this.getTokenFromCookie();
    this.intentionalClose = false;
    if (this.token) {
      // Токен через Sec-WebSocket-Protocol не попадает в URL/access-логи (P0-4)
      this.ws = new WebSocket(`${WS_BASE}/ws`, [`arkaim-token.${this.token}`]);
    } else {
      this.ws = new WebSocket(`${WS_BASE}/ws`);
    }

    this.ws.onopen = () => {
      this.connected = true;
      this.attempts = 0;
      this.emit('_connected', {});
    };
    this.ws.onmessage = (e) => {
      try {
        const msg: WsMessage = JSON.parse(e.data);
        this.emit(msg.event, msg.data ?? {});
      } catch {
        // не-JSON кадр — игнорируем (контракт строго JSON)
      }
    };
    this.ws.onclose = () => {
      this.connected = false;
      this.emit('_disconnected', {});
      // B1: onclose после disconnect() — это эхо намеренного закрытия,
      // reconnect запрещён (иначе resurrected-соединение = утечка).
      if (this.intentionalClose) return;
      this.scheduleReconnect();
    };
    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    // B1: ставим флаг ДО close() — асинхронный onclose увидит его
    // и не запланирует reconnect. Таймер тоже гасим на случай,
    // если disconnect вызван, пока reconnect уже в очереди.
    this.intentionalClose = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.ws?.close();
    this.ws = null;
    this.connected = false;
    this.attempts = 0;
  }

  on(event: WsEvent | WsLifecycle, handler: WsHandler): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(handler);
    return () => {
      this.handlers.get(event)?.delete(handler);
    };
  }

  private emit(event: string, data: Record<string, unknown>) {
    this.handlers.get(event)?.forEach((h) => h(data));
  }

  private scheduleReconnect() {
    if (this.attempts >= this.maxAttempts) return;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.attempts++;
    const baseDelay = Math.min(1000 * Math.pow(2, this.attempts - 1), 60000);
    const jitter = Math.random() * 1000;
    this.reconnectTimer = setTimeout(() => this.connect(), baseDelay + jitter);
  }

  private getTokenFromCookie(): string | null {
    if (typeof document === 'undefined') return null;
    const match = document.cookie.split('; ').find((c) => c.startsWith('arkaim_session='));
    return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : null;
  }
}

/** Синглтон приложения. */
export const wsClient = new WsClient();
