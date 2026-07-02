<template>
  <div class="documents-container">
    <div class="section-header">
      <div class="section-title-row">
        <h2 class="section-title">📄 Application Documents Library</h2>
        <div class="header-actions">
          <button
            class="deep-research-btn"
            :class="{ running: deepResearch.running, done: deepResearch.done && !deepResearch.running }"
            :disabled="deepResearch.running"
            @click="triggerDeepResearch(false, true)"
            :title="deepResearch.running ? 'Scan in progress' : 'Quick scan: GitHub + PDFs + 35+ curated resources (Reddit, Overleaf, Harvard/MIT guides, DAAD, Erasmus, Chevening, Fulbright, GKS, MEXT, FindAPhD, WriteIvy, Yocket, Facebook, LinkedIn) + Bangladeshi priority'"
          >
            <span class="dr-icon" :class="{ spin: deepResearch.running }">{{ deepResearch.running ? '⏳' : '🔬' }}</span>
            <span class="dr-text">
              {{ deepResearch.running ? 'Scanning...' : (deepResearch.done ? 'Quick Scan Again' : 'Quick Scan Documents') }}
            </span>
          </button>
          <button
            class="deep-research-btn force-btn"
            :disabled="deepResearch.running"
            @click="triggerDeepResearch(false, false)"
            title="Full scan: 10 phases across GitHub, 35+ curated resources, social media, Reddit, Medium, Bangladeshi priority, arXiv (~12 min)"
          >
            <span class="dr-icon">🔍</span>
            <span class="dr-text">Deep Scan</span>
          </button>
          <button
            class="deep-research-btn force-btn"
            :disabled="deepResearch.running"
            @click="triggerDeepResearch(true, false)"
            title="Force deep re-scan: update metadata of existing documents + all sources"
          >
            <span class="dr-icon">🔄</span>
            <span class="dr-text">Force Deep</span>
          </button>
          <button
            class="deep-research-btn clear-btn"
            :disabled="deepResearch.running"
            @click="clearLibrary"
            title="Delete all documents and start fresh"
          >
            <span class="dr-icon">🗑️</span>
            <span class="dr-text">Clear</span>
          </button>
        </div>
      </div>
        <p class="section-subtitle">
        Real SOPs, CVs, and recommendation letters from scholarship winners worldwide &mdash; including Bangladeshi students. Scanned from 35+ curated sources: r/gradadmissions, r/StatementOfPurpose, GradCafe, Overleaf CV Gallery, Harvard/MIT Resume Guides, DAAD, Erasmus, Chevening, Fulbright, GKS, MEXT, FindAPhD, WriteIvy, Yocket, GeeksforGeeks, CareersHelpDesk, RequestLetters, ResumeGenius, Scholarship Roar, Edinburgh Research, Prospects UK, Facebook groups, LinkedIn, and more.
      </p>
      <div v-if="deepResearch.progress" class="deep-research-status">
        <span class="dr-status-dot" :class="{ pulse: deepResearch.running, done: deepResearch.done }"></span>
        <span class="dr-status-text">{{ deepResearch.progress }}</span>
        <span v-if="deepResearch.done && deepResearch.added > 0" class="dr-status-result">
          +{{ deepResearch.added }} new
        </span>
      </div>
    </div>

    <!-- Sub-tabs -->
    <div class="sub-tabs">
      <button
        v-for="st in subTabs"
        :key="st.id"
        class="sub-tab"
        :class="{ active: activeSubTab === st.id }"
        @click="activeSubTab = st.id"
      >
        <span class="sub-tab-icon">{{ st.icon }}</span>
        <span class="sub-tab-label">{{ st.label }}</span>
        <span class="sub-tab-count">{{ st.count }}</span>
      </button>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="filter-search-container">
        <span class="search-icon-inside">🔍</span>
        <input type="text" v-model="filters.search" placeholder="Search by scholar, university, program, or field..." class="search-input" />
      </div>
      <select v-model="filters.country" class="filter-select">
        <option value="">All Countries</option>
        <option v-for="c in uniqueCountries" :key="c" :value="c">{{ c }}</option>
      </select>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>Loading document samples...</p>
    </div>

    <div v-else-if="filteredDocs.length === 0" class="empty-results">
      No documents match your filter criteria. Try a different search or country.
    </div>

    <div v-else class="docs-grid">
      <div v-for="doc in filteredDocs" :key="doc.id" class="doc-card">
        <div class="doc-badges-row">
          <div class="doc-type-badge" :class="doc.type">
            {{ typeLabel(doc.type) }}
          </div>
          <div v-if="doc.source" class="doc-source-badge" :class="sourceClass(doc.source)">
            {{ sourceLabel(doc.source) }}
          </div>
          <div v-if="isBangladeshi(doc)" class="bd-badge" title="Bangladeshi student document">
            🇧🇩 BD
          </div>
        </div>
        <div class="doc-card-header">
          <h3 class="doc-title">{{ doc.title }}</h3>
          <p class="doc-scholar">
            <span class="label">Scholar:</span> {{ doc.scholar_name }}
          </p>
        </div>
        <div class="doc-card-body">
          <div class="doc-detail-row">
            <span class="detail-icon">🎓</span>
            <span class="detail-text">{{ doc.scholarship_name }}</span>
          </div>
          <div class="doc-detail-row">
            <span class="detail-icon">🏛</span>
            <span class="detail-text">{{ doc.university }}</span>
          </div>
          <div class="doc-detail-row">
            <span class="detail-icon">📚</span>
            <span class="detail-text">{{ doc.program }}</span>
          </div>
          <div class="doc-detail-row">
            <span class="detail-icon">🌍</span>
            <span class="detail-text">{{ doc.country }}</span>
          </div>
          <p class="doc-description">{{ doc.description }}</p>
          <div class="doc-takeaways" v-if="doc.key_takeaways && doc.key_takeaways.length">
            <strong>Key takeaways:</strong>
            <ul>
              <li v-for="(tip, tIdx) in doc.key_takeaways" :key="tIdx">{{ tip }}</li>
            </ul>
          </div>
        </div>
        <div class="doc-card-footer">
          <a :href="doc.url" target="_blank" rel="noopener noreferrer" class="view-sample-btn">
            <span class="btn-icon">📂</span> View Sample
          </a>
          <span class="doc-field" v-if="doc.field">{{ doc.field }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DocumentsSection',
  data() {
    return {
      loading: true,
      activeSubTab: 'sop',
      allDocs: [],
      filters: {
        search: '',
        country: ''
      },
      deepResearch: {
        running: false,
        progress: '',
        done: false,
        added: 0
      },
      deepResearchPoll: null
    }
  },
  computed: {
    subTabs() {
      const counts = { sop: 0, resume: 0, recommendation: 0, motivation_letter: 0, research_proposal: 0, certificate: 0, study_plan: 0 }
      this.allDocs.forEach(d => {
        if (counts[d.type] !== undefined) counts[d.type]++
      })
      return [
        { id: 'sop', icon: '📝', label: 'Statements of Purpose', count: counts.sop },
        { id: 'motivation_letter', icon: '💌', label: 'Motivation Letters', count: counts.motivation_letter },
        { id: 'study_plan', icon: '📐', label: 'Study Plans', count: counts.study_plan },
        { id: 'research_proposal', icon: '🔬', label: 'Research Proposals', count: counts.research_proposal },
        { id: 'resume', icon: '📋', label: 'CVs & Resumes', count: counts.resume },
        { id: 'recommendation', icon: '✉️', label: 'Recommendation Letters', count: counts.recommendation },
        { id: 'certificate', icon: '🏅', label: 'Certificates', count: counts.certificate }
      ]
    },
    filteredDocs() {
      return this.allDocs.filter(d => {
        if (d.type !== this.activeSubTab) return false
        const q = this.filters.search.toLowerCase()
        if (q && !d.title.toLowerCase().includes(q) && !d.scholar_name.toLowerCase().includes(q) && !d.university.toLowerCase().includes(q) && !d.program.toLowerCase().includes(q) && !d.field.toLowerCase().includes(q)) {
          return false
        }
        if (this.filters.country && d.country !== this.filters.country) return false
        return true
      })
    },
    uniqueCountries() {
      return [...new Set(this.allDocs.filter(d => d.type === this.activeSubTab).map(d => d.country))].sort()
    }
  },
  mounted() {
    this.fetchDocuments()
    this.checkDeepResearchStatus()
  },
  beforeUnmount() {
    if (this.deepResearchPoll) {
      clearInterval(this.deepResearchPoll)
      this.deepResearchPoll = null
    }
  },
  methods: {
    fetchDocuments() {
      this.loading = true
      fetch('/api/documents')
        .then(r => r.json())
        .then(data => {
          this.allDocs = data.samples || []
          this.loading = false
        })
        .catch(err => {
          console.error('Fetch documents error:', err)
          this.loading = false
        })
    },
    clearLibrary() {
      if (!confirm('Delete ALL documents from the library? This cannot be undone.')) return
      fetch('/api/documents/clear', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          if (data.status === 'cleared') {
            this.allDocs = []
            this.deepResearch = { running: false, progress: 'Library cleared. Click Run Deep Research to start fresh.', done: true, added: 0 }
            this.fetchDocuments()
          }
        })
        .catch(err => {
          console.error('Clear library error:', err)
          alert('Failed to clear library: ' + err)
        })
    },
    checkDeepResearchStatus() {
      fetch('/api/documents/deep-research-status')
        .then(r => r.json())
        .then(status => {
          this.deepResearch.running = !!status.running
          this.deepResearch.progress = status.progress || ''
          this.deepResearch.done = !!status.done
          this.deepResearch.added = status.added || 0
          if (status.running) {
            this.startDeepResearchPolling()
          } else if (status.last_result && !this.deepResearch.progress) {
            const last = status.last_result
            this.deepResearch.progress = last.summary || ''
            this.deepResearch.added = last.added || 0
            this.deepResearch.done = true
          }
        })
        .catch(err => console.error('Deep research status error:', err))
    },
    triggerDeepResearch(force = false, quick = true) {
      this.deepResearch.running = true
      const mode = quick ? 'Quick' : 'Deep'
      this.deepResearch.progress = `Starting ${mode} scan${force ? ' (forced refresh)' : ''}...`
      this.deepResearch.done = false
      this.deepResearch.added = 0
      fetch('/api/documents/deep-research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: force, quick: quick })
      })
        .then(r => r.json())
        .then(data => {
          if (data.status === 'started') {
            this.startDeepResearchPolling()
          } else {
            this.deepResearch.running = false
            this.deepResearch.progress = data.error || 'Failed to start.'
          }
        })
        .catch(err => {
          this.deepResearch.running = false
          this.deepResearch.progress = `Failed: ${err}`
        })
    },
    startDeepResearchPolling() {
      if (this.deepResearchPoll) clearInterval(this.deepResearchPoll)
      this.deepResearchPoll = setInterval(() => {
        fetch('/api/documents/deep-research-status')
          .then(r => r.json())
          .then(status => {
            this.deepResearch.running = !!status.running
            this.deepResearch.progress = status.progress || ''
            this.deepResearch.done = !!status.done
            this.deepResearch.added = status.added || 0
            if (status.done || !status.running) {
              clearInterval(this.deepResearchPoll)
              this.deepResearchPoll = null
              this.fetchDocuments()
            }
          })
          .catch(err => {
            console.error('Deep research polling error:', err)
            clearInterval(this.deepResearchPoll)
            this.deepResearchPoll = null
          })
      }, 1500)
    },
    isBangladeshi(doc) {
      const text = (doc.country + ' ' + doc.title + ' ' + doc.description + ' ' + doc.scholar_name).toLowerCase()
      return text.includes('bangladesh') || text.includes('bangladeshi') || text.includes('dhaka') || text.includes('buet')
    },
    typeLabel(type) {
      const labels = {
        sop: 'SOP',
        resume: 'CV',
        recommendation: 'LOR',
        motivation_letter: 'Motivation',
        research_proposal: 'Proposal',
        certificate: 'Certificate',
        study_plan: 'Study Plan'
      }
      return labels[type] || type
    },
    sourceClass(source) {
      if (!source) return ''
      const s = source.toLowerCase()
      if (s.includes('facebook')) return 'src-facebook'
      if (s.includes('linkedin')) return 'src-linkedin'
      if (s.includes('twitter') || s.includes('/x.com')) return 'src-twitter'
      if (s.includes('reddit')) return 'src-reddit'
      if (s.includes('github')) return 'src-github'
      if (s.includes('youtube')) return 'src-youtube'
      if (s.includes('medium')) return 'src-medium'
      if (s.includes('telegram') || s.includes('t.me')) return 'src-telegram'
      if (s.includes('bangladesh') || s.includes('bangladeshi')) return 'src-bangladesh'
      if (s.includes('discord') || s.includes('whatsapp')) return 'src-social'
      if (s.includes('arxiv')) return 'src-arxiv'
      return 'src-web'
    },
    sourceLabel(source) {
      if (!source) return 'Web'
      const s = source
      const labels = [
        ['Facebook', 'FB'],
        ['LinkedIn', 'LI'],
        ['Twitter', 'X'],
        ['Reddit', 'Reddit'],
        ['GitHub', 'GitHub'],
        ['YouTube', 'YT'],
        ['Medium', 'Medium'],
        ['Telegram', 'TG'],
        ['Bangladesh', 'BD'],
        ['Discord', 'Discord'],
        ['WhatsApp', 'WA'],
        ['arXiv', 'arXiv'],
        ['Bing', 'Bing'],
        ['Notion', 'Notion'],
        ['Substack', 'Sub'],
        ['ResearchGate', 'RG'],
        ['Academia', 'Acad'],
        ['Issuu', 'Issuu'],
        ['Scribd', 'Scribd'],
      ]
      for (const [key, label] of labels) {
        if (s.includes(key)) return label
      }
      return s.split(':')[0].trim().substring(0, 6)
    }
  }
}
</script>

