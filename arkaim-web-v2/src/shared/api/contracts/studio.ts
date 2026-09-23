/**
 * Studio API contracts — Phase 1B backend endpoints.
 *
 * Контракты:
 *   POST /studio/create?chapter=N&scene_id=S   → {session, version}
 *   GET  /studio/list?status=S                 → session[]
 *   GET  /studio/{session_id}                  → {session, versions, messages, references}
 *   POST /studio/{session_id}/discuss?message=M → {user_message, assistant_message}
 *   POST /studio/{session_id}/modify            → version
 *   POST /studio/{session_id}/variant?count=N   → version[]
 *   POST /studio/{session_id}/activate-version?version_id=V → ok
 *   POST /studio/{session_id}/upload-reference   → reference
 *   POST /studio/{session_id}/approve            → {status, version_id}
 *   POST /studio/{session_id}/reject?reason=R    → {status, reason}
 *   GET  /studio/{session_id}/export             → StudioExport
 */

export type StudioSessionStatus = 'draft' | 'discussing' | 'approved' | 'rejected' | 'sent';

export interface StudioSession {
  session_id: string;
  user_id: string;
  title: string;
  chapter: number;
  scene_id: string;
  context_type: string;
  active_version_id: string | null;
  status: StudioSessionStatus;
  reference_assets: string[];
  created_at: string;
  updated_at: string;
  finalized_at: string | null;
}

export interface StudioMessage {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_version_id: string | null;
  created_at: string;
}

export interface UserModification {
  target: string;
  field_path: string;
  old_value: string;
  new_value: string;
  reason: string;
  timestamp?: string;
}

export interface MediaPlanSummary {
  media_kind: string;
  prompt: string;
  atmosphere?: string;
  visual_style?: string;
  duration_sec?: number;
  fps?: number;
}

export interface ScenarioShotSummary {
  shot_id: string;
  order: number;
  shot_type: string;
  description: string;
  duration_sec?: number;
  camera_action?: string;
  camera_angle?: string;
}

export interface VideoScenarioSummary {
  scenario_id: string;
  scene_id: string;
  title: string;
  synopsis: string;
  total_duration_sec: number;
  shots: ScenarioShotSummary[];
  direction_notes?: string;
}

export interface StudioVersion {
  version_id: string;
  session_id: string;
  version_number: number;
  image_description: MediaPlanSummary | null;
  video_description: MediaPlanSummary | null;
  video_scenario: VideoScenarioSummary | null;
  parent_version_id: string | null;
  derivation: string;
  user_modifications: UserModification[];
  is_active: boolean;
  is_final: boolean;
  created_by: string;
  created_at: string;
  note: string;
}

export interface ReferenceAsset {
  asset_id: string;
  session_id: string;
  description: string;
  source_type: string;
  created_at: string;
}

export interface StudioExport {
  session_id: string;
  export_id: string;
  image_description: MediaPlanSummary | null;
  video_description: MediaPlanSummary | null;
  video_scenario: VideoScenarioSummary | null;
  references: { asset_id: string; description: string; file_url: string }[];
  version_lineage: string[];
  exported_at: string;
}
