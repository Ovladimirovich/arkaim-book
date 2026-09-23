/**
 * f2-audit-b1.mjs — §6: экспериментальные teardown/reconnect-сценарии B1.
 * Используем настоящий WsClient + FakeWebSocket (как в тестах), но сценарии
 * шире: три требуемых инварианта от владельца.
 */
const out = [];
function check(name, cond, extra = '') {
  out.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) process.exitCode = 1;
}

// Fake WebSocket (эмуляция браузерного API)
class FakeWebSocket {
  static instances = [];
  url;
  onopen = null; onmessage = null; onclose = null; onerror = null;
  closed = false;
  constructor(url) { this.url = url; FakeWebSocket.instances.push(this); }
  close() {
    // close() не вызывает onclose синхронно — он асинхронный (как в браузере):
    // откладываем эхо в microtask/таймер
    this.closed = true;
    queueMicrotask(() => this.onclose?.());
  }
}

globalThis.window = {};
globalThis.WebSocket = FakeWebSocket;
const { WsClient } = await import('../src/shared/realtime/ws-client.ts');

// ── Сценарий 1: connect → disconnect → delayed close ──
{
  FakeWebSocket.instances = [];
  const c = new WsClient();
  c.connect();
  const ws1 = FakeWebSocket.instances[0];
  const before = FakeWebSocket.instances.length;
  c.disconnect();
  // delayed close-эхо приходит через секунду (имитация сетевой задержки):
  await new Promise((r) => setTimeout(r, 1000));
  ws1.onclose?.();
  // Никакого reconnect не должно было случиться:
  const after = FakeWebSocket.instances.length;
  check('S1 connect→disconnect→delayed close: НЕТ нового соединения', after === before, `инстансов: ${after}`);
  // И через backoff-окно тоже:
  await new Promise((r) => setTimeout(r, 2500));
  check('S1 …и спустя backoff-окно: инстансов не прибавилось', FakeWebSocket.instances.length === before);
  // invariant: старое соединение не инициировало reconnect
  check('S1 invariant: старое ws не породило reconnect', !c.connected);
}

// ── Сценарий 2: connect → disconnect → close callback (синхронно-поздний) ──
{
  FakeWebSocket.instances = [];
  const c = new WsClient();
  c.connect();
  const ws2 = FakeWebSocket.instances[0];
  c.disconnect();
  // close-callback стреляет ПОСЛЕ disconnect (в браузере это норм-порядок):
  ws2.onclose?.();
  await new Promise((r) => setTimeout(r, 2200)); // больше max-jitter+delay первого recon
  check('S2 connect→disconnect→close callback: 1 инстанс (reconnect не случился)', FakeWebSocket.instances.length === 1, `инстансов: ${FakeWebSocket.instances.length}`);
}

// ── Сценарий 3: connect → reconnect → stale close ──
{
  FakeWebSocket.instances = [];
  const c = new WsClient();
  c.connect();
  const wsA = FakeWebSocket.instances[0];
  // Настоящий обрыв → reconnect планируется:
  wsA.onclose?.();
  await new Promise((r) => setTimeout(r, 2200)); // reconnect успел случиться (base delay ~1s + jitter)
  const countAfterReconnect = FakeWebSocket.instances.length;
  check('S3 подготовка: после обрыва reconnect произошёл', countAfterReconnect >= 2, `инстансов: ${countAfterReconnect}`);
  // Теперь disconnect от пользователя:
  c.disconnect();
  // STALE close от СТАРОГО (первого) сокета приходит с опозданием:
  wsA.onclose?.();
  // Текущий (второй) сокет тоже закрывается (disconnect закрыл его):
  const current = FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
  if (current && current !== wsA) current.onclose?.();
  await new Promise((r) => setTimeout(r, 2500));
  // Инвариант: после disconnect НИЧТО не должно переподключиться
  check('S3 connect→reconnect→stale close: после disconnect нет воскрешений', FakeWebSocket.instances.length === countAfterReconnect, `инстансов: ${FakeWebSocket.instances.length} (было ${countAfterReconnect})`);
  check('S3 invariant: клиент не подключен', !c.connected);
}

// ── Сценарий 4 (доп): обычный обрыв ПОСЛЕ disconnect→connect — reconnect живёт ──
{
  FakeWebSocket.instances = [];
  const c = new WsClient();
  c.connect();
  c.disconnect();
  c.connect();
  const wsB = FakeWebSocket.instances.at(-1);
  wsB.onopen?.();
  wsB.onclose?.(); // подлинный обрыв активного соединения
  await new Promise((r) => setTimeout(r, 2500));
  check('S4 (доп) обычный обрыв активного соединения → reconnect работает', FakeWebSocket.instances.length >= 3, `инстансов: ${FakeWebSocket.instances.length}`);
  c.disconnect();
  await new Promise((r) => setTimeout(r, 100));
}

console.log(out.join('\n'));
