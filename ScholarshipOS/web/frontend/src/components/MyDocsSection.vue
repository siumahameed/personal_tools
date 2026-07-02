<template>
  <div class="md">
    <!-- Status -->
    <div v-if="status.progress" class="md-bar" :class="{ ok: status.done }">
      <span class="md-bar-dot"></span>{{ status.progress }}
    </div>

    <!-- Empty -->
    <div v-if="Object.keys(docs).length === 0" class="md-empty">
      <div class="md-empty-icon">📝</div>
      <h3>No documents yet</h3>
      <p>Generate AI-powered SOP, CV, Research Proposal, and more for your followed scholarships.</p>
      <button class="md-btn" @click="generateAll" :disabled="status.running">{{ status.running ? 'Generating...' : 'Generate Documents' }}</button>
    </div>

    <!-- Content -->
    <div v-else class="md-body">
      <!-- Top split: scholarship selector left, meta right -->
      <div class="md-top">
        <div class="md-picker">
          <label class="md-label">Scholarship</label>
          <select v-model="activeScholarship" @change="onSchChange" class="md-select">
            <option v-for="(d, n) in docs" :key="n" :value="n">{{ n }} ({{ readyCount(d) }}/{{ docTypes.length }})</option>
          </select>
        </div>
        <div class="md-top-actions">
          <span class="md-pill-count">{{ Object.keys(docs).length }} scholarships</span>
          <button class="md-btn md-btn-ghost" @click="generateAll" :disabled="status.running">⟳ Generate All</button>
        </div>
      </div>

      <!-- No selection -->
      <div v-if="!activeScholarship" class="md-none"><p>Select a scholarship above</p></div>

      <template v-else>
        <!-- Doc type tabs -->
        <div class="md-tabs">
          <button v-for="dt in docTypes" :key="dt.id" class="md-tab" :class="{ active: activeDocType === dt.id, done: hasContent(dt.id) }" @click="activeDocType = dt.id">
            {{ dt.label }}<span v-if="hasContent(dt.id)" class="md-check">✓</span>
          </button>
        </div>

        <!-- Toolbar -->
        <div class="md-tools" v-if="currentContent">
          <div class="md-tools-l">
            <button class="md-tb" @click="copyContent">📋 Copy</button>
            <button class="md-tb" @click="exportPdf">📄 PDF</button>
            <button class="md-tb" @click="regenerateAll" :disabled="status.running">⟳ Regenerate</button>
          </div>
          <div class="md-tools-r">
            <span class="md-wc">{{ wordCount }} words</span>
            <span class="md-sep">·</span>
            <span class="md-date">Generated {{ timeAgo(currentMeta?.generated_at) }}</span>
          </div>
        </div>

        <!-- Document -->
        <div v-if="currentContent" class="md-doc">
          <div v-for="(text, heading) in parsedSections" :key="heading" class="md-sec">
            <div class="md-sec-h">
              <h3>{{ heading }}</h3>
              <button class="md-regen" @click="regenerateSection(heading)" :disabled="status.running" title="Rewrite this section">⟳</button>
            </div>
            <div class="md-sec-b" v-html="render(text)"></div>
          </div>
        </div>
        <div v-else class="md-none">
          <p>{{ activeDocTypeLabel }} not generated</p>
          <button class="md-btn md-btn-sm" @click="generateSingle" :disabled="status.running">Generate Now</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
const api = (u, o) => fetch(u, o).then(r => { if (!r.ok) throw Error(); return r.json() });

