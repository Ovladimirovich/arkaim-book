export type Scene = { scene_id: string; chapter: number; title: string };

export type SessionStatus = 'draft' | 'discussing' | 'approved' | 'rejected' | 'sent';

export type StudioSessionT = {
  session_id: string;
  user_id: string;
  title: string;
  chapter: number;
  scene_id: string;
  context_type: string;
  active_version_id: string | null;
  status: SessionStatus;
  approved_image_asset_id?: string | null;
  reference_assets: string[];
  created_at: string;
  updated_at: string;
  finalized_at: string | null;
};

export type MotionT = {
  camera_motion?: string;
  character_actions?: unknown[];
  transitions?: unknown[];
};

export type MediaPlanT = {
  plan_id?: string;
  media_kind?: string;
  prompt?: string;
  negative_constraints?: string[];
  visual_style?: string;
  atmosphere?: string;
  duration_sec?: number;
  fps?: number;
  motion?: MotionT;
  sequence?: { shot_id?: string; prompt?: string; duration_sec?: number }[];
};

export type ProvenanceT = {
  source?: string;
  source_id?: string;
  confidence?: number;
};

export type ScenarioShotT = {
  shot_id?: string;
  order?: number;
  shot_type?: string;
  description?: string;
  duration_sec?: number;
  camera_action?: string;
  camera_angle?: string;
  transition_to_next?: string;
  lighting_note?: string;
  mood_note?: string;
  /** Локальный стиль плана — перебивает общие правила фильма (пусто → общие). */
  style_override?: string;
  /** Локальная палитра плана — перебивает общую палитру фильма. */
  palette_override?: string[];
  /** Утверждённый кадр плана (шот): последний утверждённый вариант. */
  approved_image_asset_id?: string | null;
  provenance?: ProvenanceT;
  character_actions?: {
    character_id?: string;
    character_name?: string;
    action?: string;
    emotion?: string;
    timing?: string;
  }[];
  environment_actions?: { element?: string; action?: string; intensity?: string }[];
};

export type ScenarioT = {
  scenario_id?: string;
  title?: string;
  synopsis?: string;
  total_duration_sec?: number;
  direction_notes?: string;
  shots?: ScenarioShotT[];
  /** Происхождение данных сценария (связь с описательной системой/Pulse). */
  provenance?: ProvenanceT[];
};

export type ReferenceT = {
  asset_id: string;
  session_id?: string;
  description: string;
  source_type?: string;
  created_at?: string;
};

export type StudioVersionT = {
  version_id: string;
  session_id: string;
  version_number: number;
  image_description: MediaPlanT | null;
  video_description: MediaPlanT | null;
  video_scenario: ScenarioT | null;
  parent_version_id: string | null;
  derivation: string;
  is_active: boolean;
  is_final: boolean;
  created_by: string;
  created_at: string;
  note: string;
};

export type SessionDetailT = {
  session: StudioSessionT;
  versions: StudioVersionT[];
  messages: { message_id: string; role: string; content: string; created_at: string }[];
  references: ReferenceT[];
};

// ── Единый визуальный язык фильма (art direction) ──────────────

export type ArtDirectionCharacterT = {
  knowledge_key: string;
  name: string;
  approved_image_asset_id?: string | null;
  note?: string;
};

export type ArtDirectionLocationT = {
  knowledge_key: string;
  name: string;
  palette?: string[];
  reference_asset_id?: string | null;
  note?: string;
};

export type ArtDirectionT = {
  ad_id: string;
  revision: number;
  updated_at?: string;
  updated_by?: string;
  style_preset: string;
  style_prompt?: string;
  palette?: string[];
  aspect_ratio?: string | null;
  composition_rules?: string[];
  lighting_rules?: string[];
  negative_rules?: string[];
  characters?: ArtDirectionCharacterT[];
  locations?: ArtDirectionLocationT[];
  reference_asset_ids?: string[];
  last_change_sections?: string[];
};

export type AdLibraryT = {
  styles: Record<
    string,
    { prefix?: string; aspect_ratio?: string; description?: string; negative_additions?: string[] }
  >;
  characters: Record<
    string,
    { name?: string; build?: string; face?: string; style_constants?: string[] }
  >;
  locations: Record<string, { name?: string; type?: string; palette?: string[]; atmosphere?: string }>;
};

