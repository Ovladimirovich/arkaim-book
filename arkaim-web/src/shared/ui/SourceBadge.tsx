'use client';

import { Tag, Tooltip } from 'antd';
import {
  DatabaseOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  AlertOutlined,
} from '@ant-design/icons';

/**
 * B3 (FRONTEND_RESTORE_BACKLOG): бейдж источника ответа читает РЕАЛЬНЫЕ поля
 * контракта AskAnswer (shared/api/contracts/book.ts):
 *   - source            — префиксы backend: 'knowledge:rag', 'knowledge:theme', 'pulse',
 *                         иные значения backend (прочее — «Голос книги»), 'mock';
 *   - pulse_confidence  — уверенность Pulse, число 0..1;
 *   - llm_used          — был ли включён LLM-синтез.
 *
 * Поля заполняются JSON-путём POST /book/ask. SSE-поток /v1/stream отдаёт ТОЛЬКО
 * text и related_entities (runtime/core/orchestrator.py), поэтому при отсутствии
 * source бейдж не рендерится: источник не выдумывается (принцип проекта).
 */

export type SourceBadgeProps = {
  /** Сырое поле AskAnswer.source из backend. */
  source?: string;
  /** AskAnswer.pulse_confidence (0..1). */
  confidence?: number;
  /** AskAnswer.llm_used. */
  llmUsed?: boolean;
};

type SourceMeta = { icon: React.ReactNode; color: string; label: string };

/** Фактические значения source из backend (keeper.act). */
function metaOf(source: string): SourceMeta {
  if (source === 'mock') {
    return { icon: <AlertOutlined />, color: '#6b7280', label: 'Заглушка' };
  }
  if (source === 'pulse' || source.startsWith('pulse')) {
    return { icon: <DatabaseOutlined />, color: '#059669', label: 'Геном' };
  }
  if (source.startsWith('knowledge:rag')) {
    return { icon: <DatabaseOutlined />, color: '#2563eb', label: 'База знаний' };
  }
  if (source.startsWith('knowledge:theme')) {
    return { icon: <BulbOutlined />, color: '#7c3aed', label: 'Тема книги' };
  }
  // Иное (включая пустое имя источника, которое backend всё равно прислал) — голос книги.
  return { icon: <ThunderboltOutlined />, color: '#7c3aed', label: 'Голос книги' };
}

/** Доверяем только числу 0..1; иное не показываем, чтобы не выдумывать проценты. */
function confidencePercent(confidence?: number): number | undefined {
  return typeof confidence === 'number' && Number.isFinite(confidence) && confidence >= 0 && confidence <= 1
    ? Math.round(confidence * 100)
    : undefined;
}

export function SourceBadge({ source, confidence, llmUsed }: SourceBadgeProps) {
  if (!source) return null;

  const meta = metaOf(source);
  const percent = confidencePercent(confidence);

  const tooltipLines = [`Источник: ${source}`];
  if (percent !== undefined) tooltipLines.push(`Уверенность Pulse: ${percent}%`);
  if (llmUsed) tooltipLines.push('LLM-синтез: включён');

  return (
    <Tooltip title={tooltipLines.join('\n')}>
      <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
        <Tag style={{ marginTop: 4, fontSize: 10, color: meta.color, borderColor: meta.color }}>
          {meta.icon} {meta.label}
          {percent !== undefined ? ` · ${percent}%` : ''}
        </Tag>
        {llmUsed && (
          <Tag style={{ marginTop: 4, fontSize: 10, color: '#7c3aed', borderColor: '#7c3aed' }}>
            <ThunderboltOutlined /> AI-синтез
          </Tag>
        )}
      </span>
    </Tooltip>
  );
}