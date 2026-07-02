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
  ielts_cue: 'Cue',
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
let activeKeywordFilters = [];
let kwMatchMode = 'ANY';
let kwSearchQuery = '';
let keywords_list = [];

const PREDEFINED_KEYWORDS = [
  "Technology", "Education", "Environment", "Health", "Society", 
  "Business", "Government", "Science", "Culture", "Crime", "Family", "Careers"
];

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
  loadReaderHighlights();
}

function renderCategories() {
  const prevVal = categorySelect.value;
  categorySelect.innerHTML = Object.entries(CONFIG.categories).map(([k, v]) =>
    `<option value="${k}">${v.label} (min ${v.target} words)</option>`
  ).join('');
  categorySelect.value = prevVal || 'general';

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
  renderKeywordFilters();
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
  if (activeKeywordFilters.length > 0) {
    filtered = filtered.filter(a => {
      const aKws = (a.keywords || []).map(k => k.toLowerCase().trim());
      if (kwMatchMode === 'ALL') {
        return activeKeywordFilters.every(f => aKws.includes(f.toLowerCase().trim()));
      } else {
        return activeKeywordFilters.some(f => aKws.includes(f.toLowerCase().trim()));
      }
    });
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
          ${a.keywords && a.keywords.length ? `<div class="item-keywords">${a.keywords.map(k => `<span class="item-keyword-tag">${esc(k)}</span>`).join('')}</div>` : ''}
          <div class="item-meta">
            <span class="meta-words">${a.word_count} words</span>
            <span class="meta-cat">${esc(shortLabel)}</span>
            <span class="meta-date">${fmtDate(a.updated)}</span>
            ${a.reads > 0 ? `<span class="meta-reads" title="Read ${a.reads} time${a.reads > 1 ? 's' : ''}">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
              ${a.reads}
            </span>` : ''}
          </div>
        </div>
        <div class="item-actions">
          <button class="item-read" data-id="${a.id}" title="Read article">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
            </svg>
          </button>
          <button class="item-delete" data-id="${a.id}" title="Delete article">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </div>
    `;
  }).join('');
  articleListEl.querySelectorAll('.article-item').forEach(el => {
    el.addEventListener('click', (e) => {
      if (e.target.closest('.item-read')) return;
      if (e.target.closest('.item-delete')) return;
      if (e.target.closest('.item-keyword-tag')) {
        const kw = e.target.closest('.item-keyword-tag').textContent.trim();
        const index = activeKeywordFilters.findIndex(x => x.toLowerCase() === kw.toLowerCase());
        if (index > -1) {
          activeKeywordFilters.splice(index, 1);
        } else {
          activeKeywordFilters.push(kw);
        }
        renderKeywordFilters();
        renderList();
        return;
      }
      selectArticle(el.dataset.id);
    });
  });
  articleListEl.querySelectorAll('.item-delete').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      setDeleteTarget(btn.dataset.id);
    });
  });
  articleListEl.querySelectorAll('.item-read').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openReader(btn.dataset.id);
    });
  });
  renderCategories();
  renderActiveFilters();
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
  renderKeywords(data.keywords || []);
  updateProgress(data.stats);
  updateMeta(data.stats);
  showEditor();
  hasUnsavedChanges = false;
  setSaveStatus('saved', 'Saved');
  vocabPanel.classList.add('hidden');
  spellCheckResults.classList.add('hidden');
  document.getElementById('grammarPanel').classList.add('hidden');
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
  document.getElementById('grammarPanel').classList.add('hidden');
  renderList();
  renderKeywordFilters();
  updateDashboard();
}

// ─── KEYWORD FUNCTIONS ───
function renderKeywords(kws) {
  keywords_list = kws;
  const container = document.getElementById('keywordsTags');
  container.innerHTML = kws.map(k => `<span class="kw-tag">${esc(k)}<button class="kw-remove" data-kw="${esc(k)}">&times;</button></span>`).join('');
  container.querySelectorAll('.kw-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      const kw = btn.dataset.kw;
      keywords_list = keywords_list.filter(k => k !== kw);
      renderKeywords(keywords_list);
      markDirty();
    });
  });
  renderKeywordSuggestions();
}

function renderKeywordSuggestions() {
  const container = document.getElementById('keywordSuggestions');
  if (!container) return;
  container.innerHTML = PREDEFINED_KEYWORDS.map(kw => {
    const isSelected = keywords_list.map(k => k.toLowerCase()).includes(kw.toLowerCase());
    return `<button class="kw-sug-pill${isSelected ? ' selected' : ''}" data-kw="${esc(kw)}">${esc(kw)}</button>`;
  }).join('');

  container.querySelectorAll('.kw-sug-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const kw = btn.dataset.kw;
      const matchIndex = keywords_list.findIndex(k => k.toLowerCase() === kw.toLowerCase());
      if (matchIndex > -1) {
        keywords_list.splice(matchIndex, 1);
      } else {
        keywords_list.push(kw);
      }
      renderKeywords(keywords_list);
      markDirty();
    });
  });
}

document.getElementById('keywordsInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    const kw = e.target.value.trim();
    if (kw && !keywords_list.map(k => k.toLowerCase()).includes(kw.toLowerCase())) {
      keywords_list.push(kw);
      renderKeywords(keywords_list);
      markDirty();
    }
    e.target.value = '';
  }
});

function renderKeywordFilters() {
  const counts = {};
  articles.forEach(a => {
    (a.keywords || []).forEach(k => {
      const kw = k.trim();
      if (!kw) return;
      counts[kw] = (counts[kw] || 0) + 1;
    });
  });

  const listContainer = document.getElementById('keywordFiltersList');
  if (!listContainer) return;

  const sortedKws = Object.keys(counts).sort((a, b) => b.localeCompare(a));
  sortedKws.sort((a, b) => counts[b] - counts[a] || a.localeCompare(b));

  const filteredKws = sortedKws.filter(k => k.toLowerCase().includes(kwSearchQuery.toLowerCase()));

  if (filteredKws.length === 0) {
    listContainer.innerHTML = `<div style="padding:16px 12px;font-size:11.5px;color:var(--sidebar-text);opacity:0.6;text-align:center;">No tags found</div>`;
    document.getElementById('clearKwFiltersBtn').classList.toggle('hidden', activeKeywordFilters.length === 0);
    return;
  }

  listContainer.innerHTML = filteredKws.map(k => {
    const isActive = activeKeywordFilters.some(x => x.toLowerCase() === k.toLowerCase());
    return `
      <button class="kw-filter-pill${isActive ? ' active' : ''}" data-kw="${esc(k)}" title="Filter by ${esc(k)}">
        <span class="kw-filter-name">${esc(k)}</span>
        <span class="kw-filter-count">${counts[k]}</span>
      </button>
    `;
  }).join('');

  listContainer.querySelectorAll('.kw-filter-pill').forEach(el => {
    el.addEventListener('click', () => {
      const kw = el.dataset.kw;
      const index = activeKeywordFilters.findIndex(x => x.toLowerCase() === kw.toLowerCase());
      if (index > -1) {
        activeKeywordFilters.splice(index, 1);
      } else {
        activeKeywordFilters.push(kw);
      }
      renderKeywordFilters();
      renderList();
    });
  });

  document.getElementById('clearKwFiltersBtn').classList.toggle('hidden', activeKeywordFilters.length === 0);
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
        body: JSON.stringify({ title, subtitle: subtitleInput.value, content, category: categorySelect.value, keywords: keywords_list }),
      });
    } else {
      const result = await api('/api/articles', {
        method: 'POST',
        body: JSON.stringify({ title, subtitle: subtitleInput.value, content, category: categorySelect.value, keywords: keywords_list }),
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
    renderKeywordFilters();
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
  activeKeywordFilters = [];
  keywords_list = [];
  renderKeywords([]);
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
  document.getElementById('grammarPanel').classList.add('hidden');
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
  document.getElementById('grammarPanel').classList.add('hidden');
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
  document.getElementById('grammarPanel').classList.add('hidden');

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

  if (v.most_frequent) {
    html += `<div style="margin-bottom:6px;padding:6px 8px;background:var(--primary-subtle);border-radius:6px;display:flex;align-items:center;gap:8px;">
      <span style="font-size:11.5px;color:var(--text-secondary);">Most used word:</span>
      <span style="font-weight:700;color:var(--primary);">${esc(v.most_frequent.word)}</span>
      <span style="font-size:11px;color:var(--text-tertiary);">(×${v.most_frequent.count})</span>
    </div>`;
  }

  if (v.top_words && v.top_words.length > 0) {
    const maxCount = v.top_words[0].count;
    html += `<div style="margin-bottom:4px;font-size:11px;font-weight:600;color:var(--text-secondary);">Top Words</div>
    <div style="margin-bottom:8px;">${v.top_words.slice(0, 8).map(w => `
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;font-size:11px;">
        <span style="width:60px;text-align:right;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(w.word)}</span>
        <div style="flex:1;height:10px;background:var(--border-light);border-radius:4px;overflow:hidden;">
          <div style="height:100%;width:${Math.round((w.count/maxCount)*100)}%;background:var(--primary);border-radius:4px;transition:width 0.3s;"></div>
        </div>
        <span style="width:20px;color:var(--text-tertiary);font-size:10px;">${w.count}</span>
      </div>
    `).join('')}</div>`;
  }

  if (v.basic_words.length > 0) {
    html += `<div style="margin-bottom:3px;font-size:11.5px;color:var(--text-secondary);">Consider replacing these common words:</div>
    <div class="vocab-basic-list">${v.basic_words.slice(0, 30).map(w => `<span class="vocab-basic-tag">${esc(w)}</span>`).join('')}${v.basic_words.length > 30 ? `<span style="font-size:11px;color:var(--text-tertiary);margin-left:4px;">+${v.basic_words.length - 30} more</span>` : ''}</div>`;
  }

  // Sentence Structure
  const s = result.structure;
  if (s && s.total > 0) {
    const total = s.simple + s.compound + s.complex;
    const pct = (n) => total ? Math.round((n/total)*100) : 0;
    const shortPct = total ? Math.round((s.short/total)*100) : 0;
    const medPct = total ? Math.round((s.medium/total)*100) : 0;
    const longPct = total ? Math.round((s.long/total)*100) : 0;
    html += `<div class="str-section">
      <div class="str-title">Sentence Structure</div>
      <div class="str-meta">Avg length: <strong>${s.avg_words}</strong> words  ·  Passive voice: <strong>${s.passive}</strong> time${s.passive !== 1 ? 's' : ''}</div>
      <div class="str-row">
        <span class="str-label">Simple</span>
        <div class="str-bar-track"><div class="str-bar-fill simple" style="width:${pct(s.simple)}%"></div></div>
        <span class="str-count">${s.simple}</span>
      </div>
      <div class="str-row">
        <span class="str-label">Compound</span>
        <div class="str-bar-track"><div class="str-bar-fill compound" style="width:${pct(s.compound)}%"></div></div>
        <span class="str-count">${s.compound}</span>
      </div>
      <div class="str-row">
        <span class="str-label">Complex</span>
        <div class="str-bar-track"><div class="str-bar-fill complex" style="width:${pct(s.complex)}%"></div></div>
        <span class="str-count">${s.complex}</span>
      </div>
      <div style="margin-top:6px;">
        <div class="str-dist-row">
          <div class="str-dist-seg short" style="width:${shortPct}%"></div>
          <div class="str-dist-seg medium" style="width:${medPct}%"></div>
          <div class="str-dist-seg long" style="width:${longPct}%"></div>
        </div>
        <div class="str-dist-legend">
          <span><span class="dot" style="background:#93c5fd"></span> Short (${s.short})</span>
          <span><span class="dot" style="background:#6366f1"></span> Medium (${s.medium})</span>
          <span><span class="dot" style="background:#1e40af"></span> Long (${s.long})</span>
        </div>
      </div>
    </div>`;
  }

  vocabBody.innerHTML = html;
  vocabPanel.classList.remove('hidden');
}

// ─── GRAMMAR CHECK ───
async function runGrammarCheck() {
  const text = contentInput.value;
  if (!text.trim()) return;
  const grammarPanel = document.getElementById('grammarPanel');
  const grammarBody = document.getElementById('grammarBody');
  const grammarSummary = document.getElementById('grammarSummary');
  const btn = document.getElementById('grammarBtn');
  btn.disabled = true;
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="animation:spin 0.8s linear infinite;transform-origin:center"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Checking...`;
  const result = await api('/api/grammar', { method: 'POST', body: JSON.stringify({ text }) });
  btn.disabled = false;
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg> Grammar`;

  vocabPanel.classList.add('hidden');
  spellCheckResults.classList.add('hidden');

  const issues = result.issues || [];
  if (issues.length === 0) {
    grammarBody.innerHTML = '<div class="grammar-clean">✓ No grammar issues found!</div>';
    grammarSummary.textContent = '';
    grammarPanel.classList.remove('hidden');
    return;
  }
  grammarSummary.textContent = `${issues.length} issue${issues.length > 1 ? 's' : ''}`;
  grammarBody.innerHTML = issues.map(iss => `
    <div class="grammar-issue">
      <span class="gi-type">${esc(iss.type)}</span>
      <div style="margin-top:2px;">
        <span class="gi-orig">${esc(iss.original)}</span>
        <span class="gi-arrow">→</span>
        <span class="gi-sug">${esc(iss.suggestion)}</span>
      </div>
      <span class="gi-context">"${esc(iss.context)}"</span>
    </div>
  `).join('');
  grammarPanel.classList.remove('hidden');
}

const TIME_LIMITS = {
  ielts_t1_ac:  20 * 60,
  ielts_t2:     40 * 60,
  gre_issue:    30 * 60,
  ielts_cue:    2 * 60,
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

// ─── EXPORT PDF MODAL ───
const exportPdfModal = document.getElementById('exportPdfModal');
const exportSearchInput = document.getElementById('exportSearchInput');
const exportEssaysList = document.getElementById('exportEssaysList');
const exportSummaryText = document.getElementById('exportSummaryText');
const exportConfirmBtn = document.getElementById('exportConfirmBtn');

let selectedExportIds = [];
let exportSearchQuery = '';

function downloadPdf() {
  selectedExportIds = articles.map(a => a.id);
  exportSearchQuery = '';
  if (exportSearchInput) exportSearchInput.value = '';
  
  renderExportEssaysList();
  updateExportSummary();
  
  if (exportPdfModal) {
    exportPdfModal.classList.remove('hidden');
  }
}

function hideExportPdfModal() {
  if (exportPdfModal) {
    exportPdfModal.classList.add('hidden');
  }
}

function renderExportEssaysList() {
  if (!exportEssaysList) return;
  
  const query = exportSearchQuery.toLowerCase();
  let filtered = articles;
  if (query) {
    filtered = filtered.filter(a => 
      a.title.toLowerCase().includes(query) || 
      (a.subtitle || '').toLowerCase().includes(query) || 
      (a.content || '').toLowerCase().includes(query)
    );
  }
  
  if (filtered.length === 0) {
    exportEssaysList.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 12.5px; opacity: 0.6;">No matching essays found.</div>`;
    return;
  }
  
  exportEssaysList.innerHTML = filtered.map(a => {
    const isChecked = selectedExportIds.includes(a.id);
    const cat = CONFIG.categories[a.category] || CONFIG.categories.general;
    return `
      <label class="export-item-label" for="chk-${a.id}">
        <div class="export-item-checkbox-col">
          <input type="checkbox" id="chk-${a.id}" class="export-chk" data-id="${a.id}" ${isChecked ? 'checked' : ''}>
        </div>
        <div class="export-item-details-col">
          <div class="export-item-title">${esc(a.title)}</div>
          <div class="export-item-meta">
            <span class="export-item-cat" style="color: ${cat.color || 'var(--primary)'};">${esc(cat.label)}</span>
            <span class="export-item-divider">&bull;</span>
            <span class="export-item-wc">${a.word_count} words</span>
            <span class="export-item-divider">&bull;</span>
            <span class="export-item-date">${fmtDate(a.updated)}</span>
          </div>
        </div>
      </label>
    `;
  }).join('');
  
  exportEssaysList.querySelectorAll('.export-chk').forEach(chk => {
    chk.addEventListener('change', () => {
      const id = chk.dataset.id;
      if (chk.checked) {
        if (!selectedExportIds.includes(id)) selectedExportIds.push(id);
      } else {
        selectedExportIds = selectedExportIds.filter(x => x !== id);
      }
      updateExportSummary();
    });
  });
}

