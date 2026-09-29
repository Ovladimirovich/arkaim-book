import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => {
      this.readyState = 1;
      this.onopen?.();
    }, 0);
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }

  send(_data: string) {}
}

(global as any).WebSocket = MockWebSocket;

describe('WebSocket Client', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
  });

  it('creates WebSocket connection', async () => {
    const { wsClient } = await import('@/shared/lib/ws');
    wsClient.connect('test-token');
    expect(MockWebSocket.instances.length).toBe(1);
    expect(MockWebSocket.instances[0].url).toContain('test-token');
    wsClient.disconnect();
  });

  it('handles connection events', async () => {
    const { wsClient } = await import('@/shared/lib/ws');
    const handler = vi.fn();
    wsClient.on('_connected', handler);
    wsClient.connect('test-token');

    await new Promise(r => setTimeout(r, 10));
    expect(handler).toHaveBeenCalled();
    wsClient.disconnect();
  });

  it('handles custom events', async () => {
    const { wsClient } = await import('@/shared/lib/ws');
    const handler = vi.fn();
    wsClient.on('pulse_beat', handler);
    wsClient.connect('test-token');

    await new Promise(r => setTimeout(r, 10));
    const ws = MockWebSocket.instances[0];
    ws.onmessage?.({ data: JSON.stringify({ event: 'pulse_beat', data: { status: 'active' } }) });
    expect(handler).toHaveBeenCalledWith({ status: 'active' });
    wsClient.disconnect();
  });

  it('disconnects cleanly', async () => {
    const { wsClient } = await import('@/shared/lib/ws');
    wsClient.connect('test-token');
    await new Promise(r => setTimeout(r, 10));
    wsClient.disconnect();
    expect(wsClient.isConnected).toBe(false);
  });
});