<style scoped>
.documents-container {
  padding: 0;
}

.section-header {
  margin-bottom: 1.5rem;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 800;
  color: #fff;
  margin: 0 0 0.35rem;
}

.section-subtitle {
  color: #94a3b8;
  font-size: 0.85rem;
  margin: 0.35rem 0 0;
  line-height: 1.5;
}

/* Deep Research Button */
.deep-research-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.1rem;
  background: linear-gradient(135deg, #8b5cf6, #ec4899);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.85rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3);
  white-space: nowrap;
}

.deep-research-btn.force-btn {
  background: linear-gradient(135deg, #f59e0b, #ea580c);
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.3);
}

.deep-research-btn.force-btn:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.45);
  background: linear-gradient(135deg, #d97706, #c2410c);
}

.deep-research-btn.clear-btn {
  background: linear-gradient(135deg, #ef4444, #b91c1c);
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
}

.deep-research-btn.clear-btn:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.45);
  background: linear-gradient(135deg, #dc2626, #991b1b);
}

.deep-research-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.45);
  background: linear-gradient(135deg, #7c3aed, #db2777);
}

.deep-research-btn:disabled {
  cursor: not-allowed;
  opacity: 0.95;
}

.deep-research-btn.running {
  background: rgba(139, 92, 246, 0.15);
  border: 1px solid rgba(139, 92, 246, 0.35);
  color: #c4b5fd;
  box-shadow: none;
}

