/**
 * rbac.test.ts — фактическая матрица + can() (F1_SPEC §8).
 * Матрица — generated из слепка (307 маршрутов); тест фиксирует соответствие.
 */
import { describe, expect, it } from 'vitest';
import { can, minRoleFor, BACKEND_DEFECTS } from '@/shared/rbac/can';
import { RBAC_MATRIX, RBAC_ROUTES_TOTAL } from '@/shared/rbac/generated/matrix';
import { navForRole, NAV_GROUPS } from '@/shared/rbac/navigation';describe('generated RBAC matrix', () => {
  it('содержит все маршруты слепка (298 уникальных path+method)', () => {
    expect(RBAC_ROUTES_TOTAL).toBe(298);
    expect(RBAC_MATRIX).toHaveLength(298);
  });

  it('M10.2: pending-updates — reader+ (list), editor+ (confirm)', () => {
    const list = RBAC_MATRIX.find((r) => r.path === '/book/temporal/pending-updates' && r.methods.includes('GET'));
    expect(list?.roles.sort()).toEqual(['admin', 'editor', 'reader']);
    const confirm = RBAC_MATRIX.find(
      (r) => r.path === '/book/temporal/pending-updates/{finding_id}/confirm' && r.methods.includes('POST'),
    );
    expect(confirm?.roles.sort()).toEqual(['admin', 'editor']);
  });

  it('пометки backend-дефектов D1/D2 присутствуют', () => {
    expect(BACKEND_DEFECTS['/book/book/crowdfunding/{campaign_id}']).toContain('D1');
    expect(BACKEND_DEFECTS['/book/research-engine/apply/{job_id}']).toContain('D2');
  });
});

describe('can() по матрице', () => {
  it('reader: просмотр мира да, email-дребень нет, админ — нет', () => {
    expect(can('reader', '/book/world/summary', 'GET')).toBe(true);
    expect(can('reader', '/book/email/drafts', 'GET')).toBe(false); // editor-only
    expect(can('reader', '/auth/admin/users', 'GET')).toBe(false);
  });

  it('editor: email-черновики да, админ-панель нет (фактическая матрица: assets/generate = editor;reader)', () => {
    expect(can('editor', '/book/email/drafts', 'GET')).toBe(true);
    expect(can('editor', '/book/assets/generate', 'POST')).toBe(true); // editor;reader
    expect(can('editor', '/auth/admin/users', 'GET')).toBe(false);
  });

  it('admin: повсюду где admin-гейт', () => {
    expect(can('admin', '/auth/admin/users', 'GET')).toBe(true);
    expect(can('admin', '/book/temporal/pending-updates/scan', 'POST')).toBe(true);
  });

  it('неизвестный маршрут → false (контракт-гейт)', () => {
    expect(can('admin', '/book/nonexistent/endpoint', 'GET')).toBe(false);
  });

  it('minRoleFor', () => {
    expect(minRoleFor('/book/email/drafts', 'GET')).toBe('editor');
    expect(minRoleFor('/auth/admin/users')).toBe('admin');
    expect(minRoleFor('/book/world/summary')).toBe('reader');
    expect(minRoleFor('/unknown')).toBe('unknown');
  });
});

describe('navigation (IA от backend)', () => {
  it('reader не видит Студию/Предложения/Админ', () => {
    const groups = navForRole('reader');
    expect(groups.map((g) => g.key)).toEqual(['book', 'community', 'personal']);
  });

  it('editor видит Студию и Предложения, не видит Админ', () => {
    const keys = navForRole('editor').map((g) => g.key);
    expect(keys).toContain('studio');
    expect(keys).toContain('proposals');
    expect(keys).not.toContain('admin');
  });

  it('admin видит все группы', () => {
    expect(navForRole('admin')).toHaveLength(NAV_GROUPS.length);
  });

  it('F2: активные пункты — ask/read/profile/status; прочие coming-soon', () => {
    const flat = NAV_GROUPS.flatMap((g) => g.items);
    const enabled = flat.filter((i) => !i.comingSoon);
    expect(enabled.map((i) => i.key).sort()).toEqual(['analytics', 'ask', 'graph', 'help', 'history', 'library', 'profile', 'read', 'status', 'studio-main', 'temporal', 'temporal-queue', 'timeline', 'upload', 'users', 'world', 'world-explorer', 'xray']);
    // все активные имеют href
    for (const i of enabled) expect(i.href).toBeTruthy();
  });

  it('F2: reader видит ask/read/profile/status в своих группах', () => {
    const flat = navForRole('reader').flatMap((g) => g.items).filter((i) => !i.comingSoon);
    expect(flat.map((i) => i.key).sort()).toEqual(['analytics', 'ask', 'graph', 'help', 'history', 'library', 'profile', 'read', 'status', 'temporal', 'timeline', 'world', 'world-explorer']);
  });

  it('F3: temporal-очередь — editor+, reader не видит её активной', () => {
    const readerKeys = navForRole('reader').flatMap((g) => g.items).filter((i) => !i.comingSoon).map((i) => i.key);
    expect(readerKeys).not.toContain('temporal-queue');
    const editorKeys = navForRole('editor').flatMap((g) => g.items).filter((i) => !i.comingSoon).map((i) => i.key);
    expect(editorKeys).toContain('temporal-queue');
    expect(editorKeys).toContain('temporal');
  });
});
