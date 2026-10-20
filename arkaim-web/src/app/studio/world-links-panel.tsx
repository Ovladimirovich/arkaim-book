'use client';

/**
 * WorldLinksPanel — read-only панель связей выбранной сцены с миром.
 *
 * Источник: GET /studio/scenes/{scene_id}/world-links (точечный эндпоинт
 * Studio, отдаёт уже посчитанный слой связей из read-only каталога сцен).
 *
 * Граница достоверности:
 *  - CONFIRMED — подтверждено владельцем (одобренные реестры);
 *  - DERIVED — производное сопоставление по точному правилу, не канон;
 *  - UNRESOLVED / AMBIGUOUS — данных нет, показана причина.
 * Упоминания локаций (location_mention) показываются отдельным подразделом
 * и никогда не смешиваются с локацией сцены.
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { ClockCircleOutlined, GlobalOutlined } from '@ant-design/icons';
import { LButton, LEmpty, LSpin, LTag } from '@/shared/ui/light';
import { api } from '@/shared/lib/api';
import {
  WORLD_LINK_STATUS_COLORS,
  WORLD_LINK_STATUS_LABELS,
  WORLD_LINK_TYPE_LABELS,
  unwrapData,
} from './types';
import type { Scene, WorldLinkT, WorldLinksReportT } from './types';

type Props = {
  scene: Scene;
};

/** Мок-данные тестов отдают массив — отчёт обязан быть объектом. */
function asReport(data: unknown): WorldLinksReportT | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  if (!Array.isArray((data as WorldLinksReportT).links)) return null;
  return data as WorldLinksReportT;
}

function statusTag(status: string) {
  return (
    <LTag color={WORLD_LINK_STATUS_COLORS[status] || 'default'}>
      {WORLD_LINK_STATUS_LABELS[status] || status}
    </LTag>
  );
}

function provenanceLine(link: WorldLinkT): string | null {
  const prov = link.provenance;
  if (!prov) return null;
  const parts: string[] = [];
  if (prov.category) parts.push(prov.category);
  if (prov.source_level) parts.push(`уровень ${prov.source_level}`);
  if (typeof prov.confidence === 'number') parts.push(`уверенность ${prov.confidence}`);
  return parts.length ? parts.join(' · ') : null;
}

function LinkRow({ link, reason }: { link: WorldLinkT; reason?: string }) {
  const router = useRouter();
  const targetId = link.target_id || '';
  const canOpenWorld =
    !!targetId &&
    ['world_location', 'world_character', 'world_event'].includes(link.target_kind || '');
  const canOpenEpoch = !!targetId && link.target_kind === 'world_epoch';

  const openWorld = () => {
    router.push(`/world-engine?entity_id=${encodeURIComponent(targetId)}`);
  };
  const openEpoch = () => {
    router.push(`/temporal?entity=${encodeURIComponent(targetId)}`);
  };

  return (
    <div
      data-testid="world-link"
      style={{
        padding: '6px 8px',
        borderRadius: 6,
        borderLeft: '3px solid #334155',
        background: 'rgba(148,163,184,0.05)',
        marginBottom: 4,
      }}
    >
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 13, color: '#e2e8f0' }}>
          {link.target_label || link.target_id || '—'}
        </span>
        <LTag style={{ fontSize: 10 }}>{WORLD_LINK_TYPE_LABELS[link.link_type] || link.link_type}</LTag>
        {statusTag(link.status)}
      </div>
      {link.basis && (
        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{link.basis}</div>
      )}
      {reason && (
        <div style={{ fontSize: 12, color: '#fbbf24', marginTop: 2 }}>Причина: {reason}</div>
      )}
      {provenanceLine(link) && (
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
          Происхождение: {provenanceLine(link)}
        </div>
      )}
      {link.source_files && link.source_files.length > 0 && (
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
          Источники: {link.source_files.join(', ')}
        </div>
      )}
      {(canOpenWorld || canOpenEpoch) && (
        <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
          {canOpenWorld && (
            <LButton
              type="link"
              size="small"
              icon={<GlobalOutlined />}
              onClick={openWorld}
              style={{ padding: 0, height: 'auto', fontSize: 12 }}
            >
              Открыть в World →
            </LButton>
          )}
          {canOpenEpoch && (
            <LButton
              type="link"
              size="small"
              icon={<ClockCircleOutlined />}
              onClick={openEpoch}
              style={{ padding: 0, height: 'auto', fontSize: 12 }}
            >
              Временной контекст →
            </LButton>
          )}
        </div>
      )}
    </div>
  );
}