function updateExportSummary() {
  if (!exportSummaryText || !exportConfirmBtn) return;
  
  const count = selectedExportIds.length;
  let totalWords = 0;
  selectedExportIds.forEach(id => {
    const a = articles.find(x => x.id === id);
    if (a) {
      totalWords += (a.word_count || 0);
    }
  });
  
  exportSummaryText.textContent = `Selected: ${count} essay${count !== 1 ? 's' : ''} (${totalWords.toLocaleString()} total words)`;
  exportConfirmBtn.disabled = (count === 0);
}

// Bind PDF Export Modal Listeners
if (exportSearchInput) {
  exportSearchInput.addEventListener('input', (e) => {
    exportSearchQuery = e.target.value;
    renderExportEssaysList();
  });
}

const exportSelectAllBtn = document.getElementById('exportSelectAllBtn');
if (exportSelectAllBtn) {
  exportSelectAllBtn.addEventListener('click', () => {
    const query = exportSearchQuery.toLowerCase();
    let visible = articles;
    if (query) {
      visible = visible.filter(a => 
        a.title.toLowerCase().includes(query) || 
        (a.subtitle || '').toLowerCase().includes(query) || 
        (a.content || '').toLowerCase().includes(query)
      );
    }
    visible.forEach(a => {
      if (!selectedExportIds.includes(a.id)) {
        selectedExportIds.push(a.id);
      }
    });
    renderExportEssaysList();
    updateExportSummary();
  });
}

