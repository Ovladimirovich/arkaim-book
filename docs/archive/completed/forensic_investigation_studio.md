# Forensic Investigation Report: Arkaim Frontend-v2 Architecture for Studio Feature

**Date:** 2026-09-14  
**Investigator:** AI Agent (DSH)  
**Objective:** Analyze existing frontend-v2 architecture, API contracts, and ADR documents to assess readiness for future "Studio" feature

---

## Executive Summary

### What was the goal?
To investigate the existing frontend-v2 architecture, API contracts, and ADR documents to determine what patterns, components, and infrastructure can be reused for a future "Studio" feature.

### What was actually done?
- Examined 12+ key files across frontend-v2, backend, and documentation
- Analyzed navigation structure, API envelope patterns, contract files, and RBAC implementation
- Reviewed 7 ADR documents relevant to media/studio features
- Checked backend routes structure and existing Film Studio implementation
- Mapped the complete frontend-v2 architecture patterns

### What was found?
**PASS** — The frontend-v2 architecture is well-structured with clear patterns that can be reused for Studio. The project has:
- Complete typed API contract layer with envelope pattern
- Role-based navigation structure with Studio group already defined
- Existing Film Studio backend implementation (13+ endpoints)
- Media boundary ADR establishing clear separation of concerns
- Consistent FSD (Feature-Sliced Design) architecture

### Are there problems?
**PARTIAL** — Key gaps identified:
1. **No frontend Studio pages** in arkaim-web-v2 (only navigation placeholder)
2. **No Studio-specific contracts** in frontend-v2 (only backend endpoints exist)
3. **No Studio UI components** (widgets, entities, hooks)
4. **No Studio job-tracker** pattern implemented in frontend-v2

### What is proposed next?
1. Use existing patterns from World Explorer as template for Studio pages
2. Create Studio-specific contracts based on existing backend Film Studio endpoints
3. Implement Studio widgets following the established widget pattern
4. Add Studio job-tracker for async generation tasks

---

## Detailed Investigation Results

### 1. Frontend-v2 Architecture Analysis

#### 1.1 Navigation Structure (`arkaim-web-v2/src/shared/rbac/navigation.ts`)

**What it contains:**
- **6 navigation groups**: book, studio, proposals, community, personal, admin
- **Studio group already defined** with 4 items: assets, film, upload, story
- **Role-based filtering**: `navForRole()` function filters by role
- **Roles defined**: reader (0), editor (1), admin (2)
- **Studio group roles**: editor + admin only (`E: readonly Role[] = ['editor', 'admin']`)

**Key patterns:**
```typescript
export interface NavItem {
  key: string;
  label: string;
  icon?: string;
  href?: string;
  roles: readonly Role[];
  comingSoon?: boolean;
  contractPath?: string;
}

export interface NavGroup {
  key: string;
  label: string;
  roles: readonly Role[];
  items: NavItem[];
}
```

**What can be reused for Studio:**
- ✅ **Studio group already exists** in navigation structure
- ✅ **Role-based filtering** works for editor/admin roles
- ✅ **comingSoon flag** pattern for placeholder items
- ✅ **contractPath** field links to backend endpoints
- ✅ **NavItem interface** can be extended for Studio-specific fields

**What's missing for Studio:**
- ❌ **No actual Studio pages** (all items marked `comingSoon: true`)
- ❌ **No Studio-specific icons** defined
- ❌ **No Studio route handlers** in Next.js app router

#### 1.2 API Envelope Pattern (`arkaim-web-v2/src/shared/api/envelope.ts`)

**What it contains:**
- **Two response conventions**: `enveloped` and `direct`
- **Envelope map**: `ENVELOPE_MAP` with 40+ endpoint configurations
- **Template matching**: Handles path parameters like `{epoch_id}`
- **Unwrap function**: `unwrap<T>()` extracts data from envelope

**Envelope types:**
```typescript
export type Envelope = 'enveloped' | 'direct';

// Enveloped: {"ok": true, "data": <payload>, "trace_id"?: ...}
// Direct: <raw payload> without envelope
```

**Studio-relevant endpoints already mapped:**
- `POST /book/world-explorer/explore` → enveloped
- `POST /book/world-explorer/validate` → enveloped  
- `GET /book/world-explorer/epochs` → enveloped
- Film Studio endpoints (from backend) → not yet mapped

**What can be reused for Studio:**
- ✅ **Envelope pattern** for all new Studio endpoints
- ✅ **Template matching** for Studio paths with parameters
- ✅ **unwrap function** for consistent data extraction
- ✅ **ENVELOPE_MAP** can be extended with Studio endpoints

**What's missing for Studio:**
- ❌ **Film Studio endpoints not mapped** in ENVELOPE_MAP
- ❌ **Studio-specific error handling** patterns
- ❌ **Job status endpoint mapping** for async operations

