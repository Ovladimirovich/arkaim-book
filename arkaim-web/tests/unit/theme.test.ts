import { describe, it, expect } from 'vitest';
import { getTheme } from '@/shared/lib/theme';

describe('Theme', () => {
  it('returns light theme by default', () => {
    const theme = getTheme(false);
    expect(theme.algorithm).toBeDefined();
  });

  it('returns dark theme when dark', () => {
    const theme = getTheme(true);
    expect(theme.algorithm).toBeDefined();
  });
});
