/**
 * Тема для React Native приложения.
 * Цвета совпадают с веб-приложением.
 */

export const colors = {
  primary: '#2563eb',
  primaryDark: '#1d4ed8',
  background: '#f4f6f8',
  surface: '#ffffff',
  text: '#1e293b',
  textSecondary: '#475569',
  textMuted: '#94a3b8',
  border: '#e2e8f0',
  success: '#16a34a',
  danger: '#dc2626',
  warning: '#f59e0b',
  navBg: '#1e293b',
  navText: '#ffffff',
};

export const darkColors = {
  ...colors,
  background: '#0f172a',
  surface: '#1e293b',
  text: '#e2e8f0',
  textSecondary: '#94a3b8',
  textMuted: '#64748b',
  border: '#334155',
  navBg: '#020617',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const borderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
};

export const typography = {
  h1: { fontSize: 24, fontWeight: '700' as const },
  h2: { fontSize: 20, fontWeight: '600' as const },
  h3: { fontSize: 16, fontWeight: '600' as const },
  body: { fontSize: 14 },
  caption: { fontSize: 12, color: '#94a3b8' },
};