/** Какие общие правила реально применяются к плану (снимок для показа). */
export type AppliedRulesT = {
  style_preset: string;
  style_prompt: string;
  palette: string[];
  aspect_ratio: string;
  composition_rules: string[];
  lighting_rules: string[];
  negative_rules: string[];
  preset_negative_additions: string[];
  characters: ArtDirectionCharacterT[];
  location: ArtDirectionLocationT | null;
  reference_asset_ids: string[];
  revision: number;
};

export type AppliedShotT = {
  shot_index: number;
  shot_id: string;
  order: number;
  shot_type: string;
  duration_sec: number;
  /** Утверждённый кадр плана (из сценария). */
  approved_image_asset_id?: string | null;
  applied: AppliedRulesT;
  /** Что задано локально в шоте (перебивает общие правила). */
  local_overrides: Record<string, unknown>;
  resolved_prompt: string;
  resolved_negative: string[];
};

/** Статус кадра в цикле управляемого обновления. */
export type FrameStatusT =
  | 'current' // актуален
  | 'needs_update' // требует обновления
  | 'prepared_for_update' // подготовлен к обновлению
  | 'new_variant' // новый вариант (получен, не утверждён)
  | 'approved'; // утверждён

export type PreparedBriefT = {
  prepared_id: string;
  status: string;
  new_asset_id?: string | null;
};

export type AffectedArtifactT = {
  asset_id: string;
  asset_type: string;
  title: string;
  status: string;
  reasons: string[];
  created_at?: string;
  /** Промпт, с которым кадр реально сгенерирован (для сравнения). */
  prompt_used?: string;
  /** Привязка кадра к плану сценария (generation.shot_id). */
  shot_id?: string | null;
  /** Контекст шота: применённые правила + локальные + итоговый промпт. */
  shot?: AppliedShotT | null;
  /** Статус кадра в цикле обновления (FrameStatusT). */
  frame_status?: string;
  /** Подготовленное задание по этому кадру (если есть). */
  prepared?: PreparedBriefT | null;
};

/** Подготовленное задание на обновление кадра (черновик, без генерации). */
export type PreparedUpdateT = {
  prepared_id: string;
  session_id: string;
  shot_id: string;
  source_asset_id?: string | null;
  new_prompt: string;
  negative_prompt: string[];
  motion_prompt?: string;
  applied_rules: Record<string, unknown>;
  reference_asset_ids: string[];
  backend: string;
  workflow: string;
  expected_result_type: string;
  status: 'prepared' | 'generating' | 'done' | 'approved' | 'cancelled';
  new_asset_id?: string | null;
  created_at?: string;
  updated_at?: string;
};

/** Справочник исполнителя изображений (доступность/требования — для выбора). */
export type ExecutorInfoT = {
  label: string;
  execution: string;
  execution_label: string;
  available: boolean;
  why: string;
  requirements: string;
  workflow: string;
};

/** Видео, снятое со старого кадра (требует обновления после approve). */
export type StaleVideoT = {
  asset_id: string;
  title: string;
  reference_image_id: string;
  current_approved: string;
  reason: string;
};

export type ArtDirectionApplyT = {
  art_direction: ArtDirectionT;
  scene: {
    scene_id: string;
    chapter: number;
    title: string;
    location: string;
    characters: string[];
    approved_image_asset_id: string | null;
  };
  episode: {
    shot_count: number;
    total_duration_sec: number;
    style_label: string;
    revision: number;
    last_change_sections: string[];
  };
  shots: AppliedShotT[];
  affected_artifacts: AffectedArtifactT[];
  /** Подготовленные задания обновления кадров (все статусы). */
  prepared_updates?: PreparedUpdateT[];
  /** Видео на предыдущем кадре (связь video → input image сохраняется). */
  stale_videos?: StaleVideoT[];
};

export type GenerationInfo = {
  provider?: string;
  model?: string;
  plan_id?: string | null;
  backend?: string | null;
  workflow_used?: string | null;
  media_id?: string | null;
  size?: string | null;
  /** Привязка кадра к плану сценария (шот). */
  shot_id?: string | null;
  /** Кадр, ФАКТИЧЕСКИ переданный исполнителю (i2v), а не просто выбранный. */
  reference_image_id?: string | null;
  /** sha256 байтов переданного кадра — связь видео ↔ исходному кадру. */
  input_image_sha256?: string | null;
  /** Ревизия общих правил фильма на момент генерации (art direction). */
  art_direction_revision?: number | null;
};

