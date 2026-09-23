/**
 * upload.test.ts — контракты BookOS (listDocuments / uploadDocument).
 * Ответы = фактический live-JSON backend.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import { listDocuments, uploadDocument, type Document, type IngestResult } from '@/shared/api/contracts/book';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Константы страницы ───────────────────────────────────────────────────

describe('upload constants', () => {
  it('functions are exported from contracts/book', async () => {
    const mod = await import('@/shared/api/contracts/book');
    expect(typeof mod.listDocuments).toBe('function');
    expect(typeof mod.uploadDocument).toBe('function');
  });
});

// ── listDocuments ────────────────────────────────────────────────────────

describe('GET /book/os/documents', () => {
  it('direct → Document[] (id, title, type, version, imported_at, hash)', async () => {
    const now = new Date().toISOString();
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: 'doc-1',
            title: 'test.txt',
            type: 'primary_source',
            version: '1.0.0',
            imported_at: now,
            hash: 'a'.repeat(64),
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const docs = await listDocuments();
    expect(docs).toHaveLength(1);
    expect(docs[0].id).toBe('doc-1');
    expect(docs[0].type).toBe('primary_source');
    expect(typeof docs[0].imported_at).toBe('string');
  });

  it('передаёт doc_type в query string', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    await listDocuments('external');
    const calledWith = fetchMock.mock.calls[0];
    expect(calledWith[0]).toContain('doc_type=external');
  });
});

// ── uploadDocument ───────────────────────────────────────────────────────

describe('POST /book/os/pipeline/ingest', () => {
  const mockResult: IngestResult = {
    status: 'ok',
    document_id: 'doc-abc',
    title: 'sample.pdf',
    hash: 'b'.repeat(64),
    chunks_count: 12,
    entities_added: 5,
    facts_added: 8,
    relationships_added: 3,
    chunks_indexed: 12,
  };

  it('отправляет multipart с полем file', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(mockResult), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
    await uploadDocument(file, 'secondary_source', '2.1.0');
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toMatch(/\/book\/os\/pipeline\/ingest/);
    expect(call[0]).toContain('doc_type=secondary_source');
    expect(call[0]).toContain('version=2.1.0');
    expect(call[1]?.method).toBe('POST');
    expect(call[1]?.credentials).toBe('same-origin');
    // Проверяем, что body — FormData
    const body = call[1]?.body as unknown;
    expect(body instanceof FormData).toBe(true);
    const fd = body as FormData;
    expect(fd.get('file')).toBe(file);
  });

  it('возвращает IngestResult при статусе ok', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(mockResult), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    const r = await uploadDocument(new File(['x'], 'f.txt'));
    expect(r.status).toBe('ok');
    expect(r.chunks_count).toBe(12);
    expect(r.entities_added).toBe(5);
  });

  it('кидает ошибку при HTTP 4xx/5xx', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'File too large' }), { status: 400, headers: { 'Content-Type': 'application/json' } }),
    );
    await expect(uploadDocument(new File(['x'], 'big.pdf'))).rejects.toThrow('File too large');
  });

  it('извлекает текст ошибки из массива detail (pydantic format)', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ detail: [{ loc: ['file'], msg: 'Unsupported media type', type: 'value_error' }] }),
        { status: 415, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    await expect(uploadDocument(new File(['x'], 'f.pdf'))).rejects.toThrow('Unsupported media type');
  });
});

// ── ENVELOPE_MAP ─────────────────────────────────────────────────────────

describe('ENVELOPE_MAP entries', () => {
  it('GET /book/os/documents → direct (raw array, not enveloped)', () => {
    expect(ENVELOPE_MAP['GET /book/os/documents']).toBe('direct');
  });
  it('POST /book/os/pipeline/ingest → direct (raw dict, not enveloped)', () => {
    expect(ENVELOPE_MAP['POST /book/os/pipeline/ingest']).toBe('direct');
  });
});

// ── Типы ─────────────────────────────────────────────────────────────────

describe('Type shape', () => {
  it('Document: мокаемый ответ проходит валидацию полей', () => {
    const doc = { id: 'd1', title: 't.txt', type: 'primary_source' as const, version: '1.0', imported_at: '2026-01-01', hash: 'h' } as Document;
    expect(typeof doc.id).toBe('string');
    expect(typeof doc.title).toBe('string');
    expect(['primary_source', 'secondary_source', 'external'].includes(doc.type)).toBe(true);
  });

  it('IngestResult: мокаемый ответ содержит status', () => {
    const r = { status: 'ok' as const } as IngestResult;
    expect(['ok', 'error'].includes(r.status)).toBe(true);
  });
});
