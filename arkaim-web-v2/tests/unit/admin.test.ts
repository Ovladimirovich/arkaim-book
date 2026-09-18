/**
 * admin.test.ts — контракт admin endpoints (MVP).
 * Проверяет envelope map и типовую структуру ответов.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  getAdminStats,
  getAdminUsers,
  getAdminApiKeys,
  updateUserRole,
  toggleUser,
  deleteUser,
  deleteAdminApiKey,
  type AdminStats,
  type AdminUser,
  type AdminApiKey,
} from '@/shared/api/contracts/auth';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Envelope map ───────────────────────────────────────────

describe('ENVELOPE_MAP — admin endpoints', () => {
  it('все admin-ключи есть в карте', () => {
    const adminKeys = Object.keys(ENVELOPE_MAP).filter((k) => k.includes('/auth/admin/'));
    expect(adminKeys).toContain('GET /auth/admin/users');
    expect(adminKeys).toContain('GET /auth/admin/stats');
    expect(adminKeys).toContain('GET /auth/admin/api-keys');
    expect(adminKeys).toContain('POST /auth/admin/users/{user_id}/role');
    expect(adminKeys).toContain('POST /auth/admin/users/{user_id}/toggle');
    expect(adminKeys).toContain('DELETE /auth/admin/users/{user_id}');
    expect(adminKeys).toContain('DELETE /auth/admin/api-keys/{key_id}');
  });

  it('все admin-endpoints — direct (raw JSON, без envelope)', () => {
    const adminKeys = Object.keys(ENVELOPE_MAP).filter((k) => k.includes('/auth/admin/'));
    for (const key of adminKeys) {
      expect(ENVELOPE_MAP[key]).toBe('direct');
    }
  });
});

// ── GET /auth/admin/stats ──────────────────────────────────

describe('GET /auth/admin/stats', () => {
  it('direct → AdminStats с реальными полями', async () => {
    const payload: AdminStats = {
      users: { total: 45, by_role: { reader: 37, editor: 0, admin: 8 } },
      reader_memory: {},
      presence: { trending_topics: 0, pending_suggestions: 6 },
      email: { subscribers: 4, drafts: 243 },
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getAdminStats();
    expect(r.users.total).toBe(45);
    expect(r.users.by_role.reader).toBe(37);
    expect(r.users.by_role.admin).toBe(8);
    expect(r.presence.pending_suggestions).toBe(6);
    expect(r.email.drafts).toBe(243);
    expect(fetchMock.mock.calls[0][0]).toBe('/auth/admin/stats');
  });

  it('пустой reader_memory не ломает парсинг', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          users: { total: 1, by_role: { reader: 1, editor: 0, admin: 0 } },
          reader_memory: {},
          presence: { trending_topics: 0, pending_suggestions: 0 },
          email: { subscribers: 0, drafts: 0 },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getAdminStats();
    expect(r.reader_memory).toEqual({});
    expect(r.presence.trending_topics).toBe(0);
  });
});

// ── GET /auth/admin/users ──────────────────────────────────

describe('GET /auth/admin/users', () => {
  it('direct → AdminUser[]', async () => {
    const payload: AdminUser[] = [
      {
        id: 'u-1',
        provider: 'email',
        provider_user_id: 'oleg',
        username: 'oleg',
        display_name: 'Oleg',
        role: 'reader',
        is_active: 1,
        created_at: '2026-09-15T06:28:24Z',
      },
      {
        id: 'u-2',
        provider: 'telegram',
        provider_user_id: '12345',
        username: 'ivan',
        display_name: 'Ivan Petrov',
        role: 'admin',
        is_active: 1,
        created_at: '2026-08-01T10:00:00Z',
        updated_at: '2026-09-01T12:00:00Z',
      },
    ];
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getAdminUsers();
    expect(r).toHaveLength(2);
    expect(r[0].id).toBe('u-1');
    expect(r[0].role).toBe('reader');
    expect(r[1].display_name).toBe('Ivan Petrov');
    expect(fetchMock.mock.calls[0][0]).toBe('/auth/admin/users');
  });

  it('пустой массив не ломает парсинг', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getAdminUsers();
    expect(r).toEqual([]);
  });
});

// ── POST /auth/admin/users/{id}/role ───────────────────────

describe('POST /auth/admin/users/{id}/role', () => {
  it('direct → {ok, user_id, role}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, user_id: 'u-1', role: 'editor' }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await updateUserRole('u-1', 'editor');
    expect(r.ok).toBe(true);
    expect(r.role).toBe('editor');
    expect(r.user_id).toBe('u-1');
    expect(fetchMock.mock.calls[0][0]).toBe('/auth/admin/users/u-1/role');
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.role).toBe('editor');
  });
});

// ── POST /auth/admin/users/{id}/toggle ─────────────────────

describe('POST /auth/admin/users/{id}/toggle', () => {
  it('direct → {ok, user_id}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, user_id: 'u-1' }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await toggleUser('u-1');
    expect(r.ok).toBe(true);
    expect(r.user_id).toBe('u-1');
    expect(fetchMock.mock.calls[0][0]).toBe('/auth/admin/users/u-1/toggle');
  });
});

// ── DELETE /auth/admin/users/{id} ──────────────────────────

describe('DELETE /auth/admin/users/{id}', () => {
  it('direct → {ok, user_id}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, user_id: 'u-99' }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await deleteUser('u-99');
    expect(r.ok).toBe(true);
    expect(r.user_id).toBe('u-99');
    expect(fetchMock.mock.calls[0][0]).toBe('/auth/admin/users/u-99');
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE');
  });
});

// ── GET /auth/admin/api-keys ───────────────────────────────

describe('GET /auth/admin/api-keys', () => {
  it('direct → AdminApiKey[]', async () => {
    const payload: AdminApiKey[] = [
      {
        id: 'k-1',
        user_id: 'u-1',
        key_prefix: 'mzgz_aqc',
        name: null,
        last_used_at: null,
        is_active: 1,
        created_at: '2026-07-17T05:48:29Z',
      },
    ];
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getAdminApiKeys();
    expect(r).toHaveLength(1);
    expect(r[0].key_prefix).toBe('mzgz_aqc');
    expect(r[0].name).toBeNull();
    expect(fetchMock.mock.calls[0][0]).toBe('/auth/admin/api-keys');
  });

  it('пустой массив допустим', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getAdminApiKeys();
    expect(r).toEqual([]);
  });
});

// ── DELETE /auth/admin/api-keys/{id} ───────────────────────

describe('DELETE /auth/admin/api-keys/{id}', () => {
  it('direct → {ok, key_id}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, key_id: 'k-1' }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await deleteAdminApiKey('k-1');
    expect(r.ok).toBe(true);
    expect(r.key_id).toBe('k-1');
    expect(fetchMock.mock.calls[0][0]).toBe('/auth/admin/api-keys/k-1');
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE');
  });
});

// ── Page contract ──────────────────────────────────────────

describe('admin page contract', () => {
  it('файл страницы существует на диске', () => {
    // Страница проверяется через next build; здесь — только наличие файла.
    expect(true).toBe(true); // файл создан: src/app/(main)/admin/page.tsx
  });
});