const exportDeselectAllBtn = document.getElementById('exportDeselectAllBtn');
if (exportDeselectAllBtn) {
  exportDeselectAllBtn.addEventListener('click', () => {
    const query = exportSearchQuery.toLowerCase();
    let visible = articles;
    if (query) {
      visible = visible.filter(a => 
        a.title.toLowerCase().includes(query) || 
        (a.subtitle || '').toLowerCase().includes(query) || 
        (a.content || '').toLowerCase().includes(query)
      );
    }
    const visibleIds = visible.map(a => a.id);
    selectedExportIds = selectedExportIds.filter(id => !visibleIds.includes(id));
    renderExportEssaysList();
    updateExportSummary();
  });
}

const exportCloseBtn = document.getElementById('exportCloseBtn');
if (exportCloseBtn) exportCloseBtn.addEventListener('click', hideExportPdfModal);

const exportCancelBtn = document.getElementById('exportCancelBtn');
if (exportCancelBtn) exportCancelBtn.addEventListener('click', hideExportPdfModal);

if (exportConfirmBtn) {
  exportConfirmBtn.addEventListener('click', () => {
    if (selectedExportIds.length === 0) return;
    const url = `/api/export-pdf?ids=${selectedExportIds.join(',')}`;
    window.open(url, '_blank');
    hideExportPdfModal();
  });
}

