// app.js — Arkaim Web UI

document.addEventListener('DOMContentLoaded', () => {
  loadUser();
  initTheme();

  const page = document.body.className;
  if (page === 'page-book') loadBookMeta();
  if (page === 'page-about') loadAbout();
  if (page === 'page-profile') loadProfile();
  if (page === 'page-history') loadHistory();
  // WebSocket на всех страницах для персональных уведомлений
  connectWS();
});

// ── Theme ──────────────────────────

function initTheme() {
  const saved = localStorage.getItem('theme');
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.body.classList.add('dark');
    updateThemeIcon(true);
  }
}

function toggleTheme() {
  const isDark = document.body.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = isDark ? '☀️' : '🌙';
}

// ── API helper ────────────────────────

async function api(path, opts = {}) {
  const resp = await fetch(path, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, ...opts });
  if (resp.status === 401) { window.location.href = '/auth/login'; return null; }
  return resp.json();
}

async function loadUser() {
  const data = await api('/auth/me');
  if (!data) return;
  const u = data.user;
  const nameEl = document.getElementById('navUserName');
  if (nameEl) nameEl.textContent = u.display_name || u.username || u.id;
  const uploadLink = document.getElementById('navUpload');
  if (uploadLink && (u.role === 'editor' || u.role === 'admin')) uploadLink.style.display = 'inline';
  const adminLink = document.getElementById('navAdmin');
  if (adminLink && u.role === 'admin') adminLink.style.display = 'inline';
  if (document.body.classList.contains('page-admin') && u.role === 'admin') loadAdmin();
}

// ── Book page ────────────────────────

async function loadBookMeta() {
  const [genome, profile] = await Promise.all([
    api('/book/genome').catch(() => null),
    api('/book/reader/profile').catch(() => null),
  ]);

  const themesEl = document.getElementById('bookThemes');
  if (themesEl && genome) {
    const themes = genome.themes || [];
    themesEl.textContent = themes.map(t => t.name || t).join(', ') || '—';
  }

  const topicList = document.getElementById('topicList');
  if (topicList && profile) {
    const topics = profile.topics || [];
    if (topics.length === 0) {
      topicList.innerHTML = '<div class="topic-item">Вы ещё не задавали вопросов</div>';
    } else {
      topicList.innerHTML = topics.map(t =>
        `<div class="topic-item">
          <span class="topic-name">${t.name}</span>
          <span class="topic-depth">${(t.depth * 100).toFixed(0)}%</span>
          <span class="topic-count">${t.questions} вопр.</span>
        </div>`
      ).join('');
    }
  }
}

// ── About page ───────────────────────

async function loadAbout() {
  const genome = await api('/book/genome').catch(() => null);
  if (!genome) return;

  setCard('aboutCharacters', 'list', genome.characters?.slice(0, 10).map(c =>
    `<li><strong>${c.name}</strong>${c.description ? ' — ' + c.description.slice(0, 100) : ''}</li>`
  ).join('') || 'Нет данных');

  setCard('aboutThemes', 'list', genome.themes?.slice(0, 10).map(t =>
    `<li><strong>${t.name}</strong>${t.description ? ' — ' + t.description.slice(0, 100) : ''}</li>`
  ).join('') || 'Нет данных');

  setCard('aboutSymbols', 'list', (genome.symbols || []).slice(0, 8).map(s =>
    `<li><strong>${s.name}</strong>${s.meaning ? ' — ' + s.meaning.slice(0, 100) : ''}</li>`
  ).join('') || 'Нет данных');

  setCard('aboutConflicts', 'list', (genome.conflicts || []).slice(0, 6).map(c =>
    `<li><strong>${c.name}</strong> (${c.type || ''})</li>`
  ).join('') || 'Нет данных');

  setCard('aboutEntities', 'list', (genome.world_entities || []).slice(0, 8).map(e =>
    `<li><strong>${e.name}</strong> — ${(e.description || '').slice(0, 80)}</li>`
  ).join('') || 'Нет данных');

  setCard('aboutValues', 'list', (genome.values || []).slice(0, 8).map(v =>
    `<li><strong>${v.name}</strong>${v.description ? ' — ' + v.description.slice(0, 100) : ''}</li>`
  ).join('') || 'Нет данных');
}