export default {
  name: 'MyDocsSection',
  data: () => ({
    docs: {},
    docTypes: [],
    status: { running: false, progress: '', done: false },
    activeScholarship: null,
    activeDocType: 'sop',
  }),
  computed: {
    currentContent() { return this.docs[this.activeScholarship]?.[this.activeDocType]?.content || null; },
    currentMeta() {
      const d = this.docs[this.activeScholarship]?.[this.activeDocType];
      return d?.generated_at ? (({ content, ...m }) => m)(d) : null;
    },
    wordCount() { return this.currentContent ? this.currentContent.split(/\s+/).filter(Boolean).length : 0; },
    activeDocTypeLabel() { return this.docTypes.find(d => d.id === this.activeDocType)?.label || this.activeDocType; },
    parsedSections() {
      if (!this.currentContent) return {};
      const s = {}; let h = null, l = [];
      for (const ln of this.currentContent.split('\n')) {
        const m = ln.match(/^##\s+(.+)/);
        if (m) { if (h && l.length) s[h] = l.join('\n').trim(); h = m[1].trim(); l = []; }
        else l.push(ln);
      }
      if (h && l.length) s[h] = l.join('\n').trim();
      if (!Object.keys(s).length && this.currentContent) s['Document'] = this.currentContent;
      return s;
    },
  },
  mounted() { this.fetchAll(); },
  methods: {
    readyCount(d) { return Object.keys(d).filter(k => d[k]?.content).length; },
    hasContent(t) { return !!this.docs[this.activeScholarship]?.[t]?.content; },
    onSchChange() {
      if (!this.docs[this.activeScholarship]?.[this.activeDocType]) {
        const f = this.docTypes.find(t => this.docs[this.activeScholarship]?.[t.id]);
        this.activeDocType = f?.id || this.docTypes[0]?.id || 'sop';
      }
    },
    async fetchAll() {
      try { this.docs = await api('/api/my-docs'); } catch {}
      try { this.docTypes = await api('/api/my-docs/supported-types'); } catch {}
    },
    render(t) {
      if (!t) return '';
      let h = t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
      h = h.replace(/^- (.+)/gm, '<li>$1</li>');
      h = h.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
      h = h.replace(/\n\n/g, '</p><p>');
      h = h.replace(/\n/g, '<br>');
      return '<p>' + h + '</p>';
    },
    timeAgo(d) {
      if (!d) return '';
      const s = Math.floor((Date.now() - new Date(d)) / 1000);
      if (s < 60) return 'just now';
      if (s < 3600) return Math.floor(s / 60) + 'm ago';
      if (s < 86400) return Math.floor(s / 3600) + 'h ago';
      return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    },
    async generateAll() {
      this.status = { running: true, progress: 'Generating documents...', done: false };
      try { await api('/api/my-docs/generate', { method: 'POST' }); this.poll(); }
      catch { this.status.running = false; this.status.progress = 'Error'; }
    },
    async generateSingle() {
      if (!this.activeScholarship) return;
      this.status = { running: true, progress: 'Generating...', done: false };
      try {
        const d = await api('/api/my-docs/generate-single', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: this.activeScholarship }) });
        this.docs[this.activeScholarship] = d;
        this.status = { running: false, progress: 'Done', done: true };
        setTimeout(() => { this.status.progress = ''; }, 2000);
      } catch { this.status = { running: false, progress: 'Error', done: false }; }
    },
    async regenerateSection(section) {
      try {
        const r = await api('/api/my-docs/regenerate-section', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: this.activeScholarship, doc_type: this.activeDocType, section }) });
        if (r.content) { if (!this.docs[this.activeScholarship]) this.docs[this.activeScholarship] = {}; this.docs[this.activeScholarship][this.activeDocType] = r; }
      } catch {}
    },
    async regenerateAll() { await this.generateSingle(); },
    async copyContent() {
      if (!this.currentContent) return;
      try { await navigator.clipboard.writeText(this.currentContent); this.status = { ...this.status, progress: 'Copied!', done: true }; setTimeout(() => { this.status.progress = ''; }, 1500); } catch {}
    },
    exportPdf() {
      if (!this.activeScholarship || !this.activeDocType) return;
      window.open(`/api/my-docs/export-pdf?name=${encodeURIComponent(this.activeScholarship)}&doc_type=${this.activeDocType}`, '_blank');
    },
    poll() {
      const iv = setInterval(async () => {
        try {
          const s = await api('/api/my-docs/status');
          this.status = { running: s.running, progress: s.progress, done: s.done };
          if (!s.running) { clearInterval(iv); await this.fetchAll(); setTimeout(() => { this.status.progress = ''; }, 2000); }
        } catch { clearInterval(iv); }
      }, 2000);
    },
  },
};
</script>

