'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LAlert,
  LButton,
  LCard,
  LInput,
  LSelect,
  LSpace,
  LSpin,
  LTag,
  LTextArea,
  toast,
} from '@/shared/ui/light';
import { api } from '@/shared/lib/api';
import { assetFileUrl, unwrapData } from './types';
import type {
  AdLibraryT,
  ArtDirectionCharacterT,
  ArtDirectionLocationT,
  ArtDirectionT,
  ArtDirectionApplyT,
  StudioSessionT,
} from './types';

type Props = {
  session: StudioSessionT;
};

type Draft = {
  style_preset: string;
  style_prompt: string;
  paletteStr: string;
  aspect_ratio: string;
  compositionStr: string;
  lightingStr: string;
  negativeStr: string;
  refsStr: string;
  characters: ArtDirectionCharacterT[];
  locations: ArtDirectionLocationT[];
};

function splitComma(s: string): string[] {
  return s
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean);
}

function splitLines(s: string): string[] {
  return s
    .split('\n')
    .map((p) => p.trim())
    .filter(Boolean);
}

function draftFrom(ad: ArtDirectionT): Draft {
  return {
    style_preset: ad.style_preset,
    style_prompt: ad.style_prompt || '',
    paletteStr: (ad.palette || []).join(', '),
    aspect_ratio: ad.aspect_ratio || '',
    compositionStr: (ad.composition_rules || []).join('\n'),
    lightingStr: (ad.lighting_rules || []).join('\n'),
    negativeStr: (ad.negative_rules || []).join('\n'),
    refsStr: (ad.reference_asset_ids || []).join(', '),
    characters: (ad.characters || []).map((c) => ({ ...c })),
    locations: (ad.locations || []).map((l) => ({ ...l })),
  };
}

function Chip({
  active,
  onClick,
  children,
  testId,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  testId?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      style={{
        padding: '4px 10px',
        borderRadius: 999,
        fontSize: 12,
        cursor: 'pointer',
        border: active ? '1px solid var(--color-primary, #1677ff)' : '1px solid var(--card-border)',
        background: active ? 'rgba(22,119,255,0.10)' : 'transparent',
        color: 'var(--foreground)',
      }}
    >
      {children}
    </button>
  );
}

/**
 * Правила фильма (art direction): единый источник film-wide визуальных
 * решений режиссёра — стиль/палитра, персонажи (со ссылками на
 * утверждённые изображения), локации, правила композиции/света/негатива.
 *
 * Сохранение правил НЕ трогает ручные правки шотов и утверждённые
 * артефакты: revision растёт, а «затронутые» результаты только показываются.
 */