#### 1.3 API Contracts Layer (`arkaim-web-v2/src/shared/api/contracts/`)

**What it contains:**
- **7 contract files**: auth, book, reader, temporal, world, worldExplorer, knowledge
- **Typed functions**: Each contract exports typed API functions
- **Consistent pattern**: All follow same structure

**Example contract pattern (worldExplorer.ts):**
```typescript
// Types
export interface ExplorationResult { ... }
export interface CompatibilityResult { ... }

// API functions
export async function exploreWorld(req: ExploreRequest): Promise<ExplorationResult> {
  return apiCall('POST', '/book/world-explorer/explore', { body: req });
}

export async function validateIdea(req: ValidateRequest): Promise<CompatibilityResult> {
  return apiCall('POST', '/book/world-explorer/validate', { body: req });
}
```

**What can be reused for Studio:**
- ✅ **Contract file pattern** for Studio-specific contracts
- ✅ **Type definition pattern** for Studio interfaces
- ✅ **API function pattern** for Studio endpoints
- ✅ **Barrel export** in `index.ts` for Studio contracts

**What's missing for Studio:**
- ❌ **No Studio contract file** (e.g., `studio.ts`)
- ❌ **No Studio types** (FilmProject, SceneShot, etc.)
- ❌ **No Studio API functions** (createProject, generateShot, etc.)

#### 1.4 Existing Page Patterns (`world-explorer/page.tsx`)

**What it contains:**
- **Client component** (`'use client'`)
- **Ant Design components**: Card, Row, Col, Tabs, Modal, etc.
- **TanStack Query**: `useQuery`, `useMutation` for data fetching
- **State management**: `useState` for local UI state
- **Error handling**: `message.error()` for user feedback
- **Loading states**: `isPending` checks for mutations

**Key patterns:**
```typescript
// Query pattern
const epochsQuery = useQuery({ 
  queryKey: ['we', 'epochs'], 
  queryFn: getExplorerEpochs,
  staleTime: 10 * 60_000 
});

// Mutation pattern
const exploreMutation = useMutation({
  mutationFn: () => exploreWorld({ prompt, epoch, branch_count: branchCount }),
  onSuccess: (data) => {
    setResult(data);
    setActiveTab('explore');
    // Save to history "in background"
    void saveExploration({ ... }).catch(() => undefined);
  },
  onError: (e) => message.error(e instanceof Error ? e.message : 'Error'),
});

// UI pattern
<Tabs
  activeKey={activeTab}
  onChange={setActiveTab}
  items={[
    { key: 'explore', label: 'Исследовать', children: exploreTab },
    { key: 'hypotheses', label: 'Гипотезы', children: hypothesesTab },
    // ...
  ]}
/>
```

**What can be reused for Studio:**
- ✅ **Component structure** for Studio pages
- ✅ **Query/mutation patterns** for Studio data
- ✅ **Tab-based UI** for Studio sections
- ✅ **Modal patterns** for Studio detail views
- ✅ **Error handling** and loading states

**What's missing for Studio:**
- ❌ **Job-tracker pattern** for async generation
- ❌ **Progress indicators** for long-running operations
- ❌ **File preview components** for generated assets

### 2. Backend API Structure

#### 2.1 Book Routes (`runtime/core/book_routes.py`)

**What it contains:**
- **Composite router** mounting 13+ sub-routers
- **Studio-related routers**:
  - `film_studio_router` → `/book/film/*`
  - `assets_router` → `/book/assets/*`
  - `book_os_router` → `/book/os/*`
- **Role-based dependencies**: `require_role("editor")`

**Studio endpoints (from film_studio.py):**
- `POST /book/film/create` — Create film project
- `GET /book/film/list` — List projects
- `GET /book/film/{project_id}` — Get project details
- `PUT /book/film/{project_id}` — Update project
- `POST /book/film/{project_id}/scenes/create` — Create scene
- `GET /book/film/{project_id}/scenes/list` — List scenes
- `POST /book/film/{project_id}/scenes/{scene_id}/shots/create` — Create shot
- `GET /book/film/{project_id}/scenes/{scene_id}/shots/list` — List shots
- `POST /book/film/{project_id}/scenes/{scene_id}/shots/{shot_id}/generate` — Generate shot
- `POST /book/film/{project_id}/assemble` — Assemble film
- `GET /book/film/{project_id}/assemble/status` — Assembly status
- `GET /book/film/{project_id}/output` — Get output file

**What can be reused for Studio:**
- ✅ **Router composition pattern** for Studio sub-routers
- ✅ **Role-based dependencies** (editor/admin)
- ✅ **SuccessResponse pattern** for consistent responses
- ✅ **CRUD operations pattern** for Studio entities

