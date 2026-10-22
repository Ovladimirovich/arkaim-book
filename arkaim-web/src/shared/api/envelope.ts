/**
 * envelope.ts — развёртка ответов backend'а (F1_SPEC §6).
 *
 * Backend использует ДВЕ конвенции ответов (FRONTEND_FORENSIC_AUDIT §2.2):
 *   enveloped : {"ok": true, "data": <payload>, "trace_id"?: ...}  (SuccessResponse DTO)
 *   direct    : <raw payload> без конверта (auth, world, temporal-chain и др.)
 *
 * ENVELOPE_MAP — единственная карта правды «какой endpoint как отвечает».
 * Ручная типизация F1: только auth/health (задействованные в F1); остальное
 * добавляется по фазам F2+ по мере подключения экранов.
 */

export type Envelope = 'enveloped' | 'direct';

/**
 * Карта конвертов для F1-контрактов.
 * Формат ключей — путь OpenAPI. PATH-параметры: шаблон {param}.
 */
export const ENVELOPE_MAP: Record<string, Envelope> = {
  // ── auth (direct-return; проверено forensic §2.2) ──
  'GET /auth/me': 'direct',
  'POST /auth/register': 'direct',
  'POST /auth/telegram/login': 'direct',
  'POST /auth/telegram/callback': 'direct',
  'POST /auth/dev/generate-token': 'direct',
  'POST /auth/logout': 'direct',
  'GET /auth/logout': 'direct',
  // ── admin (все raw JSON, не enveloped — проверено live) ──
  'GET /auth/admin/users': 'direct',
  'GET /auth/admin/users/{user_id}': 'direct',
  'POST /auth/admin/users/{user_id}/role': 'direct',
  'POST /auth/admin/users/{user_id}/toggle': 'direct',
  'DELETE /auth/admin/users/{user_id}': 'direct',
  'GET /auth/admin/stats': 'direct',
  'GET /auth/admin/api-keys': 'direct',
  'DELETE /auth/admin/api-keys/{key_id}': 'direct',
  // ── system ──
  'GET /health': 'direct',
  // ── book / reader (F2; live-проверено шагом 0 F2-плана) ──
  'POST /book/ask': 'enveloped',
  'GET /book/chapters': 'enveloped',
  'GET /book/chapters/{chapter_id}': 'enveloped',
  // text: пагинационные поля (offset/limit/total/has_more) живут В КОНВЕРТЕ —
  // контракт (book.ts getText) читает полный конверт, поэтому помечен direct.
  'GET /book/text': 'direct',
  'GET /book/layers': 'direct',
  'GET /book/genome': 'direct',
  'GET /book/reader/profile': 'direct',
  'GET /book/reader/history': 'enveloped',
  // reading-event: конверт {ok:true} БЕЗ data-поля (live-факт) — читаем целиком.
  'POST /book/reader/reading-event': 'direct',
  // reading-progress: stats лежит В КОНВЕРТЕ рядом с data — читаем полный конверт.
  'GET /book/reader/reading-progress': 'direct',
  'GET /book/reader/reading-position': 'enveloped',
  // analytics: reader history stats (enveloped), graph stats (direct), cache stats (enveloped)
  'GET /book/reader/history/stats': 'enveloped',
  'GET /book/graph/stats': 'direct',
  'GET /book/cache/stats': 'enveloped',
  // knowledge (F2; enveloped)
  'GET /book/knowledge/search': 'enveloped',
  'GET /book/knowledge/autocomplete': 'enveloped',
  'GET /knowledge/cards/trace/{entity_id}': 'direct',
  'GET /knowledge/cards/search': 'direct',
  'GET /knowledge/cards/{entity_id}': 'direct',
  // ── temporal (F3; live-проверено шагом 0: все enveloped {ok, data, ...}) ──
  'GET /book/temporal/chain': 'enveloped',
  'GET /book/temporal/chains': 'enveloped',
  'GET /book/temporal/nodes': 'enveloped',
  'GET /book/temporal/context/{epoch_id}': 'enveloped',
  'GET /book/temporal/node/{epoch_id}': 'enveloped',
  'POST /book/temporal/future-extrapolation': 'enveloped',
  'GET /book/temporal/pending-updates': 'enveloped',
  'GET /book/temporal/pending-updates/stats': 'enveloped',
  'GET /book/temporal/pending-updates/history': 'enveloped',
  'GET /book/temporal/pending-updates/{finding_id}': 'enveloped',
  'POST /book/temporal/pending-updates/scan': 'enveloped',
  'POST /book/temporal/pending-updates/{finding_id}/confirm': 'enveloped',
  'POST /book/temporal/pending-updates/{finding_id}/reject': 'enveloped',
  'POST /book/temporal/reconstruct': 'enveloped',
  // ── World Explorer (Исследование мира; live-факт: api_routes.py) ──
  'POST /book/world-explorer/explore': 'enveloped',
  'POST /book/world-explorer/explore/hypothesis': 'enveloped',
  'POST /book/world-explorer/validate': 'enveloped',
  'GET /book/world-explorer/epochs': 'enveloped',
  'GET /book/world-explorer/stats': 'enveloped',
  'GET /book/world-explorer/hypotheses/{epoch_id}': 'enveloped',
  'GET /book/world-explorer/possibilities/{epoch_id}': 'enveloped',
  'GET /book/world-explorer/history': 'enveloped',
  'GET /book/world-explorer/history/{exploration_id}': 'enveloped',
  'GET /book/world-explorer/feedback': 'enveloped',
  'POST /book/world-explorer/generate-from-branch': 'enveloped',
  // history POST / feedback POST / history DELETE возвращают {ok, id} БЕЗ data → direct
  'POST /book/world-explorer/history': 'direct',
  'POST /book/world-explorer/feedback': 'direct',
  'DELETE /book/world-explorer/history/{exploration_id}': 'direct',
  // \u2500\u2500 community (all raw JSON, direct) \u2500\u2500
  'GET /book/community/timeline': 'direct',
  'GET /book/community/interpretations': 'direct',
  'GET /book/community/interpretations/mine': 'direct',
  'GET /book/community/interpretations/stats': 'direct',
  'POST /book/community/interpretations': 'direct',
  'GET /book/community/artifacts': 'direct',
  'GET /book/community/artifacts/mine': 'direct',
  'GET /book/community/artifacts/stats': 'direct',
  'POST /book/community/artifacts': 'direct',
  'GET /book/community/search': 'direct',
  'GET /book/community/notifications': 'direct',
  'GET /book/community/notifications/unread-count': 'direct',
  'GET /book/community/knowledge/status': 'direct',
  // -- community moderation (F4; admin) --
  'POST /book/community/interpretations/{interp_id}/approve': 'direct',
  'POST /book/community/interpretations/{interp_id}/reject': 'direct',
  'POST /book/community/artifacts/{artifact_id}/approve': 'direct',
  'POST /book/community/artifacts/{artifact_id}/reject': 'direct',
  // -- presence (F4; reader+ view, editor+ write) --
  'GET /book/presence/suggestions': 'enveloped',
  'GET /book/presence/suggestions/stats': 'enveloped',
  'GET /book/presence/suggestions/{suggestion_id}/view': 'enveloped',
  'POST /book/presence/suggestions/{suggestion_id}/approve': 'direct',
  'POST /book/presence/suggestions/{suggestion_id}/reject': 'direct',
  'GET /book/presence/trending': 'enveloped',
  // -- email (F4; reader+ view, editor+ write) --
  'GET /book/email/drafts': 'enveloped',
  'POST /book/email/drafts/{draft_id}/send': 'direct',
  'GET /book/email/stats': 'enveloped',
  'GET /book/email/draft/auto': 'enveloped',
  'GET /book/email/draft/topic/{topic}': 'enveloped',
  // -- drafts approve (F4; reader+ view, editor+ write) --
  'GET /book/drafts': 'enveloped',
  'POST /book/drafts/{draft_id}/approve': 'direct',
  // -- xray (F5; admin+ observability) --
  'GET /xray/events/stream': 'direct',
  'GET /xray/stats': 'direct',
  'GET /xray/events': 'direct',
  'GET /xray/version': 'direct',
  // -- reader history (F5; /history page) --
  'GET /book/reader/history/sessions': 'enveloped',
  // очистка диалога читателя (конверт {ok, data:{deleted}})
  'DELETE /book/reader/history/session': 'enveloped',
  'DELETE /book/reader/history': 'enveloped',
  'GET /book/os/documents': 'direct',
  'POST /book/os/pipeline/ingest': 'direct',
  // -- studio (API returns the success envelope) --
  'POST /studio/create': 'enveloped',
  'GET /studio/list': 'enveloped',
  'GET /studio/{session_id}': 'enveloped',
  'POST /studio/{session_id}/discuss': 'enveloped',
  'POST /studio/{session_id}/modify': 'enveloped',
  'POST /studio/{session_id}/variant': 'enveloped',
  'POST /studio/{session_id}/activate-version': 'enveloped',
  'POST /studio/{session_id}/upload-reference': 'enveloped',
  'POST /studio/{session_id}/approve': 'enveloped',
  'POST /studio/{session_id}/reject': 'enveloped',
  'GET /studio/{session_id}/export': 'direct',
  'GET /book/reader/history/full': 'enveloped',
};