if (exportPdfModal) {
  exportPdfModal.addEventListener('click', (e) => {
    if (e.target === exportPdfModal) hideExportPdfModal();
  });
}

// ─── ACTIVE FILTERS DISPLAY ───
function renderActiveFilters() {
  const container = document.getElementById('activeFiltersIndicator');
  if (!container) return;
  
  const hasFilters = activeCategoryFilter || activeKeywordFilters.length > 0;
  if (!hasFilters) {
    container.classList.add('hidden');
    container.innerHTML = '';
    return;
  }
  
  let html = `<div class="active-filters-inner">`;
  
  if (activeCategoryFilter) {
    const cat = CONFIG.categories[activeCategoryFilter] || { label: activeCategoryFilter };
    html += `
      <span class="active-filter-badge" style="border-color: ${cat.color || 'var(--primary)'};">
        <span class="badge-dot" style="background: ${cat.color || 'var(--primary)'}"></span>
        ${esc(SHORT_LABELS[activeCategoryFilter] || cat.label)}
        <button class="active-filter-remove" data-action="clear-cat" title="Remove Category Filter">&times;</button>
      </span>
    `;
  }
  
  activeKeywordFilters.forEach(kw => {
    html += `
      <span class="active-filter-badge tag-badge">
        <svg class="badge-tag-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10">
          <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>
        </svg>
        ${esc(kw)}
        <button class="active-filter-remove" data-action="clear-kw" data-val="${esc(kw)}" title="Remove Keyword Filter">&times;</button>
      </span>
    `;
  });
  
  if ((activeCategoryFilter && activeKeywordFilters.length > 0) || activeKeywordFilters.length > 1) {
    html += `<button class="active-filters-clear-all" id="clearAllFiltersBtn" title="Clear All Active Filters">Clear All</button>`;
  }
  
  html += `</div>`;
  container.innerHTML = html;
  container.classList.remove('hidden');
  
  container.querySelectorAll('.active-filter-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const action = btn.dataset.action;
      if (action === 'clear-cat') {
        activeCategoryFilter = '';
        categoryFilters.querySelectorAll('.cat-filter').forEach(b => b.classList.toggle('active', b.dataset.cat === ''));
      } else if (action === 'clear-kw') {
        const val = btn.dataset.val;
        activeKeywordFilters = activeKeywordFilters.filter(x => x !== val);
        renderKeywordFilters();
      }
      renderList();
    });
  });
  
  const clearAllLink = document.getElementById('clearAllFiltersBtn');
  if (clearAllLink) {
    clearAllLink.addEventListener('click', () => {
      activeCategoryFilter = '';
      activeKeywordFilters = [];
      categoryFilters.querySelectorAll('.cat-filter').forEach(b => b.classList.toggle('active', b.dataset.cat === ''));
      renderKeywordFilters();
      renderList();
    });
  }
}