**What's missing for Studio:**
- ❌ **No Studio-specific contracts** in frontend-v2
- ❌ **No Studio job-tracker endpoints** (status polling)
- ❌ **No Studio asset management endpoints** (upload/download)

#### 2.2 RBAC Implementation (`runtime/auth/rbac.py`)

**What it contains:**
- **Role hierarchy**: reader (0) < editor (1) < admin (2)
- **require_role function**: FastAPI dependency for role checking
- **Token extraction**: Bearer token or cookie `arkaim_session`

```python
ROLE_HIERARCHY = {"reader": 0, "editor": 1, "admin": 2}

def require_role(*allowed: str):
    async def _checker(user: dict = Depends(get_current_user)):
        user_level = ROLE_HIERARCHY.get(user["role"], -1)
        allowed_levels = [ROLE_HIERARCHY.get(r, -1) for r in allowed]
        if user_level < min(allowed_levels):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _checker
```

**What can be reused for Studio:**
- ✅ **Role hierarchy** for Studio permissions
- ✅ **require_role dependency** for Studio endpoints
- ✅ **Token extraction** pattern

**What's missing for Studio:**
- ❌ **No Studio-specific permission checks** (beyond basic role)
- ❌ **No Studio resource-level permissions** (project ownership, etc.)

### 3. ADR Document Analysis

#### 3.1 ADR_ARKAIM_MEDIA_BOUNDARY.md

**What it contains:**
- **Decision 1**: Two independent projects (Arkaim = meaning, Media = execution)
- **Decision 2**: Chain and branching point (Scene Context → Media Plan → Execution)
- **Decision 3**: Vocabulary (Scene Context ≠ Media Prompt, Media Plan ≠ Workflow)
- **Decision 4**: Single integration point (MediaRequest/MediaPlan contract)
- **Decision 5**: Invariants (8 rules for future development)

**Studio relevance:**
- ✅ **Studio must respect media boundary** (no ComfyUI knowledge in Arkaim)
- ✅ **Studio should use MediaPlan contract** for generation requests
- ✅ **Studio can own Film Studio** (owner decision §16-3)
- ✅ **Studio should inherit provenance** from Scene Context

**Key invariant for Studio:**
> "Core Arkaim — media-agnostic. No module in core/CORE/ knows about ComfyUI/workflow/node-graph."

#### 3.2 ADR_MEDIA_PLAN_V0.md

**What it contains:**
- **Decision 1**: MediaPlan v0 as separate domain contract
- **Decision 2**: No execution semantics (no model/steps/cfg/seed)
- **Decision 3**: Provenance and lineage required
- **Decision 4**: ExecutionDispatch as temporary bridge
- **Decision 5-8**: Implementation order, versioning, etc.

**Studio relevance:**
- ✅ **Studio should build MediaPlans** from Scene Context
- ✅ **Studio should include provenance** in all plans
- ✅ **Studio should support lineage** (parent plan references)
- ✅ **Studio should use versioned contracts** (plan_version: "0.1.0")

**Key decision for Studio:**
> "MediaPlan contains: media_kind (image|video), intent, visual_style, constraints, negative_constraints, characters[], location, temporal_context, provenance, lineage."

### 4. Existing Film Studio Implementation

#### 4.1 Backend (`runtime/core/routes/film_studio.py`)

**What it contains:**
- **13 endpoints** for film project management
- **SQLite storage** via FilmProjectStore
- **Role protection**: All endpoints require editor role
- **CRUD operations** for projects, scenes, shots
- **Generation endpoint** (calls pipeline)
- **Assembly endpoint** (ffmpeg-based)

**Key patterns:**
```python
router = APIRouter(
    tags=["Film Studio"],
    dependencies=[Depends(require_role("editor"))],
)

@router.post("/film/create", summary="Create film project")
async def create_project(title: str = Query(...), ...):
    store = _get_store()
    project = await store.create_project(...)
    return SuccessResponse(data=project.model_dump(mode="json"))
```

**What can be reused for Studio:**
- ✅ **Endpoint structure** for Studio CRUD
- ✅ **Query parameter pattern** for filters
- ✅ **SuccessResponse pattern** for responses
- ✅ **Store pattern** for data persistence

**What's missing for Studio:**
- ❌ **No frontend contract** for these endpoints
- ❌ **No Studio job status tracking** (generation progress)
- ❌ **No Studio asset management** (upload/download)

#### 4.2 Frontend Legacy (`arkaim-web/src/app/film-studio/page.tsx`)

**What it contains:**
- **813 lines** of legacy code
- **React Query** for data fetching
- **Ant Design** components
- **Mock data** fallback
- **Tab-based UI** (Projects, Scenes, Shots, Output)

