'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlertOutlined,
  AppstoreOutlined,
  FileTextOutlined,
  PictureOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LTag } from '@/shared/ui/light/LTag';
import { LSpace } from '@/shared/ui/light/LSpace';
import { LInput } from '@/shared/ui/light/LInput';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LDivider } from '@/shared/ui/light/LDivider';
import { StateView } from '@/shared/ui/StateView';

type VisualEntry = {
  group: string;
  key: string;
  fields: Record<string, unknown>;
  prompt_preview: string;
};

type VisualCard = {
  filename: string;
  source_path: string;
  category: string;
  description: string;
  is_canon: boolean;
  requires_author_review: boolean;
  intended_use: string;
  entry_count: number;
  entries: VisualEntry[];
};

type VisualCardsResponse = {
  ok: boolean;
  data: {
    total_files: number;
    total_entries: number;
    all_require_author_review: boolean;
    cards: VisualCard[];
  };
};

function errorDescription(error: unknown): string {
  return error instanceof Error
    ? `Сервер ответил ошибкой: ${error.message}.`
    : 'Проверьте связь с сервером и повторите попытку.';
}

function fieldValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((v) => String(v)).join(', ');
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/** «Изображение» карточки — это промпт, из которого оно собирается. */
function PromptPreview({ text }: { text: string }) {
  return (
    <div
      style={{
        marginTop: 8,
        padding: '10px 12px',
        borderRadius: 8,
        border: '1px dashed #cbd5e1',
        background: '#f8fafc',
        color: '#334155',
        fontSize: 12,
        lineHeight: 1.55,
      }}
    >
      <LSpace size={6} style={{ marginBottom: 4 }}>
        <PictureOutlined />
        <span style={{ fontSize: 11, color: '#64748b' }}>промпт для генерации изображения</span>
      </LSpace>
      <div>{text || '—'}</div>
    </div>
  );
}

function EntryCard({ entry }: { entry: VisualEntry }) {
  return (
    <LCard size="small" style={{ marginBottom: 12 }}>
      <LSpace size={8} wrap>
        {entry.group && <LTag color="blue">{entry.group}</LTag>}
        <strong style={{ fontSize: 14 }}>{entry.key}</strong>
      </LSpace>
      <div style={{ marginTop: 8, display: 'grid', gap: 4 }}>
        {Object.entries(entry.fields).map(([name, value]) => (
          <div key={name} style={{ display: 'flex', gap: 8, fontSize: 12 }}>
            <span style={{ color: '#64748b', minWidth: 150, flexShrink: 0 }}>{name}</span>
            <span style={{ color: '#1e293b' }}>{fieldValue(value)}</span>
          </div>
        ))}
      </div>
      <PromptPreview text={entry.prompt_preview} />
    </LCard>
  );
}

function VisualCardsContent() {
  const [query, setQuery] = useState('');

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['visual-knowledge-cards'],
    queryFn: () => api.get<VisualCardsResponse>('/studio/visual-knowledge/cards'),
  });

  const cards = data?.data?.cards ?? [];

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return cards;
    return cards
      .map((card) => {
        const entries = card.entries.filter(
          (entry) =>
            entry.key.toLowerCase().includes(needle) ||
            entry.prompt_preview.toLowerCase().includes(needle) ||
            entry.group.toLowerCase().includes(needle),
        );
        return { ...card, entries, entry_count: entries.length };
      })
      .filter((card) => card.entry_count > 0);
  }, [cards, query]);

  if (isError) {
    return (
      <StateView
        state="error"
        title="Не удалось загрузить визуальные карточки"
        description={errorDescription(error)}
        onRetry={() => void refetch()}
      />
    );
  }

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <LSpin />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <h2>
        <AppstoreOutlined /> Визуальные карточки — обзор для ревизии
      </h2>
      <p style={{ color: '#666' }}>
        Единый просмотр всех {data?.data?.total_files ?? 8} библиотек визуального слоя
        ({data?.data?.total_entries ?? 0} записей). Это художественная модель, а не канон:
        каждая карточка ждёт вашего подтверждения. Готовых изображений в слое нет —
        показаны промпты, из которых изображения собираются отдельно.
      </p>

      <LDivider style={{ margin: '12px 0' }} />

      <LInput
        prefix={<SearchOutlined />}
        placeholder="Поиск по названию записи или тексту промпта..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ maxWidth: 460, marginBottom: 16 }}
      />

      {filtered.length === 0 ? (
        <LEmpty description="Ничего не найдено" />
      ) : (
        filtered.map((card) => (
          <LCard
            key={card.filename}
            title={
              <LSpace size={8} wrap>
                <FileTextOutlined />
                <span>{card.filename}</span>
                <LTag color="orange">{card.category}</LTag>
                <LTag color={card.requires_author_review ? 'red' : 'green'}>
                  {card.requires_author_review ? 'требует подтверждения' : 'подтверждено'}
                </LTag>
                <LTag>{card.entry_count} записей</LTag>
              </LSpace>
            }
            size="small"
            style={{ marginBottom: 16 }}
          >
            <div style={{ fontSize: 13, color: '#334155' }}>{card.description}</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>
              <strong>Назначение:</strong> {card.intended_use}
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, wordBreak: 'break-all' }}>
              {card.source_path}
            </div>
            <LDivider style={{ margin: '12px 0' }} />
            {card.entries.length === 0 ? (
              <LEmpty description="Нет записей по фильтру" />
            ) : (
              card.entries.map((entry) => (
                <EntryCard
                  key={`${entry.group}:${entry.key}`}
                  entry={entry}
                />
              ))
            )}
          </LCard>
        ))
      )}

      {data?.data?.all_require_author_review && (
        <div
          style={{
            marginTop: 8,
            padding: 12,
            borderRadius: 8,
            background: '#fff7ed',
            border: '1px solid #fed7aa',
            color: '#9a3412',
            fontSize: 12,
          }}
        >
          <LSpace size={8}>
            <AlertOutlined />
            <span>
              Все {data.data.total_files} карточек помечены ARTISTIC_MODEL и
              требуют авторского подтверждения. Пока решение не принято, слой не
              используется в медиа-пайплайне как подтверждённое знание.
            </span>
          </LSpace>
        </div>
      )}
    </div>
  );
}

export default function VisualCardsReviewPage() {
  return (
    <ProtectedRoute>
      <VisualCardsContent />
    </ProtectedRoute>
  );
}
