# `/upload` 实施计划

> 阶段：Design / Implementation Plan（read-only，等待审批）
> 创建时间：2026-07-10
> 状态：**PENDING_APPROVAL**

---

## 0. 简单说明

**目标**：在 Arkaim v2 中恢复 `/upload` 页面，让 editor/admin 角色可以上传文档（PDF/TXT/MD/JSON/DOC/DOCX），自动进入 BOOK OS 知识管线处理。

**核心发现**：
- Backend 完全就绪——两个 ingest 端点都已实现且可工作
- 前端有现成的 UI 模式可以参照（`/temporal/queue`）
- ChatPDF 集成未启用，本次不包含

---

## 1. 旧 `/upload` 分析（`arkaim-web/src/app/upload/page.tsx`）

### 可用的 UX 部分（建议恢复）
| 功能 | 旧代码位置 | 状态 |
|---|---|---|
| Drag-and-drop 上传区域 | `<LUpload>` | ✅ 可用 |
| 文件列表（名称/大小/删除） | `UploadForm` 内部 | ✅ 可用 |
| doc_type 下拉选择 | `DOC_TYPES` 常量 | ✅ 可用 |
| version 输入框 | `LInput` | ✅ 可用 |
| progress 条 | `LProgress` | ⚠️ 模拟进度，非真实 |
| success/error 提示 | `setMsg` | ✅ 可用 |
| 上传历史表格 | `UploadHistoryPanel` | ✅ 建议用真实 API 替代 |
| 格式说明信息面板 | `FormatsInfo` | ✅ 可用 |

### 不可直接复用（需改造）
| 问题 | 原因 | 解决方案 |
|---|---|---|
| 直接用 `fetch` + cookie 字符串拼接 | v2 规定所有网络调用走 `apiCall` | 改用 `apiCall` 或新建 `uploadDoc()` 函数 |
| `Promise<any>` 类型 | v2 要求完整类型定义 | 新增 `IngestResult` 类型 |
| localStorage 历史缓存 | 后端已有 `/book/os/documents` 真实数据源 | 改用 React Query 拉取真实列表 |
| Ant Design 4 + legacy light UI 组件 | v2 使用 Ant Design 5 原生组件 | 改用 `Upload` / `Table` / `Card` 等原生组件 |

---

## 2. Backend Endpoint 对比与选择

### 两个端点对比

| 维度 | `/book/os/documents/ingest` | `/book/os/pipeline/ingest` |
|---|---|---|
| **路径** | `POST /book/os/documents/ingest` | `POST /book/os/pipeline/ingest?doc_type=&version=` |
| **Body** | `multipart/form-data` (file) | `multipart/form-data` (file) + query params |
| **权限** | `require_role("editor")` | `require_role("editor")` |
| **功能** | 仅保存到 Source Store | **完整管线**：Source Store → chunking → entity/fact/rel extraction → Knowledge Graph → ChromaDB → Pulse.evolve() |
| **响应** | `Document.to_dict()` | `{status, document_id, title, hash, chunks_count, entities_added, facts_added, relationships_added, chunks_indexed}` |
| **文档来源** | `core/CORE/book_os/api_routes.py:92` | `core/CORE/book_os/api_routes.py:111` |

### 结论：使用 `POST /book/os/pipeline/ingest`

**理由**（基于代码事实）：
1. 旧前端 `arkaim-web/src/app/upload/page.tsx:75` 本身就调用这个端点
2. 它执行完整知识管线，上传后文档立即可被 RAG 检索
3. 返回详细处理结果（chunks/entities/facts/relationships 数量），前端可显示
4. 成功时自动触发 `pulse.evolve()`，让书"学习"新内容

---

## 3. 现有 v2 基础设施盘点

### 已有的（可直接使用）
| 设施 | 文件 | 用途 |
|---|---|---|
| `RoleGate` | `src/shared/rbac/RoleGate.tsx` | 页面级 editor/admin 门控 |
| `useAuth` | `src/entities/auth/AuthProvider.tsx` | 获取当前用户角色 |
| `no-access` 页面 | `src/app/(main)/no-access/page.tsx` | 无权限时展示 |
| `AppShell` | `src/widgets/app-shell/AppShell.tsx` | 带侧边栏的主布局 |
| Ant Design 5 | 已在 `providers.tsx` 配置 | `Upload`, `Table`, `Card`, `Button`, `Typography` 等 |
| `apiCall` client | `src/shared/api/client.ts` | 统一 HTTP 客户端，`credentials: same-origin` |
| `ApiError` | `src/shared/api/errors.ts` | 统一错误处理 |
| `StateView` | `src/shared/ui/StateView.tsx` | loading/error/empty 状态 |
| `envelopeOf` | `src/shared/api/envelope.ts` | 响应解包 |

