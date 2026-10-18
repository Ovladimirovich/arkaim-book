/**
 * api.ts — Централизованный API-клиент для Arkaim Digital Consciousness.
 * Обрабатывает JWT, ошибки, retry, redirect на login.
 * Использует Next.js rewrites для проксирования на бэкенд.
 * В dev-режиме: mock-данные при 401 (авторизация отключена).
 */

const API_BASE = '';

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  retries?: number;
}

class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// ── Mock Data (dev mode only — excluded from production bundle) ──

const IS_DEV = process.env.NODE_ENV === 'development';

const MOCK_DATA: Record<string, unknown> = IS_DEV ? {
  // ── Auth ──
  '/auth/me': { user: { id: 'dev-user-001', role: 'admin', username: 'developer', display_name: 'Разработчик', provider: 'dev' } },
  '/auth/admin/users': [
    { id: '1', role: 'admin', username: 'admin', provider: 'telegram', is_active: true, display_name: 'Администратор', created_at: '2026-01-01' },
    { id: '2', role: 'editor', username: 'editor1', provider: 'telegram', is_active: true, display_name: 'Редактор', created_at: '2026-02-01' },
    { id: '3', role: 'reader', username: 'reader1', provider: 'telegram', is_active: true, display_name: 'Читатель', created_at: '2026-03-01' },
  ],
  '/auth/admin/stats': { users: { total: 5, by_role: { reader: 3, editor: 1, admin: 1 } }, presence: { trending_topics: 2, pending_suggestions: 3 } },
  '/auth/api-keys': [{ id: 'k1', key_prefix: 'ak_dev', name: 'Dev Key', last_used_at: null, is_active: true, created_at: '2026-01-01' }],
  '/auth/admin/api-keys': [{ id: 'k1', key_prefix: 'ak_dev', name: 'Dev Key', last_used_at: null, is_active: true, created_at: '2026-01-01' }],
  '/auth/admin/sessions': [{ id: 's1', user_id: '1', expires_at: new Date(Date.now() + 86400000).toISOString(), created_at: new Date().toISOString() }],
  '/auth/admin/invites': [{ id: 'i1', role: 'reader', note: 'Тестовый инвайт', use_count: 0, max_uses: 5, is_active: true, url: 'http://localhost:3000/auth/invite/test' }],

  // ── Book Core ──
  '/book/genome': {
    themes: [{ name: 'Наследие', description: 'Духовное наследие древних цивилизаций' }, { name: 'Аркаим', description: 'Древнее городище на Южном Урале' }, { name: 'Древняя Русь', description: 'История и культура славян' }, { name: 'Тайны', description: 'Загадки прошлого и космоса' }],
    characters: [
      { id: 'ch_1', name: 'Велик', role: 'protagonist', description: 'Главный герой — потомок древней цивилизации' },
      { id: 'ch_2', name: 'Незнакомец', role: 'mentor', description: 'Загадочный наставник из космоса' },
    ],
    values: [{ name: 'Память предков', description: 'Связь поколений через время' }, { name: 'Единство', description: 'Гармония человека и космоса' }, { name: 'Пробуждение', description: 'Духовное просветление' }],
    world_entities: [
      { id: 'we_1', name: 'Аркаим', type: 'settlement' },
      { id: 'we_2', name: 'Космический корабль', type: 'artifact' },
      { id: 'we_3', name: 'Страна Городов', type: 'region' },
    ],
    author_intent: { main_theme: 'Пробуждение сознания через связь с предками' },
    modules: {
      scenes: [
        { chapter: 0, scene_id: 'scene_01', title: 'Пробуждение Архата', characters: ['Архат'], location: 'Пещера', emotion: 'mystery', meaning_tags: ['просветление', 'тишина'] },
        { chapter: 1, scene_id: 'scene_02', title: 'Путешествие Велика', characters: ['Велик'], location: 'Горы', emotion: 'fear', meaning_tags: ['борьба', 'преодоление'] },
        { chapter: 3, scene_id: 'scene_03', title: 'Встреча с Учителем', characters: ['Велик', 'Учитель'], location: 'Горы', emotion: 'joy', meaning_tags: ['мудрость', 'возвышение'] },
        { chapter: 4, scene_id: 'scene_04', title: 'Гиперборея', characters: ['Велик'], location: 'Гиперборея', emotion: 'joy', meaning_tags: ['единство', 'гармония'] },
        { chapter: 5, scene_id: 'scene_05', title: 'Звукознание', characters: ['Ученики'], location: 'Аудитория', emotion: 'mystery', meaning_tags: ['духовность', 'познание'] },
        { chapter: 6, scene_id: 'scene_06', title: 'Космический корабль', characters: ['Велик', 'Учитель'], location: 'Корабль', emotion: 'surprise', meaning_tags: ['открытие', 'космос'] },
        { chapter: 7, scene_id: 'scene_07', title: 'Встреча у костра', characters: ['Велик', 'Учитель'], location: 'Каменный круг', emotion: 'mystery', meaning_tags: ['ритуал', 'знание'] },
        { chapter: 8, scene_id: 'scene_08', title: 'Страна Городов', characters: ['Велик'], location: 'Аркаим', emotion: 'joy', meaning_tags: ['дом', 'возвращение'] },
      ],
      character_visuals: [
        { character_id: 'velik', name: 'Велик', archetype: 'hero', visual_description: 'Атлетичный мужчина 30-35 лет, короткие русые волосы, зелёные глаза', color_palette: ['#2563eb', '#1e40af', '#8B4513'] },
        { character_id: 'teacher', name: 'Учитель', archetype: 'sage', visual_description: 'Худощавый старец 70+, длинные седые волосы', color_palette: ['#FFF8E1', '#FFD700', '#F5F5DC'] },
      ],
      location_visuals: [
        { location_id: 'arkaim', name: 'Аркаим', atmosphere: 'sacred', architecture: 'ancient_settlement', lighting: 'golden_hour' },
        { location_id: 'cave', name: 'Пещера', atmosphere: 'mystical', architecture: 'natural_cave', lighting: 'dim_candlelight' },
        { location_id: 'mountains', name: 'Горы', atmosphere: 'dramatic', architecture: 'natural_landscape', lighting: 'cold_blue' },
      ],
    },
  },
  '/book/ask': { data: { answer: 'Это тестовый ответ. В реальном режиме книга отвечает на основе базы знаний.', source: 'mock' } },
  '/book/reader/profile': { reader_id: 'dev', display_name: 'Разработчик', questions_total: 42, conversation_count: 15, last_topic: 'Аркаим', topics: [{ name: 'Аркаим', depth: 0.8, questions: 12 }, { name: 'Гиперборея', depth: 0.5, questions: 8 }, { name: 'Древняя Русь', depth: 0.3, questions: 5 }] },
  '/book/reader/reading-progress': { data: [] },
  '/book/reader/reading-position': { data: null },

  // ── Chapters & Screenplay ──
  '/book/chapters': {
    ok: true, total: 18,
    data: [
      { id: 'ch_00', title: 'Часть 0', char_count: 718, index: 0, section_type: 'title' },
      { id: 'ch_01', title: 'Пролог', char_count: 555, index: 1, section_type: 'prologue' },
      { id: 'ch_02', title: 'Часть 1', char_count: 3115, index: 2, section_type: 'part' },
      { id: 'ch_03', title: 'Часть 2', char_count: 2145, index: 3, section_type: 'part' },
      { id: 'ch_04', title: 'Часть 3', char_count: 7776, index: 4, section_type: 'part' },
      { id: 'ch_05', title: 'Часть 4', char_count: 29047, index: 5, section_type: 'part' },
      { id: 'ch_06', title: 'Часть 5', char_count: 18316, index: 6, section_type: 'part' },
      { id: 'ch_07', title: 'Часть 6', char_count: 1513, index: 7, section_type: 'part' },
      { id: 'ch_08', title: 'Часть 7', char_count: 4421, index: 8, section_type: 'part' },
      { id: 'ch_09', title: 'Часть 8', char_count: 8277, index: 9, section_type: 'part' },
      { id: 'ch_10', title: 'Часть 9', char_count: 5205, index: 10, section_type: 'part' },
      { id: 'ch_11', title: 'Часть 10', char_count: 9036, index: 11, section_type: 'part' },
      { id: 'ch_12', title: 'Часть 11', char_count: 6899, index: 12, section_type: 'part' },
      { id: 'ch_13', title: 'Часть 12', char_count: 9559, index: 13, section_type: 'part' },
      { id: 'ch_14', title: 'Часть 13', char_count: 1430, index: 14, section_type: 'part' },
      { id: 'ch_15', title: 'Часть 14', char_count: 1294, index: 15, section_type: 'part' },
      { id: 'ch_16', title: 'Часть 15', char_count: 4586, index: 16, section_type: 'part' },
      { id: 'ch_17', title: 'Эпилог', char_count: 2407, index: 17, section_type: 'epilogue' },
    ],
  },
  '/book/screenplay': {
    ok: true, total: 53,
    data: [
      { id: 'scene_000', title: '1. EXT. ГЛУБОКИЙ КОСМОС', char_count: 320, index: 0 },
      { id: 'scene_001', title: '2. EXT. МЛЕЧНЫЙ ПУТЬ', char_count: 280, index: 1 },
      { id: 'scene_002', title: '3. EXT. СОЛНЕЧНАЯ СИСТЕМА', char_count: 250, index: 2 },
      { id: 'scene_003', title: '4. EXT. ЗЕМЛЯ', char_count: 410, index: 3 },
      { id: 'scene_004', title: '5. EXT. КОСМОС', char_count: 350, index: 4 },
      { id: 'scene_005', title: '6. INT. ПЕЩЕРА', char_count: 480, index: 5 },
    ],
  },

  // ── Layers & Evolution ──
  '/book/evolution/status': {
    current_version: '1.0.0',
    loaded_at: new Date().toISOString(),
    snapshots: {
      total_snapshots: 1, last_version: '1.0.0', last_saved_at: new Date().toISOString(),
      immutable_layers: ['identity', 'mission'], mutable_layers: ['knowledge', 'meaning'],
    },
  },
  '/book/layers': {
    knowledge_layer: 'Книга охватывает темы древней цивилизации, космических путешествий и духовного развития человечества.',
    meaning_layer: 'Аркаим — метафора пробуждения сознания. Космический корабль — аллегория перерождения.',
    identity_layer: 'Мы — потомки древних цивилизаций, несущие в себе код предков.',
    mission_layer: 'Книга существует, чтобы пробудить память о нашей истинной природе.',
    world_engine_layer: 'Мир книги включает древние городища, космические пространства и энергетические линии.',
  },

  // ── Knowledge Search ──
  '/book/knowledge/search': { data: [{ type: 'theme', name: 'Аркаим', description: 'Древнее городище на Южном Урале' }, { type: 'expansion', topic: 'Культура Синташты', score: 8.5, data: {} }], query: '', total: 2, offset: 0, limit: 10, type_filter: 'all', sort: 'relevance' },
  '/book/knowledge/autocomplete': { data: [{ text: 'Аркаим', type: 'theme', score: 8 }, { text: 'Гиперборея', type: 'theme', score: 6 }], query: '' },

  // ── Crowdfunding ──
  '/book/crowdfunding/status': { campaigns: [{ id: 'c1', title: 'Издание книги', platform: 'planeta', url: 'https://example.com', target_amount: 500000, raised_amount: 127500, backers_count: 234, days_remaining: 30, status: 'active', progress_percent: 25.5, last_checked: new Date().toISOString(), milestones: [{ percent: 30, amount: 150000, reached: false, reached_at: null }, { percent: 50, amount: 250000, reached: false, reached_at: null }, { percent: 75, amount: 375000, reached: false, reached_at: null }, { percent: 100, amount: 500000, reached: false, reached_at: null }] }], count: 1 },

  // ── Presence ──
  '/book/presence/suggestions': { suggestions: [{ id: 's1', topic: 'История Аркаима', reason: 'Читатели интересуются', status: 'pending' }, { id: 's2', topic: 'Персонажи книги', reason: 'Много вопросов', status: 'approved' }] },
  '/book/presence/trending': { trending: [{ keyword: 'Аркаим', hits: 45, sources: ['telegram'] }, { keyword: 'Гиперборея', hits: 23, sources: ['api'] }], total: 2 },

  // ── Email ──
  '/book/email/stats': { subscribers: 156, sent: 1200, errors: 3 },
  '/book/email/drafts': [{ id: 'd1', subject: 'Недельный дайджест', status: 'sent', created_at: new Date().toISOString() }],
  '/book/email/subscribers': [{ email: 'reader@example.com', name: 'Иван', subscribed_at: new Date().toISOString() }],

  // ── World Explorer ──
  '/book/world-explorer/epochs': { data: [{ id: 'satya_yuga', name: 'Satya Yuga', name_ru: 'Сатья Юга', order: 1 }, { id: 'treta_yuga', name: 'Treta Yuga', name_ru: 'Трета Юга', order: 2 }, { id: 'dvapara_yuga', name: 'Dvapara Yuga', name_ru: 'Двапара Юга', order: 3 }, { id: 'kali_yuga', name: 'Kali Yuga', name_ru: 'Кали Юга', order: 4 }] },
  '/book/world-explorer/stats': { data: { world_model: 'Мир: 12 эпох', patterns_count: 54, epochs_count: 12, locations_count: 12, events_count: 17 } },
  '/book/world-explorer/history': { data: [{ id: 1, prompt: 'Test exploration', epoch: 'satya_yuga', hypothesis_title: 'Pattern', summary: 'Test', overall_score: 0.85, branch_count_actual: 3, duration_ms: 150, created_at: new Date().toISOString() }], count: 1 },

  // ── Graph & Analytics ──
  '/book/graph/stats': { nodes: 150, edges: 300, node_types: { character: 20, location: 10, concept: 50 }, relationship_types: { knows: 50, lives_in: 30, part_of: 20 } },
  '/analytics': { total_requests: 1234, requests_by_type: { '/book/ask': 500, '/book/genome': 200, '/auth/me': 100 }, avg_response_time_ms: 150, error_rate: 2.3 },

  // ── X-Ray ──
  '/xray/stats': { active_traces: 0, completed_traces: 42, orphan_spans: 0 },
  '/xray/traces': [{ trace_id: 't1', name: 'book.ask', status: 'ok', duration_ms: 150, started_at: new Date().toISOString() }],
  '/xray/diagnostics': { checks: [{ name: 'database', status: 'ok', message: 'SQLite connected' }, { name: 'genome', status: 'ok', message: 'Loaded' }, { name: 'memory', status: 'ok', message: 'Store ready' }] },

  // ── Book OS Search ──
  '/book/os/search': { results: [{ id: 'r1', text: 'Аркаим — древнее городище...', score: 0.85, metadata: {} }] },
  '/book/os/facts/search': { facts: [{ id: 'f1', statement: 'Аркаим расположен на Южном Урале', entity_id: 'arkaim', confidence: 0.9 }] },
  '/book/os/entities': { entities: [{ name: 'Аркаим', type: 'location' }, { name: 'Велик', type: 'character' }] },

  // ── Map ──
  '/book/community/map-data': {
    regions: [
      { id: 'loc_1', name: 'Аркаим', type: 'settlement', coordinates: { lat: 52.65, lng: 59.57 }, description: 'Древнее городище на Южном Урале', era: '~4000 до н.э.', color: '#D2691E', icon: '🏛️' },
      { id: 'loc_2', name: 'Синташта', type: 'settlement', coordinates: { lat: 52.48, lng: 59.75 }, description: 'Крепость с древнейшими колесницами', era: '~2100 до н.э.', color: '#A0522D', icon: '⚔️' },
      { id: 'loc_3', name: 'Петровка', type: 'settlement', coordinates: { lat: 52.7, lng: 59.5 }, description: 'Петровская культура', era: '~2000 до н.э.', color: '#8B4513', icon: '🏘️' },
      { id: 'loc_4', name: 'Гаргарда', type: 'settlement', coordinates: { lat: 53.0, lng: 58.5 }, description: 'Сеть городищ Страны Городов', era: '~3000 до н.э.', color: '#B8860B', icon: '🏰' },
    ],
    routes: [
      { id: 'r1', name: 'Дорога предков', type: 'migration', points: [{ lat: 52.65, lng: 59.57 }, { lat: 52.48, lng: 59.75 }], color: '#FF6B35', dash: false, description: 'Маршрут миграции от Аркаима к Синташте' },
      { id: 'r2', name: 'Северный путь', type: 'trade', points: [{ lat: 52.65, lng: 59.57 }, { lat: 53.0, lng: 58.5 }], color: '#4FC3F7', dash: true, description: 'Торговый путь на север' },
    ],
    energy_lines: [
      { name: 'Линия Силы', points: [{ lat: 50.0, lng: 55.0 }, { lat: 55.0, lng: 65.0 }], color: '#FFD700', description: 'Древняя энергетическая линия' },
    ],
  },

  // ── Community: Interpretations ──
  '/book/community/interpretations': {
    interpretations: [
      { id: 'int_1', title: 'Аркаим как космический порт', author: 'Иван', content: 'Одна из интересных интерпретаций...', likes: 15, comments_count: 3, created_at: new Date().toISOString() },
      { id: 'int_2', title: 'Тайны Гипербореи', author: 'Мария', content: 'Древние знания о северной цивилизации...', likes: 8, comments_count: 1, created_at: new Date(Date.now() - 86400000).toISOString() },
    ],
    count: 2,
  },
  '/book/community/interpretations/stats': { total: 2, approved: 2, pending: 0 },
  '/book/community/interpretations/mine': { interpretations: [], count: 0 },

  // ── Community: Artifacts ──
  '/book/community/artifacts': {
    artifacts: [
      { id: 'art_1', title: 'Карта Аркаима', author: 'Пётр', category: 'map', content: 'Интерактивная карта...', likes: 12, comments_count: 2, created_at: new Date().toISOString() },
      { id: 'art_2', title: 'Хронология событий', author: 'Анна', category: 'timeline', content: 'Таймлайн из книги...', likes: 7, comments_count: 0, created_at: new Date(Date.now() - 172800000).toISOString() },
    ],
    count: 2,
  },
  '/book/community/artifacts/stats': { total: 2, pending: 0, categories: { map: 1, timeline: 1, archaeology: 0 } },
  '/book/community/artifacts/mine': { artifacts: [], count: 0 },

  // ── Community: Notifications & Comments ──
  '/book/community/notifications': { notifications: [{ id: 'n1', type: 'suggestion', title: 'Новая тема', message: 'Предложена тема: Тайны Аркаима', read: false, created_at: new Date().toISOString() }], total: 1 },
  '/book/community/search': { results: [] },

  // ── Story Engine ──
  '/book/story-engine/constraints': { ok: true, constraints: { genre: 'мифология', mood: 'таинственность', max_length: 2000 } },
  '/book/world-engine/model': { entities: [{ name: 'Аркаим', type: 'location' }, { name: 'Велик', type: 'character' }], relations: [] },

// ComfyUI Status — intentionally NOT mocked: real connectivity must be shown.
  // The frontend proxies /book/* to the backend, which reports live status.
} : {};

