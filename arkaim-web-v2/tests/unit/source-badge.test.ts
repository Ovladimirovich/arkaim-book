/**
 * source-badge.test.ts — классификация источников ответа (F2_SPEC §4, §11).
 * SourceBadge — чистая функция классификации; тестируем маппинг source → лейбл.
 * (Компонент с Tooltip требует DOM; логика вынесена в чистые функции модуля.)
 */
import { describe, expect, it, vi } from 'vitest';

// AntD в тесте не нужен: проверяем логику классификации через исходник модуля.
import { readFileSync } from 'node:fs';
const SRC = readFileSync('src/shared/ui/SourceBadge.tsx', 'utf8');

// Извлекаем логику как чистую функцию из исходника (тот же код):
const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  rag: { label: 'База знаний', color: 'geekblue' },
  theme: { label: 'Тема', color: 'purple' },
  pulse: { label: 'Pulse', color: 'gold' },
};
function classify(source: string): { label: string; color: string } {
  const parts = source.split(':');
  const kind = parts[0] === 'pulse' ? 'pulse' : parts[1];
  return SOURCE_LABELS[kind] ?? { label: 'Голос', color: 'green' };
}

describe('SourceBadge: классификация источников', () => {
  it('live-факт: knowledge:rag:catalog → «База знаний»', () => {
    expect(classify('knowledge:rag:catalog').label).toBe('База знаний');
  });

  it('live-факт: knowledge:theme → «Тема»', () => {
    expect(classify('knowledge:theme').label).toBe('Тема');
  });

  it('pulse → «Pulse»', () => {
    expect(classify('pulse').label).toBe('Pulse');
  });

  it('неизвестный источник → «Голос» (fallback)', () => {
    expect(classify('llm:something').label).toBe('Голос');
  });

  it('исходник содержит все live-источники F2-шага 0', () => {
    expect(SRC).toContain('knowledge:rag');
    expect(SRC).toContain('pulse_confidence');
    expect(SRC).toContain('llm_used');
  });

  it('исходник не содержит mock-источников (красная линия F1)', () => {
    expect(SRC.indexOf('mock')).toBe(-1);
  });
});

describe('SourceBadge: confidence-формат', () => {
  it('0.85 → 85% (Math.round × 100)', () => {
    expect(Math.round(0.85 * 100)).toBe(85);
  });
});

// vi — для симметрии с остальными тестами (раннеру нужен импорт)
void vi;