### 需要新增的
| 内容 | 文件 | 说明 |
|---|---|---|
| Document 类型 | `src/shared/api/contracts/book.ts` | `Document`, `IngestResult` 接口 |
| API 函数 | `src/shared/api/contracts/book.ts` | `listDocuments()`, `uploadDocument()` |
| ENVELOPE_MAP 条目 | `src/shared/api/envelope.ts` | 三个新路由注册 |
| 导航菜单更新 | `src/shared/rbac/navigation.ts` | 移除 `comingSoon: true` |
| `/upload` 页面 | `src/app/(main)/upload/page.tsx` | 新页面 |
| 单元测试 | `tests/unit/upload.test.ts` | 模块结构、类型、函数导出测试 |

---

## 4. 需要新增的 TypeScript 类型与 API 函数

### 4.1 类型（追加到 `contracts/book.ts`）

```typescript
/**
 * GET /book/os/documents → Document[]
 * POST /book/os/documents/ingest → Document
 * POST /book/os/pipeline/ingest → IngestResult
 */

export interface Document {
  id: string;
  title: string;        // 原始文件名
  type: 'primary_source' | 'secondary_source' | 'external';
  version: string;      // semver
  imported_at: string;  // ISO 8601 UTC
  hash: string;         // SHA-256
}

export interface IngestResult {
  status: 'ok' | 'error';
  document_id?: string;
  title?: string;
  hash?: string;
  chunks_count?: number;
  entities_added?: number;
  facts_added?: number;
  relationships_added?: number;
  chunks_indexed?: number;
  errors?: string[];
}
```

### 4.2 API 函数（追加到 `contracts/book.ts`）

```typescript
/** GET /book/os/documents → Document[] (reader+ 可访问) */
export function listDocuments(doc_type?: string): Promise<Document[]> {
  const params = doc_type ? `?doc_type=${doc_type}` : '';
  return apiCall('GET', `/book/os/documents${params}`);
}

/**
 * POST /book/os/pipeline/ingest — 完整管线上传
 * 注意：multipart 请求体，apiCall 需特殊处理
 */
export async function uploadDocument(
  file: File,
  doc_type: string = 'primary_source',
  version: string = '1.0.0',
): Promise<IngestResult> {
  // 直接使用 fetch（multipart 无法通过 JSON body 发送）
  // 与 streamAsk 相同的模式：在 contracts 层封装
  const params = new URLSearchParams({ doc_type, version });
  const resp = await fetch(`/book/os/pipeline/ingest?${params}`, {
    method: 'POST',
    credentials: 'same-origin',
    body: new FormData().append('file', file),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new ApiError(resp.status, body?.detail ?? 'Upload failed');
  }
  return resp.json();
}
```

> **注意**：`uploadDocument` 因 `multipart/form-data` 无法走 `apiCall` 的 JSON body 路径。
> 参照 `streamAsk()` 在 `contracts/book.ts` 中的写法——直接在 contract 层用 `fetch`，
> 但保留在 `src/shared/api/` 允许区域内（eslint `no-restricted-syntax` 规则例外）。

### 4.3 ENVELOPE_MAP 新增条目

```typescript
// src/shared/api/envelope.ts
'GET /book/os/documents': 'enveloped',       // → Document[]
'POST /book/os/pipeline/ingest': 'direct',   // → IngestResult (raw dict)
```

> `documents/ingest` 不需要，因为不打算在前端调用它。
> `pipeline/ingest` 返回 raw dict 不需要解包，标记为 `direct`。

---

## 5. 页面结构（`src/app/(main)/upload/page.tsx`）