.deep-research-btn.done {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #6ee7b7;
  box-shadow: none;
}

.dr-icon {
  font-size: 1rem;
  display: inline-block;
}

.dr-icon.spin {
  animation: dr-pulse 1.5s ease-in-out infinite;
}

@keyframes dr-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}

.dr-text {
  letter-spacing: 0.2px;
}

/* Deep Research status banner */
.deep-research-status {
  margin-top: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  background: rgba(139, 92, 246, 0.08);
  border: 1px solid rgba(139, 92, 246, 0.2);
  padding: 0.5rem 0.85rem;
  border-radius: 8px;
  font-size: 0.8rem;
  color: #c4b5fd;
  flex-wrap: wrap;
}

.dr-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #8b5cf6;
  flex-shrink: 0;
}

.dr-status-dot.pulse {
  animation: pulse 1.5s ease-in-out infinite;
}

.dr-status-dot.done {
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.dr-status-text {
  flex: 1;
  min-width: 0;
  line-height: 1.3;
}

.dr-status-result {
  background: rgba(16, 185, 129, 0.2);
  color: #6ee7b7;
  padding: 0.1rem 0.5rem;
  border-radius: 10px;
  font-weight: 800;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.6; }
}

/* Sub-tabs */
.sub-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.sub-tab {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.55rem 1rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
  color: #94a3b8;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.sub-tab:hover {
  background: rgba(255, 255, 255, 0.06);
  color: white;
}

