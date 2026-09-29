/**
 * envelope.ts вЂ” СЂР°Р·РІС‘СЂС‚РєР° РѕС‚РІРµС‚РѕРІ backend'Р° (F1_SPEC В§6).
 *
 * Backend РёСЃРїРѕР»СЊР·СѓРµС‚ Р”Р’Р• РєРѕРЅРІРµРЅС†РёРё РѕС‚РІРµС‚РѕРІ (FRONTEND_FORENSIC_AUDIT В§2.2):
 *   enveloped : {"ok": true, "data": <payload>, "trace_id"?: ...}  (SuccessResponse DTO)
 *   direct    : <raw payload> Р±РµР· РєРѕРЅРІРµСЂС‚Р° (auth, world, temporal-chain Рё РґСЂ.)
 *
 * ENVELOPE_MAP вЂ” РµРґРёРЅСЃС‚РІРµРЅРЅР°СЏ РєР°СЂС‚Р° РїСЂР°РІРґС‹ В«РєР°РєРѕР№ endpoint РєР°Рє РѕС‚РІРµС‡Р°РµС‚В».
 * Р СѓС‡РЅР°СЏ С‚РёРїРёР·Р°С†РёСЏ F1: С‚РѕР»СЊРєРѕ auth/health (Р·Р°РґРµР№СЃС‚РІРѕРІР°РЅРЅС‹Рµ РІ F1); РѕСЃС‚Р°Р»СЊРЅРѕРµ
 * РґРѕР±Р°РІР»СЏРµС‚СЃСЏ РїРѕ С„Р°Р·Р°Рј F2+ РїРѕ РјРµСЂРµ РїРѕРґРєР»СЋС‡РµРЅРёСЏ СЌРєСЂР°РЅРѕРІ.
 */

export type Envelope = 'enveloped' | 'direct';

/**
 * РљР°СЂС‚Р° РєРѕРЅРІРµСЂС‚РѕРІ РґР»СЏ F1-РєРѕРЅС‚СЂР°РєС‚РѕРІ.
 * Р¤РѕСЂРјР°С‚ РєР»СЋС‡РµР№ вЂ” РїСѓС‚СЊ OpenAPI. PATH-РїР°СЂР°РјРµС‚СЂС‹: С€Р°Р±Р»РѕРЅ {param}.
 */