```
'use client'

import { RoleGate } from '@/shared/rbac/RoleGate'
import { listDocuments, uploadDocument, type Document, type IngestResult } from '@/shared/api'
import { App, Button, Card, Table, Tag, Typography, Upload, message } from 'antd'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

// ── 常量 ──
const ACCEPTED_TYPES = '.txt,.md,.json,.pdf,.doc,.docx'
const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB
const DOC_TYPES = [
  { value: 'primary_source', label: '主要来源' },
  { value: 'secondary_source', label: '次要来源' },
  { value: 'external',      label: '外部文档' },
]

// ── 无权限 fallback ──
const noAccess = (
  <Typography.Paragraph type="secondary">
    文档上传需要编辑者权限。请联系管理员。
  </Typography.Paragraph>
)

// ── 主页面 ──
export default function UploadPage() {
  const { message: msgApi } = App.useApp()
  const qc = useQueryClient()
  const [docType, setDocType] = useState('primary_source')
  const [version, setVersion] = useState('1.0.0')

  // ── 文档列表 ──
  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ['os', 'documents'],
    queryFn: () => listDocuments(),
    staleTime: 60_000,
  })

  // ── 上传 mutation ──
  const uploadMut = useMutation({
    mutationFn: (file: File) => uploadDocument(file, docType, version),
    onSuccess: (result) => {
      if (result.status === 'ok') {
        msgApi.success(`已处理: ${result.title}（${result.chunks_count} 个片段）`)
        void qc.invalidateQueries({ queryKey: ['os', 'documents'] })
      } else {
        msgApi.error(result.errors?.[0] ?? '处理失败')
      }
    },
    onError: (e) => {
      msgApi.error(e instanceof ApiError ? e.message : '上传失败')
    },
  })

  const handleUpload = (file: File) => {
    if (file.size > MAX_FILE_SIZE) {
      msgApi.error('文件过大，最大 50MB')
      return false
    }
    uploadMut.mutate(file)
    return false // 阻止 Ant Design Upload 的默认XHR
  }

  // ── 文档表格列 ──
  const columns = [
    { title: '文件名', dataIndex: 'title', key: 'title' },
    { title: '类型', dataIndex: 'type', key: 'type',
      render: (t: string) => <Tag>{t}</Tag> },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: '上传时间', dataIndex: 'imported_at', key: 'imported_at',
      render: (v: string) => new Date(v).toLocaleString('zh-CN') },
  ]

  return (
    <RoleGate roles={['editor', 'admin']} fallback={<><App><App.ErrorBoundary><noAccess /></App.ErrorBoundary></App></>)}>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 0' }}>
        <Typography.Title level={3} style={{ marginBottom: 24 }}>文档上传</Typography.Title>

        {/* 上传区 */}
        <Card title="上传新文档" style={{ marginBottom: 24 }}>
          <Upload.Dragger
            accept={ACCEPTED_TYPES}
            multiple={false}
            beforeUpload={handleUpload}
            showUploadList={false}
            disabled={uploadMut.isPending}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">点击或拖拽文件至此区域</p>
            <p className="ant-upload-hint">支持 PDF / TXT / MD / JSON / DOC / DOCX，最大 50MB</p>
          </Upload.Dragger>

          {/* 配置行 */}
          <div style={{ display: 'flex', gap: 16, marginTop: 16 }}>
            <Select value={docType} onChange={setDocType} style={{ width: 160 }}>
              {DOC_TYPES.map(d => <Select.Option key={d.value} value={d.value}>{d.label}</Select.Option>)}
            </Select>
            <Input value={version} onChange={e => setVersion(e.target.value)} style={{ width: 120 }} placeholder="版本号" />
          </div>
        </Card>

        {/* 文档列表 */}
        <Card title="已上传文档">
          <Table<Document>
            dataSource={docs}
            columns={columns}
            rowKey="id"
            loading={docsLoading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      </div>
    </RoleGate>
  )
}
```

---

## 6. RBAC 设计

| 层级 | 机制 | 说明 |
|---|---|---|
| 导航菜单 | `navigation.ts` 移除 `comingSoon` | editor/admin 可见 |
| 页面门控 | `<RoleGate roles={['editor','admin']}>` | reader 直连 URL → 显示 `noAccess` |
| 后端权限 | `require_role("editor")` | 401/403 由 client 统一处理 |

**参考模式**：与 `/temporal/queue` 完全一致。

---

## 7. UX Flow

```
用户访问 /upload
  │
  ├─ reader 角色 → RoleGate fallback → "需要编辑者权限" 提示
  │
  └─ editor/admin 角色 → 正常页面
        │
        ├─ 拉取文档列表 (React Query, staleTime 60s)
        ├─ 选择 doc_type 和 version
        ├─ 拖拽/点击上传文件
        │     ├─ 文件 ≤ 50MB？→ 否则显示错误
        │     └─ 提交 FormData → POST /book/os/pipeline/ingest
        │           ├─ 成功 → message.success + 刷新列表
        │           └─ 失败 → message.error
        └─ 展示文档表格（文件名/类型/版本/时间）
```

---

## 8. Error / Loading / Success States

