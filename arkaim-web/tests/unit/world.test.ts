import { describe, expect, it, vi } from 'vitest';
import { getWorldEntity, getWorldEntityContext } from '@/shared/api/contracts/world';

vi.mock('@/shared/api/client', () => ({
  apiCall: vi.fn(),
}));

describe('World provenance API contract', () => {
  it('uses the entity endpoint with an encoded id', async () => {
    const { apiCall } = await import('@/shared/api/client');
    vi.mocked(apiCall).mockResolvedValue({ id: 'region/arkaim' });
    await getWorldEntity('region/arkaim');
    expect(apiCall).toHaveBeenCalledWith('GET', '/book/world/entity/region%2Farkaim');
  });

  it('uses the entity context endpoint without adding a second provenance request', async () => {
    const { apiCall } = await import('@/shared/api/client');
    vi.mocked(apiCall).mockResolvedValue({ entity: { id: 'region_arkaim' }, relations: {} });
    await getWorldEntityContext('region_arkaim');
    expect(apiCall).toHaveBeenCalledWith('GET', '/book/world/entity/region_arkaim/context');
  });
});