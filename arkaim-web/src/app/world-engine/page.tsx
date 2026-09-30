'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/shared/lib/api';
import { getTemporalChain, type TemporalChain } from '@/shared/api/contracts/temporal';
import { LCard, LTag, LSpace, LStatistic, LTable, LModal, LButton, LInput, LTabs, toast } from '@/shared/ui/light';
import { SearchOutlined, DatabaseOutlined, PictureOutlined, CheckCircleOutlined, SettingOutlined, GlobalOutlined, AppstoreOutlined, FileTextOutlined, ClockCircleOutlined } from '@ant-design/icons';

const API_BASE = '/book/world';

interface WorldStats {
  total_entities: number;
  total_categories: number;
  categories: Record<string, number>;
}

interface Entity {
  id: string;
  name: string;
  category: string;
  description: string;
  properties: Record<string, unknown>;
}

interface EntityRelation {
  source_id: string;
  target_id: string;
  relation_type: string;
  description?: string;
}

interface EntityContext {
  entity: Entity;
  relations: {
    outgoing_count: number;
    incoming_count: number;
    outgoing: EntityRelation[];
    incoming: EntityRelation[];
  };
}

interface WorldMode {
  mode: string;
  name: string;
  description: string;
}

interface WorldRule {
  id: string;
  name: string;
  name_ru: string;
  description: string;
  description_ru: string;
  rule_type: string;
  severity: string;
}

