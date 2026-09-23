/**
 * ws-client.test.ts — WS-инфраструктура (F1_SPEC §9): connect/reconnect/backoff.
 * Fake WebSocket; cookie-токен из arkaim_session.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// ── Fake WebSocket ──
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }
  close() {
    this.onclose?.();
  }
  emitServerFrame(msg: unknown) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }
}

vi.stubGlobal('WebSocket', FakeWebSocket);

import { WsClient } from '@/shared/realtime/ws-client';

beforeEach(() => {
  FakeWebSocket.instances = [];
  document.cookie = 'arkaim_session=test-jwt-token';
  // пере-стаб на каждый тест: restoreAllMocks в afterEach снимает глобал
  vi.stubGlobal('WebSocket', FakeWebSocket);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('WsClient', () => {
  it('connect: URL содержит токен из cookie', () => {
    const c = new WsClient();
    c.connect();
    const ws = FakeWebSocket.instances.at(-1)!;
    expect(ws.url).toContain('/ws?token=');
    expect(ws.url).toContain(encodeURIComponent('test-jwt-token'));
    c.disconnect();
  });

  it('событие backend {event,data} доходит до подписчика', () => {
    const c = new WsClient();
    const seen: unknown[] = [];
    c.on('pulse_beat', (d) => seen.push(d));
    c.connect();
    const ws = FakeWebSocket.instances.at(-1)!;
    ws.onopen?.();
    ws.emitServerFrame({ event: 'pulse_beat', data: { bpm: 12 } });
    expect(seen).toEqual([{ bpm: 12 }]);
    c.disconnect();
  });

  it('reconnect: backoff после обрыва (fake timers)', () => {
    vi.useFakeTimers();
    const c = new WsClient();
    c.connect();
    const first = FakeWebSocket.instances.at(-1)!;
    first.onclose?.(); // обрыв
    // Переподключение планируется с задержкой — до тика соединений нет
    expect(FakeWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(3000);
    expect(FakeWebSocket.instances.length).toBeGreaterThanOrEqual(2);
    c.disconnect();
    vi.useRealTimers();
  });

  // ── B1 (F1-аудит §6): disconnect → async onclose не должен resurrect ──

  it('B1: async onclose ПОСЛЕ disconnect() не создаёт новое соединение', () => {
    vi.useFakeTimers();
    const c = new WsClient();
    c.connect();
    expect(FakeWebSocket.instances).toHaveLength(1);

    c.disconnect(); // намеренное закрытие
    // ws уже null; асинхронное close-событие всё же приходит (эмулируем):
    const closed = FakeWebSocket.instances[0];
    closed.onclose?.();

    // Ни сразу, ни по прошествии reconnect-окна новых соединений быть не должно
    vi.advanceTimersByTime(70_000); // > max backoff (60с + jitter 1с)
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(c.connected).toBe(false);
    vi.useRealTimers();
  });

  it('B1: запланированный reconnect-таймер гасится disconnect()', () => {
    vi.useFakeTimers();
    const c = new WsClient();
    c.connect();
    const first = FakeWebSocket.instances.at(-1)!;
    first.onclose?.(); // обрыв → reconnect запланирован
    expect(FakeWebSocket.instances).toHaveLength(1);

    c.disconnect(); // пользователь ушёл ДО истечения backoff-задержки
    vi.advanceTimersByTime(70_000);
    expect(FakeWebSocket.instances).toHaveLength(1); // таймер погашен
    vi.useRealTimers();
  });

  it('B1: обычный обрыв ПОСЛЕ повторного connect() reconnectится как раньше', () => {
    vi.useFakeTimers();
    const c = new WsClient();
    c.connect();
    c.disconnect();
    c.connect(); // новое намеренное соединение (intentionalClose=false)
    const second = FakeWebSocket.instances.at(-1)!;
    second.onopen?.();
    second.onclose?.(); // настоящий обрыв
    vi.advanceTimersByTime(3000);
    expect(FakeWebSocket.instances.length).toBeGreaterThanOrEqual(3); // reconnect жив
    c.disconnect();
    vi.useRealTimers();
  });
});
