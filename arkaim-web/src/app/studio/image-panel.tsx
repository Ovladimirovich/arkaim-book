'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LAlert,
  LBadge,
  LButton,
  LCard,
  LEmpty,
  LSelect,
  LSpace,
  LSpin,
  LTag,
  toast,
} from '@/shared/ui/light';
import { ReloadOutlined, PlusCircleOutlined } from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import { AssetImage } from './asset-image';
import { AssetLightbox } from './asset-lightbox';
import { imageMatchesPrompt, isImageOutdated } from './staleness';
import { IMAGE_EXECUTORS, STATUS_COLORS, STATUS_LABELS, unwrapData } from './types';
import type { JobAsset, MediaPlanT, Scene, StudioSessionT } from './types';

type Props = {
  scene: Scene;
  session: StudioSessionT;
  imagePlan: MediaPlanT | null;
};

export function ImagePanel({ scene, session, imagePlan }: Props) {
  const queryClient = useQueryClient();
  const [executor, setExecutor] = useState<string>('agnes');
  const [lightboxId, setLightboxId] = useState<string | null>(null);
  const finalized =
    session.status === 'approved' || session.status === 'rejected' || session.status === 'sent';

  const prompt = imagePlan?.prompt || '';
  const planId = imagePlan?.plan_id || '';

  const assetsQuery = useQuery({
    queryKey: ['studio-image-assets', scene.scene_id],
    queryFn: () => {
      const params = new URLSearchParams({ asset_type: 'image', limit: '30', scene_id: scene.scene_id });
      return api.get(`/book/assets?${params.toString()}`);
    },
    refetchInterval: (query) => {
      const list = (unwrapData<JobAsset[]>(query.state.data) || []) as JobAsset[];
      const busy = list.some((a) => a.status === 'pending' || a.status === 'generating');
      return busy ? 3000 : false;
    },
  });

  const assets: JobAsset[] = useMemo(
    () => (unwrapData<JobAsset[]>(assetsQuery.data) || []) as JobAsset[],
    [assetsQuery.data],
  );
  const busy = assets.some((a) => a.status === 'pending' || a.status === 'generating');

  const approvedAsset = session.approved_image_asset_id
    ? assets.find((a) => a.asset_id === session.approved_image_asset_id)
    : undefined;

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['studio-image-assets', scene.scene_id] });
    queryClient.invalidateQueries({ queryKey: ['studio-session', session.session_id] });
  };

  const generate = useMutation({
    mutationFn: () =>
      api
        .post('/api/studio/image-jobs', {
          chapter: scene.chapter,
          scene_id: scene.scene_id,
          prompt,
          plan_id: planId || null,
          preferred_backend: executor,
          size: '1024x1024',
          title: `кадр: ${scene.title || scene.scene_id}`,
        })
        .then(unwrapData<{ asset_id: string; status: string }>),
    onSuccess: (data) => {
      toast.success(`Изображение запущено (${data.asset_id})`);
      invalidateAll();
    },
    onError: (err: Error) => toast.error(`Не удалось запустить генерацию: ${err.message}`),
  });

  const approve = useMutation({
    mutationFn: (assetId: string) =>
      api
        .post(`/api/studio/${session.session_id}/approve-image?asset_id=${encodeURIComponent(assetId)}`)
        .then(unwrapData<{ approved_image_asset_id: string | null }>),
    onSuccess: (data) => {
      toast.success(
        data.approved_image_asset_id
          ? 'Кадр утверждён — видео будет создаваться от него'
          : 'Утверждение снято',
      );
      invalidateAll();
    },
    onError: (err: Error) => toast.error(`Не удалось утвердить: ${err.message}`),
  });

  const canGenerate = !!prompt && !generate.isPending;

  return (
    <div>
      <LCard
        title="Утверждённый кадр"
        size="small"
        style={{ marginBottom: 12 }}
        extra={
          session.approved_image_asset_id ? (
            <LButton
              type="link"
              size="small"
              disabled={finalized || approve.isPending}
              onClick={() => approve.mutate('')}
            >
              Снять утверждение
            </LButton>
          ) : null
        }
      >
        {session.approved_image_asset_id ? (
          approvedAsset ? (
            <div>
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div style={{ width: 260, maxWidth: '100%' }}>
                  <AssetImage
                    asset={approvedAsset}
                    approved
                    height={140}
                    onOpen={() => setLightboxId(approvedAsset.asset_id)}
                  />
                </div>
                <div style={{ fontSize: 12, color: 'var(--foreground)', flex: '1 1 240px' }}>
                  <div>
                    <strong>{approvedAsset.title || approvedAsset.asset_id}</strong>
                  </div>
                  <LSpace wrap style={{ marginTop: 6 }}>
                    <LTag color="success">основа для видео</LTag>
                    {approvedAsset.generation?.provider && <LTag>{approvedAsset.generation.provider}</LTag>}
                    {approvedAsset.generation?.plan_id && (
                      <LTag color="blue">{approvedAsset.generation.plan_id}</LTag>
                    )}
                    {isImageOutdated(approvedAsset, prompt) && (
                      <LTag color="orange">создан по прежнему промпту</LTag>
                    )}
                  </LSpace>
                </div>
              </div>
              {isImageOutdated(approvedAsset, prompt) && (
                <LAlert
                  type="warning"
                  showIcon
                  style={{ marginTop: 10 }}
                  message="Промпт изображения изменился после утверждения кадра"
                  description="Кадр остаётся утверждённым — автоматически ничего не отменяется. Если хотите кадр по новому промпту: сгенерируйте вариант и утвердите его."
                />
              )}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: '#999' }}>
              Кадр утверждён ({session.approved_image_asset_id}), но его нет в списке ассетов этой сцены.
            </div>
          )
        ) : (
          <LEmpty description="Кадр не утверждён — сгенерируйте варианты и утвердите один из них." />
        )}
      </LCard>

      <LCard
        title="Варианты изображения"
        size="small"
        extra={
          <LButton
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => assetsQuery.refetch()}
          />
        }
      >
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <LSelect
            style={{ minWidth: 300 }}
            value={executor}
            onChange={(v) => setExecutor(v as string)}
            options={IMAGE_EXECUTORS}
          />
          <LButton
            type="primary"
            icon={<PlusCircleOutlined />}
            disabled={!canGenerate}
            loading={generate.isPending}
            onClick={() => generate.mutate()}
          >
            Сгенерировать вариант
          </LButton>
          {busy && (
            <span style={{ fontSize: 12, color: '#999' }}>
              <LSpin size="small" /> идёт генерация…
            </span>
          )}
        </div>

        {executor === 'agnes' && (
          <div style={{ fontSize: 12, color: '#b45309', marginTop: 8 }}>
            agnes — бесплатная интеграция Agnes; negative-ограничения промпта не поддерживаются.
          </div>
        )}
        {!prompt && (
          <LAlert
            type="info"
            showIcon
            style={{ marginTop: 10 }}
            message="Промпт изображения пуст — заполните его во вкладке «Промпт изображения»"
          />
        )}
        {finalized && (
          <LAlert
            type="info"
            showIcon
            style={{ marginTop: 10 }}
            message="Сессия финализирована — утверждение кадра недоступно"
          />
        )}

        <div style={{ marginTop: 12 }}>
          {assetsQuery.isLoading ? (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <LSpin />
            </div>
          ) : assets.length === 0 ? (
            <LEmpty description="Вариантов пока нет — запустите первую генерацию." />
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gap: 12,
              }}
            >
              {assets.map((a) => {
                const isApproved = a.asset_id === session.approved_image_asset_id;
                const samePlan = !!planId && a.generation?.plan_id === planId;
                const outdated = isImageOutdated(a, prompt);
                const matchesPrompt = imageMatchesPrompt(a, prompt);
                return (
                  <LCard key={a.asset_id} size="small" hoverable>
                    <AssetImage
                      asset={a}
                      approved={isApproved}
                      height={130}
                      onOpen={() => setLightboxId(a.asset_id)}
                    />
                    <LSpace wrap style={{ marginTop: 6 }}>
                      <LBadge status={STATUS_COLORS[a.status]} />
                      <LTag color={STATUS_COLORS[a.status]} style={{ fontSize: 10 }}>
                        {STATUS_LABELS[a.status]}
                      </LTag>
                      {samePlan && <LTag color="blue" style={{ fontSize: 10 }}>этот план</LTag>}
                      {a.generation?.provider && (
                        <LTag style={{ fontSize: 10 }}>{a.generation.provider}</LTag>
                      )}
                      {outdated && (
                        <LTag color="orange" style={{ fontSize: 10 }} title="Сгенерирован по прежнему промпту — требует обновления">
                          прежний промпт
                        </LTag>
                      )}
                      {matchesPrompt && (
                        <LTag color="green" style={{ fontSize: 10 }} title="Сгенерирован по текущему промпту image_description">
                          по текущему промпту
                        </LTag>
                      )}
                    </LSpace>
                    <div style={{ marginTop: 6 }}>
                      {isApproved ? (
                        <LTag color="success" style={{ fontSize: 11 }}>
                          выбрано для видео
                        </LTag>
                      ) : (
                        <LButton
                          size="small"
                          type={a.status === 'completed' ? 'primary' : 'default'}
                          disabled={a.status !== 'completed' || finalized || approve.isPending}
                          loading={approve.isPending && approve.variables === a.asset_id}
                          onClick={() => approve.mutate(a.asset_id)}
                        >
                          Утвердить кадр
                        </LButton>
                      )}
                    </div>
                  </LCard>
                );
              })}
            </div>
          )}
        </div>
      </LCard>

      <AssetLightbox
        asset={lightboxId ? assets.find((a) => a.asset_id === lightboxId) || null : null}
        open={!!lightboxId && assets.some((a) => a.asset_id === lightboxId)}
        onClose={() => setLightboxId(null)}
        approved={lightboxId === session.approved_image_asset_id}
        currentPrompt={prompt}
        outdated={
          lightboxId
            ? isImageOutdated(
                assets.find((a) => a.asset_id === lightboxId) || { status: 'failed', prompt_used: '' },
                prompt,
              )
            : false
        }
      />
    </div>
  );
}