function setCard(id, tag, html) {
  const el = document.getElementById(id);
  if (!el) return;
  if (tag === 'list') el.querySelector('.about-loading')?.remove();
  el.innerHTML += `<ul>${html}</ul>`;
}

// ── Profile page ─────────────────────

async function loadProfile() {
  const profile = await api('/book/reader/profile').catch(() => null);
  if (!profile) return;

  const summary = document.getElementById('profileSummary');
  if (summary) summary.textContent = `Всего вопросов: ${profile.questions_total}, тем: ${(profile.topics || []).length}`;

  const topicsEl = document.getElementById('profileTopics');
  if (topicsEl) {
    const topics = profile.topics || [];
    const listEl = topicsEl.querySelector('.topics-loading') || topicsEl.querySelector('div');
    if (listEl) {
      if (topics.length === 0) {
        listEl.innerHTML = '<p>Вы ещё не задавали вопросов. Откройте <a href="/_ui/book">страницу книги</a>.</p>';
      } else {
        listEl.outerHTML = '<div class="topics-list">' +
          topics.map(t =>
            `<div class="topic-item">
              <span class="topic-name">${t.name}</span>
              <span class="topic-depth">глубина: ${(t.depth * 100).toFixed(0)}%</span>
              <span class="topic-count">${t.questions} вопросов</span>
            </div>`
          ).join('') + '</div>';
      }
    }
  }
}

// ── Admin ────────────────────────────

async function loadAdmin() {
  loadUsers();
  loadInvites();
  loadSessions();
  loadApiKeys();
  loadSuggestions();
  loadAdminStats();
}

async function loadUsers() {
  const data = await api('/auth/admin/users').catch(() => []);
  const tbody = document.getElementById('usersBody');
  const count = document.getElementById('userCount');
  if (count) count.textContent = data.length + ' чел.';
  if (!tbody) return;
  if (!data.length) { tbody.innerHTML = '<tr><td colspan="6">Нет пользователей</td></tr>'; return; }
  tbody.innerHTML = data.map(u => `<tr>
    <td class="cell-id">${u.id.slice(0, 8)}..</td>
    <td>${u.display_name || u.username || '—'}</td>
    <td>${u.provider}</td>
    <td><select class="role-select" data-id="${u.id}" onchange="changeRole('${u.id}', this.value)">
      ${['reader','editor','admin'].map(r => `<option ${r === u.role ? 'selected' : ''}>${r}</option>`).join('')}
    </select></td>
    <td>${u.is_active ? '✅' : '⛔'}</td>
    <td>
      <button class="btn-sm" onclick="viewUser('${u.id}')" title="Просмотр">👁</button>
      <button class="btn btn-sm ${u.is_active ? 'btn-outline' : 'btn-primary'}" onclick="toggleUser('${u.id}')">${u.is_active ? 'Деакт.' : 'Акт.'}</button>
      <button class="btn-danger" onclick="deleteUser('${u.id}')" title="Удалить">🗑</button>
    </td>
  </tr>`).join('');
}

async function changeRole(userId, role) {
  await api(`/auth/admin/users/${userId}/role?role=${role}`, { method: 'POST' });
}

async function toggleUser(userId) {
  await api(`/auth/admin/users/${userId}/toggle`, { method: 'POST' });
  loadUsers();
}

