'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { LCard, LButton, LSelect, LSlider, LSpace, LTag, LTabs, LProgress, LModal, LAlert, LSpin, LEmpty, LStatistic, LBadge, LDivider, LTextArea, LAvatar, toast } from '@/shared/ui/light';
import { ExperimentOutlined, ThunderboltOutlined, HistoryOutlined, DeleteOutlined, SwapOutlined, BranchesOutlined, BulbOutlined, NodeIndexOutlined, StarOutlined } from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ProtectedRoute } from '@/shared/lib/guards';
import { useWsEvent } from '@/shared/lib/ws-hooks';

type Epoch = { id: string; name: string; name_ru: string; order: number };
type Hypothesis = { id: string; title: string; description: string; type: string; epoch: string; confidence: number; tags: string[] };
type RankedBranch = { rank: number; branch_type: string; title: string; quality_score: number; quality_summary: string; strengths: string[]; weaknesses: string[]; impact_score: number; contradictions: number; delta_changes: number };
type ExplorationResult = { request: { prompt: string; epoch?: string; location?: string; branch_count: number }; hypothesis: Hypothesis | null; scenario: { branch_count: number; best_branch_id: string; summary: string }; ranked_branches: RankedBranch[]; duration_ms: number; summary: string };
type CompatibilityResult = { overall_score: number; is_compatible: boolean; risk_level: string; axis_scores: { axis: string; score: number; violations_count: number; warnings_count: number }[]; violations_count: number; warnings_count: number; recommendations: string[] };
type Possibility = { id: string; title: string; title_ru: string; description: string; category: string; confidence: number; tags: string[] };
type HistoryItem = { id: string; timestamp: number; prompt: string; epoch?: string; result: ExplorationResult };
type HistoryApiItem = { id: string | number; created_at: string; prompt: string; epoch?: string; result?: ExplorationResult; duration_ms?: number; summary?: string };
type GeneratedTextResponse = { system_instruction: string; user_prompt: string };

const RISK_COLORS: Record<string, string> = { low: '#52c41a', medium: '#faad14', high: '#ff7a45', rejected: '#ff4d4f' };
const BRANCH_TYPE_LABELS: Record<string, string> = { conservative: 'Консервативное', moderate: 'Умеренное', radical: 'Радикальное', unexpected: 'Неожиданное' };
const CRITERIA_LABELS: Record<string, string> = { canon_alignment: 'Канон', logical_consistency: 'Логика', thematic_depth: 'Глубина', dramatic_potential: 'Драма', originality: 'Оригинал' };
const PROGRESS_STEPS = ['Проверка совместимости', 'Генерация гипотез', 'Моделирование', 'Влияние', 'Противоречия', 'Изменения', 'Оценка', 'Ранжирование'];

async function loadHistory(): Promise<HistoryItem[]> {
  try {
    const res = await api.get<{ data: HistoryApiItem[] }>('/book/world-explorer/history?limit=50');
    return (res.data || []).map((item: HistoryApiItem) => ({
      id: String(item.id), timestamp: new Date(item.created_at).getTime(), prompt: item.prompt, epoch: item.epoch,
      result: item.result || { request: { prompt: item.prompt, branch_count: 0 }, hypothesis: null, scenario: { branch_count: 0, best_branch_id: '', summary: '' }, ranked_branches: [], duration_ms: item.duration_ms || 0, summary: item.summary || '' },
    }));
  } catch { return []; }
}

async function saveHistory(item: HistoryItem) {
  try { await api.post('/book/world-explorer/history', { prompt: item.prompt, epoch: item.epoch, branch_count: item.result?.request?.branch_count || 3, hypothesis_id: item.result?.hypothesis?.id || null, hypothesis_title: item.result?.hypothesis?.title || null, result_json: JSON.stringify(item.result), summary: item.result?.summary || '', overall_score: item.result?.ranked_branches?.[0]?.quality_score || 0, branch_count_actual: item.result?.ranked_branches?.length || 0, duration_ms: item.result?.duration_ms || 0 }); }
  catch { }
}