// ── Dynamic POST/DELETE/PUT mocks (prefix-matched) ──

const DYNAMIC_POST_MOCKS: Array<{ pattern: RegExp; response: () => Record<string, unknown> }> = IS_DEV ? [
  // Presence suggestions
  { pattern: /^\/book\/presence\/suggestions\/[^/]+\/approve$/, response: () => ({ ok: true }) },
  { pattern: /^\/book\/presence\/suggestions\/[^/]+\/reject$/, response: () => ({ ok: true }) },
  // Email drafts
  { pattern: /^\/book\/email\/drafts\/[^/]+\/approve$/, response: () => ({ ok: true }) },
  { pattern: /^\/book\/email\/drafts\/[^/]+\/send$/, response: () => ({ ok: true, sent: 10, errors: 0 }) },
  // Community likes
  { pattern: /^\/book\/community\/interpretations\/[^/]+\/like$/, response: () => ({ ok: true }) },
  { pattern: /^\/book\/community\/artifacts\/[^/]+\/like$/, response: () => ({ ok: true }) },
  // Community moderation
  { pattern: /^\/book\/community\/interpretations\/[^/]+\/approve$/, response: () => ({ ok: true }) },
  { pattern: /^\/book\/community\/interpretations\/[^/]+\/reject$/, response: () => ({ ok: true }) },
  { pattern: /^\/book\/community\/artifacts\/[^/]+\/approve$/, response: () => ({ ok: true }) },
  { pattern: /^\/book\/community\/artifacts\/[^/]+\/reject$/, response: () => ({ ok: true }) },
  // Community notifications
  { pattern: /^\/book\/community\/notifications\/[^/]+\/read$/, response: () => ({ ok: true }) },
  // Community comments
  { pattern: /^\/book\/community\/comments\/[^/]+\/[^/]+$/, response: () => ({ comments: [{ id: 'c1', author: 'Читатель', text: 'Отличная работа!', likes: 3, created_at: new Date().toISOString() }], count: 1 }) },
  { pattern: /^\/book\/community\/comments\/[^/]+$/, response: () => ({ ok: true, id: 'c_' + Date.now() }) },
  { pattern: /^\/book\/community\/comments\/[^/]+\/like$/, response: () => ({ ok: true }) },
  // Admin users
  { pattern: /^\/auth\/admin\/users\/[^/]+\/role$/, response: () => ({ ok: true }) },
  { pattern: /^\/auth\/admin\/users\/[^/]+\/toggle$/, response: () => ({ ok: true }) },
  // World Explorer
  { pattern: /^\/book\/world-explorer\/explore$/, response: () => ({ ok: true, data: { exploration_id: 'exp_' + Date.now(), hypothesis_title: 'Альтернативное развитие', summary: 'Если бы цивилизация не погибла...', branches: 3, overall_score: 0.82, duration_ms: 250 } }) },
  { pattern: /^\/book\/world-explorer\/explore\/hypothesis$/, response: () => ({ ok: true, data: { exploration_id: 'exp_h_' + Date.now(), summary: 'Развитие по гипотезе...', branches: 2, overall_score: 0.78 } }) },
  { pattern: /^\/book\/world-explorer\/validate$/, response: () => ({ ok: true, compatible: true, compatibility_score: 0.85, issues: [] }) },
  { pattern: /^\/book\/world-explorer\/feedback$/, response: () => ({ ok: true }) },
  { pattern: /^\/book\/world-explorer\/generate-from-branch$/, response: () => ({ ok: true, data: { system_instruction: 'Ты — рассказчик.', user_prompt: 'Сгенерированный текст...', style: 'literary', max_length: 2000, branch_title: 'Test', quality_score: 0.85 } }) },
  // World Explorer hypotheses/possibilities
  { pattern: /^\/book\/world-explorer\/hypotheses\/[^/]+$/, response: () => ({ data: [{ id: 'h1', title: 'Альтернативное развитие', description: 'Что если...', probability: 0.3 }, { id: 'h2', title: 'Параллельная линия', description: 'Другой вариант...', probability: 0.5 }] }) },
  { pattern: /^\/book\/world-explorer\/possibilities\/[^/]+$/, response: () => ({ data: [{ id: 'p1', title: 'Новая технология', description: 'Открытие энергии', impact: 'high' }, { id: 'p2', title: 'Миграция', description: 'Переселение народа', impact: 'medium' }] }) },
  // World Explorer history
  { pattern: /^\/book\/world-explorer\/history\/[^/]+$/, response: () => ({ ok: true }) },
  // DELETE for all dynamic paths
  { pattern: /^\/book\/community\/interpretations\/[^/]+$/, response: () => ({ ok: true }) },
  { pattern: /^\/book\/community\/artifacts\/[^/]+$/, response: () => ({ ok: true }) },
  { pattern: /^\/auth\/admin\/sessions\/[^/]+$/, response: () => ({ ok: true }) },
  { pattern: /^\/auth\/admin\/users\/[^/]+$/, response: () => ({ ok: true }) },
  { pattern: /^\/auth\/admin\/invites\/[^/]+$/, response: () => ({ ok: true }) },
  { pattern: /^\/auth\/admin\/api-keys\/[^/]+$/, response: () => ({ ok: true }) },
  { pattern: /^\/auth\/api-keys\/[^/]+$/, response: () => ({ ok: true }) },
] : [];