async function viewUser(userId) {
  const data = await api(`/auth/admin/users/${userId}`).catch(() => null);
  if (!data) return;
  const modal = document.getElementById('userModal');
  const details = document.getElementById('modalUserDetails');
  const nameEl = document.getElementById('modalUserName');
  nameEl.textContent = data.display_name || data.username || data.id;
  details.innerHTML = `
    <p><strong>ID:</strong> ${data.id}</p>
    <p><strong>Провайдер:</strong> ${data.provider} (${data.provider_user_id})</p>
    <p><strong>Имя:</strong> ${data.username || '—'}</p>
    <p><strong>Отображаемое имя:</strong> ${data.display_name || '—'}</p>
    <p><strong>Роль:</strong> ${data.role}</p>
    <p><strong>Статус:</strong> ${data.is_active ? '✅ Активен' : '⛔ Заблокирован'}</p>
    <p><strong>Создан:</strong> ${data.created_at || '—'}</p>
    <p><strong>Обновлён:</strong> ${data.updated_at || '—'}</p>
  `;
  modal.style.display = 'flex';
}

function closeUserModal() {
  document.getElementById('userModal').style.display = 'none';
}

async function deleteUser(userId) {
  if (!confirm('Удалить пользователя и все его данные? Это действие необратимо.')) return;
  await api(`/auth/admin/users/${userId}`, { method: 'DELETE' });
  loadUsers();
}

// ── Invites ──────────────────────────

function showCreateInvite() {
  document.getElementById('createInviteForm').style.display = 'block';
}

async function createInvite() {
  const role = document.getElementById('inviteRole').value;
  const maxUses = document.getElementById('inviteMaxUses').value;
  const note = document.getElementById('inviteNote').value;
  const data = await api(`/auth/admin/invites?role=${role}&max_uses=${maxUses}&note=${encodeURIComponent(note)}`, { method: 'POST' });
  if (data?.ok) {
    // Копировать ссылку в буфер обмена
    const url = data.url;
    try { await navigator.clipboard.writeText(url); alert('Ссылка скопирована:\n' + url); } catch { alert('Ссылка:\n' + url); }
    document.getElementById('createInviteForm').style.display = 'none';
    loadInvites();
  }
}

async function loadInvites() {
  const data = await api('/auth/admin/invites').catch(() => []);
  const tbody = document.getElementById('invitesBody');
  const count = document.getElementById('inviteCount');
  if (count) count.textContent = data.length + ' шт.';
  if (!tbody) return;
  if (!data.length) { tbody.innerHTML = '<tr><td colspan="7">Нет инвайтов</td></tr>'; return; }
  tbody.innerHTML = data.map(inv => {
    const isActive = inv.is_active && inv.use_count < inv.max_uses;
    const expired = inv.expires_at && new Date(inv.expires_at) < new Date();
    const status = expired ? '⏰ Истёк' : isActive ? '✅ Активен' : '⛔ Использован';
    return `<tr>
      <td><code style="font-size:0.75rem;word-break:break-all;">${inv.url || inv.token.slice(0, 20) + '...'}</code>
        <button class="btn-sm" onclick="navigator.clipboard.writeText('${inv.url || ''}').then(()=>alert('Скопировано'))" title="Копировать">📋</button></td>
      <td>${inv.role}</td>
      <td>${inv.use_count} / ${inv.max_uses}</td>
      <td>${inv.expires_at ? new Date(inv.expires_at).toLocaleString('ru') : 'Бессрочно'}</td>
      <td>${inv.note || '—'}</td>
      <td>${status}</td>
      <td><button class="btn-danger" onclick="deleteInvite('${inv.id}')">Удалить</button></td>
    </tr>`;
  }).join('');
}

async function deleteInvite(inviteId) {
  if (!confirm('Удалить инвайт?')) return;
  await api(`/auth/admin/invites/${inviteId}`, { method: 'DELETE' });
  loadInvites();
}