function Group({
  title,
  hint,
  links,
  missing,
}: {
  title: string;
  hint?: string;
  links: WorldLinkT[];
  missing: Record<string, string>;
}) {
  if (links.length === 0) return null;
  return (
    <div style={{ marginBottom: 10 }} data-testid={`world-link-group-${title}`}>
      <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
        {`${title} · ${links.length}${hint ? ` · ${hint}` : ''}`}
      </div>
      {links.map((link, index) => (
        <LinkRow
          key={`${link.link_type}-${link.target_id}-${index}`}
          link={link}
          reason={missing[link.link_type]}
        />
      ))}
    </div>
  );
}

export function WorldLinksPanel({ scene }: Props) {
  const query = useQuery({
    queryKey: ['studio-world-links', scene.scene_id],
    queryFn: () =>
      api
        .get(
          `/api/studio/scenes/${encodeURIComponent(scene.scene_id)}/world-links?chapter=${scene.chapter}`,
        )
        .then(unwrapData<WorldLinksReportT>),
    enabled: !!scene.scene_id,
  });

  const report = useMemo(() => asReport(query.data), [query.data]);

  const groups = useMemo(() => {
    const links = report?.links ?? [];
    const missing = report?.missing ?? {};
    return {
      confirmed: links.filter((link) => link.status === 'CONFIRMED'),
      derived: links.filter((link) => link.status === 'DERIVED' && link.link_type !== 'location_mention'),
      mentions: links.filter((link) => link.status === 'DERIVED' && link.link_type === 'location_mention'),
      unresolved: links.filter(
        (link) => link.status === 'UNRESOLVED' || link.status === 'AMBIGUOUS',
      ),
      missing,
    };
  }, [report]);

  if (query.isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 12 }}>
        <LSpin />
      </div>
    );
  }

  if (query.isError) {
    return (
      <div style={{ fontSize: 12, color: '#f87171' }}>
        Не удалось загрузить связи сцены с миром.
      </div>
    );
  }

  if (!report) {
    return <LEmpty description="Связи сцены с миром недоступны." />;
  }

  const total =
    groups.confirmed.length + groups.derived.length + groups.mentions.length + groups.unresolved.length;

  if (total === 0) {
    return (
      <div>
        <LEmpty description="Для этой сцены подтверждённых связей с миром не найдено." />
        {Object.keys(groups.missing).length > 0 && (
          <div style={{ fontSize: 12, color: '#94a3b8' }}>
            {Object.entries(groups.missing).map(([type, reason]) => (
              <div key={type}>
                {WORLD_LINK_TYPE_LABELS[type] || type}: {reason}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  const summary = report.summary ?? {};

  return (
    <div data-testid="world-links-panel">
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
        <LTag color="success">подтверждено: {summary.confirmed ?? groups.confirmed.length}</LTag>
        <LTag color="processing">производное: {summary.derived ?? groups.derived.length + groups.mentions.length}</LTag>
        <LTag color="warning">нет данных: {summary.unresolved ?? groups.unresolved.length}</LTag>
        {report.provenance?.world_links && (
          <LTag style={{ fontSize: 10 }}>происхождение: {report.provenance.world_links}</LTag>
        )}
      </div>

      <Group
        title="Подтверждённые связи"
        hint="подтверждено владельцем"
        links={groups.confirmed}
        missing={groups.missing}
      />
      <Group
        title="Производные связи"
        hint="точное сопоставление, не канон"
        links={groups.derived}
        missing={groups.missing}
      />
      <Group
        title="Упоминания локаций"
        hint="упоминание в тексте, не место действия"
        links={groups.mentions}
        missing={groups.missing}
      />
      <Group
        title="Нет данных"
        hint="основание не найдено"
        links={groups.unresolved}
        missing={groups.missing}
      />
    </div>
  );
}