const DYNAMIC_GET_MOCKS: Array<{ pattern: RegExp; response: () => Record<string, unknown> }> = IS_DEV ? [
  { pattern: /^\/auth\/admin\/users\/[^/]+$/, response: () => ({ id: '1', role: 'admin', username: 'user', provider: 'dev', is_active: true, display_name: 'Пользователь', created_at: '2026-01-01' }) },
  { pattern: /^\/book\/graph\/entity\/[^/]+$/, response: () => ({ neighbors: [{ id: 'n1', name: 'Аркаим', type: 'location' }] }) },
  { pattern: /^\/book\/chapters\/[^/]+$/, response: () => ({ ok: true, data: { id: 'ch_01', title: 'Пролог', content: 'Среди мириад звездных систем во Вселенной...', char_count: 555, index: 1, section_type: 'prologue' } }) },
  { pattern: /^\/book\/screenplay\/[^/]+$/, response: () => ({ ok: true, data: { id: 'scene_000', title: '1. EXT. ГЛУБОКИЙ КОСМОС', content: '(Камера медленно движется сквозь космос...)', char_count: 320, index: 0 } }) },
  { pattern: /^\/book\/world-explorer\/hypotheses\/[^/]+$/, response: () => ({ data: [{ id: 'h1', title: 'Альтернативное развитие', description: 'Что если...', probability: 0.3 }, { id: 'h2', title: 'Параллельная линия', description: 'Другой вариант...', probability: 0.5 }] }) },
  { pattern: /^\/book\/world-explorer\/possibilities\/[^/]+$/, response: () => ({ data: [{ id: 'p1', title: 'Новая технология', description: 'Открытие энергии', impact: 'high' }, { id: 'p2', title: 'Миграция', description: 'Переселение народа', impact: 'medium' }] }) },
  { pattern: /^\/book\/community\/comments\/[^/]+\/[^/]+$/, response: () => ({ comments: [{ id: 'c1', author: 'Читатель', text: 'Отличная работа!', likes: 3, created_at: new Date().toISOString() }], count: 1 }) },
] : [];