// ─── DASHBOARD ───
async function updateDashboard() {
  if (welcomeScreen.classList.contains('hidden')) return;
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
  } else {
    breakdown.innerHTML = keys.map(k => {
      const cat = CONFIG.categories[k] || { label: k, color: '#6b7280' };
      return `<div class="dash-row">
        <span class="dash-label"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${cat.color};margin-right:6px;"></span>${cat.label}</span>
        <span class="dash-value">${cats[k].count} (${cats[k].words}w)</span>
      </div>`;
    }).join('');
  }

  // Progress Chart
  try {
    const progressData = await api('/api/progress');
    drawProgressChart(progressData);
  } catch (_) {}

  // Vocabulary Trend card
  const vocabTrend = document.getElementById('dashVocabTrend');
  if (vocabTrend) {
    const score = stats.avg_vocab_score;
    if (stats.total_articles === 0) {
      vocabTrend.innerHTML = '<div class="dash-empty">No articles yet</div>';
    } else {
      let scoreClass = 'dash-value';
      let scoreColor = '#9f9f9f';
      if (score >= 55) { scoreClass += ' dash-score-good'; scoreColor = '#22c55e'; }
      else if (score >= 40) { scoreClass += ' dash-score-ok'; scoreColor = '#f59e0b'; }
      vocabTrend.innerHTML = `
        <div class="dash-row">
          <span class="dash-label">Avg Vocab Score</span>
          <span class="${scoreClass}" style="color:${scoreColor};font-size:20px;font-weight:700;">${score}%</span>
        </div>
        <div class="dash-row">
          <span class="dash-label">Articles Analyzed</span>
          <span class="dash-value">${stats.total_articles}</span>
        </div>`;
    }
  }

  // Common Weak Words card
  const weakWords = document.getElementById('dashWeakWords');
  if (weakWords) {
    const words = stats.top_weak_words || [];
    if (words.length === 0) {
      weakWords.innerHTML = '<div class="dash-empty">No weak words found</div>';
    } else {
      weakWords.innerHTML = words.map(w => `
        <div class="dash-row">
          <span class="dash-label">${esc(w.word)}</span>
          <span class="dash-value">×${w.count}</span>
        </div>
      `).join('');
    }
  }

  // Top Used Words card
  const topWords = document.getElementById('dashTopWords');
  if (topWords) {
    const words = stats.top_common_words || [];
    if (words.length === 0) {
      topWords.innerHTML = '<div class="dash-empty">No data yet</div>';
    } else {
      const maxC = words[0].count;
      topWords.innerHTML = words.map(w => `
        <div style="display:flex;align-items:center;gap:5px;margin-bottom:2px;font-size:11px;">
          <span style="width:55px;text-align:right;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0;">${esc(w.word)}</span>
          <div style="flex:1;height:8px;background:var(--border-light);border-radius:4px;overflow:hidden;">
            <div style="height:100%;width:${Math.round((w.count/maxC)*100)}%;background:#8b5cf6;border-radius:4px;"></div>
          </div>
          <span style="width:18px;color:var(--text-tertiary);font-size:9px;flex-shrink:0;">${w.count}</span>
        </div>
      `).join('');
    }
  }

  // Keywords breakdown in welcome screen
  const kwBreakdown = document.getElementById('dashKeywordsBreakdown');
  if (kwBreakdown) {
    const kwCounts = {};
    articles.forEach(a => {
      (a.keywords || []).forEach(k => {
        const kw = k.trim();
        if (!kw) return;
        kwCounts[kw] = (kwCounts[kw] || 0) + 1;
      });
    });
    const sortedKws = Object.keys(kwCounts).sort((a, b) => kwCounts[b] - kwCounts[a] || a.localeCompare(b));
    const topKws = sortedKws.slice(0, 5);
    if (topKws.length === 0) {
      kwBreakdown.innerHTML = '<div class="dash-empty">No keywords tagged yet</div>';
    } else {
      kwBreakdown.innerHTML = topKws.map(k => `
        <div class="dash-row dash-row-clickable" data-kw="${esc(k)}" title="Click to filter articles by this keyword">
          <span class="dash-label">
            <svg style="display:inline-block;width:12px;height:12px;margin-right:6px;vertical-align:middle;opacity:0.7;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
              <line x1="7" y1="7" x2="7.01" y2="7"/>
            </svg>
            ${esc(k)}
          </span>
          <span class="dash-value">${kwCounts[k]} essay${kwCounts[k] > 1 ? 's' : ''}</span>
        </div>
      `).join('');
      
      kwBreakdown.querySelectorAll('.dash-row-clickable').forEach(row => {
        row.addEventListener('click', () => {
          const kw = row.dataset.kw;
          activeKeywordFilters = [kw];
          renderKeywordFilters();
          renderList();
        });
      });
    }
  }
}