| 状态 | 处理方式 |
|---|---|
| 加载中（列表） | `Table.loading={docsLoading}` |
| 上传中 | `Upload.Dragger.disabled={uploadMut.isPending}` |
| 上传成功 | `message.success` + `qc.invalidateQueries` |
| 上传失败（网络） | `message.error` from `ApiError.message` |
| 上传失败（后端错误） | `message.error` from response detail |
| reader 直连 URL | `<RoleGate>` fallback 显示 noAccess 文本 |
| 空列表 | `<Table dataSource=[]>` 自动显示空状态 |

---

## 9. 文件变更清单

### 新增文件
| 文件 | 说明 |
|---|---|
| `src/app/(main)/upload/page.tsx` | 上传页面主组件 |
| `tests/unit/upload.test.ts` | 单元测试 |

### 修改文件
| 文件 | 变更内容 |
|---|---|
| `src/shared/api/contracts/book.ts` | 新增 `Document`、`IngestResult` 类型 + `listDocuments()`、`uploadDocument()` 函数 |
| `src/shared/api/envelope.ts` | ENVELOPE_MAP 新增 2 条 |
| `src/shared/rbac/navigation.ts` | `upload` 项移除 `comingSoon: true` |
| `tests/unit/book.test.ts` | 新增 upload 相关 it-blocks |

---

## 10. 测试计划

### 单元测试（`tests/unit/upload.test.ts`）
```
it('模块导出正确 shape')
it('Document 类型包含必要字段')
it('IngestResult 类型包含 status 字段')
it('listDocuments 调用正确路径')
it('uploadDocument 构建正确 URL 参数')
it('DOC_TYPES 包含三个选项')
it('ACCEPTED_TYPES 包含 .pdf')
it('MAX_FILE_SIZE = 50MB')
```

### 参考模式
参照 `tests/unit/reading/use-streaming-chat.test.ts`（6 it-blocks）。

---

## 11. Runtime Smoke Test（手动验证清单）

| # | 步骤 | 预期结果 |
|---|---|---|
| 1 | 以 **reader** 角色登录，访问 `/upload` | 显示"需要编辑者权限" |
| 2 | 以 **editor** 角色登录，访问 `/upload` | 显示上传页面 |
| 3 | 上传一个 `.txt` 文件（<50MB） | 成功提示，列表出现新文档 |
| 4 | 上传一个超过 50MB 的文件（模拟） | 前端拦截，显示错误 |
| 5 | 上传一个 `.pdf` 文件 | 成功，处理完成后列表刷新 |
| 6 | 切换 doc_type，再次上传 | 新文档 type 正确 |
| 7 | 浏览器 Network 面板检查请求 | `POST /book/os/pipeline/ingest?...` multipart |
| 8 | 检查 Swagger `localhost:8642/docs` | 端点存在且可手动测试 |

---

## 12. 明确不包含的内容

| 项目 | 原因 |
|---|---|
| ChatPDF 集成 | forensic 确认：`chatpdf_client.py` 不存在，`CHATPDF_KEY` 未配置 |
| `/book/os/documents/ingest` 端点 | 简单存储，不走完整管线；用户希望上传即可被检索 |
| 文件预览/下载 | 后续需求，当前只需列表展示 |
| 批量上传 | 单次单文件，满足核心场景 |
| 版本历史管理 | 新版本 = 新 Document 记录，已有 Hash 去重 |
| 删除文档功能 | backend 有 `DELETE` 但前端暂不暴露 |
| `/analytics` 页面修改 | scope 外 |
| `/reading` 页面修改 | scope 外 |
| `/ask` 页面修改 | scope 外 |
| Backend 任何修改 | 规则约束 |

---

## 13. 风险与依赖

| 风险 | 缓解 |
|---|---|
| `uploadDocument` 用 raw fetch（不走 apiCall） | 参照 `streamAsk` 现有模式，在 contracts/book.ts 内封装 |
| ENVELOPE_MAP 缺少 book_os 路由导致解包错误 | 提前注册 `GET /book/os/documents` 和 `POST /book/os/pipeline/ingest` |
| 旧前端用模拟进度条 | 新页面去掉模拟进度，用 `uploadMut.isPending` 控制 Upload disabled 状态 |
| PDF 提取依赖 pdfplumber/PyPDF2 | backend 已有 graceful fallback；前端无需处理 |

---

## 14. 预估工作量

| 任务 | 预估 |
|---|---|
| 类型 + API 函数 | 15 min |
| ENVELOPE_MAP 注册 | 5 min |
| 导航菜单更新 | 5 min |
| 页面组件实现 | 30 min |
| 单元测试 | 15 min |
| Smoke test + 调试 | 20 min |
| **合计** | **~1.5 小时** |

---

**计划完成。等待审批后开始实现。**