async function loadSessions() {
  const data = await api('/auth/admin/sessions').catch(() => []);
  const tbody = document.getElementById('sessionsBody');
  const count = document.getElementById('sessionCount');
  if (count) count.textContent = data.length + ' шт.';
  if (!tbody) return;
  if (!data.length) { tbody.innerHTML = '<tr><td colspan="5">Нет активных сессий</td></tr>'; return; }
  tbody.innerHTML = data.map(s => `<tr>
    <td class="cell-id">${s.id.slice(0, 12)}..</td>
    <td>${s.user_id.slice(0, 8)}..</td>
    <td>${s.expires_at ? new Date(s.expires_at).toLocaleString('ru') : '—'}</td>
    <td>${s.created_at ? new Date(s.created_at).toLocaleString('ru') : '—'}</td>
    <td><button class="btn-danger" onclick="deleteSession('${s.id}')">Отозвать</button></td>
  </tr>`).join('');
}

async function deleteSession(sessionId) {
  if (!confirm('Отозвать эту сессию?')) return;
  await api(`/auth/admin/sessions/${sessionId}`, { method: 'DELETE' });
  loadSessions();
}

async function loadApiKeys() {
  const data = await api('/auth/admin/api-keys').catch(() => []);
  const tbody = document.getElementById('apiKeysBody');
  const count = document.getElementById('apiKeyCount');
  if (count) count.textContent = data.length + ' шт.';
  if (!tbody) return;
  if (!data.length) { tbody.innerHTML = '<tr><td colspan="6">Нет API-ключей</td></tr>'; return; }
  tbody.innerHTML = data.map(k => `<tr>
    <td>${k.key_prefix}...</td>
    <td>${k.name || '—'}</td>
    <td>${k.user_id.slice(0, 8)}..</td>
    <td>${k.last_used_at ? new Date(k.last_used_at).toLocaleString('ru') : 'Никогда'}</td>
    <td class="${k.is_active ? 'status-active' : 'status-inactive'}">${k.is_active ? 'Активен' : 'Отозван'}</td>
    <td>${k.is_active ? `<button class="btn-danger" onclick="deleteApiKey('${k.id}')">Отозвать</button>` : '—'}</td>
  </tr>`).join('');
}

async function deleteApiKey(keyId) {
  if (!confirm('Отозвать этот API-ключ?')) return;
  await api(`/auth/admin/api-keys/${keyId}`, { method: 'DELETE' });
  loadApiKeys();
}

async function loadSuggestions() {
  const el = document.getElementById('suggestionsList');
  const data = await api('/book/presence/suggestions').catch(() => ({ suggestions: [] }));
  if (!el) return;
  const list = data.suggestions || [];
  if (!list.length) { el.innerHTML = '<p class="text-muted">Нет предложений</p>'; return; }
  el.innerHTML = list.map(s => `<div class="suggestion-item">
    <div class="suggestion-main">
      <strong>${s.topic}</strong>
      <p class="suggestion-reason">${s.reason || ''}</p>
      <span class="badge badge-${s.status}">${s.status}</span>
      <span class="suggestion-action">${s.suggested_action}</span>
    </div>
    <div class="suggestion-actions">
      <button class="btn btn-sm btn-primary" onclick="approveSuggestion('${s.id}')">Одобрить</button>
      <button class="btn btn-sm btn-outline" onclick="rejectSuggestion('${s.id}')">Отклонить</button>
    </div>
  </div>`).join('');
}

async function approveSuggestion(id) {
  await api(`/book/presence/suggestions/${id}/approve`, { method: 'POST' });
  loadSuggestions();
}

async function rejectSuggestion(id) {
  await api(`/book/presence/suggestions/${id}/reject`, { method: 'POST' });
  loadSuggestions();
}