export type JobAsset = {
  asset_id: string;
  asset_type: string;
  chapter: number;
  scene_id: string;
  title: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  file_path: string | null;
  error: string | null;
  duration_sec?: number;
  fps?: number;
  prompt_used?: string;
  created_at?: string;
  generation?: GenerationInfo;
};

export const IMAGE_EXECUTORS = [
  { value: 'agnes', label: 'agnes — бесплатная интеграция Agnes' },
  { value: 'mock', label: 'mock — тестовые ответы (без трат)' },
  { value: 'auto', label: 'auto — авто-выбор исполнителя' },
];

export const VIDEO_EXECUTORS = [
  { value: 'mock', label: 'mock — тестовые ответы (без трат)' },
  { value: 'auto', label: 'auto — авто-выбор исполнителя' },
  { value: 'comfyicu', label: 'comfyicu — облачный LTX 2.5 (кредиты)' },
];

/** Параметры клипа (разрешение кадра) для панели подготовки видео. */
export const VIDEO_SIZES = [
  { value: '1024x576', label: '1024×576 — горизонтальный' },
  { value: '576x1024', label: '576×1024 — вертикальный' },
  { value: '1024x1024', label: '1024×1024 — квадрат' },
];

// ── История экспериментов ─────────────────────────────────

export type ExperimentStatus = 'experimental' | 'candidate' | 'approved' | 'used' | 'archived';

export type ExperimentGroup = {
  shot_id: string | null;
  total: number;
  by_status: Partial<Record<ExperimentStatus, number>>;
};

export type ExperimentT = JobAsset & {
  experiment_status?: string | null;
};

export type ExperimentsListT = {
  experiments: ExperimentT[];
  total: number;
  limit: number;
  offset: number;
  groups: ExperimentGroup[];
};

export const EXPERIMENT_STATUS_LABELS: Record<ExperimentStatus, string> = {
  experimental: 'эксперимент',
  candidate: 'кандидат',
  approved: 'утверждён',
  used: 'используется',
  archived: 'архив',
};

export const EXPERIMENT_STATUS_COLORS: Record<ExperimentStatus, string> = {
  experimental: 'default',
  candidate: 'processing',
  approved: 'success',
  used: 'success',
  archived: 'warning',
};

export const EXPERIMENT_STATUSES: ExperimentStatus[] = [
  'experimental',
  'candidate',
  'approved',
  'used',
  'archived',
];

export const STATUS_COLORS: Record<string, 'default' | 'processing' | 'success' | 'error'> = {
  pending: 'default',
  generating: 'processing',
  completed: 'success',
  failed: 'error',
};

export const STATUS_LABELS: Record<string, string> = {
  pending: 'ожидание',
  generating: 'выполняется',
  completed: 'готово',
  failed: 'ошибка',
};

export function assetFileUrl(assetId: string): string {
  return `/book/assets/${assetId}/file`;
}

// ── Дерево фильма (Фаза 0): эпизод → сцена → план ─────────────

export type FilmShotT = {
  shot_id: string;
  order: number;
  index: number;
  shot_type: string;
  duration_sec: number;
  transition_to_next: string;
  approved_image_asset_id: string | null;
  has_video: boolean;
  video_asset_id: string | null;
};

export type FilmSceneStatus = 'no_session' | 'prompts' | 'frame_approved' | 'video';

export type FilmSceneT = {
  scene_id: string;
  chapter: number;
  index_in_episode: number;
  order_global: number;
  title: string;
  location: string;
  characters: string[];
  emotion: string;
  visual_style_hint: string;
  has_session: boolean;
  session_id: string | null;
  session_status: SessionStatus | null;
  approved_image_asset_id: string | null;
  shot_count: number;
  total_duration_sec: number;
  video_count: number;
  has_video: boolean;
  status: FilmSceneStatus;
  shots: FilmShotT[];
};

export type FilmEpisodeT = {
  episode_id: string;
  chapter: number;
  title: string;
  scene_count: number;
  total_duration_sec: number;
  scenes: FilmSceneT[];
};

export type FilmT = {
  film: {
    book_id: string;
    title: string;
    episode_count: number;
    scene_count: number;
    total_duration_sec: number;
  };
  episodes: FilmEpisodeT[];
};

export const FILM_SCENE_STATUS_LABELS: Record<FilmSceneStatus, string> = {
  no_session: 'нет рабочей области',
  prompts: 'промпты',
  frame_approved: 'кадр утверждён',
  video: 'видео',
};

