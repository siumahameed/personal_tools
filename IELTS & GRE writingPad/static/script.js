let articles = [];
let currentId = null;
let hasUnsavedChanges = false;
let timerInterval = null;
let timerSeconds = 0;
let timerRunning = false;

const CONFIG = { categories: {} };
let lastCelebratedTarget = false;
let pendingDeleteId = null;

const SHORT_LABELS = {
  ielts_t1_ac: 'T1',
  ielts_t2: 'T2',
  gre_issue: 'GRE',
  general: 'General',
};

const sidebar = document.getElementById('sidebar');
const articleListEl = document.getElementById('articleList');
const welcomeScreen = document.getElementById('welcomeScreen');
const editorScreen = document.getElementById('editorScreen');
const titleInput = document.getElementById('titleInput');
const subtitleInput = document.getElementById('subtitleInput');
const contentInput = document.getElementById('contentInput');
const searchInput = document.getElementById('searchInput');
const categorySelect = document.getElementById('categorySelect');
const spellCheckResults = document.getElementById('spellCheckResults');
const vocabPanel = document.getElementById('vocabPanel');
const vocabBody = document.getElementById('vocabBody');
const saveIndicator = document.getElementById('saveIndicator');
const saveText = document.getElementById('saveText');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const progressCount = document.getElementById('progressCount');
const timerDisplay = document.getElementById('timerDisplay');
const timerBar = document.getElementById('timerBar');
const categoryFilters = document.getElementById('categoryFilters');
let activeCategoryFilter = '';

// ─── API ───
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// ─── INIT ───
async function init() {
  const config = await api('/api/config');
  Object.assign(CONFIG, config);
  renderCategories();
  await loadList();
}

function renderCategories() {
  categorySelect.innerHTML = Object.entries(CONFIG.categories).map(([k, v]) =>
    `<option value="${k}">${v.label} (min ${v.target} words)</option>`
  ).join('');

  categoryFilters.innerHTML = `<button class="cat-filter${activeCategoryFilter === '' ? ' active' : ''}" data-cat="">All</button>` +
    Object.entries(CONFIG.categories).map(([k]) =>
      `<button class="cat-filter${activeCategoryFilter === k ? ' active' : ''}" data-cat="${k}">${SHORT_LABELS[k] || k}</button>`
    ).join('');

  categoryFilters.querySelectorAll('.cat-filter').forEach(el => {
    el.addEventListener('click', () => {
      if (el.dataset.cat === activeCategoryFilter) return;
      activeCategoryFilter = el.dataset.cat;
      categoryFilters.querySelectorAll('.cat-filter').forEach(b => b.classList.toggle('active', b.dataset.cat === activeCategoryFilter));
      articleListEl.classList.add('filtering');
      setTimeout(() => {
        renderList();
        requestAnimationFrame(() => articleListEl.classList.remove('filtering'));
      }, 130);
    });
  });
}

// ─── ARTICLES LIST ───
async function loadList() {
  articles = await api('/api/articles');
  renderList();
  updateDashboard();
}

function renderList() {
  const q = searchInput.value.toLowerCase();
  let filtered = articles;
  if (q) {
    filtered = filtered.filter(a => a.title.toLowerCase().includes(q) || (a.subtitle || '').toLowerCase().includes(q) || (a.content || '').toLowerCase().includes(q));
  }
  if (activeCategoryFilter) {
    filtered = filtered.filter(a => a.category === activeCategoryFilter);
  }

  if (filtered.length === 0) {
    articleListEl.innerHTML = `<div style="padding:28px 14px;text-align:center;color:var(--sidebar-text);font-size:12.5px;">${q || activeCategoryFilter ? 'No matching articles.' : 'No articles yet. Create one!'}</div>`;
    renderCategories();
    return;
  }
  articleListEl.innerHTML = filtered.map((a, i) => {
    const cat = CONFIG.categories[a.category] || CONFIG.categories.general;
    const shortLabel = SHORT_LABELS[a.category] || cat.label;
    const preview = (a.content || '').replace(/\s+/g, ' ').trim().slice(0, 80);
    return `
      <div class="article-item ${a.id === currentId ? 'active' : ''}" data-id="${a.id}" data-category="${a.category}" style="--cat-color:${cat.color};--i:${i}">
        <div class="item-col">
          <div class="item-title">${esc(a.title)}</div>
          ${a.subtitle ? `<div class="item-subtitle">${esc(a.subtitle)}</div>` : ''}
          ${preview ? `<div class="item-preview">${esc(preview)}${a.content.trim().length > 80 ? '…' : ''}</div>` : ''}
          <div class="item-meta">
            <span class="meta-words">${a.word_count} words</span>
            <span class="meta-cat">${esc(shortLabel)}</span>
            <span class="meta-date">${fmtDate(a.updated)}</span>
          </div>
        </div>
        <button class="item-delete" data-id="${a.id}" title="Delete article">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </div>
    `;
  }).join('');
  articleListEl.querySelectorAll('.article-item').forEach(el => {
    el.addEventListener('click', (e) => {
      if (e.target.closest('.item-delete')) return;
      selectArticle(el.dataset.id);
    });
  });
  articleListEl.querySelectorAll('.item-delete').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      setDeleteTarget(btn.dataset.id);
    });
  });
  renderCategories();
}