async function loadAdminStats() {
  const el = document.getElementById('statsGrid');
  const [data, sessions, apiKeys, invites] = await Promise.all([
    api('/auth/admin/stats').catch(() => null),
    api('/auth/admin/sessions').catch(() => []),
    api('/auth/admin/api-keys').catch(() => []),
    api('/auth/admin/invites').catch(() => []),
  ]);
  if (!el || !data) { if (el) el.innerHTML = '<p class="text-muted">Ошибка загрузки</p>'; return; }
  const activeInvites = invites.filter(i => i.is_active && i.use_count < i.max_uses).length;
  el.innerHTML = `
    <div class="stat-card"><div class="stat-value">${data.users?.total || 0}</div><div class="stat-label">Пользователей</div></div>
    <div class="stat-card"><div class="stat-value">${data.users?.by_role?.reader || 0}</div><div class="stat-label">Читателей</div></div>
    <div class="stat-card"><div class="stat-value">${data.users?.by_role?.editor || 0}</div><div class="stat-label">Редакторов</div></div>
    <div class="stat-card"><div class="stat-value">${activeInvites}</div><div class="stat-label">Активных инвайтов</div></div>
    <div class="stat-card"><div class="stat-value">${sessions.length}</div><div class="stat-label">Активных сессий</div></div>
    <div class="stat-card"><div class="stat-value">${apiKeys.filter(k => k.is_active).length}</div><div class="stat-label">API-ключей</div></div>
    <div class="stat-card"><div class="stat-value">${data.presence?.pending_suggestions || 0}</div><div class="stat-label">Предложений</div></div>
  `;
}

function updateServiceStatus(data) {
  const el = document.getElementById('serviceStatus');
  if (!el) return;
  el.innerHTML = Object.entries(data).map(([k, v]) =>
    `<div class="d-flex justify-content-between mb-2"><span>${k}</span><span class="status-dot ${v ? 'status-success' : 'status-error'}"></span></div>`
  ).join('');
}

function onAdminSuggestion() {
  wsNotifCount++;
  const badge = document.getElementById('wsBadge');
  if (badge) { badge.textContent = wsNotifCount; badge.style.display = 'inline'; }
  if (document.getElementById('tab-suggestions')?.classList.contains('active')) loadSuggestions();
}

function switchTab(name) {
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name)?.classList.add('active');
  document.querySelector(`.tab-btn[onclick*="'${name}'"]`)?.classList.add('active');
  // Обновить данные при переключении вкладки
  if (name === 'users') loadUsers();
  if (name === 'invites') loadInvites();
  if (name === 'sessions') loadSessions();
  if (name === 'apikeys') loadApiKeys();
  if (name === 'suggestions') loadSuggestions();
  if (name === 'stats') loadAdminStats();
}

document.getElementById('subscribeForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = { email: form.email.value, name: form.name.value };
  const resultEl = document.getElementById('subscribeResult');
  try {
    const resp = await fetch('/book/email/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const json = await resp.json();
    resultEl.style.display = 'block';
    if (json.ok) {
      resultEl.className = 'subscribe-result ok';
      resultEl.textContent = '✓ Подписка оформлена!';
      form.email.value = '';
      form.name.value = '';
    } else {
      resultEl.className = 'subscribe-result err';
      resultEl.textContent = '✗ ' + (json.detail || 'Ошибка подписки');
    }
  } catch (err) {
    resultEl.style.display = 'block';
    resultEl.className = 'subscribe-result err';
    resultEl.textContent = '✗ Ошибка соединения';
  }
});

async function generateApiKey() {
  const data = await api('/auth/api-key', { method: 'POST' });
  if (!data || !data.key) return;
  const reveal = document.getElementById('newKeyReveal');
  const field = document.getElementById('newKeyField');
  if (reveal && field) {
    field.value = data.key;
    reveal.style.display = 'block';
    field.select();
    try { await navigator.clipboard.writeText(data.key); } catch {}
  }
}

// ── WebSocket ─────────────────────────

let ws = null;
let wsNotifCount = 0;