function getMockData(path: string, method: string = 'GET'): Record<string, unknown> {
  const basePath = path.split('?')[0];

  // ── DELETE / PUT: always return success for any known prefix ──
  if (method === 'DELETE' || method === 'PUT') {
    for (const entry of DYNAMIC_POST_MOCKS) {
      if (entry.pattern.test(basePath)) return entry.response();
    }
    return { ok: true };
  }

  // ── POST: static + dynamic ──
  if (method === 'POST') {
    const POST_MOCKS: Record<string, Record<string, unknown>> = {
      '/auth/api-key': { key: 'ak_test_' + Math.random().toString(36).slice(2, 10), key_masked: 'ak_test_...' },
      '/book/email/subscribe': { ok: true, email: 'subscribed' },
      '/book/ask': { data: { answer: 'Это тестовый ответ. В реальном режиме книга отвечает на основе базы знаний.', source: 'mock' } },
      '/book/crowdfunding/check-now': { checked: 1, alerts: [], milestones: [] },
      '/book/crowdfunding/config': { ok: true, campaigns: [] },
      '/auth/admin/invites': { ok: true, url: 'http://localhost:3000/auth/invite/' + Math.random().toString(36).slice(2, 10) },
      '/book/visual-genome/scene': { ok: true, scene_id: 'scene_' + Date.now() },
      '/book/visual-genome/character': { ok: true },
      '/book/visual-genome/location': { ok: true },
      '/book/visual-genome/from-speech': { ok: true },
          '/book/email/draft/auto': { ok: true, draft_id: 'draft_' + Date.now(), subject: 'Новый черновик' },
      '/book/email/send/weekly-digest': { ok: true, sent: 150 },
      '/book/community/interpretations': { ok: true, id: 'int_' + Date.now() },
      '/book/community/artifacts': { ok: true, id: 'art_' + Date.now() },
      '/book/story-engine/generate': { ok: true },
      '/book/reader/reading-event': { ok: true },
      '/auth/update-profile': { ok: true },
    };
    if (POST_MOCKS[basePath]) return POST_MOCKS[basePath];

    // Dynamic POST patterns
    for (const entry of DYNAMIC_POST_MOCKS) {
      if (entry.pattern.test(basePath)) return entry.response();
    }
  }

  // ── GET: static + dynamic ──
  if (MOCK_DATA[basePath]) return MOCK_DATA[basePath] as Record<string, unknown>;

  for (const entry of DYNAMIC_GET_MOCKS) {
    if (entry.pattern.test(basePath)) return entry.response();
  }

  // Default
  return {};
}