// ─── SELECTION ───
function selectArticle(id) {
  if (hasUnsavedChanges) {
    if (!confirm('You have unsaved changes. Discard them?')) return;
  }
  stopTimer();
  currentId = id;
  loadArticle(id);
  renderList();
}

async function loadArticle(id) {
  const data = await api(`/api/articles/${id}`);
  titleInput.value = data.title;
  subtitleInput.value = data.subtitle || '';
  contentInput.value = data.content;
  categorySelect.value = data.category || 'general';
  updateProgress(data.stats);
  updateMeta(data.stats);
  showEditor();
  hasUnsavedChanges = false;
  setSaveStatus('saved', 'Saved');
  vocabPanel.classList.add('hidden');
  spellCheckResults.classList.add('hidden');
}

// ─── SIDEBAR COLLAPSE ───
function collapseSidebar() {
  sidebar.classList.add('collapsed');
}

function expandSidebar() {
  sidebar.classList.remove('collapsed');
}

function toggleSidebar() {
  if (sidebar.classList.contains('collapsed')) {
    expandSidebar();
  } else {
    collapseSidebar();
  }
}

function showEditor() {
  welcomeScreen.classList.add('hidden');
  editorScreen.classList.remove('hidden');
  timerStarted = false;
  initTimer();
}

function showWelcome() {
  welcomeScreen.classList.remove('hidden');
  editorScreen.classList.add('hidden');
  expandSidebar();
  stopTimer();
  currentId = null;
  titleInput.value = '';
  subtitleInput.value = '';
  contentInput.value = '';
  spellCheckResults.classList.add('hidden');
  vocabPanel.classList.add('hidden');
  hasUnsavedChanges = false;
  renderList();
}

// ─── META & PROGRESS ───
function updateMeta(stats) {
  if (!stats) {
    stats = calcStats(contentInput.value);
  }
  document.getElementById('editorWordCount').textContent = `${stats.word_count} words`;
  document.getElementById('editorCharCount').textContent = `${stats.char_count} chars`;
  document.getElementById('editorSentenceCount').textContent = `${stats.sentences} sentences`;
  document.getElementById('editorParaCount').textContent = `${stats.paragraphs} paragraphs`;
}

function updateProgress(stats) {
  if (!stats) {
    stats = calcStats(contentInput.value);
  }
  const catKey = categorySelect.value;
  const cat = CONFIG.categories[catKey];
  const target = cat ? cat.target : 0;
  const wc = stats.word_count;

  if (target > 0) {
    progressText.textContent = `${cat.label} Target`;
    const pct = Math.min(Math.round((wc / target) * 100), 200);
    progressFill.style.width = `${Math.min(pct, 100)}%`;
    const met = wc >= target;
    progressFill.className = `progress-fill${met ? ' over-target' : ''}`;
    progressCount.textContent = `${wc} / ${target} words`;
    progressCount.className = met ? 'target-met' : '';
    if (met && !lastCelebratedTarget) {
      progressFill.classList.add('celebrate');
      setTimeout(() => progressFill.classList.remove('celebrate'), 800);
      lastCelebratedTarget = true;
    }
    if (!met) lastCelebratedTarget = false;
  } else {
    progressText.textContent = 'Word Count';
    progressFill.style.width = '0%';
    progressFill.className = 'progress-fill';
    progressCount.textContent = `${wc} words`;
  }
}

