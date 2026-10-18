'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  LAlert,
  LButton,
  LCard,
  LDivider,
  LEmpty,
  LInput,
  LInputNumber,
  LSpace,
  LTag,
  LTabs,
  LTextArea,
  toast,
} from '@/shared/ui/light';
import { UploadOutlined } from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import { unwrapData } from './types';
import type { MediaPlanT, ReferenceT, ScenarioT, StudioSessionT, StudioVersionT } from './types';

type Draft = {
  synopsis: string;
  imagePrompt: string;
  cameraMotion: string;
  duration: number;
  fps: number;
};

type Props = {
  session: StudioSessionT;
  versions: StudioVersionT[];
  activeVersion: StudioVersionT | null;
  references?: ReferenceT[];
};

function draftFrom(activeVersion: StudioVersionT | null): Draft {
  const scenario: ScenarioT = activeVersion?.video_scenario || {};
  const image: MediaPlanT = activeVersion?.image_description || {};
  const video: MediaPlanT = activeVersion?.video_description || {};
  return {
    synopsis: scenario.synopsis || '',
    imagePrompt: image.prompt || '',
    cameraMotion: video.motion?.camera_motion || 'static',
    duration: video.duration_sec ?? 8,
    fps: video.fps ?? 24,
  };
}

export function PromptsPanel({ session, versions, activeVersion, references = [] }: Props) {
  const queryClient = useQueryClient();
  const finalized = session.status === 'approved' || session.status === 'rejected' || session.status === 'sent';

  const original = useMemo(() => draftFrom(activeVersion), [activeVersion]);
  const [draft, setDraft] = useState<Draft>(original);

  useEffect(() => {
    setDraft(draftFrom(activeVersion));
  }, [activeVersion?.version_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['studio-session', session.session_id] });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const uploadReference = async (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('description', file.name);
    setUploading(true);
    try {
      await api.post(`/api/studio/${session.session_id}/upload-reference`, fd);
      toast.success(`Референс «${file.name}» загружен`);
      invalidate();
    } catch (err) {
      toast.error(`Не удалось загрузить референс: ${(err as Error).message}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const modify = useMutation({
    mutationFn: (p: { target: string; field_path: string; new_value: string }) =>
      api.post(
        `/api/studio/${session.session_id}/modify?target=${encodeURIComponent(p.target)}` +
          `&field_path=${encodeURIComponent(p.field_path)}&new_value=${encodeURIComponent(p.new_value)}`,
      ).then(unwrapData),
    onSuccess: () => {
      toast.success('Промпт сохранён — создана новая версия');
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось сохранить: ${err.message}`),
  });

  const activate = useMutation({
    mutationFn: (versionId: string) =>
      api.post(
        `/api/studio/${session.session_id}/activate-version?version_id=${encodeURIComponent(versionId)}`,
      ).then(unwrapData),
    onSuccess: () => {
      toast.success('Версия активирована');
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось активировать: ${err.message}`),
  });

  const saveButton = (target: string, fieldPath: string, value: string, originalValue: string) => (
    <LButton
      type="primary"
      size="small"
      disabled={finalized || modify.isPending || value === originalValue}
      loading={modify.isPending}
      onClick={() => modify.mutate({ target, field_path: fieldPath, new_value: value })}
    >
      Сохранить промпт
    </LButton>
  );

  const negative = activeVersion?.image_description?.negative_constraints || [];
  const shots = activeVersion?.video_scenario?.shots || [];

  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      <div style={{ flex: '1 1 480px', minWidth: 320 }}>
        <LTabs
          items={[
            {
              key: 'scenario',
              label: 'Контент сцены',
              children: (
                <div>
                  <LAlert
                    type="info"
                    showIcon
                    style={{ marginBottom: 10 }}
                    message="Содержание сцены — по книге (описательная система Arkaim)"
                    description="Это раздельное поле: правка синопсиса/шотов создаёт новую версию сценария и НЕ подменяет утверждённые изображения и уже созданные видео — они остаются утверждёнными, пока вы явно не смените кадр или не перегенерируете их."
                  />
                  <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
                    Синопсис сцены — о чём происходит действие (video_scenario.synopsis)
                  </div>
                  <LTextArea
                    value={draft.synopsis}
                    rows={7}
                    disabled={finalized}
                    onChange={(e) => setDraft((d) => ({ ...d, synopsis: e.target.value }))}
                  />
                  <div style={{ marginTop: 8 }}>
                    {saveButton('video_scenario', 'synopsis', draft.synopsis, original.synopsis)}
                  </div>
                  {shots.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <LTag color="blue">шоты сцены</LTag>
                      <div style={{ marginTop: 6, fontSize: 12, color: 'var(--foreground)' }}>
                        {shots.slice(0, 5).map((s, i) => (
                          <div key={s.shot_id || i} style={{ marginBottom: 4 }}>
                            <strong>{s.shot_id || `#${i + 1}`}</strong>
                            {s.duration_sec ? <span> · {s.duration_sec} с</span> : null}
                            {s.camera_action ? <span> · {s.camera_action}</span> : null}
                            <div style={{ color: '#999' }}>{s.description}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {activeVersion?.video_scenario?.direction_notes && (
                    <div style={{ marginTop: 12, fontSize: 12 }}>
                      <div style={{ color: '#999', marginBottom: 4 }}>
                        Режиссёрские указания (direction_notes):
                      </div>
                      <div style={{ color: 'var(--foreground)' }}>
                        {activeVersion.video_scenario.direction_notes}
                      </div>
                    </div>
                  )}
                  {(activeVersion?.video_scenario?.provenance || []).length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
                        Связь с источниками данных (provenance сценария):
                      </div>
                      <LSpace wrap>
                        {(activeVersion?.video_scenario?.provenance || []).map((p, i) => (
                          <LTag key={`${p.source}-${i}`} style={{ fontSize: 10 }}>
                            {p.source || '—'}
                            {p.confidence !== undefined ? ` · ${p.confidence}` : ''}
                          </LTag>
                        ))}
                      </LSpace>
                    </div>
                  )}
                </div>
              ),
            },
            {
              key: 'image',
              label: 'Промпт изображения',
              children: (
                <div>
                  <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
                    Что должно быть на кадре (image_description.prompt) — из этого промпта
                    генерируются изображения-варианты
                  </div>
                  <LTextArea
                    value={draft.imagePrompt}
                    rows={7}
                    disabled={finalized}
                    onChange={(e) => setDraft((d) => ({ ...d, imagePrompt: e.target.value }))}
                  />
                  <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    {saveButton('image_description', 'prompt', draft.imagePrompt, original.imagePrompt)}
                    {activeVersion?.image_description?.plan_id && (
                      <LTag color="blue">план: {activeVersion.image_description.plan_id}</LTag>
                    )}
                  </div>
                  {negative.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      <div style={{ fontSize: 12, color: '#999' }}>
                        Ограничения (negative, только чтение):
                      </div>
                      <LSpace wrap style={{ marginTop: 4 }}>
                        {negative.map((n) => (
                          <LTag key={n} style={{ fontSize: 10 }}>{n}</LTag>
                        ))}
                      </LSpace>
                      <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                        Исполнитель agnes не поддерживает negative-ограничения.
                      </div>
                    </div>
                  )}
                </div>
              ),
            },
            {
              key: 'motion',
              label: 'Движение',
              children: (
                <div>
                  <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
                    Инструкции движения для видео (video_description.motion) — как движется камера
                  </div>
                  <LInput
                    value={draft.cameraMotion}
                    disabled={finalized}
                    placeholder="например: slow_push_in"
                    onChange={(e) => setDraft((d) => ({ ...d, cameraMotion: e.target.value }))}
                  />
                  <div style={{ marginTop: 8 }}>
                    {saveButton(
                      'video_description',
                      'motion.camera_motion',
                      draft.cameraMotion,
                      original.cameraMotion,
                    )}
                  </div>

                  <LDivider style={{ margin: '14px 0 10px' }} />

                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>Длительность, c</div>
                      <LInputNumber
                        value={draft.duration}
                        min={1}
                        max={60}
                        disabled={finalized}
                        onChange={(v) => setDraft((d) => ({ ...d, duration: v ?? 1 }))}
                      />
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>FPS</div>
                      <LInputNumber
                        value={draft.fps}
                        min={1}
                        max={60}
                        disabled={finalized}
                        onChange={(v) => setDraft((d) => ({ ...d, fps: v ?? 24 }))}
                      />
                    </div>
                    <LButton
                      size="small"
                      disabled={finalized || modify.isPending || draft.duration === original.duration}
                      loading={modify.isPending}
                      onClick={() =>
                        modify.mutate({
                          target: 'video_description',
                          field_path: 'duration_sec',
                          new_value: String(draft.duration),
                        })
                      }
                    >
                      Сохранить длительность
                    </LButton>
                    <LButton
                      size="small"
                      disabled={finalized || modify.isPending || draft.fps === original.fps}
                      loading={modify.isPending}
                      onClick={() =>
                        modify.mutate({
                          target: 'video_description',
                          field_path: 'fps',
                          new_value: String(draft.fps),
                        })
                      }
                    >
                      Сохранить FPS
                    </LButton>
                  </div>
                </div>
              ),
            },
            {
              key: 'references',
              label: `Референсы (${references.length})`,
              children: (
                <div>
                  <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
                    Референсные изображения (наглядный ввод автора: свет, композиция, стиль) —
                    отдельное поле, не часть промптов и не результат генерации.
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    data-testid="reference-file-input"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) void uploadReference(file);
                    }}
                  />
                  <LButton
                    icon={<UploadOutlined />}
                    disabled={finalized || uploading}
                    loading={uploading}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Загрузить референс
                  </LButton>
                  {references.length === 0 ? (
                    <LEmpty
                      style={{ marginTop: 12 }}
                      description="Референсов пока нет — загрузите изображение-образец."
                    />
                  ) : (
                    <div
                      style={{
                        marginTop: 12,
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                        gap: 12,
                      }}
                    >
                      {references.map((r) => (
                        <LCard key={r.asset_id} size="small">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={`/book/assets/${r.asset_id}/file`}
                            alt={r.description || r.asset_id}
                            style={{
                              width: '100%',
                              height: 110,
                              objectFit: 'cover',
                              borderRadius: 6,
                              background: '#111',
                            }}
                          />
                          <div style={{ fontSize: 11, marginTop: 6, color: 'var(--foreground)' }}>
                            {r.description || 'без описания'}
                          </div>
                          <LTag style={{ fontSize: 10 }}>{r.asset_id}</LTag>
                        </LCard>
                      ))}
                    </div>
                  )}
                </div>
              ),
            },
          ]}
        />
        {finalized && (
          <LAlert
            type="info"
            showIcon
            style={{ marginTop: 10 }}
            message="Сессия финализирована — редактирование промптов закрыто"
          />
        )}
      </div>

      <div style={{ flex: '0 1 280px', minWidth: 240 }}>
        <LCard
          title={`Версии (${versions.length})`}
          size="small"
          extra={
            <LTag color={activeVersion ? 'blue' : 'default'} style={{ fontSize: 10 }}>
              активная: {activeVersion ? `v${activeVersion.version_number}` : '—'}
            </LTag>
          }
        >
          <div style={{ maxHeight: 340, overflowY: 'auto' }}>
            {[...versions].reverse().map((v) => (
              <div
                key={v.version_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 0',
                  borderBottom: '1px solid var(--card-border)',
                }}
              >
                <strong style={{ fontSize: 12 }}>v{v.version_number}</strong>
                <LTag style={{ fontSize: 10 }}>{v.derivation}</LTag>
                {v.version_id === session.active_version_id && (
                  <LTag color="blue" style={{ fontSize: 10 }}>активная</LTag>
                )}
                <span
                  style={{ fontSize: 11, color: '#999', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  title={v.note}
                >
                  {v.note}
                </span>
                {v.version_id !== session.active_version_id && (
                  <LButton
                    type="link"
                    size="small"
                    disabled={finalized || activate.isPending}
                    loading={activate.isPending}
                    onClick={() => activate.mutate(v.version_id)}
                  >
                    Включить
                  </LButton>
                )}
              </div>
            ))}
          </div>
        </LCard>
      </div>
    </div>
  );
}