/**
 * Пути, для которых подмена ошибки мок-данными недопустима никогда:
 * интерфейс обязан показать реальную причину, а не придуманные данные.
 *
 * - `/book/reader/history*` — реальная память читателя (иначе UI показывает
 *   несуществующие диалоги);
 * - `/book/chapters*` — реальное содержание книги (экран «Чтение»; иначе
 *   при 5xx показывается демо-глава вместо честной ошибки);
 * - `/book/reader/profile` — реальный профиль читателя (экраны «Профиль»
 *   и «Книга»; иначе при 5xx рисуются выдуманные счётчики диалогов);
 * - `/book/comfyui/*` — реальный статус связи с сервисом генерации
 *   (см. исторический комментарий у MOCK_DATA: ComfyUI намеренно не мокается).
 */
function isNeverMockedPath(path: string): boolean {
  const basePath = path.split('?')[0];
  if (basePath.startsWith('/book/reader/history')) return true;
  if (basePath.startsWith('/book/chapters')) return true;
  if (basePath.startsWith('/book/reader/profile')) return true;
  if (basePath.startsWith('/book/comfyui')) return true;
  return false;
}

/** Мок-подмена разрешена только для 5xx и только вне never-mocked путей. */
function canMockFallback(path: string): boolean {
  if (IS_DEV !== true) return false;
  return !isNeverMockedPath(path);
}