.sub-tab.active {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.25);
  color: #60a5fa;
}

.sub-tab-icon {
  font-size: 0.9rem;
}

.sub-tab-count {
  background: rgba(255, 255, 255, 0.06);
  padding: 0.1rem 0.45rem;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 700;
}

.sub-tab.active .sub-tab-count {
  background: rgba(59, 130, 246, 0.2);
}

/* Filter */
.filter-bar {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  align-items: center;
  flex-wrap: wrap;
}

.filter-search-container {
  position: relative;
  flex: 1;
  min-width: 200px;
}

.search-icon-inside {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.85rem;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.55rem 0.75rem 0.55rem 2.2rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: #e2e8f0;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.search-input:focus {
  border-color: rgba(59, 130, 246, 0.4);
}

.search-input::placeholder {
  color: #64748b;
}

.filter-select {
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: #e2e8f0;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  outline: none;
  cursor: pointer;
  min-width: 140px;
}

.filter-select option {
  background: #1a2744;
  color: #e2e8f0;
}

/* Loading & Empty */
.loading-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #94a3b8;
}

.loader {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(255, 255, 255, 0.05);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 0.75rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-results {
  text-align: center;
  padding: 3rem 1rem;
  color: #64748b;
  font-size: 0.9rem;
}

/* Grid */
.docs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 1rem;
}