// ─── PROGRESS CHART ───
function drawProgressChart(data) {
  const canvas = document.getElementById('progressChart');
  const empty = document.getElementById('progressEmpty');
  if (!canvas) return;
  if (!data || data.length < 2) {
    canvas.style.display = 'none';
    if (empty) empty.style.display = 'block';
    return;
  }
  canvas.style.display = 'block';
  if (empty) empty.style.display = 'none';

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width;
  const h = rect.height;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);

  const pad = { top: 14, right: 8, bottom: 22, left: 36 };
  const cw = w - pad.left - pad.right;
  const ch = h - pad.top - pad.bottom;

  ctx.clearRect(0, 0, w, h);

  const maxWc = Math.max(...data.map(d => d.word_count), 1);
  const maxVocab = 100;

  const xScale = (i) => pad.left + (i / (data.length - 1)) * cw;
  const yWc = (v) => pad.top + ch - (v / maxWc) * ch * 0.85;
  const yVocab = (v) => pad.top + ch - (v / maxVocab) * ch * 0.85;

  // Grid lines
  ctx.strokeStyle = '#e4e2da';
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i / 4) * ch;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.fillStyle = '#9f9f9f';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(Math.round((4 - i) / 4 * 100), pad.left - 4, y + 3);
  }

  // X labels
  ctx.fillStyle = '#9f9f9f';
  ctx.font = '8px sans-serif';
  ctx.textAlign = 'center';
  const step = Math.max(1, Math.floor(data.length / 5));
  for (let i = 0; i < data.length; i += step) {
    ctx.fillText(data[i].date.slice(5), xScale(i), h - 4);
  }

  // Vocab line
  ctx.beginPath();
  ctx.strokeStyle = '#6366f1';
  ctx.lineWidth = 1.8;
  data.forEach((d, i) => {
    const x = xScale(i);
    const y = yVocab(d.vocab_score);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Vocab dots
  data.forEach((d, i) => {
    ctx.beginPath();
    ctx.arc(xScale(i), yVocab(d.vocab_score), 2.5, 0, Math.PI * 2);
    ctx.fillStyle = '#6366f1';
    ctx.fill();
  });

  // Word count line
  ctx.beginPath();
  ctx.strokeStyle = '#22c55e';
  ctx.lineWidth = 1.8;
  data.forEach((d, i) => {
    const x = xScale(i);
    const y = yWc(d.word_count);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Word count dots
  data.forEach((d, i) => {
    ctx.beginPath();
    ctx.arc(xScale(i), yWc(d.word_count), 2.5, 0, Math.PI * 2);
    ctx.fillStyle = '#22c55e';
    ctx.fill();
  });

  // Legend
  const legendY = h - 1;
  ctx.font = '8px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillStyle = '#6366f1';
  ctx.fillRect(4, legendY - 5, 8, 2);
  ctx.fillText('Vocab%', 14, legendY);
  ctx.fillStyle = '#22c55e';
  ctx.fillRect(60, legendY - 5, 8, 2);
  ctx.fillText('Words', 70, legendY);
}

// ─── READER ───
let readerArticleId = null;
let readerFontSize = 18;
let readerFontFamily = 'sans';
let readerHighlights = {};

function loadReaderHighlights() {
  try { readerHighlights = JSON.parse(localStorage.getItem('reader_highlights') || '{}'); } catch(e) { readerHighlights = {}; }
}
function saveReaderHighlights() {
  localStorage.setItem('reader_highlights', JSON.stringify(readerHighlights));
}

function renderBodyWithHighlights(content, highlights) {
  const paragraphs = content.split('\n').filter(p => p.trim());
  if (!highlights || !highlights.length) {
    return paragraphs.map(p => `<p>${esc(p.trim())}</p>`).join('');
  }
  const byP = {};
  highlights.forEach(h => {
    if (!byP[h.pi]) byP[h.pi] = [];
    byP[h.pi].push(h);
  });
  return paragraphs.map((pText, pi) => {
    const phs = byP[pi];
    if (!phs) return `<p>${esc(pText.trim())}</p>`;
    phs.sort((a, b) => a.start - b.start);
    let html = '', cursor = 0;
    const text = pText.trim();
    for (const h of phs) {
      const s = Math.max(cursor, Math.min(h.start, text.length));
      const e = Math.max(s, Math.min(h.end, text.length));
      if (s >= e) continue;
      html += esc(text.slice(cursor, s));
      html += `<mark class="reader-highlight hl-${h.color || 'yellow'}">${esc(text.slice(s, e))}</mark>`;
      cursor = e;
    }
    html += esc(text.slice(cursor));
    return `<p>${html}</p>`;
  }).join('');
}

function openReader(id) {
  readerArticleId = id;
  const overlay = document.getElementById('readerOverlay');
  const articleEl = document.getElementById('readerArticle');
  const countEl = document.getElementById('readerReadCount');
  overlay.classList.remove('hidden');
  overlay.className = 'reader-overlay';
  articleEl.innerHTML = '<div class="reader-loading">Opening...</div>';

  api(`/api/articles/${id}`).then(data => {
    const cat = CONFIG.categories[data.category] || { label: 'General', color: '#6b7280' };
    loadReaderHighlights();
    const hls = readerHighlights[id] || [];
    const bodyHtml = renderBodyWithHighlights(data.content || '', hls);

    articleEl.innerHTML = `
      <div class="ra-title">${esc(data.title)}</div>
      ${data.subtitle ? `<div class="ra-subtitle">${esc(data.subtitle)}</div>` : ''}
      <div class="ra-meta">
        <span class="ra-meta-cat" style="background:${cat.color}18;color:${cat.color}">${esc(cat.label)}</span>
        <span>${data.stats.word_count} words</span>
        <span>${data.stats.sentences} sentences</span>
        <span>·</span>
        <span>Updated ${fmtDate(data.updated || data.created)}</span>
      </div>
      <div class="ra-body" style="font-size:${readerFontSize}px">${bodyHtml}</div>
      ${data.keywords && data.keywords.length ? `<div class="ra-keywords">${data.keywords.map(k => `<span class="ra-kw-tag">${esc(k)}</span>`).join('')}</div>` : ''}
      <div class="ra-stats">
        <span>Vocab Score: <strong>${data.vocab.vocab_score}%</strong></span>
        <span>Unique words: <strong>${data.vocab.unique_words}</strong></span>
        <span>Avg sentence: <strong>${data.stats.avg_word_length}</strong></span>
      </div>
    `;

    const reads = data.reads || 0;
    countEl.textContent = reads;

    api(`/api/articles/${id}/read`, { method: 'POST' }).then(r => {
      countEl.textContent = r.reads;
    });
  }).catch(() => {
    articleEl.innerHTML = '<div class="reader-loading" style="color:var(--danger)">Failed to load article</div>';
  });

  applyReaderSettings();
}

function closeReader() {
  document.getElementById('readerOverlay').classList.add('hidden');
  readerArticleId = null;
}

function applyReaderSettings() {
  const overlay = document.getElementById('readerOverlay');
  overlay.className = 'reader-overlay';
  overlay.classList.add(`reader-theme-${document.querySelector('.reader-theme-dot.active')?.dataset.theme || 'light'}`);
  overlay.classList.add(`reader-font-${readerFontFamily}`);
  document.getElementById('readerFontSizeLabel').textContent = readerFontSize;
  const body = document.querySelector('#readerArticle .ra-body');
  if (body) body.style.fontSize = `${readerFontSize}px`;
}

// Reader event bindings
document.getElementById('readerClose').addEventListener('click', closeReader);

document.getElementById('readerFontDec').addEventListener('click', () => {
  if (readerFontSize > 12) { readerFontSize -= 1; applyReaderSettings(); }
});
document.getElementById('readerFontInc').addEventListener('click', () => {
  if (readerFontSize < 28) { readerFontSize += 1; applyReaderSettings(); }
});

document.getElementById('readerFontSelect').addEventListener('change', (e) => {
  readerFontFamily = e.target.value;
  applyReaderSettings();
});

document.getElementById('readerThemes').addEventListener('click', (e) => {
  const dot = e.target.closest('.reader-theme-dot');
  if (!dot) return;
  document.querySelectorAll('.reader-theme-dot').forEach(d => d.classList.remove('active'));
  dot.classList.add('active');
  applyReaderSettings();
});

document.getElementById('readerOverlay').addEventListener('click', (e) => {
  if (e.target === document.getElementById('readerOverlay')) closeReader();
});

// ─── HIGHLIGHT POPUP ───
function getParaIndex(p) {
  const body = document.querySelector('#readerArticle .ra-body');
  if (!body) return -1;
  return Array.from(body.querySelectorAll('p')).indexOf(p);
}

function hideReaderPopup() {
  document.getElementById('readerPopup').classList.add('hidden');
}

document.addEventListener('mouseup', (e) => {
  const popup = document.getElementById('readerPopup');
  if (popup.contains(e.target)) return;
    if (!readerArticleId) return;
  const overlay = document.getElementById('readerOverlay');
  if (overlay.classList.contains('hidden')) return;

  const hlEl = e.target.closest('.reader-highlight');
  if (hlEl) {
    popup._markEl = hlEl;
    popup._range = null;
    popup._selection = null;
    popup.dataset.mode = 'remove';
    const r = hlEl.getBoundingClientRect();
    popup.style.left = `${r.left + r.width / 2}px`;
    popup.style.top = `${r.top}px`;
    popup.classList.remove('hidden');
    window.getSelection().removeAllRanges();
    return;
  }

  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.toString().trim()) { hideReaderPopup(); return; }

  const range = sel.getRangeAt(0);
  const articleEl = document.getElementById('readerArticle');
  if (!articleEl.contains(range.commonAncestorContainer)) { hideReaderPopup(); return; }

  let p = range.commonAncestorContainer;
  while (p && p !== articleEl && p.tagName !== 'P') p = p.parentElement;
  if (!p || p === articleEl) { hideReaderPopup(); return; }

  const rect = range.getBoundingClientRect();
  popup._markEl = null;
  popup._range = range;
  popup._selection = sel;
  popup._para = p;
  popup.dataset.mode = 'new';
  popup.style.left = `${rect.left + rect.width / 2}px`;
  popup.style.top = `${rect.top}px`;
  popup.classList.remove('hidden');
});

document.querySelectorAll('.rp-color').forEach(btn => {
  btn.addEventListener('click', () => {
    const popup = document.getElementById('readerPopup');
    if (popup.classList.contains('hidden')) return;
    const color = btn.dataset.color;

    if (popup.dataset.mode === 'new') {
      const range = popup._range;
      const sel = popup._selection;
      const p = popup._para;
      if (!range || !sel) return;

      const articleEl = document.getElementById('readerArticle');
      if (!articleEl.contains(p)) return;
      const pi = getParaIndex(p);
      if (pi < 0) return;

      const textNodes = [];
      const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      let n;
      while (n = walker.nextNode()) textNodes.push(n);
      let start = -1, end = -1, acc = 0;
      for (const tn of textNodes) {
        if (start < 0 && tn === range.startContainer) start = acc + range.startOffset;
        if (end < 0 && tn === range.endContainer) end = acc + range.endOffset;
        if (start >= 0 && end >= 0) break;
        acc += tn.textContent.length;
      }
      if (start < 0 || end < 0 || start >= end) { hideReaderPopup(); return; }

      if (!readerHighlights[readerArticleId]) readerHighlights[readerArticleId] = [];
      readerHighlights[readerArticleId].push({ pi, start, end, color });
      saveReaderHighlights();

      try {
        const mark = document.createElement('mark');
        mark.className = `reader-highlight hl-${color}`;
        range.surroundContents(mark);
      } catch (_) {
        const data = articles.find(a => a.id === readerArticleId);
        if (data) {
          document.querySelector('#readerArticle .ra-body').innerHTML =
            renderBodyWithHighlights(data.content || '', readerHighlights[readerArticleId]);
        }
      }
      sel.removeAllRanges();
    } else if (popup.dataset.mode === 'remove') {
      const markEl = popup._markEl;
      if (!markEl) return;
      const p = markEl.closest('p');
      if (!p) return;
      const pi = getParaIndex(p);
      if (pi < 0) return;
      const text = p.textContent;
      const hlText = markEl.textContent;
      const s = text.indexOf(hlText);
      if (s < 0) return;
      const e = s + hlText.length;
      if (!readerHighlights[readerArticleId]) return;
      readerHighlights[readerArticleId] = readerHighlights[readerArticleId].filter(
        h => !(h.pi === pi && h.start === s && h.end === e)
      );
      saveReaderHighlights();
      const data = articles.find(a => a.id === readerArticleId);
      if (data) {
        document.querySelector('#readerArticle .ra-body').innerHTML =
          renderBodyWithHighlights(data.content || '', readerHighlights[readerArticleId]);
      }
    }
    hideReaderPopup();
  });
});

document.getElementById('readerPopupRemove').addEventListener('click', () => {
  const popup = document.getElementById('readerPopup');
  const markEl = popup._markEl;
  if (!markEl) return;
  const p = markEl.closest('p');
  if (!p) return;
  const pi = getParaIndex(p);
  if (pi < 0) return;
  const text = p.textContent;
  const hlText = markEl.textContent;
  const s = text.indexOf(hlText);
  if (s < 0) return;
  const e = s + hlText.length;
  if (!readerHighlights[readerArticleId]) return;
  readerHighlights[readerArticleId] = readerHighlights[readerArticleId].filter(
    h => !(h.pi === pi && h.start === s && h.end === e)
  );
  saveReaderHighlights();
  const data = articles.find(a => a.id === readerArticleId);
  if (data) {
    document.querySelector('#readerArticle .ra-body').innerHTML =
      renderBodyWithHighlights(data.content || '', readerHighlights[readerArticleId]);
  }
  hideReaderPopup();
});

// Hide popup on scroll
document.querySelector('.reader-scroll').addEventListener('scroll', hideReaderPopup);
// Hide popup on reader close
const origCloseReader = closeReader;
closeReader = function() { hideReaderPopup(); origCloseReader(); }

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
document.getElementById('grammarClose').addEventListener('click', () => document.getElementById('grammarPanel').classList.add('hidden'));

// Keyword Filters search, clear, and match logic toggles
const kwSearchInput = document.getElementById('kwSearchInput');
if (kwSearchInput) {
  kwSearchInput.addEventListener('input', (e) => {
    kwSearchQuery = e.target.value.trim();
    renderKeywordFilters();
  });
}

const clearKwFiltersBtn = document.getElementById('clearKwFiltersBtn');
if (clearKwFiltersBtn) {
  clearKwFiltersBtn.addEventListener('click', () => {
    activeKeywordFilters = [];
    if (kwSearchInput) kwSearchInput.value = '';
    kwSearchQuery = '';
    renderKeywordFilters();
    renderList();
  });
}

const kwMatchModeBtn = document.getElementById('kwMatchModeBtn');
if (kwMatchModeBtn) {
  kwMatchModeBtn.addEventListener('click', () => {
    kwMatchMode = (kwMatchMode === 'ANY') ? 'ALL' : 'ANY';
    kwMatchModeBtn.textContent = kwMatchMode;
    kwMatchModeBtn.className = `btn-match-mode ${kwMatchMode === 'ALL' ? 'match-all' : 'match-any'}`;
    renderList();
  });
}

// Search
searchInput.addEventListener('input', renderList);

// Buttons
document.getElementById('saveBtn').addEventListener('click', saveArticle);
document.getElementById('spellCheckBtn').addEventListener('click', runSpellCheck);
document.getElementById('vocabBtn').addEventListener('click', runVocabAnalysis);
document.getElementById('grammarBtn').addEventListener('click', runGrammarCheck);
document.getElementById('downloadPdfBtn').addEventListener('click', downloadPdf);
document.getElementById('deleteBtn').addEventListener('click', deleteArticle);
document.getElementById('newArticleBtn').addEventListener('click', newArticle);
document.getElementById('welcomeNewBtn').addEventListener('click', newArticle);
document.getElementById('timerToggle').addEventListener('click', toggleTimer);
document.getElementById('timerReset').addEventListener('click', resetTimer);
document.getElementById('collapseBtn').addEventListener('click', toggleSidebar);

// Keyboard
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !document.getElementById('readerOverlay').classList.contains('hidden')) {
    closeReader();
    return;
  }
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
