/**
 * shared/api/studio.ts — Studio API functions.
 *
 * Studio API routed through /api/studio to avoid conflict with /studio page route.
 * /api/* rewrite forwards to backend in next.config.ts.
 */

import { apiCall } from './client';
import type {
  StudioSession,
  StudioVersion,
  StudioMessage,
  ReferenceAsset,
  StudioExport,
} from './contracts/studio';

const BASE = '/api/studio';

// ── 0. Available scenes ───────────────────────────────────────

export function listStudioScenes(): Promise<Array<{ scene_id: string; chapter: number; title: string }>> {
  return apiCall('GET', `${BASE}/scenes`);
}

// ── 1. Create session ──────────────────────────────────────────

export function createStudioSession(chapter: number, scene_id: string): Promise<{ session: StudioSession; version: StudioVersion }> {
  return apiCall('POST', `${BASE}/create?chapter=${chapter}&scene_id=${encodeURIComponent(scene_id)}`);
}

// ── 2. List sessions ───────────────────────────────────────────

export function listStudioSessions(params?: { status?: string; limit?: number; offset?: number }): Promise<StudioSession[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.offset) qs.set('offset', String(params.offset));
  const query = qs.toString();
  return apiCall('GET', `${BASE}/list${query ? '?' + query : ''}`);
}

// ── 3. Get session ─────────────────────────────────────────────

export function getStudioSession(sessionId: string): Promise<{
  session: StudioSession;
  versions: StudioVersion[];
  messages: StudioMessage[];
  references: ReferenceAsset[];
}> {
  return apiCall('GET', `${BASE}/${sessionId}`);
}

// ── 4. Discuss ─────────────────────────────────────────────────

export function studioDiscuss(sessionId: string, message: string): Promise<{
  user_message: StudioMessage;
  assistant_message: StudioMessage;
}> {
  return apiCall('POST', `${BASE}/${sessionId}/discuss?message=${encodeURIComponent(message)}`);
}

// ── 5. Modify ──────────────────────────────────────────────────

export function studioModify(sessionId: string, params: {
  target: string;
  field_path: string;
  new_value: string;
  note?: string;
}): Promise<StudioVersion> {
  const qs = new URLSearchParams({
    target: params.target,
    field_path: params.field_path,
    new_value: params.new_value,
  });
  if (params.note) qs.set('note', params.note);
  return apiCall('POST', `${BASE}/${sessionId}/modify?${qs.toString()}`);
}

// ── 6. Create variants ─────────────────────────────────────────

export function studioCreateVariants(sessionId: string, count: number, notes?: string): Promise<StudioVersion[]> {
  const qs = new URLSearchParams({ count: String(count) });
  if (notes) qs.set('notes', notes);
  return apiCall('POST', `${BASE}/${sessionId}/variant?${qs.toString()}`);
}

// ── 7. Activate version ────────────────────────────────────────

export function studioActivateVersion(sessionId: string, versionId: string): Promise<{ activated: string }> {
  return apiCall('POST', `${BASE}/${sessionId}/activate-version?version_id=${encodeURIComponent(versionId)}`);
}

// ── 8. Upload reference ────────────────────────────────────────

export async function studioUploadReference(sessionId: string, file: File, description?: string): Promise<ReferenceAsset> {
  const formData = new FormData();
  formData.append('file', file);
  if (description) formData.append('description', description);

  const res = await fetch(`${BASE}/${sessionId}/upload-reference`, {
    method: 'POST',
    body: formData,
    credentials: 'same-origin',
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message || `Upload failed: ${res.status}`);
  }
  const envelope = await res.json();
  return envelope?.data ?? envelope;
}

// ── 9. Approve ─────────────────────────────────────────────────

export function studioApprove(sessionId: string, versionId?: string): Promise<{ status: string; version_id: string }> {
  const qs = versionId ? `?version_id=${encodeURIComponent(versionId)}` : '';
  return apiCall('POST', `${BASE}/${sessionId}/approve${qs}`);
}

// ── 10. Reject ─────────────────────────────────────────────────

export function studioReject(sessionId: string, reason?: string): Promise<{ status: string; reason: string }> {
  const qs = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  return apiCall('POST', `${BASE}/${sessionId}/reject${qs}`);
}

// ── 11. Export ─────────────────────────────────────────────────

export function studioExport(sessionId: string): Promise<StudioExport> {
  return apiCall('GET', `${BASE}/${sessionId}/export`);
}

// ── 12. Delete session ─────────────────────────────────────────

export function deleteStudioSession(sessionId: string): Promise<{ deleted: string }> {
  return apiCall('DELETE', `${BASE}/${sessionId}`);
}
