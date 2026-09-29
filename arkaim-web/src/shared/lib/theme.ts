/**
 * theme.ts — Конфигурация темы Ant Design с поддержкой dark mode.
 */

import { theme } from 'antd';
import type { ThemeConfig } from 'antd';

export const lightTheme: ThemeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#2563eb',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f4f6f8',
    colorText: '#1e293b',
    colorTextSecondary: '#475569',
    colorBorder: '#e2e8f0',
    borderRadius: 8,
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
  },
  components: {
    Layout: {
      headerBg: '#1e293b',
      headerColor: '#ffffff',
    },
    Menu: {
      darkItemBg: '#1e293b',
      darkItemSelectedBg: '#334155',
    },
    Table: {
      headerBg: '#f8fafc',
      rowHoverBg: '#f1f5f9',
    },
  },
};

export const darkTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#3b82f6',
    colorBgContainer: '#1e293b',
    colorBgLayout: '#0f172a',
    colorText: '#e2e8f0',
    colorTextSecondary: '#94a3b8',
    colorBorder: '#334155',
    borderRadius: 8,
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
  },
  components: {
    Layout: {
      headerBg: '#020617',
      headerColor: '#e2e8f0',
    },
    Menu: {
      darkItemBg: '#020617',
      darkItemSelectedBg: '#334155',
    },
    Table: {
      headerBg: '#1e293b',
      rowHoverBg: '#334155',
    },
  },
};

export function getTheme(isDark: boolean): ThemeConfig {
  return isDark ? darkTheme : lightTheme;
}