export const ENVELOPE_MAP: Record<string, Envelope> = {
  // в”Ђв”Ђ auth (direct-return; РїСЂРѕРІРµСЂРµРЅРѕ forensic В§2.2) в”Ђв”Ђ
  'GET /auth/me': 'direct',
  'POST /auth/register': 'direct',
  'POST /auth/telegram/login': 'direct',
  'POST /auth/telegram/callback': 'direct',
  'POST /auth/dev/generate-token': 'direct',
  'POST /auth/logout': 'direct',
  'GET /auth/logout': 'direct',
  // в”Ђв”Ђ admin (РІСЃРµ raw JSON, РЅРµ enveloped вЂ” РїСЂРѕРІРµСЂРµРЅРѕ live) в”Ђв”Ђ
  'GET /auth/admin/users': 'direct',
  'GET /auth/admin/users/{user_id}': 'direct',
  'POST /auth/admin/users/{user_id}/role': 'direct',
  'POST /auth/admin/users/{user_id}/toggle': 'direct',
  'DELETE /auth/admin/users/{user_id}': 'direct',
  'GET /auth/admin/stats': 'direct',
  'GET /auth/admin/api-keys': 'direct',
  'DELETE /auth/admin/api-keys/{key_id}': 'direct',
  // в”Ђв”Ђ system в”Ђв”Ђ
  'GET /health': 'direct',
  // в”Ђв”Ђ book / reader (F2; live-РїСЂРѕРІРµСЂРµРЅРѕ С€Р°РіРѕРј 0 F2-РїР»Р°РЅР°) в”Ђв”Ђ
  'POST /book/ask': 'enveloped',
  'GET /book/chapters': 'enveloped',
  'GET /book/chapters/{chapter_id}': 'enveloped',
  // text: РїР°РіРёРЅР°С†РёРѕРЅРЅС‹Рµ РїРѕР»СЏ (offset/limit/total/has_more) Р¶РёРІСѓС‚ Р’ РљРћРќР’Р•Р РўР• вЂ”
  // РєРѕРЅС‚СЂР°РєС‚ (book.ts getText) С‡РёС‚Р°РµС‚ РїРѕР»РЅС‹Р№ РєРѕРЅРІРµСЂС‚, РїРѕСЌС‚РѕРјСѓ РїРѕРјРµС‡РµРЅ direct.
  'GET /book/text': 'direct',
  'GET /book/layers': 'direct',
  'GET /book/genome': 'direct',
  'GET /book/reader/profile': 'direct',
  'GET /book/reader/history': 'enveloped',
  // reading-event: РєРѕРЅРІРµСЂС‚ {ok:true} Р‘Р•Р— data-РїРѕР»СЏ (live-С„Р°РєС‚) вЂ” С‡РёС‚Р°РµРј С†РµР»РёРєРѕРј.
  'POST /book/reader/reading-event': 'direct',
  // reading-progress: stats Р»РµР¶РёС‚ Р’ РљРћРќР’Р•Р РўР• СЂСЏРґРѕРј СЃ data вЂ” С‡РёС‚Р°РµРј РїРѕР»РЅС‹Р№ РєРѕРЅРІРµСЂС‚.
  'GET /book/reader/reading-progress': 'direct',
  'GET /book/reader/reading-position': 'enveloped',
  // analytics: reader history stats (enveloped), graph stats (direct), cache stats (enveloped)
  'GET /book/reader/history/stats': 'enveloped',
  'GET /book/graph/stats': 'direct',
  'GET /book/cache/stats': 'enveloped',
  // knowledge (F2; enveloped)
  'GET /book/knowledge/search': 'enveloped',
  'GET /book/knowledge/autocomplete': 'enveloped',
  // в”Ђв”Ђ temporal (F3; live-РїСЂРѕРІРµСЂРµРЅРѕ С€Р°РіРѕРј 0: РІСЃРµ enveloped {ok, data, ...}) в”Ђв”Ђ
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
  // в”Ђв”Ђ World Explorer (РСЃСЃР»РµРґРѕРІР°РЅРёРµ РјРёСЂР°; live-С„Р°РєС‚: api_routes.py) в”Ђв”Ђ
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
  // history POST / feedback POST / history DELETE РІРѕР·РІСЂР°С‰Р°СЋС‚ {ok, id} Р‘Р•Р— data в†’ direct
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
  // Query-string РІ РєР»СЋС‡Рё РєР°СЂС‚С‹ РЅРµ РІС…РѕРґРёС‚ (РєРѕРЅС‚СЂР°РєС‚С‹ СЂР°Р·Р»РёС‡Р°СЋС‚СЃСЏ С‚РѕР»СЊРєРѕ path'РѕРј):
  // 'GET /book/reader/history?limit=5' в†’ 'GET /book/reader/history'.
  const m = method.toUpperCase();
  const barePath = path.split('?')[0];
  // 1. РўРѕС‡РЅРѕРµ СЃРѕРІРїР°РґРµРЅРёРµ (СЃС‚Р°С‚РёС‡РµСЃРєРёРµ РїСѓС‚Рё).
  const exact = ENVELOPE_MAP[`${m} ${barePath}`];
  if (exact) return exact;
  // 2. Template-Р·Р°РїРёСЃРё (F3 вЂ” РїРµСЂРІС‹Рµ path-param РєРѕРЅС‚СЂР°РєС‚С‹):
  // 'GET /book/temporal/context/{epoch_id}' РјР°С‚С‡РёС‚ '/book/temporal/context/arkaim_era'.
  // РЎРµРіРјРµРЅС‚ {param} = Р»СЋР±РѕР№ РЅРµРїСѓСЃС‚РѕР№ СЃРµРіРјРµРЅС‚; СЃС‚Р°С‚РёС‡РµСЃРєРёРµ СЃРµРіРјРµРЅС‚С‹ вЂ” РїСЂРёРѕСЂРёС‚РµС‚
  // (exact-lookup РІС‹С€Рµ СѓР¶Рµ СЂР°Р·СЂРµС€РёР» /stats, /history, /scan Рё С‚.Рї.).
  for (const rule of TEMPLATE_RULES) {
    if (rule.method === m && rule.re.test(barePath)) return rule.envelope;
  }
  return 'direct';
}

/** РџСЂРµРґРєРѕРјРїРёР»РёСЂРѕРІР°РЅРЅС‹Рµ template-РїСЂР°РІРёР»Р° РёР· ENVELOPE_MAP (РѕРґРёРЅ СЂР°Р· РЅР° РјРѕРґСѓР»СЊ). */
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
 * Р Р°Р·РІРµСЂРЅСѓС‚СЊ РѕС‚РІРµС‚ СЃРѕРіР»Р°СЃРЅРѕ РєРѕРЅРІРµСЂС‚Сѓ.
 * Enveloped: РІС‹С‚Р°С‰РёС‚СЊ .data; РїСЂРѕРІРµСЂРёС‚СЊ ok===true.
 * Direct: РІРµСЂРЅСѓС‚СЊ РєР°Рє РµСЃС‚СЊ.
 */
export function unwrap<T>(method: string, path: string, body: unknown): T {
  if (envelopeOf(method, path) === 'direct') {
    return body as T;
  }
  const b = body as { ok?: boolean; data?: unknown };
  if (!b || typeof b !== 'object' || b.ok !== true) {
    throw new Error(`envelope: РѕС‚РІРµС‚ ${method} ${path} РЅРµ СЏРІР»СЏРµС‚СЃСЏ ok-РєРѕРЅРІРµСЂС‚РѕРј`);
  }
  return b.data as T;
}