export function ArtDirectionPanel({ session }: Props) {
  const queryClient = useQueryClient();

  const adQuery = useQuery({
    queryKey: ['studio-ad'],
    queryFn: () => api.get('/api/studio/art-direction').then(unwrapData<ArtDirectionT>),
    staleTime: 30_000,
  });

  const libQuery = useQuery({
    queryKey: ['studio-ad-lib'],
    queryFn: () => api.get('/api/studio/art-direction/library').then(unwrapData<AdLibraryT>),
    staleTime: 300_000,
  });

  const applyQuery = useQuery({
    queryKey: ['studio-apply', session.session_id],
    queryFn: () =>
      api.get(`/api/studio/${session.session_id}/art-direction/apply`).then(unwrapData<ArtDirectionApplyT>),
    staleTime: 30_000,
  });

  const ad = adQuery.data;
  const lib = libQuery.data;
  const [draft, setDraft] = useState<Draft | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (ad && !dirty) setDraft(draftFrom(ad));
  }, [ad, dirty]);

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
    setDirty(true);
  };

  const toggleCharacter = (key: string) => {
    if (!draft) return;
    const exists = draft.characters.find((c) => c.knowledge_key === key);
    set(
      'characters',
      exists
        ? draft.characters.filter((c) => c.knowledge_key !== key)
        : [...draft.characters, { knowledge_key: key, name: lib?.characters[key]?.name || key }],
    );
  };

  const toggleLocation = (key: string) => {
    if (!draft) return;
    const exists = draft.locations.find((l) => l.knowledge_key === key);
    set(
      'locations',
      exists
        ? draft.locations.filter((l) => l.knowledge_key !== key)
        : [
            ...draft.locations,
            {
              knowledge_key: key,
              name: lib?.locations[key]?.name || key,
              palette: lib?.locations[key]?.palette || [],
            },
          ],
    );
  };

  const updateCharacter = (key: string, patch: Partial<ArtDirectionCharacterT>) => {
    if (!draft) return;
    set(
      'characters',
      draft.characters.map((c) => (c.knowledge_key === key ? { ...c, ...patch } : c)),
    );
  };

  const updateLocation = (key: string, patch: Partial<ArtDirectionLocationT>) => {
    if (!draft) return;
    set('locations', draft.locations.map((l) => (l.knowledge_key === key ? { ...l, ...patch } : l)));
  };

  const save = useMutation({
    mutationFn: (payload: ArtDirectionT) =>
      api.put('/api/studio/art-direction', payload).then(unwrapData<{ art_direction: ArtDirectionT; changed_sections: string[] }>),
    onSuccess: (data) => {
      setDirty(false);
      if (data.changed_sections.length > 0) {
        toast.success(
          `Правила сохранены — ревизия ${data.art_direction.revision} · изменено: ${data.changed_sections.join(', ')}`,
        );
      } else {
        toast.info('Изменений нет — ревизия правил не изменилась');
      }
      queryClient.invalidateQueries({ queryKey: ['studio-ad'] });
      queryClient.invalidateQueries({ queryKey: ['studio-apply'] });
    },
    onError: (err: Error) => toast.error(`Не удалось сохранить правила: ${err.message}`),
  });

  const apply = applyQuery.data;
  const affected = apply?.affected_artifacts || [];

  if (adQuery.isLoading || !draft) {
    return (
      <div style={{ textAlign: 'center', padding: 24 }}>
        <LSpin />
      </div>
    );
  }

  const styleOptions = Object.entries(lib?.styles || {}).map(([key, s]) => ({
    value: key,
    label: `${key}${s.description ? ` — ${s.description}` : ''}`,
  }));

  const dirtyCheck = dirty || !ad;

  return (
    <div>
      <LSpace wrap style={{ marginBottom: 12 }}>
        <span data-testid="ad-revision"><LTag color="blue" style={{ fontSize: 11 }}>
          ревизия: {ad?.revision ?? 0}
        </LTag></span>
        {ad?.updated_at && <LTag style={{ fontSize: 11 }}>обновлено: {ad.updated_at}</LTag>}
        {(ad?.last_change_sections || []).length > 0 && (
          <LTag color="gold" style={{ fontSize: 11 }}>
            последнее изменение: {ad?.last_change_sections?.join(', ')}
          </LTag>
        )}
        {affected.length > 0 && (
          <span data-testid="ad-affected-count"><LTag color="orange" style={{ fontSize: 11 }}>
            затронуто результатов: {affected.length}
          </LTag></span>
        )}
      </LSpace>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 320px', minWidth: 280 }}>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>Стиль фильма (пресет)</div>
          <LSelect
            value={draft.style_preset}
            options={styleOptions}
            disabled={save.isPending}
            onChange={(v) => set('style_preset', String(v))}
            style={{ width: '100%' }}
          />

          <div style={{ fontSize: 12, color: '#999', margin: '10px 0 4px' }}>
            Свободный стиль режиссёра (пусто → пресет)
          </div>
          <LTextArea
            value={draft.style_prompt}
            rows={3}
            disabled={save.isPending}
            placeholder="например: ночная северная сказка, приглушённый свет"
            onChange={(e) => set('style_prompt', e.target.value)}
          />

          <div style={{ fontSize: 12, color: '#999', margin: '10px 0 4px' }}>
            Палитра фильма (через запятую; пусто → палитра локации)
          </div>
          <LInput
            value={draft.paletteStr}
            disabled={save.isPending}
            placeholder="иней, тёмно-синий, янтарь"
            onChange={(e) => set('paletteStr', e.target.value)}
          />

          <div style={{ fontSize: 12, color: '#999', margin: '10px 0 4px' }}>
            Соотношение сторон (пусто → из пресета)
          </div>
          <LInput
            value={draft.aspect_ratio}
            disabled={save.isPending}
            placeholder="16:9"
            onChange={(e) => set('aspect_ratio', e.target.value)}
          />
        </div>

        <div style={{ flex: '1 1 320px', minWidth: 280 }}>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
            Правила композиции (по правилу на строку)
          </div>
          <LTextArea
            value={draft.compositionStr}
            rows={4}
            disabled={save.isPending}
            placeholder={'центр композиции — силуэт героя\nместо для титров снизу'}
            onChange={(e) => set('compositionStr', e.target.value)}
          />

          <div style={{ fontSize: 12, color: '#999', margin: '10px 0 4px' }}>
            Правила света (по правилу на строку)
          </div>
          <LTextArea
            value={draft.lightingStr}
            rows={3}
            disabled={save.isPending}
            placeholder="мягкий боковой свет, длинные тени"
            onChange={(e) => set('lightingStr', e.target.value)}
          />

          <div style={{ fontSize: 12, color: '#999', margin: '10px 0 4px' }}>
            Дополнительный негатив (дополняет пресет)
          </div>
          <LTextArea
            value={draft.negativeStr}
            rows={2}
            disabled={save.isPending}
            placeholder="перенасыщенные цвета"
            onChange={(e) => set('negativeStr', e.target.value)}
          />
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
          Персонажи фильма (ссылки на Visual Knowledge; для отмеченных — id утверждённого
          изображения)
        </div>
        <LSpace wrap style={{ marginBottom: 8 }}>
          {Object.keys(lib?.characters || {}).map((key) => (
            <Chip
              key={key}
              active={!!draft.characters.find((c) => c.knowledge_key === key)}
              onClick={() => toggleCharacter(key)}
              testId={`ad-chip-char-${key}`}
            >
              {lib?.characters[key]?.name || key}
            </Chip>
          ))}
        </LSpace>
        {draft.characters.map((c) => (
          <div
            key={c.knowledge_key}
            style={{ display: 'flex', gap: 8, marginBottom: 6, flexWrap: 'wrap', alignItems: 'center' }}
          >
            <LTag color="geekblue" style={{ fontSize: 11 }}>
              {c.name || c.knowledge_key}
            </LTag>
            <LInput
              value={c.approved_image_asset_id || ''}
              placeholder="id утверждённого изображения"
              disabled={save.isPending}
              onChange={(e) => updateCharacter(c.knowledge_key, { approved_image_asset_id: e.target.value })}
            />
            {c.approved_image_asset_id && (
              <a
                href={assetFileUrl(c.approved_image_asset_id)}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: 11 }}
              >
                открыть образ
              </a>
            )}
            <LInput
              value={c.note || ''}
              placeholder="заметка режиссёра"
              disabled={save.isPending}
              onChange={(e) => updateCharacter(c.knowledge_key, { note: e.target.value })}
            />
          </div>
        ))}
      </div>

      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
          Локации фильма (ссылки на Visual Knowledge; своя палитра перекрывает палитру знаний)
        </div>
        <LSpace wrap style={{ marginBottom: 8 }}>
          {Object.keys(lib?.locations || {}).map((key) => (
            <Chip
              key={key}
              active={!!draft.locations.find((l) => l.knowledge_key === key)}
              onClick={() => toggleLocation(key)}
              testId={`ad-chip-loc-${key}`}
            >
              {lib?.locations[key]?.name || key}
            </Chip>
          ))}
        </LSpace>
        {draft.locations.map((l) => (
          <div
            key={l.knowledge_key}
            style={{ display: 'flex', gap: 8, marginBottom: 6, flexWrap: 'wrap', alignItems: 'center' }}
          >
            <LTag color="purple" style={{ fontSize: 11 }}>
              {l.name || l.knowledge_key}
            </LTag>
            <LInput
              value={(l.palette || []).join(', ')}
              placeholder="палитра (через запятую)"
              disabled={save.isPending}
              onChange={(e) => updateLocation(l.knowledge_key, { palette: splitComma(e.target.value) })}
            />
            <LInput
              value={l.reference_asset_id || ''}
              placeholder="id эталонного кадра"
              disabled={save.isPending}
              onChange={(e) => updateLocation(l.knowledge_key, { reference_asset_id: e.target.value })}
            />
            {l.reference_asset_id && (
              <a href={assetFileUrl(l.reference_asset_id)} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>
                открыть кадр
              </a>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
          Общие референсы фильма (asset_id через запятую)
        </div>
        <LInput
          value={draft.refsStr}
          disabled={save.isPending}
          placeholder="ast_…, ast_…"
          onChange={(e) => set('refsStr', e.target.value)}
        />
      </div>

      <div style={{ marginTop: 16, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <LButton
          type="primary"
          disabled={!dirtyCheck || save.isPending}
          loading={save.isPending}
          onClick={() => {
            if (!ad || !draft) return;
            save.mutate({
              ...ad,
              style_preset: draft.style_preset,
              style_prompt: draft.style_prompt,
              palette: splitComma(draft.paletteStr),
              aspect_ratio: draft.aspect_ratio.trim() || null,
              composition_rules: splitLines(draft.compositionStr),
              lighting_rules: splitLines(draft.lightingStr),
              negative_rules: splitLines(draft.negativeStr),
              reference_asset_ids: splitComma(draft.refsStr),
              characters: draft.characters,
              locations: draft.locations,
            });
          }}
        >
          Сохранить правила фильма
        </LButton>
        {dirty && <LTag color="orange" style={{ fontSize: 11 }}>есть несохранённые изменения</LTag>}
        <span style={{ fontSize: 11, color: '#999' }}>
          Сохранение не затирает правки шотов и утверждённые результаты — они помечаются как
          затронутые.
        </span>
      </div>

      {affected.length > 0 && (
        <LCard size="small" style={{ marginTop: 14 }} title="Затронутые изменениями правил результаты">
          <div data-testid="ad-affected">
            {affected.slice(0, 15).map((a) => (
              <div key={a.asset_id} style={{ marginBottom: 8, fontSize: 12 }}>
                <LSpace wrap>
                  <LTag color={a.asset_type === 'video' ? 'purple' : 'blue'} style={{ fontSize: 11 }}>
                    {a.asset_type === 'video' ? 'видео' : 'изображение'}
                  </LTag>
                  <strong>{a.title || a.asset_id}</strong>
                  <a href={assetFileUrl(a.asset_id)} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>
                    открыть
                  </a>
                </LSpace>
                <div style={{ color: '#999', fontSize: 11 }}>{a.reasons.join('; ')}</div>
              </div>
            ))}
            {affected.length > 15 && (
              <div style={{ fontSize: 11, color: '#999', marginBottom: 8 }}>
                …и ещё {affected.length - 15}: это ранее подготовленные кадры и клипы этой сцены
              </div>
            )}
          </div>
          <LAlert
            type="info"
            showIcon
            message="Ничего не удалено и не пересоздано"
            description="Список — только к сведению: обновите конкретные кадры или клипы, когда решите, что правила стали применяться к ним."
          />
        </LCard>
      )}
    </div>
  );
}
