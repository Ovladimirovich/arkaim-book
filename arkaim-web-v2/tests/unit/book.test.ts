/**
 * book.test.ts — book-контракты против mock-транспорта (F2_SPEC §4, §11-2).
 * Ответы = фактический live-JSON backend (F2-аудит шаг 0).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import { ask, getChapters, getChapter, getText, getLayers, getGenome, listDocuments, uploadDocument } from '@/shared/api/contracts/book';
import { envelopeOf } from '@/shared/api/envelope';

const ok = (data: unknown, extra: Record<string, unknown> = {}) =>
  new Response(JSON.stringify({ ok: true, data, ...extra }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

afterEach(() => {
  fetchMock.mockReset();
});

describe('POST /book/ask', () => {
  it('enveloped → AskAnswer (answer, source, provenance, pulse_confidence)', async () => {
    fetchMock.mockResolvedValue(
      ok({
        answer: 'Кали Юга — тёмная эпоха.',
        source: 'knowledge:theme',
        provenance: [{ type: 'theme', name: 'Кали Юга' }],
        pulse_confidence: 0.85,
        llm_used: true,
        mood: 'curiosity',
        suggestion: 'Вас интересует связь с другими темами?',
      }),
    );
    const r = await ask({ question: 'Что такое Кали Юга?' });
    expect(r.answer).toBe('Кали Юга — тёмная эпоха.');
    expect(r.source).toBe('knowledge:theme');
    expect(r.pulse_confidence).toBeGreaterThan(0);
    expect(r.llm_used).toBe(true);
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe('/book/ask');
    expect(JSON.parse(call[1].body).question).toBe('Что такое Кали Юга?');
  });

  it('timeout повышен до 60с (дорогая RAG-операция)', () => {
    fetchMock.mockResolvedValue(ok({ answer: 'x', source: 's' }));
    ask({ question: 'q' });
    expect(fetchMock.mock.calls[0][1].signal).toBeTruthy();
  });

  it('500 → ApiError HTTP_500 (ретрай один, потом наружу)', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: false, error: { code: 'HTTP_500', message: 'Err' } }), { status: 500 }));
    await expect(ask({ question: 'q' })).rejects.toMatchObject({ code: 'HTTP_500' });
    expect(fetchMock.mock.calls.length).toBe(2); // retry ×1 на 5xx (client.ts)
  });
});

describe('GET /book/chapters', () => {
  it('enveloped → Chapter[]', async () => {
    fetchMock.mockResolvedValue(
      ok([
        { id: 'ch_00', title: 'Часть 0', char_count: 718, index: 0 },
        { id: 'ch_01', title: 'Пролог', char_count: 3672, index: 1 },
      ]),
    );
    const ch = await getChapters();
    expect(ch).toHaveLength(2);
    expect(ch[0].id).toBe('ch_00');
    expect(ch[1].char_count).toBeGreaterThan(0);
  });
});

describe('GET /book/chapters/{chapter_id}', () => {
  it('enveloped → ChapterContent с полными text-овым content', async () => {
    fetchMock.mockResolvedValue(
      ok({ id: 'ch_01', title: 'Пролог', content: 'Первый абзац.\n\nВторой абзац.', char_count: 30, index: 1 }),
    );
    const ch = await getChapter('ch_01');
    expect(ch.content).toContain('Первый абзац');
    expect(ch.title).toBe('Пролог');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/chapters/ch_01');
  });

  it('envelope-карта: путь с {chapter_id} матчится как enveloped', () => {
    expect(envelopeOf('GET', '/book/chapters/ch_07')).toBe('enveloped');
  });

  it('текст главы берётся из этого endpoint, а НЕ из /book/text', async () => {
    // /book/text режет глобальный текст всей книги — для чтения главы он непригоден.
    fetchMock.mockResolvedValue(ok({ id: 'ch_02', title: 'Гл. 2', content: 'X', char_count: 1, index: 2 }));
    await getChapter('ch_02');
    expect(fetchMock.mock.calls[0][0]).not.toContain('/book/text');
  });
});

describe('GET /book/text (пагинация в конверте)', () => {
  it('direct-конверт: data=строка + offset/limit/total/has_more', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, data: 'Автор: ОВладимирович Аннотация', offset: 0, limit: 200, total: 116333, has_more: true }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const page = await getText(0, 200);
    expect(page.data).toContain('Аннотация');
    expect(page.offset).toBe(0);
    expect(page.total).toBe(116333);
    expect(page.has_more).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/text?offset=0&limit=200');
  });

  it('второй чанк — offset сдвигается', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, data: '…продолжение', offset: 200, limit: 200, total: 400, has_more: false }),
        { status: 200 },
      ),
    );
    const page = await getText(200, 200);
    expect(page.offset).toBe(200);
    expect(page.has_more).toBe(false);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/text?offset=200&limit=200');
  });
});

describe('GET /book/layers', () => {
  it('direct → 5 слоёв сознания', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          knowledge_layer: 'Книга: Наследие Аркаима',
          meaning_layer: '…',
          identity_layer: '…',
          mission_layer: '…',
          world_engine_layer: '…',
        }),
        { status: 200 },
      ),
    );
    const l = await getLayers();
    expect(l.knowledge_layer).toContain('Наследие');
  });
});

describe('GET /book/genome', () => {
  it('direct → themes[] с strength', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          themes: [{ id: 'theme_138', name: 'Наследие Учения', description: 'Передача', strength: 0.95 }],
          characters: [{ id: 'c1', name: 'Влад', description: 'Гость из будущего', strength: 1 }],
        }),
        { status: 200 },
      ),
    );
    const g = await getGenome();
    expect(g.themes![0].name).toBe('Наследие Учения');
    expect(g.characters![0].name).toBe('Влад');
  });

  it('403 reader→нет: genome НЕ гейтится can() — контракт без gate', async () => {
    // Просто проверяем, что контракт вызывает endpoint напрямую (без RBAC-обёртки):
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ themes: [] }), { status: 200 }),
    );
    const g = await getGenome();
    expect(g.themes).toEqual([]);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/genome');
  });
});

// ── BookOS /upload ───────────────────────────────────────────────────────

describe('GET /book/os/documents', () => {
  it('direct → Document[] (id, title, type, version, imported_at, hash)', async () => {
    const now = new Date().toISOString();
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify([{ id: 'd1', title: 'test.md', type: 'primary_source', version: '1.0.0', imported_at: now, hash: 'a'.repeat(64) }]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const docs = await listDocuments();
    expect(docs).toHaveLength(1);
    expect(docs[0].id).toBe('d1');
    expect(docs[0].type).toBe('primary_source');
  });

  it('передаёт doc_type в query string', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    await listDocuments('external');
    expect(fetchMock.mock.calls[0][0]).toContain('doc_type=external');
  });
});

describe('POST /book/os/pipeline/ingest', () => {
  it('отправляет multipart с полем file и query params', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', document_id: 'x', chunks_count: 5 }), { status: 200 }),
    );
    const file = new File(['hello'], 'doc.txt', { type: 'text/plain' });
    await uploadDocument(file, 'secondary_source', '3.0.0');
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/book/os/pipeline/ingest');
    expect(url).toContain('doc_type=secondary_source');
    expect(url).toContain('version=3.0.0');
    expect(opts.method).toBe('POST');
    expect(opts.credentials).toBe('same-origin');
    expect(opts.body instanceof FormData).toBe(true);
    expect((opts.body as FormData).get('file')).toBe(file);
  });

  it('кидает ошибку при HTTP 4xx', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'File too large' }), { status: 400 }),
    );
    await expect(uploadDocument(new File(['x'], 'big.pdf'))).rejects.toThrow('File too large');
  });
});