function connectWS() {
  // Получаем токен из cookie для аутентификации
  const token = document.cookie.split('; ').find(c => c.startsWith('arkaim_session='))?.split('=')[1] || '';
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = token
    ? `${proto}//${location.host}/ws?token=${encodeURIComponent(token)}`
    : `${proto}//${location.host}/ws`;
  ws = new WebSocket(url);
  ws.onopen = () => {
    const badge = document.getElementById('wsBadge');
    if (badge) { badge.textContent = '●'; badge.style.color = '#16a34a'; badge.style.display = 'inline'; }
  };
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.event === 'new_suggestion') {
        onAdminSuggestion();
        showToast('Новое предложение от Presence', 'info');
      }
      if (msg.event === 'service_status') {
        updateServiceStatus(msg.data);
      }
      if (msg.event === 'new_question') {
        onAdminSuggestion();
        showToast('Новый вопрос от читателя', 'info');
      }
      if (msg.event === 'pulse_beat') {
        showToast('Pulse: ядро книги активно', 'success');
      }
      if (msg.event === 'crowdfunding_milestone') {
        showToast('Краудфандинг: ' + (msg.data?.title || 'майлстоун'), 'success');
      }
      if (msg.event === 'chat_response') {
        showToast('Книга ответила на ваш вопрос', 'success');
      }
    } catch {}
  };
  ws.onclose = () => {
    const badge = document.getElementById('wsBadge');
    if (badge) { badge.textContent = '●'; badge.style.color = '#dc2626'; badge.style.display = 'inline'; }
    setTimeout(connectWS, 5000);
  };
  ws.onerror = () => { ws?.close(); };
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ── History page ─────────────────────

async function loadHistory() {
  const sessionId = document.getElementById('sessionFilter')?.value || '';
  const statsEl = document.getElementById('historyStats');
  const listEl = document.getElementById('historyList');
  const filterEl = document.getElementById('sessionFilter');

  // Load stats
  const stats = await api('/book/reader/history/stats').catch(() => null);
  if (statsEl && stats) {
    statsEl.innerHTML = `
      <span class="stat-item">Вопросов: ${stats.questions || 0}</span>
      <span class="stat-item">Сессий: ${stats.sessions || 0}</span>
      ${stats.last_active ? `<span class="stat-item">Последняя: ${new Date(stats.last_active).toLocaleString('ru')}</span>` : ''}
    `;
  }

  // Load sessions for filter
  if (filterEl && filterEl.options.length <= 1) {
    const sessions = await api('/book/reader/history/sessions').catch(() => ({ data: [] }));
    for (const sid of (sessions.data || [])) {
      const opt = document.createElement('option');
      opt.value = sid;
      opt.textContent = sid.slice(0, 20) + '...';
      filterEl.appendChild(opt);
    }
  }

  // Load history
  if (!listEl) return;
  const url = sessionId
    ? `/book/reader/history/full?session_id=${encodeURIComponent(sessionId)}&limit=100`
    : '/book/reader/history?limit=50';
  const data = await api(url).catch(() => ({ data: [] }));
  const items = data.data || [];

  if (!items.length) {
    listEl.innerHTML = '<div class="empty-state"><p>Нет истории вопросов</p><p>Задайте вопрос в чате, и он появится здесь.</p></div>';
    return;
  }

  if (sessionId) {
    // Full conversation view
    listEl.innerHTML = items.map(m => `
      <div class="history-item" style="border-left: 3px solid ${m.role === 'user' ? '#3b82f6' : '#10b981'};">
        <div class="history-item-header">
          <strong>${m.role === 'user' ? 'Вы' : 'Книга'}</strong>
          <span class="history-item-date">${m.created_at ? new Date(m.created_at).toLocaleString('ru') : ''}</span>
        </div>
        <div class="history-item-content">${escapeHtml(m.content)}</div>
      </div>
    `).join('');
  } else {
    // Questions list
    listEl.innerHTML = items.map(q => `
      <div class="history-item" onclick="viewSession('${q.session_id}')" style="cursor:pointer;">
        <div class="history-item-header">
          <div class="history-item-content">${escapeHtml(q.content)}</div>
          <span class="history-item-date">${q.created_at ? new Date(q.created_at).toLocaleString('ru') : ''}</span>
        </div>
        <div class="history-item-session">Сессия: ${q.session_id.slice(0, 16)}...</div>
      </div>
    `).join('');
  }
}

function viewSession(sessionId) {
  const filter = document.getElementById('sessionFilter');
  if (filter) {
    filter.value = sessionId;
    loadHistory();
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}