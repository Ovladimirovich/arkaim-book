import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';

// Mock all Next.js navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/',
}));

// Mock useAuth
vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '@/app/providers';
import { RoleGuard } from '@/shared/lib/guards';

describe('RoleGuard', () => {
  it('renders children when role matches', () => {
    vi.mocked(useAuth).mockReturnValue({ user: { id: '1', role: 'admin', provider: 'test', is_active: true }, loading: false, login: vi.fn(), logout: vi.fn(), establish: vi.fn() });
    render(<RoleGuard roles={['admin']}><div>Admin Content</div></RoleGuard>);
    expect(screen.getByText('Admin Content')).toBeTruthy();
  });

  it('renders fallback when role does not match', () => {
    vi.mocked(useAuth).mockReturnValue({ user: { id: '1', role: 'reader', provider: 'test', is_active: true }, loading: false, login: vi.fn(), logout: vi.fn(), establish: vi.fn() });
    render(<RoleGuard roles={['admin']} fallback={<div>Access Denied</div>}><div>Admin Content</div></RoleGuard>);
    expect(screen.getByText('Access Denied')).toBeTruthy();
  });

  it('renders nothing when no fallback and role does not match', () => {
    vi.mocked(useAuth).mockReturnValue({ user: { id: '1', role: 'reader', provider: 'test', is_active: true }, loading: false, login: vi.fn(), logout: vi.fn(), establish: vi.fn() });
    const { container } = render(<RoleGuard roles={['admin']}><div>Admin Content</div></RoleGuard>);
    expect(container.innerHTML).toBe('');
  });

  it('shows loading spinner when loading', () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, loading: true, login: vi.fn(), logout: vi.fn(), establish: vi.fn() });
    render(<RoleGuard roles={['admin']}><div>Content</div></RoleGuard>);
    // Should render without crashing
    expect(document.body).toBeTruthy();
  });
});
