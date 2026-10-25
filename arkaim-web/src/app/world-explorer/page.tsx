'use client';

import { useState, useEffect, useCallback } from 'react';
import { LCard, LButton, LSelect, LSlider, LSpace, LTag, LTabs, LProgress, LModal, LAlert, LSpin, LEmpty, LStatistic, LBadge, LDivider, LTextArea, toast, LInput } from '@/shared/ui/light';
import { ExperimentOutlined, ThunderboltOutlined, HistoryOutlined, DeleteOutlined, SwapOutlined, BranchesOutlined, BulbOutlined, NodeIndexOutlined, StarOutlined, SearchOutlined, ClusterOutlined, FlagOutlined, DatabaseOutlined, DownloadOutlined } from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ProtectedRoute } from '@/shared/lib/guards';
import { useWsEvent } from '@/shared/lib/ws-hooks';
import { useAuth } from '@/app/providers';

type Epoch = { id: string; name: string; name_ru: string; order: number };
type Hypothesis = { id: string; title: string; description: string; type: string; epoch: string; confidence: number; tags: string[] };
type RankedBranch = { rank: number; branch_type: string; title: string; quality_score: number; quality_summary?: string; strengths: string[]; weaknesses: string[]; impact_score: number; contradictions: number; delta_changes: number };
type ExplorationResult = { request: { prompt: string; epoch?: string; location?: string; branch_count: number }; hypothesis: Hypothesis | null; scenario: { branch_count: number; best_branch_id: string; summary: string }; ranked_branches: RankedBranch[]; duration_ms: number; summary: string };
type CompatibilityResult = { overall_score: number; is_compatible: boolean; risk_level: string; axis_scores: { axis: string; score: number; violations_count: number; warnings_count: number }[]; violations_count: number; warnings_count: number; recommendations: string[] };
type Possibility = { id: string; title: string; title_ru: string; description: string; category: string; confidence: number; tags: string[] };
type HistoryItem = { id: string; timestamp: number; prompt: string; epoch?: string; result: ExplorationResult };
type HistoryApiItem = { id: string | number; created_at: string; prompt: string; epoch?: string; result?: ExplorationResult; duration_ms?: number; summary?: string; overall_score?: number; branch_count_actual?: number };
type GeneratedTextResponse = { system_instruction: string; user_prompt: string };
type StoryEngineResponse = { data: { system_instruction: string; user_prompt: string; style: string; max_length: number; branch_title: string; quality_score: number; constraints_summary?: string } };
type WorldExplorerStats = { world_model: string; patterns_count: number; epochs_count: number; locations_count: number; events_count: number };
type FreePoint = { id: string; title: string; description: string; epoch?: string; category: string; confidence: number };
type FeedbackItem = { id: number; rating: number; comment: string; branch_title: string; branch_type: string; created_at: string };

const RISK_COLORS: Record<string, string> = { low: '#52c41a', medium: '#faad14', high: '#ff7a45', rejected: '#ff4d4f' };
const BRANCH_TYPE_LABELS: Record<string, string> = { conservative: 'Консервативное', moderate: 'Умеренное', radical: 'Радикальное', unexpected: 'Неожиданное' };
const CRITERIA_LABELS: Record<string, string> = { canon_alignment: 'Канон', logical_consistency: 'Логика', thematic_depth: 'Глубина', dramatic_potential: 'Драма', originality: 'Оригинал' };
const PROGRESS_STEPS = [
  { key: 'compatibility', label: 'Проверка совместимости' },
  { key: 'hypotheses', label: 'Генерация гипотез' },
  { key: 'modeling', label: 'Моделирование' },
  { key: 'impact', label: 'Оценка влияния' },
  { key: 'contradictions', label: 'Противоречия' },
  { key: 'delta', label: 'Изменения мира' },
  { key: 'quality', label: 'Оценка качества' },

  { key: 'ranking', label: 'Ранжирование' },
];

async function loadHistory(limit = 20, offset = 0): Promise<{ items: HistoryItem[]; count: number }> {
  try {
    const res = await api.get<{ data: HistoryApiItem[]; count: number }>(`/book/world-explorer/history?limit=${limit}&offset=${offset}`);
    return {
      items: (res.data || []).map((item: HistoryApiItem) => ({
        id: String(item.id), timestamp: new Date(item.created_at).getTime(), prompt: item.prompt, epoch: item.epoch,
        result: item.result || { request: { prompt: item.prompt, branch_count: 0 }, hypothesis: null, scenario: { branch_count: 0, best_branch_id: '', summary: '' }, ranked_branches: [], duration_ms: item.duration_ms || 0, summary: item.summary || '' },
        overall_score: item.overall_score,
        branch_count_actual: item.branch_count_actual,
      })),
      count: res.count || 0,
    };
  } catch { return { items: [], count: 0 }; }
}

async function saveHistory(item: HistoryItem) {
  try { await api.post('/book/world-explorer/history', { prompt: item.prompt, epoch: item.epoch, branch_count: item.result?.request?.branch_count || 3, hypothesis_id: item.result?.hypothesis?.id || null, hypothesis_title: item.result?.hypothesis?.title || null, result_json: JSON.stringify(item.result), summary: item.result?.summary || '', overall_score: item.result?.ranked_branches?.[0]?.quality_score || 0, branch_count_actual: item.result?.ranked_branches?.length || 0, duration_ms: item.result?.duration_ms || 0 }); }
  catch { }
}

