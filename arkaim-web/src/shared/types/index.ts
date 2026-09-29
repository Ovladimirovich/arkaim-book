/**
 * РћР±С‰РёРµ TypeScript С‚РёРїС‹ РґР»СЏ Arkaim Digital Consciousness.
 */

// в”Ђв”Ђ Auth в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export type UserRole = 'reader' | 'editor' | 'admin';

export interface User {
  id: string;
  role: UserRole;
  username?: string;
  display_name?: string;
  provider: string;
  provider_user_id?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Session {
  id: string;
  user_id: string;
  expires_at: string;
  created_at: string;
}

export interface ApiKey {
  id: string;
  user_id: string;
  key_prefix: string;
  name?: string;
  last_used_at?: string;
  is_active: boolean;
  created_at: string;
}

export interface Invite {
  id: string;
  token: string;
  url: string;
  created_by: string;
  role: UserRole;
  max_uses: number;
  use_count: number;
  expires_at?: string;
  is_active: boolean;
  created_at: string;
  note?: string;
}

// в”Ђв”Ђ Book в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export interface Genome {
  themes: Theme[];
  characters: Character[];
  values: Value[];
  world_entities: WorldEntity[];
  author_intent: Record<string, unknown>;
}

export interface Theme {
  name: string;
  description?: string;
}

export interface Character {
  id: string;
  name: string;
  role?: string;
  description?: string;
}

export interface Value {
  name: string;
  description?: string;
}

export interface WorldEntity {
  id: string;
  name: string;
  type?: string;
}

export interface BookLayers {
  knowledge_layer: string;
  meaning_layer: string;
  identity_layer: string;
  mission_layer: string;
}

// в”Ђв”Ђ Reader в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export interface ReaderProfile {
  reader_id: string;
  display_name: string;
  questions_total: number;
  conversation_count: number;
  last_topic: string;
  topics: ReaderTopic[];
}

export interface ReaderTopic {
  name: string;
  depth: number;
  questions: number;
}

export interface HistoryItem {
  id: number;
  session_id: string;
  content: string;
  created_at: string;
}

export interface HistoryStats {
  questions: number;
  sessions: number;
  last_active: string | null;
}

// в”Ђв”Ђ Messages в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

// в”Ђв”Ђ Visual в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export interface VisualScene {
  chapter: number;
  scene_id: string;
  title: string;
  characters: string[];
  location: string;
  emotion: string;
  meaning_tags: string[];
  color_palette?: string[];
}

export interface VisualCharacter {
  character_id: string;
  name: string;
  archetype?: string;
  color_palette: string[];
  visual_description: string;
}

export interface VisualLocation {
  location_id: string;
  name: string;
  atmosphere?: string;
  architecture?: string;
  lighting?: string;
}

// в”Ђв”Ђ Crowdfunding в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export interface Campaign {
  id: string;
  platform: string;
  url: string;
  title: string;
  target_amount: number;
  current_amount: number;
  backers_count: number;
  days_left: number;
  milestones: Milestone[];
}

export interface Milestone {
  id: string;
  title: string;
  target_amount: number;
  reached: boolean;
}

// в”Ђв”Ђ Admin в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export interface AdminStats {
  users: {
    total: number;
    by_role: Record<UserRole, number>;
  };
  reader_memory: Record<string, unknown>;
  presence: {
    trending_topics: number;
    pending_suggestions: number;
  };
  email: Record<string, unknown>;
}

// в”Ђв”Ђ Suggestions в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export interface Suggestion {
  id: string;
  topic: string;
  reason?: string;
  suggested_action?: string;
  status: 'pending' | 'approved' | 'rejected';
}

// в”Ђв”Ђ WebSocket Events в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

export type WsEvent =
  | 'pulse_beat'
  | 'new_suggestion'
  | 'service_status'
  | 'new_question'
  | 'your_question_answered'
  | 'chat_response'
  | 'crowdfunding_milestone';

// ── Narrative Engine (World Model + Story Engine) ──────

export type SourceLevel =
  | 'CANON'
  | 'AUTHOR_INTERPRETATION'
  | 'HISTORICAL'
  | 'MYTHOLOGICAL'
  | 'SCIENTIFIC'
  | 'SYSTEM_INTERPRETATION'
  | 'USER_HYPOTHESIS';

export interface ProvenanceTag {
  source_level: SourceLevel;
  source_url?: string;
  source_title?: string;
  confidence: number;
  added_at: string;
  added_by: string;
  notes?: string;
}

export interface Epoch {
  id: string;
  name: string;
  name_ru: string;
  description: string;
  order: number;
  duration_years?: number;
  technologies_available: string[];
  civilizations_active: string[];
  source_level: SourceLevel;
  provenance: ProvenanceTag[];
}

