'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LAlert,
  LButton,
  LCard,
  LInput,
  LInputNumber,
  LSpace,
  LTag,
  LTextArea,
  toast,
} from '@/shared/ui/light';
import { api } from '@/shared/lib/api';
import { unwrapData } from './types';
import type { ArtDirectionApplyT, ScenarioShotT, StudioSessionT, StudioVersionT } from './types';

type Props = {
  session: StudioSessionT;
  activeVersion: StudioVersionT | null;
};

type ShotDraft = {
  description: string;
  cameraAction: string;
  duration: number;
  styleOverride: string;
  paletteStr: string;
};

function draftFrom(shot: ScenarioShotT | null): ShotDraft {
  return {
    description: shot?.description || '',
    cameraAction: shot?.camera_action || '',
    duration: shot?.duration_sec ?? 3,
    styleOverride: shot?.style_override || '',
    paletteStr: (shot?.palette_override || []).join(', '),
  };
}

/**
 * Планы сцены (шоты): список планов + пошотовое редактирование.
 * Содержание — из video_scenario (описательная система/Pulse); правка шота
 * создаёт новую версию и НЕ затрагивает утверждённые изображения/видео.
 */
export function ShotsPanel({ session, activeVersion }: Props) {
  const queryClient = useQueryClient();
  const finalized =
    session.status === 'approved' || session.status === 'rejected' || session.status === 'sent';

  const shots = useMemo(() => activeVersion?.video_scenario?.shots || [], [activeVersion]);
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    setSelectedIndex(0);
  }, [activeVersion?.version_id]);

  const applyQuery = useQuery({
    queryKey: ['studio-apply', session.session_id],
    queryFn: () =>
      api
        .get(`/api/studio/${session.session_id}/art-direction/apply`)
        .then(unwrapData<ArtDirectionApplyT>),
    staleTime: 30_000,
  });

  const safeIndex = selectedIndex < shots.length ? selectedIndex : 0;
  const shot = shots[safeIndex] || null;
  const appliedShot = useMemo(
    () => applyQuery.data?.shots?.[safeIndex] || null,
    [applyQuery.data, safeIndex],
  );
  const original = useMemo(() => draftFrom(shot), [shot]);
  const [draft, setDraft] = useState<ShotDraft>(original);

  useEffect(() => {
    setDraft(draftFrom(shot));
  }, [shot?.shot_id, safeIndex, activeVersion?.version_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['studio-session', session.session_id] });
    queryClient.invalidateQueries({ queryKey: ['studio-apply', session.session_id] });
  };

  const modify = useMutation({
    mutationFn: (p: { field_path: string; new_value: string }) =>
      api
        .post(
          `/api/studio/${session.session_id}/modify?target=video_scenario` +
            `&field_path=${encodeURIComponent(p.field_path)}&new_value=${encodeURIComponent(p.new_value)}`,
        )
        .then(unwrapData),
    onSuccess: () => {
      toast.success('План сохранён — создана новая версия');
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось сохранить план: ${err.message}`),
  });

  const saveButton = (field: string, value: string, originalValue: string, label: string) => (
    <LButton
      type="primary"
      size="small"
      disabled={finalized || modify.isPending || value === originalValue}
      loading={modify.isPending && modify.variables?.field_path === `shots.${safeIndex}.${field}`}
      onClick={() => modify.mutate({ field_path: `shots.${safeIndex}.${field}`, new_value: value })}
    >
      {label}
    </LButton>
  );

  if (shots.length === 0) {
    return (
      <LAlert
        type="info"
        showIcon
        message="Планы (шоты) сцены пока не сформированы"
        description="Сценарий этой версии не содержит планов — содержание сцены задано синопсисом во вкладке «Контент сцены»."
      />
    );
  }

  const prov = shot?.provenance;
  const characterActions = shot?.character_actions || [];
  const environmentActions = shot?.environment_actions || [];

  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      <div style={{ flex: '0 1 300px', minWidth: 240 }}>
        <LCard
          title={`Планы сцены (${shots.length})`}
          size="small"
          extra={<LTag color="blue">v{activeVersion?.version_number}</LTag>}
        >
          <div style={{ maxHeight: 360, overflowY: 'auto' }}>
            {shots.map((s, i) => (
              <button
                key={s.shot_id || i}
                onClick={() => setSelectedIndex(i)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '8px 10px',
                  marginBottom: 6,
                  borderRadius: 6,
                  border:
                    i === safeIndex
                      ? '1px solid var(--color-primary, #1677ff)'
                      : '1px solid var(--card-border)',
                  background: i === safeIndex ? 'rgba(22,119,255,0.08)' : 'transparent',
                  cursor: 'pointer',
                  color: 'var(--foreground)',
                }}
                data-testid={`shot-item-${i}`}
              >
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: 12 }}>#{(s.order ?? i) + 1}</strong>
                  <LTag style={{ fontSize: 10 }}>{s.shot_type || '—'}</LTag>
                  {(s.style_override || (s.palette_override && s.palette_override.length > 0)) && (
                    <LTag color="orange" style={{ fontSize: 10 }}>
                      локально
                    </LTag>
                  )}
                  {s.duration_sec ? <span style={{ fontSize: 11, color: '#999' }}>{s.duration_sec} с</span> : null}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: '#999',
                    marginTop: 2,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                  }}
                >
                  {s.description || 'без описания'}
                </div>
              </button>
            ))}
          </div>
        </LCard>
      </div>

      <div style={{ flex: '1 1 420px', minWidth: 300 }}>
        <LCard
          title={`План #${(shot?.order ?? safeIndex) + 1} — ${shot?.shot_type || ''}`}
          size="small"
        >
          <div
            data-testid="shot-sequence-strip"
            style={{
              display: 'flex',
              gap: 6,
              overflowX: 'auto',
              paddingBottom: 6,
              marginBottom: 8,
              borderBottom: '1px solid var(--card-border)',
            }}
          >
            {shots.map((s, i) => (
              <button
                key={s.shot_id || i}
                type="button"
                onClick={() => setSelectedIndex(i)}
                data-testid={`strip-shot-${i}`}
                style={{
                  flex: '0 0 auto',
                  padding: '3px 9px',
                  fontSize: 11,
                  borderRadius: 999,
                  cursor: 'pointer',
                  border:
                    i === safeIndex
                      ? '1px solid var(--color-primary, #1677ff)'
                      : '1px solid var(--card-border)',
                  background: i === safeIndex ? 'rgba(22,119,255,0.10)' : 'transparent',
                  color: 'var(--foreground)',
                }}
              >
                #{(s.order ?? i) + 1}
                {s.duration_sec ? ` · ${s.duration_sec}с` : ''}
              </button>
            ))}
          </div>
          <LSpace style={{ marginBottom: 10 }}>
            <LButton
              size="small"
              disabled={safeIndex === 0}
              onClick={() => setSelectedIndex((i) => Math.max(0, i - 1))}
            >
              ← Предыдущий
            </LButton>
            <LButton
              size="small"
              disabled={safeIndex >= shots.length - 1}
              onClick={() => setSelectedIndex((i) => Math.min(shots.length - 1, i + 1))}
            >
              Следующий →
            </LButton>
            <span style={{ fontSize: 11, color: '#999' }}>
              {safeIndex + 1} из {shots.length}
            </span>
          </LSpace>

          <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
            Что происходит в этом плане (video_scenario.shots[{safeIndex}].description)
          </div>
          <LTextArea
            value={draft.description}
            rows={5}
            disabled={finalized}
            onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
          />
          <div style={{ marginTop: 8 }}>
            {saveButton('description', draft.description, original.description, 'Сохранить описание плана')}
          </div>

          <div style={{ display: 'flex', gap: 12, marginTop: 14, flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 220px' }}>
              <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
                Движение камеры (camera_action)
              </div>
              <LInput
                value={draft.cameraAction}
                disabled={finalized}
                placeholder="например: slow dolly in"
                onChange={(e) => setDraft((d) => ({ ...d, cameraAction: e.target.value }))}
              />
              <div style={{ marginTop: 6 }}>
                {saveButton(
                  'camera_action',
                  draft.cameraAction,
                  original.cameraAction,
                  'Сохранить движение камеры',
                )}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>Длительность, с</div>
              <LInputNumber
                value={draft.duration}
                min={0.5}
                max={30}
                step={0.5}
                disabled={finalized}
                onChange={(v) => setDraft((d) => ({ ...d, duration: v ?? 3 }))}
              />
              <div style={{ marginTop: 6 }}>
                {saveButton(
                  'duration_sec',
                  String(draft.duration),
                  String(original.duration),
                  'Сохранить длительность плана',
                )}
              </div>
            </div>
          </div>

          <div
            style={{
              marginTop: 16,
              paddingTop: 12,
              borderTop: '1px dashed var(--card-border)',
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
              Визуальный язык плана (общие правила фильма → применённые)
            </div>

            {applyQuery.isLoading ? (
              <div style={{ fontSize: 11, color: '#999' }}>загрузка правил…</div>
            ) : appliedShot ? (
              <div data-testid="applied-rules" style={{ marginBottom: 10 }}>
                <LSpace wrap>
                  <LTag color="blue" style={{ fontSize: 10 }}>
                    стиль: {appliedShot.applied.style_preset}
                  </LTag>
                  {appliedShot.applied.palette.length > 0 && (
                    <LTag style={{ fontSize: 10 }}>палитра: {appliedShot.applied.palette.join(', ')}</LTag>
                  )}
                  {appliedShot.applied.composition_rules.length > 0 && (
                    <LTag color="geekblue" style={{ fontSize: 10 }}>
                      композиция: {appliedShot.applied.composition_rules.length} прав.
                    </LTag>
                  )}
                  {appliedShot.applied.lighting_rules.length > 0 && (
                    <LTag color="gold" style={{ fontSize: 10 }}>
                      свет: {appliedShot.applied.lighting_rules.join('; ')}
                    </LTag>
                  )}
                  <LTag style={{ fontSize: 10 }}>ревизия правил: {appliedShot.applied.revision}</LTag>
                </LSpace>

                <LSpace wrap style={{ marginTop: 6 }}>
                  <span style={{ fontSize: 11, color: '#999' }}>локально задано:</span>
                  {Object.keys(appliedShot.local_overrides).length === 0 ? (
                    <span style={{ fontSize: 11, color: '#999' }}>нет (план идёт по общим правилам)</span>
                  ) : (
                    Object.entries(appliedShot.local_overrides).map(([k, v]) => (
                      <LTag key={k} color="orange" style={{ fontSize: 10 }}>
                        {k}:{' '}
                        {Array.isArray(v) ? v.join(', ') : String(v)}
                      </LTag>
                    ))
                  )}
                </LSpace>

                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, color: '#999', marginBottom: 3 }}>
                    Итоговый промпт плана (правила + локальные переопределения)
                  </div>
                  <div
                    data-testid="resolved-prompt"
                    style={{
                      fontSize: 11,
                      lineHeight: 1.5,
                      padding: '8px 10px',
                      borderRadius: 6,
                      background: 'rgba(22,119,255,0.06)',
                      border: '1px solid var(--card-border)',
                      wordBreak: 'break-word',
                    }}
                  >
                    {appliedShot.resolved_prompt || '—'}
                  </div>
                </div>
              </div>
            ) : (
              <LAlert
                type="info"
                showIcon
                message="Правила фильма не применены"
                description="Откройте панель «Правила фильма» — там задаются стиль, палитра, персонажи и локации всего фильма."
              />
            )}

            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 220px' }}>
                <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
                  Свой стиль плана (перебивает общий)
                </div>
                <LInput
                  value={draft.styleOverride}
                  disabled={finalized}
                  placeholder="пусто → стиль фильма"
                  onChange={(e) => setDraft((d) => ({ ...d, styleOverride: e.target.value }))}
                />
                <div style={{ marginTop: 6 }}>
                  {saveButton(
                    'style_override',
                    draft.styleOverride,
                    original.styleOverride,
                    'Сохранить стиль плана',
                  )}
                </div>
              </div>
              <div style={{ flex: '1 1 220px' }}>
                <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
                  Своя палитра плана (через запятую)
                </div>
                <LInput
                  value={draft.paletteStr}
                  disabled={finalized}
                  placeholder="пусто → палитра фильма"
                  onChange={(e) => setDraft((d) => ({ ...d, paletteStr: e.target.value }))}
                />
                <div style={{ marginTop: 6 }}>
                  {saveButton(
                    'palette_override',
                    draft.paletteStr,
                    original.paletteStr,
                    'Сохранить палитру плана',
                  )}
                </div>
              </div>
            </div>
          </div>

          <LSpace wrap style={{ marginTop: 14 }}>
            {shot?.camera_angle && <LTag style={{ fontSize: 10 }}>угол: {shot.camera_angle}</LTag>}
            {shot?.transition_to_next && (
              <LTag style={{ fontSize: 10 }}>переход: {shot.transition_to_next}</LTag>
            )}
            {shot?.lighting_note && <LTag style={{ fontSize: 10 }}>свет: {shot.lighting_note}</LTag>}
            {shot?.mood_note && <LTag style={{ fontSize: 10 }}>настроение: {shot.mood_note}</LTag>}
          </LSpace>

          {prov && (prov.source || prov.confidence !== undefined) && (
            <div style={{ marginTop: 10, fontSize: 11, color: '#999' }}>
              источник данных: <strong>{prov.source || '—'}</strong>
              {prov.confidence !== undefined ? ` · уверенность ${prov.confidence}` : ''}
              {prov.source_id ? ` · ${prov.source_id}` : ''}
            </div>
          )}

          {(characterActions.length > 0 || environmentActions.length > 0) && (
            <div style={{ marginTop: 10, fontSize: 12 }}>
              {characterActions.length > 0 && (
                <div style={{ marginBottom: 4 }}>
                  <LTag color="blue" style={{ fontSize: 10 }}>персонажи</LTag>{' '}
                  <span style={{ color: 'var(--foreground)' }}>
                    {characterActions.map((c) => `${c.character_name || c.character_id}: ${c.action}`).join('; ')}
                  </span>
                </div>
              )}
              {environmentActions.length > 0 && (
                <div>
                  <LTag color="geekblue" style={{ fontSize: 10 }}>среда</LTag>{' '}
                  <span style={{ color: 'var(--foreground)' }}>
                    {environmentActions.map((e) => `${e.element}: ${e.action}`).join('; ')}
                  </span>
                </div>
              )}
            </div>
          )}

          <LAlert
            type="info"
            showIcon
            style={{ marginTop: 12 }}
            message="Правка плана не затрагивает утверждённые изображения и видео"
            description="Содержание сцены, промпт изображения и промпт движения — раздельные поля: изменение плана создаёт новую версию сценария, а кадры и клипы остаются утверждёнными как есть (обновляйте их явно, когда решите)."
          />
        </LCard>
      </div>
    </div>
  );
}