function WorldExplorerContent() {
  // OWNER-GO (Q4): dev-панели (Поиск в источниках, Кэш) — только editor/admin.
  // Backend дублирует гейт: require_role('editor') на /cache/* и /sources/search.
  const { user } = useAuth();
  const canDev = user ? user.role === 'editor' || user.role === 'admin' : false;

  const [prompt, setPrompt] = useState('');
  const [epoch, setEpoch] = useState<string | undefined>();
  const [branchCount, setBranchCount] = useState(3);
  const [result, setResult] = useState<ExplorationResult | null>(null);
  const [compatibility, setCompatibility] = useState<CompatibilityResult | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<RankedBranch | null>(null);
  const [compareBranches, setCompareBranches] = useState<RankedBranch[]>([]);
  const [showCompare, setShowCompare] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyCount, setHistoryCount] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historyLimit] = useState(20);
  const [progress, setProgress] = useState(-1);
  const [activeTab, setActiveTab] = useState('explore');
  const [generatedText, setGeneratedText] = useState<{ system_instruction: string; user_prompt: string } | null>(null);
  const [generatingText, setGeneratingText] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [deepTree, setDeepTree] = useState<any>(null);
  const [deepLoading, setDeepLoading] = useState(false);
  const [freePoints, setFreePoints] = useState<FreePoint[]>([]);
  const [freePointsLoading, setFreePointsLoading] = useState(false);
  const [bestPaths, setBestPaths] = useState<any[]>([]);
  const [bestPathsLoading, setBestPathsLoading] = useState(false);
  const [unifiedResult, setUnifiedResult] = useState<any>(null);
  const [unifiedLoading, setUnifiedLoading] = useState(false);
  const [exportResult, setExportResult] = useState<any>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [externalSearchQuery, setExternalSearchQuery] = useState('');
  const [externalResults, setExternalResults] = useState<any[]>([]);
  const [externalLoading, setExternalLoading] = useState(false);
  const [feedbackList, setFeedbackList] = useState<FeedbackItem[]>([]);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [cacheStats, setCacheStats] = useState<any>(null);
  const [cacheLoading, setCacheLoading] = useState(false);

  const { data: epochsData } = useQuery({ queryKey: ['we-epochs'], queryFn: () => api.get<{ data: Epoch[] }>('/book/world-explorer/epochs') });
  const epochs = epochsData?.data || [];
  const { data: statsData } = useQuery({ queryKey: ['we-stats'], queryFn: () => api.get<{ data: WorldExplorerStats }>('/book/world-explorer/stats') });
  const stats = statsData?.data || null;
  const { data: hypsData, isLoading: hypsLoading } = useQuery({ queryKey: ['we-hypotheses', epoch], queryFn: () => api.get<{ data: Hypothesis[] }>(`/book/world-explorer/hypotheses/${epoch || 'satya_yuga'}?limit=10`), enabled: activeTab === 'hypotheses' });
  const hypotheses = hypsData?.data || [];
  const { data: possData, isLoading: possLoading } = useQuery({ queryKey: ['we-possibilities', epoch], queryFn: () => api.get<{ data: Possibility[] }>(`/book/world-explorer/possibilities/${epoch || 'satya_yuga'}?limit=10`), enabled: activeTab === 'possibilities' });
  const possibilities = possData?.data || [];

  useEffect(() => {
    loadHistory(historyLimit, historyOffset).then(({ items, count }) => { setHistory(items); setHistoryCount(count); });
  }, [historyOffset, historyLimit]);

  const checkCompatibility = useCallback(async () => {
    if (!prompt || prompt.length < 5) { setCompatibility(null); return; }
    try { const res = await api.post<{ data: CompatibilityResult }>('/book/world-explorer/validate', { prompt, epoch: epoch || null, location: null }); setCompatibility(res.data); } catch { setCompatibility(null); }
  }, [prompt, epoch]);

  useEffect(() => { const t = setTimeout(checkCompatibility, 500); return () => clearTimeout(t); }, [checkCompatibility]);

  useWsEvent('exploration_progress', (data: Record<string, unknown>) => { if (typeof data.step === 'number') setProgress(data.step); });
  useWsEvent('exploration_complete', () => setProgress(-1));
  useWsEvent('exploration_started', () => setProgress(0));

  const exploreMutation = useMutation({
    mutationFn: async () => { setProgress(0); return api.post<{ data: ExplorationResult; summary: string }>('/book/world-explorer/explore', { prompt, epoch: epoch || undefined, branch_count: branchCount }); },
    onSuccess: (res) => { setResult(res.data); setProgress(-1); const item: HistoryItem = { id: Date.now().toString(), timestamp: Date.now(), prompt, epoch, result: res.data }; setHistory(prev => [item, ...prev].slice(0, 50)); saveHistory(item); toast.success('Исследование завершено'); },
    onError: () => { setProgress(-1); toast.error('Ошибка исследования'); },
  });

  const exploreFromHypothesis = async (hyp: Hypothesis) => {
    try {
      setProgress(0);
      const res = await api.post<{ data: ExplorationResult }>(`/book/world-explorer/explore/hypothesis?hypothesis_id=${hyp.id}&epoch=${hyp.epoch || 'satya_yuga'}&branch_count=${branchCount}`, {});
      setResult(res.data); setProgress(-1); setActiveTab('explore');
    } catch { setProgress(-1); toast.error('Ошибка'); }
  };

  const loadFromHistory = (item: HistoryItem) => { setPrompt(item.prompt); setEpoch(item.epoch); setResult(item.result); setActiveTab('explore'); };
  const deleteFromHistory = async (id: string) => { try { await api.delete('/book/world-explorer/history/' + id); } catch {} setHistory(prev => prev.filter(x => x.id !== id)); };
  const toggleCompare = (branch: RankedBranch) => { setCompareBranches(prev => { const exists = prev.find(b => b.rank === branch.rank); if (exists) return prev.filter(b => b.rank !== branch.rank); if (prev.length >= 3) return prev; return [...prev, branch]; }); };

  const submitFeedback = async (branch: RankedBranch) => {
    if (feedbackRating === 0) { toast.warning('Выберите оценку'); return; }
    try { await api.post('/book/world-explorer/feedback', { branch_rank: branch.rank, branch_type: branch.branch_type, branch_title: branch.title, rating: feedbackRating, comment: feedbackComment }); toast.success('Отзыв сохранён'); setFeedbackRating(0); setFeedbackComment(''); }
    catch { toast.error('Ошибка сохранения'); }
  };

  const generateTextFromBranch = async (branch: RankedBranch) => {
    setGeneratingText(true);
    try { const res = await api.post<{ data: GeneratedTextResponse }>('/book/world-explorer/generate-from-branch', { exploration_prompt: prompt, branch_title: branch.title, branch_type: branch.branch_type, epoch, style: 'literary', max_length: 2000, quality_score: branch.quality_score, strengths: branch.strengths, weaknesses: branch.weaknesses }); setGeneratedText(res.data); }
    catch { toast.error('Ошибка генерации'); }
    setGeneratingText(false);
  };

  // ── Глубокое исследование ──
  const runDeepExploration = async () => {
    if (!prompt) { toast.warning('Введите идею'); return; }
    setDeepLoading(true);
    try {
      const res: { ok: true; data: { total_nodes: number; max_depth: number; summary: string; nodes: Record<string, { id: string; hypothesis_title: string; hypothesis_type: string; quality_score: number; depth: number; children: string[]; parent_id: string }> } } = await api.post<{ ok: true; data: { total_nodes: number; max_depth: number; summary: string; nodes: Record<string, { id: string; hypothesis_title: string; hypothesis_type: string; quality_score: number; depth: number; children: string[]; parent_id: string }> } }>('/book/world-explorer/explore-deep', { prompt, epoch, max_depth: 3, branches_per_level: 3 });
      setDeepTree(res.data || res);
      toast.success('Глубокое исследование завершено');
    } catch { toast.error('Ошибка глубокого исследования'); }
    setDeepLoading(false);
  };

  // ── Свободные точки мира ──
  const loadFreePoints = async () => {
    setFreePointsLoading(true);
    try {
      const res: { ok: true; data: { id: string; title: string; description: string; epoch?: string; category: string; confidence: number }[] } = await api.get<{ ok: true; data: { id: string; title: string; description: string; epoch?: string; category: string; confidence: number }[] }>(`/book/world-explorer/free-points${epoch ? `?epoch=${epoch}` : ''}`);
      setFreePoints(res.data ?? []);
    } catch { setFreePoints([]); }
    setFreePointsLoading(false);
  };

  // ── Лучшие пути ──
  const loadBestPaths = async () => {
    setBestPathsLoading(true);
    try {
      const res: { ok: true; data: any[] } = await api.get<{ ok: true; data: any[] }>('/book/world-explorer/best-paths?tree_id=root&top_n=3');
      setBestPaths(res.data ?? []);
    } catch { setBestPaths([]); }
    setBestPathsLoading(false);
  };

  // ── Unified Pipeline ──
  const runUnifiedPipeline = async () => {
    if (!prompt) { toast.warning('Введите идею'); return; }
    setUnifiedLoading(true);
    try {
      const res: { ok: true; data: { story: { system_instruction: string; user_prompt: string }; summary?: string } } = await api.post<{ ok: true; data: { story: { system_instruction: string; user_prompt: string }; summary?: string } }>('/book/world-explorer/unified', { prompt, epoch, branch_count: branchCount, generate_story: true, select_best: true });
      setUnifiedResult(res.data || res);
      toast.success('Unified Pipeline завершён');
    } catch { toast.error('Ошибка Unified Pipeline'); }
    setUnifiedLoading(false);
  };

  // ── Экспорт в Markdown ──
  const runExport = async () => {
    if (!result) { toast.warning('Сначала выполните исследование'); return; }
    setExportLoading(true);
    try {
      const res: { ok: true; data: { markdown: string } } = await api.post<{ ok: true; data: { markdown: string } }>('/book/world-explorer/export', { prompt, epoch, branch_count: branchCount });
      setExportResult(res.data || res);
      toast.success('Отчёт экспортирован');
    } catch { toast.error('Ошибка экспорта'); }
    setExportLoading(false);
  };

  const downloadMarkdown = () => {
    if (!exportResult?.data?.markdown) return;
    const blob = new Blob([exportResult.data.markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `world-explorer-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Поиск во внешних источниках ──
  const searchExternal = async () => {
    if (!externalSearchQuery.trim()) return;
    setExternalLoading(true);
    try {
      const res: { ok: true; data: any[] } = await api.get<{ ok: true; data: any[] }>(`/book/world-explorer/sources/search?query=${encodeURIComponent(externalSearchQuery)}&limit=5`);
      setExternalResults(res.data ?? []);
    } catch { setExternalResults([]); }
    setExternalLoading(false);
  };

  // ── Обратная связь ──
  const loadFeedback = async () => {
    setFeedbackLoading(true);
    try {
      const res: { ok: true; data: { id: number; rating: number; comment: string; branch_title: string; branch_type: string; created_at: string }[] } = await api.get<{ ok: true; data: { id: number; rating: number; comment: string; branch_title: string; branch_type: string; created_at: string }[] }>('/book/world-explorer/feedback?limit=50');
      setFeedbackList(res.data ?? []);
    } catch { setFeedbackList([]); }
    setFeedbackLoading(false);
  };

  // ── Статистика кэша ──
  const loadCacheStats = async () => {
    setCacheLoading(true);
    try {
      const res: { ok: true; data: { caches: unknown; performance_metrics: unknown } } = await api.get<{ ok: true; data: { caches: unknown; performance_metrics: unknown } }>('/book/world-explorer/cache/stats');
      setCacheStats(res.data || res);
    } catch { setCacheStats(null); }
    setCacheLoading(false);
  };
const sendToStoryEngine = async (branch: RankedBranch) => {
  try {
    setGeneratingText(true);
    const res = await api.post<{ data: StoryEngineResponse }>(
      '/book/world-explorer/send-to-story',
      { branch_id: branch.rank, exploration_prompt: prompt, branch_title: branch.title, branch_type: branch.branch_type, epoch }
    );
    setGeneratedText(res.data.data);
    toast.success('Данные отправлены в Story Engine');
  } catch (error) {
    toast.error('Ошибка отправки в Story Engine');
    console.error(error);
  } finally {
    setGeneratingText(false);
  }
};

  useEffect(() => {
    loadFeedback();
  }, []);

  useEffect(() => {
    // Кэш-статистика — dev-панель: автозагрузка только для editor/admin.
    if (canDev) loadCacheStats();
  }, [canDev]);

  const epochOptions = epochs.map(e => ({ value: e.id, label: e.name_ru }));

  // Dev-вкладки — только для editor/admin (OWNER-GO Q4):
  // reader не видит ни вкладок, ни автозагрузки кэш-статистики.
  const externalSearchTab = {
    key: 'external-search',
    label: <><SearchOutlined /> Поиск в источниках</>,
    children: (
      <>
        <LCard style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <LInput placeholder="Поиск по источникам книги..." value={externalSearchQuery} onChange={e => setExternalSearchQuery(e.target.value)} style={{ flex: 1 }} />
            <LButton type="primary" disabled={externalLoading || !externalSearchQuery.trim()} onClick={searchExternal} loading={externalLoading}>
              Искать
            </LButton>
          </div>
        </LCard>
        {externalResults.length > 0 && (
          <div style={{ maxHeight: 400, overflow: 'auto' }}>
            {externalResults.map((r: any, i: number) => (
              <div key={i} style={{ padding: 10, borderBottom: '1px solid #f0f0f0' }}>
                <div style={{ fontWeight: 600 }}>{r.title || r.source || `Результат #${i + 1}`}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{r.snippet || r.description || ''}</div>
              </div>
            ))}
          </div>
        )}
        {!externalLoading && externalResults.length === 0 && externalSearchQuery.trim() && <LEmpty description="Ничего не найдено" />}
      </>
    ),
  };

  const cacheStatsTab = {
    key: 'cache-stats',
    label: <><DatabaseOutlined /> Кэш</>,
    children: (
      <>
        <LCard style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
            <LButton type="primary" disabled={cacheLoading} onClick={loadCacheStats} loading={cacheLoading}>
              Загрузить статистику кэша
            </LButton>
          </div>
        </LCard>
        {cacheStats && (
          <div style={{ maxHeight: 400, overflow: 'auto' }}>
            {Object.entries(cacheStats.data?.caches || {}).map(([name, stat]: [string, any]) => (
              <div key={name} style={{ padding: 8, borderBottom: '1px solid #f0f0f0' }}>
                <div style={{ fontWeight: 600 }}>{name}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{JSON.stringify(stat)}</div>
              </div>
            ))}
          </div>
        )}
        {!cacheLoading && !cacheStats && <LEmpty description="Нажмите «Загрузить статистику кэша»" />}
      </>
    ),
  };

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}><h2 style={{ margin: 0 }}><BranchesOutlined style={{ marginRight: 8 }} />Исследование мира</h2><span style={{ color: '#999' }}>Исследуйте альтернативные линии развития мира книги</span></div>

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <LStatistic title="Эпох" value={stats.epochs_count || 0} />
          <LStatistic title="Локаций" value={stats.locations_count || 0} />
          <LStatistic title="Паттернов" value={stats.patterns_count || 0} />
          <LStatistic title="Событий" value={stats.events_count || 0} />
        </div>
      )}

      <LTabs items={[
        { key: 'explore', label: <><ExperimentOutlined /> Исследование</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <LTextArea rows={3} placeholder="Опишите вашу идею..." value={prompt} onChange={e => setPrompt(e.target.value)} style={{ fontSize: 15 }} />
                <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
                  <LSelect placeholder="Эпоха" value={epoch} onChange={setEpoch} options={epochOptions} style={{ width: 200 }} />
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span>Ветвей:</span>
                    <LSlider min={2} max={8} value={branchCount} onChange={setBranchCount} style={{ width: 120 }} />
                    <strong>{branchCount}</strong>
                  </div>
                  <LButton type="primary" icon={<ExperimentOutlined />} loading={exploreMutation.isPending} disabled={!prompt || prompt.length < 5} onClick={() => exploreMutation.mutate()}>Исследовать</LButton>
                </div>
              </div>
            </LCard>

            {progress >= 0 && (
              <LCard style={{ marginBottom: 16 }}>
                <strong>Прогресс:</strong>
                <LProgress percent={Math.round(((progress + 1) / PROGRESS_STEPS.length) * 100)} status="active" style={{ marginTop: 8 }} />
                <span style={{ color: '#999', fontSize: 12 }}>{PROGRESS_STEPS[progress]?.label || 'Завершение...'}</span>
              </LCard>
            )}

            {compatibility && (
              <LCard title="Совместимость" style={{ marginBottom: 16 }} size="small">
                <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 12 }}>
                  <LProgress type="circle" percent={Math.round(compatibility.overall_score * 100)} size={60} strokeColor={RISK_COLORS[compatibility.risk_level] || '#1890ff'} />
                  <div>
                    <strong>Балл: {compatibility.overall_score.toFixed(2)}</strong><br />
                    <LTag color={RISK_COLORS[compatibility.risk_level]}>{compatibility.risk_level.toUpperCase()}</LTag>
                    {compatibility.is_compatible && <LTag color="green">ОК</LTag>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {compatibility.axis_scores.map(ax => (
                    <div key={ax.axis} title={`${CRITERIA_LABELS[ax.axis] || ax.axis}: ${ax.score.toFixed(2)}`} style={{ textAlign: 'center' }}>
                      <LProgress type="circle" percent={Math.round(ax.score * 100)} size={40} strokeColor={ax.score >= 0.7 ? '#52c41a' : ax.score >= 0.4 ? '#faad14' : '#ff4d4f'} />
                      <div style={{ fontSize: 10, marginTop: 2 }}>{CRITERIA_LABELS[ax.axis] || ax.axis}</div>
                    </div>
                  ))}
                </div>
                {compatibility.recommendations.length > 0 && <LAlert type="info" message={compatibility.recommendations[0]} style={{ marginTop: 12 }} />}
              </LCard>
            )}

            {result && (
              <LCard title="Результаты" style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', gap: 24 }}>
                  <div><strong>Гипотеза:</strong> {result.hypothesis?.title || '-'}</div>
                  <div><strong>Ветвей:</strong> {result.scenario.branch_count}</div>
                  <div><strong>Время:</strong> {result.duration_ms.toFixed(0)}ms</div>
                </div>
              </LCard>
            )}

            {result && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                {result.ranked_branches.map(branch => (
                  <LBadge key={branch.rank} count={'#' + branch.rank} color={branch.rank === 1 ? '#52c41a' : '#1890ff'}>
                    <LCard size="small" hoverable onClick={() => setSelectedBranch(branch)} style={{ width: 260, cursor: 'pointer', border: branch.rank === 1 ? '2px solid #52c41a' : '1px solid #f0f0f0' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <LTag color={branch.branch_type === 'unexpected' ? 'purple' : branch.branch_type === 'radical' ? 'orange' : branch.branch_type === 'moderate' ? 'green' : 'blue'}>{BRANCH_TYPE_LABELS[branch.branch_type] || branch.branch_type}</LTag>
                        <strong style={{ fontSize: 13 }}>{branch.title}</strong>
                        <LProgress percent={Math.round(branch.quality_score * 100)} size="small" strokeColor={branch.quality_score >= 0.8 ? '#52c41a' : branch.quality_score >= 0.6 ? '#faad14' : '#ff4d4f'} />
                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>Влияние: {(branch.impact_score * 100).toFixed(0)}% | Противоречия: {branch.contradictions}</div>
                        <LButton size="small" icon={<SwapOutlined />} onClick={(e) => { e.stopPropagation(); toggleCompare(branch); }} type={compareBranches.find(b => b.rank === branch.rank) ? 'primary' : 'default'}>Сравнить</LButton>
                      </div>
                    </LCard>
                  </LBadge>
                ))}
              </div>
            )}

            {compareBranches.length >= 2 && <LButton type="primary" icon={<SwapOutlined />} onClick={() => setShowCompare(true)} style={{ marginBottom: 16 }}>Сравнить ({compareBranches.length})</LButton>}
            {!result && !exploreMutation.isPending && <LEmpty description="Введите идею и нажмите «Исследовать»" />}
          </>
        )},
        { key: 'hypotheses', label: <><BulbOutlined /> Гипотезы</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}><LSelect placeholder="Эпоха" value={epoch} onChange={setEpoch} options={epochOptions} style={{ width: 250 }} /></LCard>
            {hypsLoading ? <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div> : hypotheses.length === 0 ? <LEmpty description="Нет гипотез" /> : hypotheses.map(hyp => (
              <div key={hyp.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 12, borderBottom: '1px solid #f0f0f0' }}>
                <div><LTag>{hyp.type}</LTag> <strong>{hyp.title}</strong><div style={{ fontSize: 12, color: '#666' }}>{hyp.description}</div></div>
                <LButton type="primary" size="small" onClick={() => exploreFromHypothesis(hyp)}>Исследовать</LButton>
              </div>
            ))}
          </>
        )},
        { key: 'possibilities', label: <><ThunderboltOutlined /> Возможности</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}><LSelect placeholder="Эпоха" value={epoch} onChange={setEpoch} options={epochOptions} style={{ width: 250 }} /></LCard>
            {possLoading ? <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div> : possibilities.length === 0 ? <LEmpty description="Нет возможностей" /> : possibilities.map(p => (
              <div key={p.id} style={{ padding: 12, borderBottom: '1px solid #f0f0f0' }}>
                <LTag color="blue">{p.category}</LTag> <strong>{p.title_ru}</strong>
                <div style={{ fontSize: 12, color: '#666' }}>{p.description}</div>
              </div>
            ))}
          </>
        )},
        { key: 'history', label: <><HistoryOutlined /> История</>, children: (
          <>
            {history.length === 0 ? <LEmpty description="История пуста" /> : (
              <>
                {history.map(item => (
                  <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 12, borderBottom: '1px solid #f0f0f0' }}>
                    <div><strong>{item.prompt}</strong><div style={{ display: 'flex', gap: 8, marginTop: 4 }}><LTag>{item.epoch || 'Все эпохи'}</LTag><LTag color="blue">{item.result?.ranked_branches?.length || 0} ветвей</LTag><span style={{ fontSize: 12, color: '#999' }}>{new Date(item.timestamp).toLocaleString('ru-RU')}</span></div></div>
                    <LSpace><LButton size="small" onClick={() => loadFromHistory(item)}>Загрузить</LButton><LButton size="small" danger icon={<DeleteOutlined />} onClick={() => deleteFromHistory(item.id)} /></LSpace>
                  </div>
                ))}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, padding: 8, borderTop: '1px solid #f0f0f0' }}>
                  <LButton size="small" disabled={historyOffset === 0} onClick={() => setHistoryOffset(prev => Math.max(0, prev - historyLimit))}>‹ Назад</LButton>
                  <span style={{ fontSize: 12, color: '#666' }}>{historyOffset + 1}–{Math.min(historyOffset + history.length, historyCount)} из {historyCount}</span>
                  <LButton size="small" disabled={historyOffset + history.length >= historyCount} onClick={() => setHistoryOffset(prev => prev + historyLimit)}>Вперёд ›</LButton>
                </div>
              </>
            )}
          </>
        )},
        { key: 'deep', label: <><ClusterOutlined /> Глубокое исследование</>, children: (
          <>
            {activeTab === 'deep' && (
              <>
                <LCard style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
                    <LButton type="primary" disabled={deepLoading || !prompt} onClick={runDeepExploration} loading={deepLoading}>
                      Запустить глубокое исследование
                    </LButton>
                    <span style={{ fontSize: 12, color: '#999' }}>До 3 уровней ветвления</span>
                  </div>
                </LCard>
                {deepTree && (
                  <LCard title="Результат глубокого исследования" size="small">
                    <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
                      <div><strong>Узлов:</strong> {deepTree.total_nodes}</div>
                      <div><strong>Глубина:</strong> {deepTree.max_depth}</div>
                      <div><strong>Итог:</strong> {deepTree.summary}</div>
                    </div>
                    {deepTree.nodes && Object.keys(deepTree.nodes).length > 0 && (
                      <div style={{ maxHeight: 400, overflow: 'auto' }}>
                        {Object.values(deepTree.nodes).map((node: any) => (
                          <div key={node.id} style={{ padding: 8, borderBottom: '1px solid #f0f0f0', fontSize: 13 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <strong>{node.hypothesis_title || 'Без названия'}</strong>
                              <span style={{ fontSize: 11, color: '#999' }}>глубина {node.depth} • качество {Math.round((node.quality_score || 0) * 100)}%</span>
                            </div>
                            <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{node.children?.length || 0} дочерних ветвей</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </LCard>
                )}
                {!deepTree && !deepLoading && <LEmpty description="Нажмите «Запустить глубокое исследование»" />}
              </>
            )}
          </>
        )},
        { key: 'deep', label: <><ClusterOutlined /> Глубокое исследование</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
                <LButton type="primary" disabled={deepLoading || !prompt} onClick={runDeepExploration} loading={deepLoading}>
                  Запустить глубокое исследование
                </LButton>
                <span style={{ fontSize: 12, color: '#999' }}>До 3 уровней ветвления</span>
              </div>
            </LCard>
            {deepTree && (
              <LCard title="Результат глубокого исследования" size="small">
                <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
                  <div><strong>Узлов:</strong> {deepTree.total_nodes}</div>
                  <div><strong>Глубина:</strong> {deepTree.max_depth}</div>
                  <div><strong>Итог:</strong> {deepTree.summary}</div>
                </div>
                {deepTree.nodes && Object.keys(deepTree.nodes).length > 0 && (
                  <div style={{ maxHeight: 400, overflow: 'auto' }}>
                    {Object.values(deepTree.nodes).map((node: any) => (
                      <div key={node.id} style={{ padding: 8, borderBottom: '1px solid #f0f0f0', fontSize: 13 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong>{node.hypothesis_title || 'Без названия'}</strong>
                          <span style={{ fontSize: 11, color: '#999' }}>глубина {node.depth} • качество {Math.round((node.quality_score || 0) * 100)}%</span>
                        </div>
                        <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{node.children?.length || 0} дочерних ветвей</div>
                      </div>
                    ))}
                  </div>
                )}
              </LCard>
            )}
            {!deepTree && !deepLoading && <LEmpty description="Нажмите «Запустить глубокое исследование»" />}
          </>
        )},
        { key: 'free-points', label: <><BulbOutlined /> Свободные точки</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}>
              <LButton type="primary" disabled={freePointsLoading} onClick={loadFreePoints} loading={freePointsLoading}>
                Загрузить свободные точки мира
              </LButton>
              <span style={{ fontSize: 12, color: '#999', marginLeft: 12 }}>Где есть потенциал для развития сюжета</span>
            </LCard>
            {freePoints.length > 0 && (
              <div style={{ maxHeight: 500, overflow: 'auto' }}>
                {freePoints.map((fp: FreePoint) => (
                  <div key={fp.id} style={{ padding: 12, borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <LTag color="blue">{fp.category}</LTag>
                        <span style={{ fontSize: 11, color: '#999' }}>{fp.epoch || '—'}</span>
                      </div>
                      <strong>{fp.title}</strong>
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{fp.description}</div>
                    </div>
                    <LBadge count={Math.round((fp.confidence || 0) * 100)} color="#1890ff" style={{ fontSize: 12 }} />
                  </div>
                ))}
              </div>
            )}
            {!freePointsLoading && freePoints.length === 0 && <LEmpty description="Нажмите «Загрузить свободные точки мира»" />}
          </>
        )},
        { key: 'best-paths', label: <><FlagOutlined /> Лучшие пути</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
                <LButton type="primary" disabled={bestPathsLoading} onClick={loadBestPaths} loading={bestPathsLoading}>
                  Найти лучшие пути
                </LButton>
                <span style={{ fontSize: 12, color: '#ff7a45' }}>⚠ Дерево не сохраняется между сессиями</span>
              </div>
            </LCard>
            {bestPaths.length > 0 && (
              <div style={{ maxHeight: 400, overflow: 'auto' }}>
                {bestPaths.map((bp: any, i: number) => (
                  <div key={i} style={{ padding: 12, borderBottom: '1px solid #f0f0f0' }}>
                    <div style={{ fontWeight: 600 }}>Путь #{i + 1}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>{bp.nodes?.join(' → ') || '—'}</div>
                    <div style={{ fontSize: 12, marginTop: 4 }}><strong>Суммарный балл:</strong> {bp.total_score?.toFixed(2) || '—'}</div>
                  </div>
                ))}
              </div>
            )}
            {!bestPathsLoading && bestPaths.length === 0 && <LEmpty description="Дерево не создано. Сначала запустите глубокое исследование." />}
          </>
        )},
        { key: 'unified', label: <><ThunderboltOutlined /> Unified Pipeline</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
                <LButton type="primary" disabled={unifiedLoading || !prompt} onClick={runUnifiedPipeline} loading={unifiedLoading}>
                  Запустить Unified Pipeline
                </LButton>
                <span style={{ fontSize: 12, color: '#999' }}>Исследование → Story Engine → Валидация</span>
              </div>
            </LCard>
            {unifiedResult && (
              <LCard title="Результат Unified Pipeline" size="small">
                <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
                  {unifiedResult.data?.exploration && (
                    <div>
                      <strong>Исследование:</strong> {unifiedResult.data.exploration.branch_count} ветвей, лучший балл {unifiedResult.data.exploration.best_score?.toFixed(2)}
                    </div>
                  )}
                  {unifiedResult.data?.story && (
                    <div>
                      <strong>Story Engine:</strong> сгенерирован промпт ({unifiedResult.data.story.user_prompt.length} симв.)
                    </div>
                  )}
                  <div><strong>Шагов:</strong> {unifiedResult.data?.pipeline_steps?.length || 0}</div>
                  <div><strong>Время:</strong> {unifiedResult.duration_ms?.toFixed(0)}ms</div>
                </div>
                {unifiedResult.data?.story && (
                  <div style={{ marginTop: 12, padding: 12, background: '#f5f5f5', borderRadius: 6, fontSize: 12, maxHeight: 300, overflow: 'auto' }}>
                    <strong>system_instruction:</strong> {unifiedResult.data.story.system_instruction}
                    <br /><br />
                    <strong>user_prompt:</strong> {unifiedResult.data.story.user_prompt}
                  </div>
                )}
                {unifiedResult.summary && <div style={{ marginTop: 12, fontSize: 12, color: '#666' }}>{unifiedResult.summary}</div>}
              </LCard>
            )}
            {!unifiedResult && !unifiedLoading && <LEmpty description="Нажмите «Запустить Unified Pipeline»" />}
          </>
        )},
        { key: 'export', label: <><DownloadOutlined /> Экспорт</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
                <LButton type="primary" disabled={exportLoading || !result} onClick={runExport} loading={exportLoading}>
                  Экспортировать в Markdown
                </LButton>
                <LButton disabled={!exportResult?.data?.markdown} onClick={downloadMarkdown}>
                  Скачать .md
                </LButton>
              </div>
            </LCard>
            {exportResult?.data?.markdown && (
              <div style={{ maxHeight: 500, overflow: 'auto', padding: 12, background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6, fontSize: 12, fontFamily: 'monospace' }}>
                {exportResult.data.markdown}
              </div>
            )}
            {!exportResult && !exportLoading && <LEmpty description="Сначала выполните исследование, затем нажмите «Экспортировать в Markdown»" />}
          </>
        )},
        ...(canDev ? [externalSearchTab] : []),
        { key: 'feedback', label: <><StarOutlined /> Обратная связь</>, children: (
          <>
            <LCard style={{ marginBottom: 16 }}>
              <LButton type="primary" disabled={feedbackLoading} onClick={loadFeedback} loading={feedbackLoading}>
                Загрузить оценки ветвей
              </LButton>
            </LCard>
            {feedbackList.length > 0 && (
              <div style={{ maxHeight: 500, overflow: 'auto' }}>
                {feedbackList.map((fb: FeedbackItem) => (
                  <div key={fb.id} style={{ padding: 12, borderBottom: '1px solid #f0f0f0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <strong>{fb.branch_title}</strong>
                      <span style={{ fontSize: 12, color: '#999' }}>{fb.created_at}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <LTag color={fb.branch_type === 'unexpected' ? 'purple' : fb.branch_type === 'radical' ? 'orange' : fb.branch_type === 'moderate' ? 'green' : 'blue'}>{BRANCH_TYPE_LABELS[fb.branch_type] || fb.branch_type}</LTag>
                      <div>{'★'.repeat(fb.rating)}${'☆'.repeat(5 - fb.rating)}</div>
                    </div>
                    {fb.comment && <div style={{ fontSize: 12, color: '#666' }}>{fb.comment}</div>}
                  </div>
                ))}
              </div>
            )}
            {!feedbackLoading && feedbackList.length === 0 && <LEmpty description="Нет сохранённых оценок" />}
          </>
        )},
        ...(canDev ? [cacheStatsTab] : []),
      ]} />

      <LModal title={selectedBranch?.title || 'Детали ветви'} open={!!selectedBranch} onCancel={() => { setSelectedBranch(null); setGeneratedText(null); }} footer={selectedBranch ? [<LButton key="gen" type="primary" loading={generatingText} onClick={() => selectedBranch && generateTextFromBranch(selectedBranch)}>Сгенерировать текст</LButton>, <LButton key="story" type="primary" onClick={() => sendToStoryEngine(selectedBranch)}>Отправить в Story Engine</LButton>] : []} width={700}>
        {selectedBranch && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', gap: 16 }}><LTag>{BRANCH_TYPE_LABELS[selectedBranch.branch_type] || selectedBranch.branch_type}</LTag><span>#{selectedBranch.rank}</span></div>
            <LDivider />
            <h5>Критерии</h5>
            {Object.entries(CRITERIA_LABELS).map(([key, label]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ width: 120, fontSize: 13 }}>{label}</span>
                <LProgress percent={Math.round(selectedBranch.quality_score * 100)} size="small" style={{ flex: 1 }} />
              </div>
            ))}
            <LDivider />
            <div style={{ display: 'flex', gap: 16 }}>
              <div style={{ flex: 1 }}><strong>Сильные стороны:</strong>{selectedBranch.strengths.length > 0 ? selectedBranch.strengths.map((s, i) => <div key={i}><LTag color="green">{s}</LTag></div>) : <span style={{ color: '#999' }}>Нет</span>}</div>
              <div style={{ flex: 1 }}><strong>Слабые стороны:</strong>{selectedBranch.weaknesses.length > 0 ? selectedBranch.weaknesses.map((w, i) => <div key={i}><LTag color="red">{w}</LTag></div>) : <span style={{ color: '#999' }}>Нет</span>}</div>
            </div>
            <LDivider />
            <div style={{ display: 'flex', gap: 24 }}>
              <div><LProgress type="circle" percent={Math.round(selectedBranch.impact_score * 100)} size={50} /><div style={{ fontSize: 11 }}>Влияние</div></div>
              <div><LBadge count={selectedBranch.contradictions} showZero color={selectedBranch.contradictions > 0 ? 'red' : 'green'}><NodeIndexOutlined style={{ fontSize: 24 }} /></LBadge><div style={{ fontSize: 11 }}>Противоречия</div></div>
              <div><LStatistic title="Изменения" value={selectedBranch.delta_changes} /></div>
            </div>
            {generatedText && <><LDivider /><h5>Сгенерированный промпт</h5><LCard size="small" style={{ maxHeight: 300, overflow: 'auto' }}><span style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>{generatedText.user_prompt}</span></LCard></>}
            <LDivider />
            <h5>Оценить ветвь</h5>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {[1, 2, 3, 4, 5].map(v => <span key={v} onClick={() => setFeedbackRating(v)} style={{ cursor: 'pointer', fontSize: 20, color: v <= feedbackRating ? '#faad14' : '#d9d9d9' }}>★</span>)}
            </div>
            <LTextArea rows={2} placeholder="Комментарий..." value={feedbackComment} onChange={e => setFeedbackComment(e.target.value)} />
            <LButton size="small" onClick={() => submitFeedback(selectedBranch)}>Отправить</LButton>
          </div>
        )}
      </LModal>

      <LModal title="Сравнение ветвей" open={showCompare} onCancel={() => setShowCompare(false)} footer={null} width={900}>
        <div style={{ display: 'flex', gap: 16 }}>
          {compareBranches.map(branch => (
            <LCard key={branch.rank} size="small" style={{ flex: 1 }}>
              <h5>{branch.title}</h5>
              <LTag color={branch.rank === 1 ? 'green' : 'blue'}>#{branch.rank}</LTag>
              <LDivider />
              {Object.entries(CRITERIA_LABELS).map(([key, label]) => (
                <div key={key} style={{ marginBottom: 4 }}><span style={{ fontSize: 12 }}>{label}</span><LProgress percent={Math.round(branch.quality_score * 100)} size="small" strokeColor={branch.quality_score >= 0.8 ? '#52c41a' : '#faad14'} /></div>
              ))}
              <LDivider />
              <LStatistic title="Балл" value={branch.quality_score} precision={3} />
            </LCard>
          ))}
        </div>
      </LModal>
    </div>
  );
}

export default function WorldExplorerPage() { return <ProtectedRoute><WorldExplorerContent /></ProtectedRoute>; }