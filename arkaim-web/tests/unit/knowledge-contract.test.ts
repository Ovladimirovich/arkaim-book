import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api/client', () => ({
  apiCall: vi.fn(),
}));

describe('getKnowledgeTrace contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('requests the trace endpoint without query params by default', async () => {
    const { apiCall } = await import('@/shared/api/client');
    const { getKnowledgeTrace } = await import('@/shared/api/contracts/knowledge');
    vi.mocked(apiCall).mockResolvedValue({} as never);

    await getKnowledgeTrace('archaeology:синташта');

    expect(apiCall).toHaveBeenCalledTimes(1);
    const [method, url] = vi.mocked(apiCall).mock.calls[0] as [string, string];
    expect(method).toBe('GET');
    expect(url.startsWith('/knowledge/cards/trace/')).toBe(true);
    expect(url).toContain(encodeURIComponent('archaeology:синташта'));
    expect(url).not.toContain('?');
  });

  it('passes offset and limit as query params for a later page', async () => {
    const { apiCall } = await import('@/shared/api/client');
    const { getKnowledgeTrace } = await import('@/shared/api/contracts/knowledge');
    vi.mocked(apiCall).mockResolvedValue({} as never);

    await getKnowledgeTrace('region_arkaim', { offset: 50, limit: 10 });

    const [, url] = vi.mocked(apiCall).mock.calls[0] as [string, string];
    expect(url).toContain('/knowledge/cards/trace/region_arkaim?offset=50&limit=10');
  });

  it('omits absent pagination params instead of sending empty values', async () => {
    const { apiCall } = await import('@/shared/api/client');
    const { getKnowledgeTrace } = await import('@/shared/api/contracts/knowledge');
    vi.mocked(apiCall).mockResolvedValue({} as never);

    await getKnowledgeTrace('region_arkaim', { offset: 0 });

    const [, url] = vi.mocked(apiCall).mock.calls[0] as [string, string];
    expect(url).toContain('?offset=0');
    expect(url).not.toContain('limit');
  });
});