function calcStats(text) {
  const trimmed = text.trim();
  const words = trimmed ? trimmed.split(/\s+/).filter(Boolean) : [];
  const sentences = trimmed ? trimmed.split(/[.!?]+/).filter(s => s.trim().length > 0).length : 0;
  const paragraphs = text.split('\n').filter(p => p.trim()).length;
  return {
    word_count: words.length,
    char_count: text.length,
    char_no_space: text.replace(/\s/g, '').length,
    sentences,
    paragraphs,
  };
}

// ─── SAVE ───
function setSaveStatus(status, text) {
  saveIndicator.className = 'save-indicator ' + status;
  saveText.textContent = text;
}

function markDirty() {
  if (!hasUnsavedChanges) {
    hasUnsavedChanges = true;
    setSaveStatus('dirty', 'Unsaved');
  }
}

async function saveArticle() {
  const title = titleInput.value.trim();
  const content = contentInput.value;
  if (!title) {
    titleInput.focus();
    titleInput.style.outline = '2px solid var(--danger)';
    setTimeout(() => titleInput.style.outline = '', 1500);
    return;
  }

  const btn = document.getElementById('saveBtn');
  btn.classList.add('saving');
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M21 12a9 9 0 1 1-6.219-8.56" style="animation:spin 0.8s linear infinite;transform-origin:center"/></svg> Saving...`;
  setSaveStatus('saving', 'Saving...');

  try {
    if (currentId) {
      await api(`/api/articles/${currentId}`, {
        method: 'PUT',
        body: JSON.stringify({ title, subtitle: subtitleInput.value, content, category: categorySelect.value }),
      });
    } else {
      const result = await api('/api/articles', {
        method: 'POST',
        body: JSON.stringify({ title, subtitle: subtitleInput.value, content, category: categorySelect.value }),
      });
      currentId = result.id;
    }
    hasUnsavedChanges = false;
    setSaveStatus('saved', 'Saved');
    btn.classList.remove('saving');
    btn.classList.add('saved-state');
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polyline points="20 6 9 17 4 12"/></svg> Saved`;
    setTimeout(() => {
      btn.classList.remove('saved-state');
      btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Save`;
    }, 2000);
    await loadList();
  } catch (e) {
    setSaveStatus('dirty', 'Save failed');
    btn.classList.remove('saving');
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Save`;
  }
}

// ─── NEW ARTICLE ───
async function newArticle() {
  if (hasUnsavedChanges) {
    if (!confirm('You have unsaved changes. Discard them?')) return;
  }
  stopTimer();
  currentId = null;
  titleInput.value = '';
  subtitleInput.value = '';
  contentInput.value = '';
  categorySelect.value = 'general';
  activeCategoryFilter = '';
  updateMeta(calcStats(''));
  updateProgress(calcStats(''));
  showEditor();
  collapseSidebar();
  hasUnsavedChanges = false;
  setSaveStatus('saved', 'New');
  titleInput.focus();
  renderList();
  vocabPanel.classList.add('hidden');
  spellCheckResults.classList.add('hidden');
}

// ─── DELETE ───
const deleteModal = document.getElementById('deleteModal');
const deleteConfirmBtn = document.getElementById('deleteConfirmBtn');
const deleteCancelBtn = document.getElementById('deleteCancelBtn');
const deleteArticleTitle = document.getElementById('deleteArticleTitle');

function hideDeleteModal() {
  deleteModal.classList.add('hidden');
  pendingDeleteId = null;
}

function setDeleteTarget(id) {
  pendingDeleteId = id;
  const a = articles.find(x => x.id === id);
  deleteArticleTitle.textContent = a ? `"${a.title}"` : 'this article';
  deleteModal.classList.remove('hidden');
}

deleteConfirmBtn.addEventListener('click', async () => {
  const id = pendingDeleteId;
  if (!id) return;
  hideDeleteModal();
  await api(`/api/articles/${id}`, { method: 'DELETE' });
  if (currentId === id) showWelcome();
  await loadList();
});

deleteCancelBtn.addEventListener('click', hideDeleteModal);
deleteModal.addEventListener('click', (e) => {
  if (e.target === deleteModal) hideDeleteModal();
});

async function deleteArticle() {
  if (!currentId) return;
  setDeleteTarget(currentId);
}

// ─── SPELL CHECK ───
async function runSpellCheck() {
  const text = contentInput.value;
  if (!text.trim()) return;
  const btn = document.getElementById('spellCheckBtn');
  btn.disabled = true;
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="animation:spin 0.8s linear infinite;transform-origin:center"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Checking...`;
  const result = await api('/api/spellcheck', { method: 'POST', body: JSON.stringify({ text }) });
  btn.disabled = false;
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg> Spell`;

  vocabPanel.classList.add('hidden');
  if (result.misspelled.length === 0) {
    spellCheckResults.innerHTML = '<span style="color:var(--success);font-weight:500;">No spelling mistakes found.</span>';
    spellCheckResults.classList.remove('hidden');
    return;
  }
  let html = '<strong>Possible spelling mistakes:</strong><br>';
  result.misspelled.forEach(w => {
    const sug = result.suggestions[w];
    html += `<span class="misspelled-word">${esc(w)}</span>`;
    if (sug) html += ` → <span class="suggestion">${esc(sug)}</span>`;
    html += '<br>';
  });
  spellCheckResults.innerHTML = html;
  spellCheckResults.classList.remove('hidden');
}

// ─── VOCAB ANALYSIS ───
async function runVocabAnalysis() {
  const text = contentInput.value;
  if (!text.trim()) return;
  const result = await api('/api/analyze', { method: 'POST', body: JSON.stringify({ text }) });
  spellCheckResults.classList.add('hidden');

  const v = result.vocab;
  let scoreClass = 'low';
  if (v.vocab_score >= 55) scoreClass = 'good';
  else if (v.vocab_score >= 40) scoreClass = 'ok';

  let html = `<div class="vocab-score">
    <span>Vocabulary Score:</span>
    <span class="vocab-score-value ${scoreClass}">${v.vocab_score}%</span>
    <span style="font-size:11px;color:var(--text-tertiary);">(advanced / total words)</span>
  </div>
  <div style="margin-bottom:6px;">
    <span style="color:var(--text-secondary);">Unique words: ${v.unique_words} · </span>
    <span style="color:var(--text-secondary);">Basic: ${v.basic_count} · </span>
    <span style="color:var(--success);font-weight:500;">Advanced: ${v.advanced_count}</span>
  </div>`;

  if (v.basic_words.length > 0) {
    html += `<div style="margin-bottom:3px;font-size:11.5px;color:var(--text-secondary);">Consider replacing these common words:</div>
    <div class="vocab-basic-list">${v.basic_words.slice(0, 30).map(w => `<span class="vocab-basic-tag">${esc(w)}</span>`).join('')}${v.basic_words.length > 30 ? `<span style="font-size:11px;color:var(--text-tertiary);margin-left:4px;">+${v.basic_words.length - 30} more</span>` : ''}</div>`;
  }

  vocabBody.innerHTML = html;
  vocabPanel.classList.remove('hidden');
}

const TIME_LIMITS = {
  ielts_t1_ac:  20 * 60,
  ielts_t2:     40 * 60,
  gre_issue:    30 * 60,
  general:      0,
};

// ─── TIMER ───
function getTimeLimit() {
  return TIME_LIMITS[categorySelect.value] || 0;
}

function initTimer() {
  const limit = getTimeLimit();
  if (limit > 0) {
    timerSeconds = limit;
    timerDisplay.textContent = formatTime(limit);
    timerBar.dataset.mode = 'countdown';
  } else {
    timerSeconds = 0;
    timerDisplay.textContent = '00:00';
    timerBar.dataset.mode = 'stopwatch';
  }
  timerRunning = false;
  timerBar.classList.remove('warning', 'expired', 'running');
  document.getElementById('timerToggle').classList.remove('active');
}

function autoStartTimer() {
  if (timerRunning) return;
  const limit = getTimeLimit();
  if (limit > 0 && timerSeconds <= 0) return;
  timerRunning = true;
  timerBar.classList.add('running');
  document.getElementById('timerToggle').classList.add('active');
  timerInterval = setInterval(() => {
    const limit = getTimeLimit();
    if (limit > 0) {
      timerSeconds--;
      timerDisplay.textContent = formatTime(timerSeconds);
      if (timerSeconds <= 300) timerBar.classList.add('warning');
      if (timerSeconds <= 0) {
        clearInterval(timerInterval);
        timerRunning = false;
        timerBar.classList.remove('running', 'warning');
        timerBar.classList.add('expired');
        document.getElementById('timerToggle').classList.remove('active');
        timerDisplay.textContent = '00:00';
      }
    } else {
      timerSeconds++;
      timerDisplay.textContent = formatTime(timerSeconds);
    }
  }, 1000);
}

function toggleTimer() {
  if (timerRunning) {
    clearInterval(timerInterval);
    timerRunning = false;
    timerBar.classList.remove('running');
    document.getElementById('timerToggle').classList.remove('active');
  } else {
    autoStartTimer();
  }
}

function stopTimer() {
  clearInterval(timerInterval);
  timerRunning = false;
  timerBar.classList.remove('running');
  document.getElementById('timerToggle').classList.remove('active');
}

function resetTimer() {
  stopTimer();
  timerBar.classList.remove('warning', 'expired');
  initTimer();
}

function formatTime(secs) {
  if (secs <= 0) return '00:00';
  const m = String(Math.floor(secs / 60)).padStart(2, '0');
  const s = String(secs % 60).padStart(2, '0');
  return `${m}:${s}`;
}

// Scroll-based meta-line hide
contentInput.addEventListener('scroll', () => {
  const topbar = document.querySelector('.editor-topbar');
  if (!topbar) return;
  if (contentInput.scrollTop > 40) {
    topbar.classList.add('compact');
  } else {
    topbar.classList.remove('compact');
  }
});

// ─── EXPORT PDF ───
function downloadPdf() {
  window.open('/api/export-pdf', '_blank');
}

// ─── DASHBOARD ───
async function updateDashboard() {
  const stats = await api('/api/stats');
  document.getElementById('dashTotalArticles').textContent = stats.total_articles;
  document.getElementById('dashTotalWords').textContent = stats.total_words.toLocaleString();
  document.getElementById('dashAvgWords').textContent = stats.total_articles > 0
    ? Math.round(stats.total_words / stats.total_articles).toLocaleString()
    : '0';

  const breakdown = document.getElementById('dashCategoryBreakdown');
  const cats = stats.by_category;
  const keys = Object.keys(cats);
  if (keys.length === 0) {
    breakdown.innerHTML = '<div class="dash-empty">No articles yet</div>';
    return;
  }
  breakdown.innerHTML = keys.map(k => {
    const cat = CONFIG.categories[k] || { label: k, color: '#6b7280' };
    return `<div class="dash-row">
      <span class="dash-label"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${cat.color};margin-right:6px;"></span>${cat.label}</span>
      <span class="dash-value">${cats[k].count} (${cats[k].words}w)</span>
    </div>`;
  }).join('');
}

// ─── HELPERS ───
function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60) return 'now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// ─── EVENT BINDINGS ───

let timerStarted = false;

// Content changes
contentInput.addEventListener('input', () => {
  const stats = calcStats(contentInput.value);
  updateMeta(stats);
  updateProgress(stats);
  markDirty();
  if (!timerStarted && contentInput.value.trim().length > 0) {
    timerStarted = true;
    autoStartTimer();
  }
});

titleInput.addEventListener('input', markDirty);
subtitleInput.addEventListener('input', markDirty);
categorySelect.addEventListener('change', () => {
  updateProgress(calcStats(contentInput.value));
  if (currentId) markDirty();
  initTimer();
  if (getTimeLimit() > 0) {
    timerStarted = true;
    autoStartTimer();
  }
});

// Click dismiss
spellCheckResults.addEventListener('click', () => spellCheckResults.classList.add('hidden'));
document.getElementById('vocabClose').addEventListener('click', () => vocabPanel.classList.add('hidden'));

// Search
searchInput.addEventListener('input', renderList);

// Buttons
document.getElementById('saveBtn').addEventListener('click', saveArticle);
document.getElementById('spellCheckBtn').addEventListener('click', runSpellCheck);
document.getElementById('vocabBtn').addEventListener('click', runVocabAnalysis);
document.getElementById('downloadPdfBtn').addEventListener('click', downloadPdf);
document.getElementById('deleteBtn').addEventListener('click', deleteArticle);
document.getElementById('newArticleBtn').addEventListener('click', newArticle);
document.getElementById('welcomeNewBtn').addEventListener('click', newArticle);
document.getElementById('timerToggle').addEventListener('click', toggleTimer);
document.getElementById('timerReset').addEventListener('click', resetTimer);
document.getElementById('collapseBtn').addEventListener('click', toggleSidebar);

// Keyboard
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    saveArticle();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    if (!editorScreen.classList.contains('hidden')) {
      e.preventDefault();
      saveArticle();
    }
  }
  if ((e.ctrlKey || e.metaKey) && e.key === '\\') {
    e.preventDefault();
    toggleSidebar();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
    e.preventDefault();
    newArticle();
  }
});

// Spin animation keyframes
const style = document.createElement('style');
style.textContent = `@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
document.head.appendChild(style);

// ─── START ───
init();