@media (max-width: 600px) {
  .docs-grid {
    grid-template-columns: 1fr;
  }
}

/* Card */
.doc-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.doc-card:hover {
  border-color: rgba(59, 130, 246, 0.2);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.doc-badges-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0.75rem 0.75rem 0;
  flex-wrap: wrap;
}

.doc-type-badge {
  padding: 0.25rem 0.65rem;
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  border-radius: 6px;
}

.doc-source-badge {
  padding: 0.2rem 0.5rem;
  font-size: 0.6rem;
  font-weight: 700;
  border-radius: 4px;
  letter-spacing: 0.3px;
  white-space: nowrap;
}

.doc-source-badge.src-github { background: rgba(110, 84, 148, 0.2); color: #a78bfa; }
.doc-source-badge.src-reddit { background: rgba(255, 69, 0, 0.15); color: #ff6b4a; }
.doc-source-badge.src-facebook { background: rgba(24, 119, 242, 0.15); color: #6b9ff2; }
.doc-source-badge.src-linkedin { background: rgba(0, 119, 181, 0.15); color: #4a9bc2; }
.doc-source-badge.src-twitter { background: rgba(29, 161, 242, 0.15); color: #6bb8f2; }
.doc-source-badge.src-medium { background: rgba(18, 180, 100, 0.15); color: #5cc88a; }
.doc-source-badge.src-youtube { background: rgba(255, 0, 0, 0.15); color: #ff5c5c; }
.doc-source-badge.src-telegram { background: rgba(0, 136, 204, 0.15); color: #4ab0e0; }
.doc-source-badge.src-bangladesh { background: rgba(0, 106, 78, 0.2); color: #4cc9a0; }
.doc-source-badge.src-arxiv { background: rgba(179, 27, 27, 0.12); color: #cc5555; }
.doc-source-badge.src-web { background: rgba(255, 255, 255, 0.06); color: #94a3b8; }
.doc-source-badge.src-social { background: rgba(139, 92, 246, 0.12); color: #a78bfa; }

.bd-badge {
  padding: 0.2rem 0.45rem;
  font-size: 0.6rem;
  font-weight: 800;
  border-radius: 4px;
  background: rgba(0, 106, 78, 0.25);
  color: #34d399;
  border: 1px solid rgba(0, 106, 78, 0.3);
  white-space: nowrap;
}

.doc-type-badge.sop {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.doc-type-badge.resume {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}

.doc-type-badge.recommendation {
  background: rgba(168, 85, 247, 0.15);
  color: #a78bfa;
}

.doc-type-badge.motivation_letter {
  background: rgba(236, 72, 153, 0.15);
  color: #f472b6;
}

.doc-type-badge.research_proposal {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.doc-type-badge.certificate {
  background: rgba(34, 211, 238, 0.15);
  color: #67e8f9;
}

.doc-type-badge.study_plan {
  background: rgba(52, 211, 153, 0.15);
  color: #6ee7b7;
}

.doc-card-header {
  padding: 0.75rem 0.75rem 0;
}

.doc-title {
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0 0 0.35rem;
  line-height: 1.4;
}

.doc-scholar {
  font-size: 0.75rem;
  color: #94a3b8;
  margin: 0;
}

.doc-scholar .label {
  color: #64748b;
}

.doc-card-body {
  padding: 0.75rem;
  flex: 1;
}

.doc-detail-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  color: #cbd5e1;
  margin-bottom: 0.3rem;
}

.detail-icon {
  font-size: 0.7rem;
  width: 1rem;
  text-align: center;
  flex-shrink: 0;
}

.detail-text {
  line-height: 1.4;
}

.doc-description {
  font-size: 0.75rem;
  color: #94a3b8;
  line-height: 1.5;
  margin: 0.6rem 0;
}

.doc-takeaways {
  font-size: 0.7rem;
  color: #94a3b8;
  margin-top: 0.5rem;
}

.doc-takeaways strong {
  color: #64748b;
  display: block;
  margin-bottom: 0.25rem;
}

.doc-takeaways ul {
  margin: 0;
  padding-left: 1rem;
}

.doc-takeaways li {
  margin-bottom: 0.2rem;
  line-height: 1.4;
}

.doc-card-footer {
  padding: 0.65rem 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.view-sample-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  background: rgba(59, 130, 246, 0.1);
  color: #60a5fa;
  font-size: 0.75rem;
  font-weight: 700;
  text-decoration: none;
  transition: background 0.2s;
}

.view-sample-btn:hover {
  background: rgba(59, 130, 246, 0.2);
}

.btn-icon {
  font-size: 0.75rem;
}

.doc-field {
  font-size: 0.65rem;
  color: #64748b;
  background: rgba(255, 255, 255, 0.04);
  padding: 0.2rem 0.45rem;
  border-radius: 4px;
  white-space: nowrap;
}
</style>