<style scoped>
.md {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Bar */
.md-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.85rem;
  border-radius: 8px;
  font-size: 0.8rem;
  background: rgba(59,130,246,0.07);
  border: 1px solid rgba(59,130,246,0.12);
  color: #93c5fd;
}
.md-bar.ok { background: rgba(16,185,129,0.07); border-color: rgba(16,185,129,0.12); color: #6ee7b7; }
.md-bar-dot { width: 6px; height: 6px; border-radius: 50%; background: #3b82f6; flex-shrink: 0; }
.md-bar.ok .md-bar-dot { background: #10b981; }

/* Empty */
.md-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  gap: 0.3rem;
}
.md-empty-icon { font-size: 2.5rem; }
.md-empty h3 { font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 700; color: #94a3b8; margin: 0; }
.md-empty p { font-size: 0.82rem; color: #64748b; margin: 0 0 0.75rem; }

/* Buttons */
.md-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 7px;
  font-family: inherit;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  box-shadow: 0 3px 10px rgba(59,130,246,0.2);
  transition: all 0.15s;
}
.md-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 5px 15px rgba(59,130,246,0.3); }
.md-btn:disabled { opacity: 0.4; cursor: not-allowed; box-shadow: none; }
.md-btn-ghost { background: rgba(255,255,255,0.04); color: #94a3b8; box-shadow: none; border: 1px solid rgba(255,255,255,0.06); }
.md-btn-ghost:hover:not(:disabled) { background: rgba(255,255,255,0.07); color: #e2e8f0; box-shadow: none; transform: none; }
.md-btn-sm { padding: 0.35rem 0.8rem; font-size: 0.78rem; }

/* Body */
.md-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Top row */
.md-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
}
.md-picker { display: flex; flex-direction: column; gap: 0.2rem; min-width: 0; flex: 1; max-width: 500px; }
.md-label { font-size: 0.68rem; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; }
.md-select {
  background: rgba(13,22,38,0.6);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 7px;
  padding: 0.5rem 0.7rem;
  color: #e2e8f0;
  font-size: 0.85rem;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  min-width: 0;
}
.md-select:focus { outline: none; border-color: rgba(59,130,246,0.4); }
.md-top-actions { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }
.md-pill-count { font-size: 0.72rem; color: #475569; background: rgba(255,255,255,0.02); padding: 0.2rem 0.5rem; border-radius: 5px; }

/* Tabs */
.md-tabs {
  display: flex;
  gap: 2px;
  background: rgba(255,255,255,0.02);
  border-radius: 8px;
  padding: 2px;
  overflow-x: auto;
}
.md-tab {
  background: none;
  border: none;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  color: #64748b;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
  font-family: inherit;
  white-space: nowrap;
  transition: all 0.12s;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.md-tab:hover { color: #94a3b8; }
.md-tab.active { background: rgba(59,130,246,0.12); color: #60a5fa; }
.md-check { font-size: 0.6rem; color: #10b981; }

/* Tools */
.md-tools {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.md-tools-l { display: flex; gap: 0.2rem; }
.md-tb {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 5px;
  padding: 0.3rem 0.6rem;
  color: #64748b;
  cursor: pointer;
  font-size: 0.72rem;
  font-family: inherit;
  font-weight: 500;
  transition: all 0.12s;
}
.md-tb:hover:not(:disabled) { background: rgba(255,255,255,0.05); color: #e2e8f0; border-color: rgba(255,255,255,0.08); }
.md-tb:disabled { opacity: 0.3; cursor: not-allowed; }
.md-tools-r { display: flex; align-items: center; gap: 0.3rem; font-size: 0.7rem; color: #475569; }
.md-wc { color: #64748b; }
.md-sep { color: #334155; }
.md-date { color: #475569; }

/* Document */
.md-doc {
  background: rgba(13,22,38,0.3);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  padding: 1.5rem 2rem;
  max-height: 600px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.md-sec {
  position: relative;
}
.md-sec-h {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
}
.md-sec-h h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0 0 0.25rem;
  padding-bottom: 0.15rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.md-regen {
  background: none;
  border: none;
  color: #334155;
  cursor: pointer;
  font-size: 0.8rem;
  padding: 0.15rem;
  opacity: 0;
  transition: opacity 0.12s, color 0.12s;
  flex-shrink: 0;
}
.md-sec:hover .md-regen { opacity: 1; }
.md-regen:hover { color: #a78bfa; }
.md-regen:disabled { opacity: 0; cursor: not-allowed; }
.md-sec-b {
  font-size: 0.85rem;
  line-height: 1.8;
  color: #cbd5e1;
}
.md-sec-b :deep(p) { margin: 0.3em 0; }
.md-sec-b :deep(ul) { padding-left: 1.2rem; margin: 0.3em 0; list-style: none; }
.md-sec-b :deep(li) { position: relative; padding-left: 0.5rem; margin: 0.1em 0; }
.md-sec-b :deep(li)::before { content: '•'; position: absolute; left: -0.1rem; color: #6366f1; }
.md-sec-b :deep(strong) { color: #f1f5f9; font-weight: 600; }

/* None */
.md-none {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  text-align: center;
  gap: 0.5rem;
  background: rgba(13,22,38,0.2);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.03);
  flex: 1;
}
.md-none p { font-size: 0.82rem; color: #475569; margin: 0; }
</style>
