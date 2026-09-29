import { describe, it, expect } from 'vitest';
import type { User, UserRole, Genome, ReaderProfile } from '@/shared/types';

describe('Types', () => {
  it('User type has required fields', () => {
    const user: User = {
      id: '1',
      role: 'reader',
      provider: 'telegram',
      is_active: true,
    };
    expect(user.id).toBe('1');
    expect(user.role).toBe('reader');
  });

  it('UserRole includes all roles', () => {
    const roles: UserRole[] = ['reader', 'editor', 'admin'];
    expect(roles).toHaveLength(3);
  });
});