function buildHeaders(opts: RequestOptions): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    ...((opts.headers as Record<string, string>) || {}),
  };
}

/**
 * FormData уходит как есть (без JSON.stringify): браузер сам ставит
 * Content-Type с boundary — хедер application/json здесь сбрасывается.
 */
function isFormDataBody(body: unknown): body is FormData {
  return typeof FormData !== 'undefined' && body instanceof FormData;
}

async function readErrorBody(resp: Response): Promise<unknown> {
  try {
    return await resp.json();
  } catch {
    return null;
  }
}

function toApiError(status: number, data: unknown): ApiError {
  return new ApiError(status, `HTTP ${status}`, data);
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { body, retries = 0, ...fetchOpts } = opts;
  const url = `${API_BASE}${path}`;
  const method = (fetchOpts.method || 'GET').toUpperCase();
  const allowMockFallback = canMockFallback(path);

  // Сессия живёт в HttpOnly-cookie `arkaim_session` и уходит сама через
  // `credentials: 'same-origin'`. Ручной `Authorization: Bearer` из
  // `document.cookie` технически нечитаем (HttpOnly) и лишь перебивал бы
  // валидную cookie-сессию — поэтому заголовок здесь не формируется.
  const headers = buildHeaders(opts);
  const formBody = isFormDataBody(body);
  if (formBody) delete (headers as Record<string, string>)['Content-Type'];

  try {
    const resp = await fetch(url, {
      ...fetchOpts,
      headers,
      credentials: 'same-origin',
      body: formBody ? (body as FormData) : body ? JSON.stringify(body) : undefined,
    });

    // 401 / 403 / 404 — настоящая ошибка запроса. Раньше она молча
    // подменялась мок-данными (на 401 — даже пустым `{}`), из-за чего
    // потеря сессии или несуществующий адрес выглядели как «работает».
    if (resp.status === 401 || resp.status === 403 || resp.status === 404) {
      throw toApiError(resp.status, await readErrorBody(resp));
    }

    // 5xx — временный сбой backend. Dev-подмена сохранена намеренно.
    if (allowMockFallback && resp.status >= 500) {
      const mockData = getMockData(path, method);
      if (Object.keys(mockData).length > 0) return mockData as T;
    }

    if (!resp.ok) {
      throw toApiError(resp.status, await readErrorBody(resp));
    }

    const contentType = resp.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      return resp.json() as Promise<T>;
    }
    return resp.text() as unknown as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;

    // Сетевая ошибка (backend не поднят) — не возвращаем ни пустой объект,
    // ни выдуманные данные: вызывающий код должен увидеть реальный сбой.
    if (retries > 0) {
      await new Promise(r => setTimeout(r, 1000));
      return request<T>(path, { ...opts, retries: retries - 1 });
    }
    throw err;
  }
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { method: 'GET', ...opts }),

  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { method: 'POST', body, ...opts }),

  put: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { method: 'PUT', body, ...opts }),

  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { method: 'PATCH', body, ...opts }),

  delete: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { method: 'DELETE', ...opts }),
};

export { ApiError, API_BASE };

// Экспорт типизированных функций контрактов
export * from '@/shared/api/contracts';