export interface WorldLocation {
  id: string;
  name: string;
  name_ru: string;
  type: string;
  description: string;
  coordinates?: { lat: number; lng: number };
  epochs_present: string[];
  related_entities: string[];
  source_level: SourceLevel;
  provenance: ProvenanceTag[];
}

export interface Civilization {
  id: string;
  name: string;
  name_ru: string;
  description: string;
  epochs: string[];
  values: string[];
  technologies: string[];
  source_level: SourceLevel;
}

export interface Technology {
  id: string;
  name: string;
  name_ru: string;
  description: string;
  epoch_first?: string;
  source_level: SourceLevel;
}

export interface CharacterPresence {
  character_name: string;
  epoch: string;
  location_id?: string;
  status: 'alive' | 'awakened' | 'departed' | 'mythic';
  notes: string;
  source_level: SourceLevel;
}

export interface CanonicalEvent {
  id: string;
  title: string;
  title_ru: string;
  description: string;
  epoch: string;
  location_id?: string;
  characters_involved: string[];
  chapter?: number;
  order_in_epoch: number;
  source_level: SourceLevel;
}

export interface CausalRule {
  id: string;
  description: string;
  rule_type: 'prerequisite' | 'exclusion' | 'dependency';
  condition: string;
  source_level: SourceLevel;
}

export interface WorldModel {
  version: string;
  updated_at: string;
  epochs: Epoch[];
  locations: WorldLocation[];
  civilizations: Civilization[];
  technologies: Technology[];
  canonical_events: CanonicalEvent[];
  causal_rules: CausalRule[];
  characters_living: Record<string, CharacterPresence[]>;
}

export interface StoryRequest {
  prompt: string;
  epoch?: string;
  location?: string;
  character_type?: string;
  max_length?: number;
  style?: 'literary' | 'documentary' | 'poetic';
}

export interface ResolvedContext {
  epoch?: Epoch;
  location?: WorldLocation;
  characters_alive: CharacterPresence[];
  technologies_available: Technology[];
  applicable_rules: CausalRule[];
}

export interface ConstraintModel {
  story_request: StoryRequest;
  resolved_context: ResolvedContext;
  hard_constraints: string[];
  soft_constraints: string[];
  forbidden_elements: string[];
  required_elements: string[];
}

export interface GeneratedStory {
  id: string;
  text: string;
  word_count: number;
  constraints: ConstraintModel;
  validation: {
    passed: boolean;
    violations: Array<{ rule_id: string; rule_text: string; severity: string }>;
    warnings: string[];
  };
}

// --- Film Studio ---

export type ProjectStatus = 'draft' | 'generating' | 'assembling' | 'complete' | 'failed';
export type ShotStatus = 'pending' | 'generating' | 'completed' | 'failed';

export interface FilmProject {
  id: string;
  title: string;
  description: string;
  status: ProjectStatus;
  style: string;
  mood: string;
  aspect_ratio: string;
  fps: number;
  scenes: SceneShot[];
  output_path: string | null;
  output_duration_sec: number;
  created_at: string;
  updated_at: string;
}

export interface FilmProjectSummary {
  id: string;
  title: string;
  status: ProjectStatus;
  scene_count: number;
  shot_count: number;
  completed_shots: number;
  total_duration_sec: number;
  created_at: string;
  updated_at: string;
}

export interface SceneShot {
  id: string;
  scene_id: string;
  order: number;
  prompt_override: string;
  camera: CameraSpec;
  duration_sec: number;
  versions: ShotVersion[];
  active_version_id: string | null;
}

export interface ShotVersion {
  id: string;
  asset_id: string | null;
  prompt: string;
  camera: CameraSpec;
  duration_sec: number;
  negative_prompt: string[];
  status: ShotStatus;
  error: string | null;
  is_active: boolean;
  quality: string;
  created_at: string;
}

export interface CameraSpec {
  shot_type: string;
  angle: string;
  motion: string;
}

// --- World Engine ---

export interface WorldEntity {
  id: string;
  name: string;
  category: string;
  description: string;
  properties: Record<string, unknown>;
  relations: WorldRelation[];
}

export interface WorldRelation {
  target_id: string;
  type: string;
  weight: number;
}

export interface WorldSummary {
  total_entities: number;
  total_relations: number;
  categories: Record<string, number>;
}

// --- Visual Assets ---

export type AssetType = 'image' | 'video';
export type AssetStatus = 'pending' | 'generating' | 'completed' | 'failed';

export interface VisualAsset {
  asset_id: string;
  asset_type: AssetType;
  chapter: number;
  scene_id: string;
  title: string;
  mood: string;
  style: string;
  status: AssetStatus;
  file_path: string | null;
  thumbnail_path: string | null;
  prompt_used: string;
  created_at: string;
}

// --- Expansion Layer ---

export interface ExpansionTopic {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
}