export default function WorldEnginePage() {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<WorldStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Entity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [entityContext, setEntityContext] = useState<EntityContext | null>(null);
  const [visualPrompt, setVisualPrompt] = useState('');
  const [modes, setModes] = useState<WorldMode[]>([]);
  const [rules, setRules] = useState<WorldRule[]>([]);
  const [categories, setCategories] = useState<Record<string, number>>({});
  // Глубокая ссылка /world-engine?entity_id=... — сущность открывается сразу во вкладке
  // «Контекст» через существующий контракт GET /book/world/entity/{id}/context.
  // Без query-параметра поведение страницы полностью обратимо (вкладка «Поиск»).
  const [activeTab, setActiveTab] = useState(() => (
    typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('entity_id') ? 'context' : 'search'
  ));
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedRule, setSelectedRule] = useState<WorldRule | null>(null);
  const [categoryEntities, setCategoryEntities] = useState<Entity[]>([]);
  // B2: «след расследования» — последовательность посещённых сущностей.
  // Позволяет вернуться назад без потери контекста.
  const [entityTrail, setEntityTrail] = useState<string[]>([]);
  // B3: временная цепочка кэшируется один раз — из неё фильтруются эпохи,
  // у которых backend реально указал данную сущность в entity_ids.
  const [temporalChain, setTemporalChain] = useState<TemporalChain | null>(null);
  const [temporalChainError, setTemporalChainError] = useState(false);

  const loadStats = async () => {
    try { const data = await api.get<{ stats: WorldStats }>("/book/world/summary"); setStats(data.stats); }
    catch (e) { console.error('Error loading stats:', e); }
  };

  const loadModes = async () => {
    try { const data = await api.get<{ modes: WorldMode[] }>("/book/world/modes"); setModes(data.modes); }
    catch (e) { console.error('Error loading modes:', e); }
  };

  const loadRules = async () => {
    try { const data = await api.get<{ rules: WorldRule[] }>("/book/world/rules"); setRules(data.rules); }
    catch (e) { console.error('Error loading rules:', e); }
  };

  const loadCategories = async () => {
    try { const data = await api.get<{ categories: Record<string, number> }>("/book/world/categories"); setCategories(data.categories); }
    catch (e) { console.error('Error loading categories:', e); }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStats();
      void loadModes();
      void loadRules();
      void loadCategories();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const loadCategoryEntities = async (category: string) => {
    setSelectedCategory(category);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/search`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: category, limit: 50 }) });
      const data = await res.json();
      setCategoryEntities(Array.isArray(data.world_model) ? data.world_model as Entity[] : []);
      setActiveTab('search');
    } catch { toast.error('Ошибка загрузки категории'); }
    finally { setLoading(false); }
  };

  const handleSearch = async (query: string) => {
    if (!query) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/search`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, limit: 20 }) });
      const data = await res.json();
      setSearchResults(Array.isArray(data.world_model) ? data.world_model as Entity[] : []);
      // B2: поисковый запрос живёт в URL — refresh не теряет поиск.
      const url = new URL(window.location.href);
      url.searchParams.set('q', query);
      window.history.replaceState(null, '', url.toString());
    } catch { toast.error('Ошибка поиска'); }
    finally { setLoading(false); }
  };

  const loadEntityContext = async (entityId: string) => {
    try {
      const data = await api.get<EntityContext>(`/book/world/entity/${entityId}/context`);
      setEntityContext(data);
      setSelectedEntity(data.entity);
      // B2: обновляем след. Если сущность уже посещалась — откатываемся к ней,
      // иначе дописываем в конец. Повторный клик по текущей не создаёт дублей.
      setEntityTrail(prev => {
        const idx = prev.lastIndexOf(entityId);
        if (idx >= 0) return prev.slice(0, idx + 1);
        return prev[prev.length - 1] === entityId ? prev : [...prev, entityId];
      });
      // Поле ввода синхронизируем с реально загруженной сущностью,
      // чтобы после перехода по связи ID в поле не расходился с карточкой.
      const input = document.getElementById('context-entity-id') as HTMLInputElement | null;
      if (input) input.value = entityId;
      // A3: выбранная сущность отражается в URL — refresh и deep link восстанавливают её
      const url = new URL(window.location.href);
      url.searchParams.set('entity_id', entityId);
      window.history.replaceState(null, '', url.toString());
    } catch { toast.error('Ошибка загрузки контекста'); }
  };

  const openTemporalEntityContext = (entityId: string) => {
    const query = new URLSearchParams({ entity: entityId });
    const sessionId = new URLSearchParams(window.location.search).get('session');
    if (sessionId) query.set('session', sessionId);
    window.location.href = `/temporal?${query.toString()}`;
  };

  // B3: переход сущность → эпоха. На /temporal параметр epoch = era_id узла цепочки.
  const openEpochForEntity = (entityId: string, eraId: string) => {
    const query = new URLSearchParams({ entity: entityId, epoch: eraId });
    const sessionId = new URLSearchParams(window.location.search).get('session');
    if (sessionId) query.set('session', sessionId);
    window.location.href = `/temporal?${query.toString()}`;
  };

  // B3: загрузка временной цепочки один раз; ошибка фиксируется, чтобы не долбить API.
  useEffect(() => {
    if (temporalChain || temporalChainError) return;
    let cancelled = false;
    getTemporalChain()
      .then(chain => { if (!cancelled) setTemporalChain(chain); })
      .catch(() => { if (!cancelled) setTemporalChainError(true); });
    return () => { cancelled = true; };
  }, [temporalChain, temporalChainError]);

  // B2: восстановление поискового запроса из ?q=... при загрузке страницы.
  // Срабатывает один раз после монтирования; результат кладётся в URL снова — без ветвлений.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    if (!q) return;
    const timer = setTimeout(() => {
      setSearchQuery(q);
      void handleSearch(q);
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  // Глубокая ссылка: автозагрузка контекста сущности из ?entity_id=...
  // Отложенный вызов после монтировки вкладки «Контекст», чтобы поле ввода уже
  // существовал в DOM и в теле эффекта не было синхронной записи состояния.
  useEffect(() => {
    const entityId = new URLSearchParams(window.location.search).get('entity_id');
    if (!entityId) return;
    const timer = setTimeout(() => {
      const el = document.getElementById('context-entity-id') as HTMLInputElement | null;
      if (el) el.value = entityId;
      void loadEntityContext(entityId);
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  const generateVisualPrompt = async (entityId: string) => {
    try {
      const data = await api.get<{ prompt: string }>(`/book/world/entity/${entityId}/visual-prompt?style=cinematic`);
      setVisualPrompt(data.prompt);
    } catch { toast.error('Ошибка генерации промпта'); }
  };

  // B1: полный список связей с переходом сущность → связанная сущность.
  // Исходящая связь ведёт в target_id, входящая — в source_id (кто ссылается).
  const renderRelationList = (
    title: string,
    list: EntityRelation[] | undefined,
    pickTarget: (r: EntityRelation) => string,
  ) => {
    if (!list || list.length === 0) return null;
    return (
      <div style={{ marginBottom: 16 }}>
        <p style={{ margin: '0 0 6px' }}><strong>{title} ({list.length})</strong></p>
        <div style={{ maxHeight: 260, overflowY: 'auto', display: 'grid', gap: 6 }}>
          {list.map((rel, i) => {
            const targetId = pickTarget(rel);
            return (
              <button
                key={`${rel.source_id}|${rel.relation_type}|${rel.target_id}|${i}`}
                type="button"
                onClick={() => { void loadEntityContext(targetId); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                style={{
                  display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
                  textAlign: 'left', padding: '8px 10px', borderRadius: 6, cursor: 'pointer',
                  background: 'var(--surface-bg)', border: '1px solid var(--card-border)',
                  color: 'var(--foreground)',
                }}
                title={`Перейти к ${targetId}`}
              >
                <LTag style={{ margin: 0 }}>{rel.relation_type}</LTag>
                <span style={{ color: '#1890ff' }}>{targetId}</span>
                {rel.description && (
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>— {rel.description}</span>
                )}
                <span style={{ marginLeft: 'auto', fontSize: 12, color: '#94a3b8' }}>→</span>
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 150 },
    { title: 'Название', dataIndex: 'name', key: 'name' },
    { title: 'Категория', dataIndex: 'category', key: 'category',
      render: (v: unknown) => <LTag color="blue">{String(v)}</LTag> },
    { title: 'Описание', dataIndex: 'description', key: 'description',
      render: (v: unknown) => String(v).substring(0, 100) + '...' },
    { title: 'Действия', key: 'actions',
      render: (_: unknown, record: unknown) => {
        const r = record as Entity;
        return <LSpace><LButton size="small" onClick={() => loadEntityContext(r.id)}>Контекст</LButton><LButton size="small" onClick={() => generateVisualPrompt(r.id)}>Промпт</LButton></LSpace>;
      },
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><GlobalOutlined /> World Engine</h2>
      <p style={{ color: '#999' }}>Вычислимая модель мира книги «Наследие Аркаима» — 547 сущностей, 287 связей, 55 форм</p>

      {stats && (
        /* minWidth: 0 + flexWrap: без minWidth flex-элементы не сжимаются
           ниже ширины содержимого и на узких экранах выходят за вьюпорт. */
        <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 140px', minWidth: 0 }}><LCard><LStatistic title="Сущностей" value={stats.total_entities} prefix={<DatabaseOutlined />} /></LCard></div>
          <div style={{ flex: '1 1 140px', minWidth: 0 }}><LCard><LStatistic title="Категорий" value={stats.total_categories} prefix={<AppstoreOutlined />} /></LCard></div>
          <div style={{ flex: '1 1 140px', minWidth: 0 }}><LCard><LStatistic title="Режимов" value={modes.length} prefix={<SettingOutlined />} /></LCard></div>
          <div style={{ flex: '1 1 140px', minWidth: 0 }}><LCard><LStatistic title="Правил" value={rules.length} prefix={<CheckCircleOutlined />} /></LCard></div>
        </div>
      )}

      <LTabs activeKey={activeTab} onChange={setActiveTab} items={[
        { key: 'search', label: <><SearchOutlined /> Поиск</>, children: (
          <LCard>
            <LSpace style={{ marginBottom: 16, flexWrap: 'wrap' }}>
              <LInput placeholder="Поиск по миру (например: Аркаим, Гиперборея, философия)" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} style={{ width: 'min(400px, 100%)' }} />
              <LButton type="primary" icon={<SearchOutlined />} loading={loading} onClick={() => handleSearch(searchQuery)}>Найти</LButton>
            </LSpace>
            {selectedCategory && (
              <div style={{ marginBottom: 16 }}>
                <LTag color="purple" style={{ cursor: 'default' }} onClick={() => { setSelectedCategory(null); setCategoryEntities([]); }}>
                  ✕ Категория: {selectedCategory}
                </LTag>
              </div>
            )}
            <LTable columns={columns} dataSource={selectedCategory ? categoryEntities : searchResults} rowKey="id" pagination={{ pageSize: 10 }} />
          </LCard>
        )},
        { key: 'categories', label: <><AppstoreOutlined /> Категории</>, children: (
          <LCard>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
              {Object.entries(categories).map(([cat, count]) => (
                <div key={cat} style={{ flex: '1 1 calc(25% - 16px)', minWidth: 150 }}>
                  <LCard hoverable onClick={() => loadCategoryEntities(cat)} style={{ textAlign: 'center' }}>
                    <LStatistic title={cat} value={count} />
                  </LCard>
                </div>
              ))}
            </div>
          </LCard>
        )},
        { key: 'modes', label: <><SettingOutlined /> Режимы</>, children: (
          <LCard title="Режимы работы World Engine">
            <p style={{ marginBottom: 16 }}>Выберите режим для перехода к соответствующему функционалу:</p>
            {modes.map((mode) => {
              const routes: Record<string, string> = { 'dialog': '/book', 'story': '/story', 'movie': '/film-studio', 'quest': '/world-explorer', 'game': '/world-explorer', 'research': '/search', 'lesson': '/library', 'timeline': '/map', 'documentary': '/film-studio', 'illustration': '/visual-view' };
              return (
                <div key={mode.mode} style={{ cursor: 'pointer', padding: 12, marginBottom: 8, borderRadius: 8, border: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                  onClick={() => { window.location.href = routes[mode.mode] || '/world-engine'; }}>
                  <div><strong>{mode.name}</strong><div style={{ fontSize: 12, color: '#666' }}>{mode.description}</div></div>
                  <LSpace><LTag color="green">{mode.mode}</LTag><span style={{ color: '#1890ff' }}>→</span></LSpace>
                </div>
              );
            })}
          </LCard>
        )},
        { key: 'rules', label: <><CheckCircleOutlined /> Правила</>, children: (
          <LCard title="Правила консистентности мира">
            <p style={{ marginBottom: 16 }}>Правила определяют допустимость построений в мире книги:</p>
            {rules.map((rule) => (
              <div key={rule.id} style={{ cursor: 'pointer', padding: 12, marginBottom: 8, borderRadius: 8, border: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                onClick={() => setSelectedRule(rule)}>
                <div><strong>{rule.name_ru}</strong><div style={{ fontSize: 12, color: '#666' }}>{rule.description_ru?.substring(0, 100) + '...'}</div></div>
                <LSpace><LTag color={rule.severity === 'hard' ? 'red' : 'orange'}>{rule.severity}</LTag><LTag>{rule.rule_type}</LTag><span style={{ color: '#1890ff' }}>Подробнее →</span></LSpace>
              </div>
            ))}

            <LModal open={!!selectedRule} title={selectedRule?.name_ru || 'Правило'} onCancel={() => setSelectedRule(null)}
              width={600}
              footer={<><LButton onClick={() => setSelectedRule(null)}>Закрыть</LButton><LButton type="primary" onClick={() => window.location.href = '/editor'}>Открыть редактор</LButton></>}>
              {selectedRule && (
                <div>
                  <p><strong>Описание:</strong> {selectedRule.description_ru}</p>
                  <p><strong>Тип:</strong> <LTag>{selectedRule.rule_type}</LTag></p>
                  <p><strong>Серьёзность:</strong> <LTag color={selectedRule.severity === 'hard' ? 'red' : 'orange'}>{selectedRule.severity}</LTag></p>
                </div>
              )}
            </LModal>
          </LCard>
        )},
        { key: 'visual', label: <><PictureOutlined /> Визуал</>, children: (
          <>
            {stats && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 24 }}>
                {Object.entries(stats.categories || {}).map(([cat, count]) => (
                  <div key={cat} style={{ flex: '1 1 calc(25% - 16px)', minWidth: 150 }}>
                    <LCard hoverable onClick={() => loadCategoryEntities(cat)} style={{ textAlign: 'center', cursor: 'pointer' }}>
                      <LStatistic title={cat} value={count} />
                      <div style={{ marginTop: 8, fontSize: 12, color: '#1890ff' }}>Нажмите для поиска →</div>
                    </LCard>
                  </div>
                ))}
              </div>
            )}
            <LCard title="Генерация визуального промпта">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <LSpace style={{ flexWrap: 'wrap' }}>
                  <LInput placeholder="ID сущности (например: region_arkaim)" id="visual-entity-id" style={{ width: 'min(400px, 100%)' }} />
                  <LButton type="primary" icon={<PictureOutlined />} onClick={() => {
                    const el = document.getElementById('visual-entity-id') as HTMLInputElement;
                    if (el) generateVisualPrompt(el.value);
                  }}>Генерировать</LButton>
                </LSpace>
                {visualPrompt && (
                  <LCard size="small" title="Промпт" style={{ marginTop: 8 }}>
                    <p style={{ fontSize: 13 }}>{visualPrompt}</p>
                  </LCard>
                )}
              </div>
            </LCard>
          </>
        )},
        { key: 'context', label: <><FileTextOutlined /> Контекст</>, children: (
          <LCard title="Контекст сущности">
            <p style={{ marginBottom: 16 }}>Введите ID сущности для просмотра её контекста и связей:</p>
            <LSpace style={{ marginBottom: 16, flexWrap: 'wrap' }}>
              <LInput placeholder="ID сущности (например: region_arkaim)" id="context-entity-id" style={{ width: 'min(400px, 100%)' }} />
              <LButton type="primary" icon={<SearchOutlined />} onClick={() => {
                const el = document.getElementById('context-entity-id') as HTMLInputElement;
                if (el) loadEntityContext(el.value);
              }}>Загрузить</LButton>
            </LSpace>

            {selectedEntity && (
              <>
                {entityTrail.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginTop: 16, marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>След:</span>
                    {entityTrail.map((id, i) => (
                      <React.Fragment key={`${id}-${i}`}>
                        {i > 0 && <span style={{ color: '#94a3b8' }}>→</span>}
                        <button
                          type="button"
                          disabled={i === entityTrail.length - 1}
                          onClick={() => { void loadEntityContext(id); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                          title={i === entityTrail.length - 1 ? 'Текущая сущность' : `Вернуться к ${id}`}
                          style={{
                            padding: '2px 8px', borderRadius: 4, fontSize: 12, cursor: i === entityTrail.length - 1 ? 'default' : 'pointer',
                            background: i === entityTrail.length - 1 ? '#1890ff' : 'var(--surface-bg)',
                            color: i === entityTrail.length - 1 ? '#fff' : '#1890ff',
                            border: '1px solid var(--card-border)',
                          }}
                        >
                          {id}
                        </button>
                      </React.Fragment>
                    ))}
                  </div>
                )}

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 16, padding: 16, border: '1px solid var(--card-border)', borderRadius: 8 }}>
                  <div style={{ flex: '1 1 50%' }}><strong>ID:</strong> {selectedEntity.id}</div>
                  <div style={{ flex: '1 1 50%' }}><strong>Название:</strong> {selectedEntity.name}</div>
                  <div style={{ flex: '1 1 50%' }}><strong>Категория:</strong> <LTag color="blue">{selectedEntity.category}</LTag></div>
                  <div style={{ flex: '1 1 100%' }}><strong>Описание:</strong> {selectedEntity.description}</div>
                  <div style={{ flex: '1 1 100%', marginTop: 8 }}>
                    <LSpace>
                      <LButton
                        type="primary"
                        icon={<ClockCircleOutlined />}
                        onClick={() => openTemporalEntityContext(selectedEntity.id)}
                      >
                        Временной контекст →
                      </LButton>
                    </LSpace>
                  </div>
                </div>

                {selectedEntity && (
                  <LCard
                    title={<><ClockCircleOutlined /> Связанные эпохи и события</>}
                    style={{ marginTop: 16 }}
                  >
                    {!temporalChain && !temporalChainError && (
                      <p style={{ color: '#999', margin: 0 }}>Загружаем временную цепочку…</p>
                    )}
                    {temporalChainError && (
                      <p style={{ color: '#999', margin: 0 }}>
                        Не удалось загрузить временную цепочку. Откройте «Время мира» напрямую — там тоже есть
                        временной контекст этой сущности.
                      </p>
                    )}
                    {temporalChain && (() => {
                      const linked = temporalChain.nodes.filter(
                        node => Array.isArray(node.entity_ids) && node.entity_ids.includes(selectedEntity.id),
                      );
                      if (linked.length === 0) {
                        return (
                          <p style={{ color: '#999', margin: 0 }}>
                            Backend не указал связанных эпох этой сущности в временной цепочке.
                          </p>
                        );
                      }
                      return (
                        <div style={{ display: 'grid', gap: 6 }}>
                          {linked.map(node => (
                            <button
                              key={node.id}
                              type="button"
                              onClick={() => openEpochForEntity(selectedEntity.id, node.era_id)}
                              title={`Открыть эпоху «${node.label}» во Времени мира`}
                              style={{
                                display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
                                textAlign: 'left', padding: '8px 10px', borderRadius: 6, cursor: 'pointer',
                                background: 'var(--surface-bg)', border: '1px solid var(--card-border)',
                                color: 'var(--foreground)',
                              }}
                            >
                              <ClockCircleOutlined style={{ color: '#1890ff' }} />
                              <span style={{ color: '#1890ff' }}>{node.label}</span>
                              {node.bounds?.start && (
                                <span style={{ fontSize: 12, color: '#94a3b8' }}>
                                  {node.bounds.start}{node.bounds.end ? ` — ${node.bounds.end}` : ''}
                                </span>
                              )}
                              {node.event_ids.length > 0 && (
                                <LTag style={{ margin: 0 }}>событий: {node.event_ids.length}</LTag>
                              )}
                              <span style={{ marginLeft: 'auto', fontSize: 12, color: '#94a3b8' }}>→</span>
                            </button>
                          ))}
                        </div>
                      );
                    })()}
                  </LCard>
                )}

                {entityContext?.relations && (
                  <LCard title="Связи" style={{ marginTop: 16 }}>
                    <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
                      <LStatistic title="Исходящих" value={entityContext.relations.outgoing_count} />
                      <LStatistic title="Входящих" value={entityContext.relations.incoming_count} />
                    </div>
                    {renderRelationList('Исходящие связи', entityContext.relations.outgoing, r => r.target_id)}
                    {renderRelationList('Входящие связи', entityContext.relations.incoming, r => r.source_id)}
                    {(!entityContext.relations.outgoing?.length && !entityContext.relations.incoming?.length) && (
                      <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
                        <p>У этой сущности пока нет связей в графе мира.</p>
                      </div>
                    )}
                  </LCard>
                )}
              </>
            )}

            {!selectedEntity && (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                <FileTextOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <p>Введите ID сущности и нажмите «Загрузить»</p>
                <p style={{ fontSize: 12 }}>Примеры: region_arkaim, region_hyperborea</p>
              </div>
            )}
          </LCard>
        )},
      ]} />
    </div>
  );
}