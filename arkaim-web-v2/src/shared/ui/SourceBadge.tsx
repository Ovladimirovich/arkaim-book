/**
 * SourceBadge — бейдж источника ответа книги (F2_SPEC §4, экран «Спросить книгу»).
 *
 * Контракт /book/ask (live-факт F2-шаг 0):
 *   source: "knowledge:rag:catalog" | "knowledge:theme" | …
 *   pulse_confidence: 0..1, llm_used: bool
 *
 * Источники (по префиксу):
 *   knowledge:rag:*  → «База знаний» (RAG-поиск по каталогу)
 *   knowledge:theme  → «Тема» (тематический слой)
 *   pulse            → «Pulse» (живое ядро)
 *   прочее           → «Голос» (LLM-синтез)
 * Legacy SourceBadge (arkaim-web) — только UX-паттерн; код новый.
 */
'use client';

import { Tag, Tooltip } from 'antd';

export interface SourceBadgeProps {
  source: string;
  confidence?: number;
  llmUsed?: boolean;
}

const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  rag: { label: 'База знаний', color: 'geekblue' },
  theme: { label: 'Тема', color: 'purple' },
  pulse: { label: 'Pulse', color: 'gold' },
};

function classify(source: string): { label: string; color: string } {
  // «knowledge:rag:catalog» → rag; «knowledge:theme» → theme
  const parts = source.split(':');
  const kind = parts[0] === 'pulse' ? 'pulse' : parts[1];
  return SOURCE_LABELS[kind] ?? { label: 'Голос', color: 'green' };
}

export function SourceBadge({ source, confidence, llmUsed }: SourceBadgeProps) {
  const { label, color } = classify(source);
  const conf = typeof confidence === 'number' ? `${Math.round(confidence * 100)}%` : null;
  return (
    <Tooltip
      title={`Источник: ${source}${llmUsed === true ? ' · формулировка LLM (ядро Pulse проверило)' : ''}`}
    >
      <Tag color={color} style={{ marginInlineEnd: 8 }}>
        {label}
        {conf ? ` · ${conf}` : ''}
        {llmUsed ? ' · LLM' : ''}
      </Tag>
    </Tooltip>
  );
}