**What can be reused for Studio:**
- ✅ **UI structure** (tabs, cards, forms)
- ✅ **Data flow patterns** (queries, mutations)
- ✅ **Component organization** (panels, forms, lists)

**What's missing for Studio:**
- ❌ **No typed contracts** (uses string API paths)
- ❌ **No proper error handling** (mock fallback)
- ❌ **No job-tracker** for generation progress

### 5. Current Development State

#### 5.1 Project Status
- **MD-5 ACCEPTED** (2026-09-14): Media boundary established
- **Frontend-v2**: 11 pages implemented, Studio group defined but empty
- **Backend**: Film Studio fully implemented (13+ endpoints)
- **ADR**: Media boundary and MediaPlan v0 accepted

#### 5.2 Key Findings for Studio
1. **Studio navigation exists** but has no pages
2. **Film Studio backend exists** but no frontend contracts
3. **Media boundary established** — Studio must respect it
4. **MediaPlan contract defined** — Studio should use it
5. **World Explorer pattern** can be template for Studio pages

---

## Summary: Reusable Patterns and Gaps

### ✅ Reusable Patterns for Studio

| Pattern | Source | Studio Application |
|---------|--------|-------------------|
| **Navigation structure** | `navigation.ts` | Studio group already defined |
| **API envelope** | `envelope.ts` | All Studio endpoints |
| **Typed contracts** | `contracts/*.ts` | Studio contract file |
| **Query/mutation** | World Explorer | Studio data fetching |
| **Role-based access** | `rbac.py` | Editor/admin permissions |
| **SuccessResponse** | Backend routes | Studio API responses |
| **FSD architecture** | Frontend-v2 | Studio entity/feature layers |
| **Tab-based UI** | World Explorer | Studio sections |
| **Modal patterns** | World Explorer | Studio detail views |

### ❌ Gaps to Fill for Studio

| Gap | Priority | Effort | Description |
|-----|----------|--------|-------------|
| **Studio contract file** | HIGH | Medium | Create `contracts/studio.ts` with typed functions |
| **Studio pages** | HIGH | Large | Implement 4 pages: assets, film, upload, story |
| **Studio widgets** | MEDIUM | Medium | Job-tracker, asset-preview, film-editor |
| **Studio entities** | MEDIUM | Medium | Film, asset, job entities with hooks |
| **Job-tracker pattern** | HIGH | Large | Async generation status polling |
| **Studio error handling** | MEDIUM | Small | Studio-specific error states |
| **Studio loading states** | MEDIUM | Small | Skeleton loaders, progress indicators |

### 🎯 Recommended Implementation Order

1. **Phase 1**: Create Studio contract file with typed functions for existing backend endpoints
2. **Phase 2**: Implement Studio navigation pages (assets, film) using World Explorer pattern
3. **Phase 3**: Add job-tracker widget for async generation tasks
4. **Phase 4**: Implement upload and story pages
5. **Phase 5**: Add Studio-specific error handling and loading states

---

## Technical Recommendations

### 1. Contract File Structure
```typescript
// contracts/studio.ts
export interface FilmProject { ... }
export interface SceneShot { ... }
export interface Asset { ... }
export interface JobStatus { ... }

export async function createProject(req: CreateProjectRequest): Promise<FilmProject> {
  return apiCall('POST', '/book/film/create', { body: req });
}

export async function getProject(id: string): Promise<FilmProject> {
  return apiCall('GET', `/book/film/${id}`);
}

// ... etc
```

### 2. Page Structure
```typescript
// app/(main)/studio/assets/page.tsx
'use client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getAssets, generateAsset } from '@/shared/api';
// ... follow World Explorer pattern
```

### 3. Job-Tracker Widget
```typescript
// widgets/job-tracker/JobTrackerWidget.tsx
export function JobTrackerWidget({ jobId }: { jobId: string }) {
  const { data: status } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId),
    refetchInterval: (query) => 
      query.state.data?.status === 'completed' ? false : 2000,
  });
  // ... render progress
}
```

### 4. Envelope Map Extension
```typescript
// Add to envelope.ts ENVELOPE_MAP:
'POST /book/film/create': 'enveloped',
'GET /book/film/list': 'enveloped',
'GET /book/film/{project_id}': 'enveloped',
// ... etc
```

---

## Conclusion

The frontend-v2 architecture provides a solid foundation for implementing Studio features. The existing patterns (navigation, API envelope, typed contracts, role-based access) are well-designed and can be directly reused. The main gaps are in the frontend implementation layer — Studio pages, contracts, and widgets need to be built following the established patterns.

The backend Film Studio implementation is complete and ready for frontend integration. The ADR documents provide clear guidance on respecting the media boundary and using the MediaPlan contract.

**Next step**: Create Studio contract file (`contracts/studio.ts`) and implement the first Studio page (assets) using the World Explorer pattern as template.