export const FILM_SCENE_STATUS_COLORS: Record<FilmSceneStatus, string> = {
  no_session: 'default',
  prompts: 'processing',
  frame_approved: 'success',
  video: 'success',
};

/** Плоский список сцен из дерева фильма (для выбора/панелей). */
export function scenesFromFilm(film: FilmT | null | undefined): Scene[] {
  if (!film || !Array.isArray(film.episodes)) return [];
  return film.episodes.flatMap((ep) =>
    (ep.scenes || []).map((s) => ({ scene_id: s.scene_id, chapter: s.chapter, title: s.title })),
  );
}

// ── Связность (Continuity, Фаза 1): планы, сцены, эпизоды ─────

export type ContinuityFindingT = {
  field: string;
  kind: string; // difference | change
  severity: string; // warning | info
  message: string;
  subject: string;
  from_value: string;
  to_value: string;
  certainty: string; // confirmed | candidate
  sources: string[];
};

export type ContinuityDecisionT = {
  decision_id: string;
  link_key: string;
  session_id: string;
  action: string;
  note: string;
  by: string;
  basis: Record<string, unknown>;
  stale: boolean;
  constraints: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ContinuityCharacterStubT = {
  character_id: string;
  name: string;
  appearance: string;
  clothing: string;
  approved_image_asset_id: string | null;
  sources: string[];
};

export type ShotContinuitySnapshotT = {
  shot_id: string;
  order: number;
  shot_type: string;
  lighting_note: string;
  mood_note: string;
  style_override: string;
  palette_override: string[];
  approved_image_asset_id: string | null;
  character_ids: string[];
  character_names: string[];
  environment_elements: string[];
};

export type ClipBoundaryContractT = {
  previous_clip_asset_id: string | null;
  end_frame_asset_id: string | null;
  next_clip_asset_id: string | null;
  start_frame_asset_id: string | null;
  status: string; // unknown | declared
  note: string;
};

export type SceneContinuitySnapshotT = {
  scene_id: string;
  chapter: number;
  order_global: number;
  title: string;
  location: string;
  location_reference_asset_id: string | null;
  time_of_day: string;
  season: string;
  weather: string;
  lighting_direction: string;
  lighting_color: string;
  palette: string[];
  visual_style: string;
  emotion: string;
  characters: ContinuityCharacterStubT[];
  approved_image_asset_id: string | null;
  has_session: boolean;
  session_id: string | null;
  has_scenario: boolean;
  shot_count: number;
  shots: ShotContinuitySnapshotT[];
  art_direction_revision: number;
  known_fields: string[];
  provenance: Record<string, string>;
};

export type ContinuityLinkT = {
  link_id: string;
  link_key: string;
  relation: string;
  certainty: string; // confirmed | candidate
  from_ref: string;
  to_ref: string;
  from_scene_id: string;
  to_scene_id: string;
  status: string;
  findings: ContinuityFindingT[];
  reason: string;
  decision: ContinuityDecisionT | null;
  clip_boundary: ClipBoundaryContractT | null;
  basis: Record<string, unknown>;
};

export type SceneContinuityReportT = {
  scene: SceneContinuitySnapshotT;
  links: ContinuityLinkT[];
  overall_status: string;
  limitations: string[];
  neighbors: { prev_scene_id: string | null; next_scene_id: string | null };
  episode: { chapter: number; index_in_episode: number; scene_count: number };
};

export type ContinuitySummaryEntryT = {
  overall_status: string;
  mismatch_count: number;
  waived_count: number;
  pending_count: number;
  link_count: number;
};

export type ContinuitySummaryT = {
  scenes: Record<string, ContinuitySummaryEntryT>;
  with_context: boolean;
};

export type MatchContextPromptChangeT = {
  shot_id: string;
  changed: boolean;
  before: string;
  after: string;
};

export type MatchContextT = {
  available: boolean;
  reason?: string;
  from_scene_id?: string;
  to_scene_id?: string;
  constraints?: Record<string, unknown>;
  sources?: Record<string, string>;
  remaining_differences?: ContinuityFindingT[];
  prompt_changes?: MatchContextPromptChangeT[];
  applied?: boolean;
  applied_stale?: boolean;
  applied_decision?: ContinuityDecisionT | null;
  note?: string;
  limitations?: string[];
};

export const CONTINUITY_STATUS_LABELS: Record<string, string> = {
  unchecked: 'проверка не выполнена',
  mismatch: 'есть потенциальное несоответствие',
  consistent: 'согласовано',
  waived: 'отличие разрешено режиссёром',
};

export const CONTINUITY_STATUS_COLORS: Record<string, string> = {
  unchecked: 'default',
  mismatch: 'warning',
  consistent: 'success',
  waived: 'processing',
};

export const CONTINUITY_RELATION_LABELS: Record<string, string> = {
  shots_within_scene: 'Соседние планы одной сцены',
  scene_boundary_shots: 'Граница сцен (последний план → первый план)',
  adjacent_scenes: 'Соседние сцены эпизода',
  cross_episode: 'Смысловая связь разных эпизодов',
};

export const CONTINUITY_FIELD_LABELS: Record<string, string> = {
  location: 'локация',
  time_of_day: 'время суток',
  weather: 'погода',
  season: 'сезон',
  lighting: 'свет',
  palette: 'палитра',
  style: 'стиль',
  visual_style: 'визуальный стиль',
  character_appearance: 'внешность персонажа',
  character_approved_image: 'утверждённый образ',
};

// ── Story Reel (Фаза 3): Эпизод → Сцена → План → Кадр → Клип ──

export type ReelFrameStatus = 'approved' | 'none' | 'needs_update';

export type ReelClipStatus = 'none' | 'generating' | 'failed' | 'mock' | 'ready' | 'stale';

export type ReelFrameT = { status: ReelFrameStatus; asset_id: string | null };

export type ReelExecutorT = {
  provider?: string | null;
  backend?: string | null;
  workflow_used?: string | null;
  model?: string | null;
  media_id?: string | null;
};

export type ReelClipT = {
  status: ReelClipStatus;
  asset_id: string | null;
  mock: boolean;
  stale_reasons: string[];
  error?: string | null;
  executor?: ReelExecutorT;
  created_at?: string | null;
};

export type ReelLinkT = {
  status: string;
  relation: string;
  certainty: string;
  from_ref: string;
  to_ref: string;
  from_scene_id: string;
  to_scene_id: string;
  finding_count: number;
  findings: ContinuityFindingT[];
  decision: ContinuityDecisionT | null;
  reason: string;
};

export type ReelTransferT = {
  applied: boolean;
  stale: boolean;
  from_scene_id: string | null;
  note: string;
};

export type ReelShotT = {
  shot_id: string;
  order: number;
  index: number;
  shot_type: string;
  description: string;
  duration_sec: number;
  transition_to_next: string;
  frame: ReelFrameT;
  video: ReelClipT;
  resolved_prompt: string;
  continuity_next: ReelLinkT | null;
};

export type ReelSceneT = {
  scene_id: string;
  chapter: number;
  index_in_episode: number;
  order_global: number;
  title: string;
  location: string;
  characters: string[];
  has_session: boolean;
  session_id: string | null;
  session_status: SessionStatus | null;
  approved_image_asset_id: string | null;
  shot_count: number;
  total_duration_sec: number;
  continuity_from_prev_scene: ReelLinkT | null;
  transfer: ReelTransferT | null;
  shots: ReelShotT[];
  warnings: string[];
};

export type ReelSequenceItemT = {
  scene_id: string;
  chapter: number;
  index_in_episode: number;
  shot_id: string;
  shot_order: number;
  shot_index: number;
  kind: 'clip' | 'frame' | 'placeholder';
  frame_asset_id: string | null;
  clip_asset_id: string | null;
  clip_status: ReelClipStatus;
  duration_sec: number;
  transition_to_next: string;
  description: string;
};

export type ReelSummaryT = {
  scene_count: number;
  shot_count: number;
  clip_count: number;
  frame_count: number;
  placeholder_count: number;
  mock_count: number;
  stale_count: number;
  total_duration_sec: number;
};

export type ReelScope = 'scene' | 'sequence' | 'episode' | 'film';

export type ReelT = {
  scope: ReelScope;
  chapter: number | null;
  scene_ids: string[];
  film: { book_id: string; title: string; episode_count?: number };
  scenes: ReelSceneT[];
  sequence: ReelSequenceItemT[];
  summary: ReelSummaryT;
  limitations: string[];
};

export const REEL_FRAME_LABELS: Record<ReelFrameStatus, string> = {
  approved: 'кадр утверждён',
  none: 'кадр отсутствует',
  needs_update: 'кадр требует обновления',
};

export const REEL_FRAME_COLORS: Record<ReelFrameStatus, string> = {
  approved: 'success',
  none: 'default',
  needs_update: 'warning',
};

export const REEL_CLIP_LABELS: Record<ReelClipStatus, string> = {
  none: 'клип отсутствует',
  generating: 'клип создаётся',
  failed: 'ошибка создания клипа',
  mock: 'mock-клип (без реального видео)',
  ready: 'реальный клип',
  stale: 'клип устарел',
};

export const REEL_CLIP_COLORS: Record<ReelClipStatus, string> = {
  none: 'default',
  generating: 'processing',
  failed: 'error',
  mock: 'orange',
  ready: 'green',
  stale: 'warning',
};

export const REEL_KIND_LABELS: Record<ReelSequenceItemT['kind'], string> = {
  clip: 'клип',
  frame: 'кадр',
  placeholder: 'нет материала',
};

export const REEL_SCOPE_LABELS: Record<ReelScope, string> = {
  scene: 'сцена',
  sequence: 'последовательность сцен',
  episode: 'эпизод',
  film: 'весь фильм',
};

// ── План сборки последовательности (Фаза 4): тайминг · разрывы · ──
//    переходы · исполнители · текст плана. Read-only, без монтажа.  ──

export type SequenceSegmentKind = 'clip' | 'frame' | 'placeholder';

export type SequenceSegmentT = {
  index: number;
  scene_id: string;
  chapter: number;
  index_in_episode: number;
  shot_id: string;
  shot_order: number;
  shot_index: number;
  kind: SequenceSegmentKind;
  clip_status: ReelClipStatus;
  frame_status: ReelFrameStatus;
  mock: boolean;
  ready: boolean;
  duration_sec: number;
  start_sec: number;
  end_sec: number;
  transition_to_next: string;
  scene_boundary_after: boolean;
  clip_asset_id: string | null;
  frame_asset_id: string | null;
  executor?: ReelExecutorT | null;
  executor_key: string | null;
  executor_label: string | null;
  description: string;
};

export type SequenceAssembledT = {
  index: number;
  scene_id: string;
  chapter: number;
  shot_id: string;
  start_sec: number;
  end_sec: number;
  duration_sec: number;
  clip_asset_id: string | null;
  executor_label: string | null;
  transition_to_next: string;
};

export type SequenceGapT = {
  start_index: number;
  end_index: number;
  segment_count: number;
  start_sec: number;
  end_sec: number;
  duration_sec: number;
  kinds: SequenceSegmentKind[];
  scene_ids: string[];
  shot_ids: string[];
};

export type SequenceTransitionT = {
  index: number;
  from_shot_id: string;
  to_shot_id: string;
  transition: string;
  scene_boundary: boolean;
  from_ready: boolean;
  to_ready: boolean;
};

export type SequenceExecutorT = {
  key: string;
  label: string;
  count: number;
  duration_sec: number;
  shot_ids: string[];
};

export type SequenceSummaryT = {
  segment_count: number;
  scene_count: number;
  episode_count: number;
  clip_count: number;
  ready_count: number;
  frame_count: number;
  placeholder_count: number;
  mock_count: number;
  stale_count: number;
  assembled_count: number;
  gap_count: number;
  executor_count: number;
  total_duration_sec: number;
  assembled_duration_sec: number;
  gap_duration_sec: number;
};

export type SequencePlanT = {
  segments: SequenceSegmentT[];
  assembled: SequenceAssembledT[];
  gaps: SequenceGapT[];
  transitions: SequenceTransitionT[];
  executors: SequenceExecutorT[];
  executor_mixed: boolean;
  summary: SequenceSummaryT;
  limitations: string[];
  plan_text: string;
  edl_xml?: string | null;
  scope?: ReelScope;
  chapter?: number | null;
  scene_ids?: string[];
  film?: { book_id: string; title: string; episode_count?: number };
};

export const SEQUENCE_KIND_LABELS: Record<SequenceSegmentKind, string> = {
  clip: 'клип',
  frame: 'кадр',
  placeholder: 'нет материала',
};

export const SEQUENCE_KIND_COLORS: Record<SequenceSegmentKind, string> = {
  clip: 'green',
  frame: 'blue',
  placeholder: 'default',
};

/** Ответы бэкенда бывают и enveloped ({ok, data}), и прямыми — нормализуем. */
export function unwrapData<T>(resp: unknown): T {
  if (resp && typeof resp === 'object' && 'ok' in resp && 'data' in resp) {
    return (resp as { data: T }).data;
  }
  return resp as T;
}
