import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['tests/unit/setup.ts'],
    exclude: ['tests/e2e/**', 'node_modules/**'],
    // Длинные интеграционные сценарии (например, полный цикл Studio
    // «промпт → кадр → видео») под полной параллельностью на загруженной
    // машине укладывались в 20 с не всегда — тест падал по таймауту, хотя
    // логика была верной. Таймаут теста поднят; таймаут асинхронных
    // утилит testing-library задан в tests/unit/setup.ts.
    testTimeout: 60000,
    hookTimeout: 30000,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
});