export function envelopeOf(method: string, path: string): Envelope {
  // Query-string в ключи карты не входит (контракты различаются только path'ом):
  // 'GET /book/reader/history?limit=5' → 'GET /book/reader/history'.
  const m = method.toUpperCase();
  const barePath = path.split('?')[0];
  // 1. Точное совпадение (статические пути).
  const exact = ENVELOPE_MAP[`${m} ${barePath}`];
  if (exact) return exact;
  // 2. Template-записи (F3 — первые path-param контракты):
  // 'GET /book/temporal/context/{epoch_id}' матчит '/book/temporal/context/arkaim_era'.
  // Сегмент {param} = любой непустой сегмент; статические сегменты — приоритет
  // (exact-lookup выше уже разрешил /stats, /history, /scan и т.п.).
  for (const rule of TEMPLATE_RULES) {
    if (rule.method === m && rule.re.test(barePath)) return rule.envelope;
  }
  return 'direct';
}

/** Предкомпилированные template-правила из ENVELOPE_MAP (один раз на модуль). */
const TEMPLATE_RULES: { method: string; re: RegExp; envelope: Envelope }[] = Object.entries(
  ENVELOPE_MAP,
)
  .filter(([key]) => key.includes('{'))
  .map(([key, envelope]) => {
    const [method, tplPath] = key.split(' ');
    const re = new RegExp(
      '^' +
        tplPath
          .split('/')
          .map((seg) =>
            seg.startsWith('{') && seg.endsWith('}')
              ? '[^/]+'
              : seg.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
          )
          .join('/') +
        '$',
    );
    return { method, re, envelope };
  });

/**
 * Развернуть ответ согласно конверту.
 * Enveloped: вытащить .data; проверить ok===true.
 * Direct: вернуть как есть.
 */
export function unwrap<T>(method: string, path: string, body: unknown): T {
  if (envelopeOf(method, path) === 'direct') {
    return body as T;
  }
  const b = body as { ok?: boolean; data?: unknown };
  if (!b || typeof b !== 'object' || b.ok !== true) {
    throw new Error(`envelope: ответ ${method} ${path} не является ok-конвертом`);
  }
  return b.data as T;
}