function WorldExplorerContent() {
  const [prompt, setPrompt] = useState('');
  const [epoch, setEpoch] = useState<string | undefined>();
  const [branchCount, setBranchCount] = useState(3);
  const [result, setResult] = useState<ExplorationResult | null>(null);
  const [compatibility, setCompatibility] = useState<CompatibilityResult | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<RankedBranch | null>(null);
  const [compareBranches, setCompareBranches] = useState<RankedBranch[]>([]);
  const [showCompare, setShowCompare] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [progress, setProgress] = useState(-1);
  const [activeTab, setActiveTab] = useState('explore');
  const [generatedText, setGeneratedText] = useState<{ system_instruction: string; user_prompt: string } | null>(null);
  const [generatingText, setGeneratingText] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState('');

  const { data: epochsData } = useQuery({ queryKey: ['we-epochs'], queryFn: () => api.get<{ data: Epoch[] }>('/book/world-explorer/epochs') });
  const epochs = epochsData?.data || [];
  const { data: statsData } = useQuery({ queryKey: ['we-stats'], queryFn: () => api.get<{ data: Record<string, number> }>('/book/world-explorer/stats') });
  const { data: hypsData, isLoading: hypsLoading } = useQuery({ queryKey: ['we-hypotheses', epoch], queryFn: () => api.get<{ data: Hypothesis[] }>(`/book/world-explorer/hypotheses/${epoch || 'satya_yuga'}?limit=10`), enabled: activeTab === 'hypotheses' });
  const hypotheses = hypsData?.data || [];
  const { data: possData, isLoading: possLoading } = useQuery({ queryKey: ['we-possibilities', epoch], queryFn: () => api.get<{ data: Possibility[] }>(`/book/world-explorer/possibilities/${epoch || 'satya_yuga'}?limit=10`), enabled: activeTab === 'possibilities' });
  const possibilities = possData?.data || [];

  useEffect(() => { loadHistory().then(setHistory); }, []);

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

  const epochOptions = epochs.map(e => ({ value: e.id, label: e.name_ru }));

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}><h2 style={{ margin: 0 }}><BranchesOutlined style={{ marginRight: 8 }} />Исследование мира</h2><span style={{ color: '#999' }}>Исследуйте альтернативные линии развития мира книги</span></div>

      {statsData?.data && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <LStatistic title="Эпох" value={statsData.data.epochs_count || 0} />
          <LStatistic title="Локаций" value={statsData.data.locations_count || 0} />
          <LStatistic title="Паттернов" value={statsData.data.patterns_count || 0} />
          <LStatistic title="Событий" value={statsData.data.events_count || 0} />
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
                <span style={{ color: '#999', fontSize: 12 }}>{PROGRESS_STEPS[progress] || 'Завершение...'}</span>
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
        { key: 'history', label: <><HistoryOutlined /> История</>, children: history.length === 0 ? <LEmpty description="История пуста" /> : history.map(item => (
          <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 12, borderBottom: '1px solid #f0f0f0' }}>
            <div><strong>{item.prompt}</strong><div style={{ display: 'flex', gap: 8, marginTop: 4 }}><LTag>{item.epoch || 'Все эпохи'}</LTag><LTag color="blue">{item.result?.ranked_branches?.length || 0} ветвей</LTag><span style={{ fontSize: 12, color: '#999' }}>{new Date(item.timestamp).toLocaleString('ru-RU')}</span></div></div>
            <LSpace><LButton size="small" onClick={() => loadFromHistory(item)}>Загрузить</LButton><LButton size="small" danger icon={<DeleteOutlined />} onClick={() => deleteFromHistory(item.id)} /></LSpace>
          </div>
        ))},
      ]} />

      <LModal title={selectedBranch?.title || 'Детали ветви'} open={!!selectedBranch} onCancel={() => { setSelectedBranch(null); setGeneratedText(null); }} footer={selectedBranch ? [<LButton key="gen" type="primary" loading={generatingText} onClick={() => selectedBranch && generateTextFromBranch(selectedBranch)}>Сгенерировать текст</LButton>] : []} width={700}>
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