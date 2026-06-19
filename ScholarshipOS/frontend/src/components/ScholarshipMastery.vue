<template>
  <div class="mastery-container">
    <div class="mastery-header">
      <div class="header-left">
        <h2 class="mastery-title">Scholarship Mastery</h2>
        <p class="mastery-desc">Deep-dive guidance for your 8 target scholarships</p>
      </div>
      <div class="header-right">
        <div class="overall-progress" v-if="overallProgress > 0">
          <div class="progress-ring">
            <svg width="48" height="48" viewBox="0 0 48 48">
              <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="4"/>
              <circle cx="24" cy="24" r="20" fill="none" stroke="#3b82f6" stroke-width="4"
                :stroke-dasharray="circumference" :stroke-dashoffset="progressOffset"
                stroke-linecap="round" transform="rotate(-90 24 24)"/>
            </svg>
            <span class="progress-text">{{ Math.round(overallProgress) }}%</span>
          </div>
          <span class="progress-label">Overall</span>
        </div>
        <button class="rescan-btn" @click="triggerScan" :disabled="scanStatus.running">
          <span class="scan-icon-spin" :class="{ spinning: scanStatus.running }">⟳</span>
          {{ scanStatus.running ? 'Scanning...' : 'Refresh Data' }}
        </button>
      </div>
    </div>

    <!-- Search & Filter Bar -->
    <div class="filter-bar mastery-filter-bar" v-if="!loading">
      <div class="filter-search-container">
        <span class="search-icon-inside">🔍</span>
        <input type="text" v-model="filters.search" placeholder="Search scholarships, providers, countries..." class="search-input" />
      </div>
      <select v-model="filters.country" class="filter-select">
        <option value="">All Countries</option>
        <option v-for="c in uniqueCountries" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="filters.coverage" class="filter-select">
        <option value="">Any Coverage</option>
        <option value="Full-Ride">Full-Ride</option>
        <option value="Tuition Waiver">Tuition Waiver</option>
      </select>
      <label class="toggle-container">
        <input type="checkbox" v-model="filters.onlyFollowed" />
        <span class="toggle-slider"></span>
        <span class="toggle-label">Tracked Only</span>
      </label>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>Loading scholarship data...</p>
    </div>

    <div v-else-if="filteredScholarships.length === 0" class="empty-results">
      No scholarships match your filter criteria.
    </div>

    <div v-else class="mastery-grid">
      <div v-for="s in filteredScholarships" :key="s.slug" class="mastery-card"
        :class="{ 'expanded': expandedSlug === s.slug, 'is-followed': followedNames.has(s.name) }"
        @click="openDetail(s.slug)">
        <div class="card-actions-top">
          <button class="card-follow-btn" :class="{ followed: followedNames.has(s.name) }"
            @click.stop="toggleFollow(s.name)" :title="followedNames.has(s.name) ? 'Unfollow' : 'Follow'">
            {{ followedNames.has(s.name) ? '♥' : '♡' }}
          </button>
        </div>
        <div class="card-top-bar">
          <div class="card-country">{{ s.country }}</div>
          <div class="card-match" :class="matchClass(s.match_score)">{{ s.match_score }}% Match</div>
        </div>
        <h3 class="card-name">{{ s.name }}</h3>
        <p class="card-provider">{{ s.provider }}</p>
        <div class="card-summary-row">
          <span class="summary-chip coverage">{{ s.coverage_type }}</span>
          <span class="summary-chip amount">{{ s.currency }} {{ s.amount || 'Full' }}</span>
          <span class="summary-chip deadline">{{ s.deadline_end || 'Varies' }}</span>
        </div>
        <div class="card-deadline-countdown" v-if="deadlineCountdown(s)">
          <span class="countdown-badge" :class="deadlineUrgencyClass(s)">{{ deadlineCountdown(s) }}</span>
        </div>
        <div class="card-progress-bar">
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: stepProgressPercent(s) + '%' }"></div>
          </div>
          <span class="progress-num">{{ s.completed_steps }}/{{ s.total_steps }} steps</span>
        </div>
      </div>
    </div>

    <!-- Expanded Detail Panel -->
    <div v-if="detailLoading" class="loading-state">
      <div class="loader"></div>
      <p>Loading scholarship details...</p>
    </div>
    <transition name="panel-slide">
      <div v-if="activeScholarship && !detailLoading" class="detail-panel">
        <div class="panel-header">
          <button class="back-btn" @click="closeDetail">← Back</button>
          <div>
            <h3>{{ activeScholarship.name }}</h3>
            <p class="panel-subtitle">{{ activeScholarship.country }} · {{ activeScholarship.provider }}</p>
          </div>
          <div class="panel-match" :class="matchClass(activeScholarship.match_score)">
            {{ activeScholarship.match_score }}%
          </div>
        </div>

        <div class="sub-tabs">
          <button v-for="tab in subTabs" :key="tab.id"
            class="sub-tab"
            :class="{ active: activeSubTab === tab.id }"
            @click.stop="activeSubTab = tab.id">
            {{ tab.icon }} {{ tab.name }}
          </button>
        </div>

        <!-- OVERVIEW TAB -->
        <div v-if="activeSubTab === 'overview'" class="tab-content">
          <div class="detail-grid">
            <div class="detail-block full-width" v-if="activeScholarship.coverage_details">
              <h4>Coverage</h4>
              <p class="highlight-box">{{ activeScholarship.coverage_details }}</p>
            </div>
            <div class="detail-block">
              <h4>Eligibility</h4>
              <p><strong>Nationality:</strong> {{ activeScholarship.eligibility_nationality }}</p>
              <p><strong>Academics:</strong> {{ activeScholarship.eligibility_academics }}</p>
              <p><strong>Experience:</strong> {{ activeScholarship.eligibility_experience || 'Not required' }}</p>
            </div>
            <div class="detail-block">
              <h4>Requirements</h4>
              <p><strong>English:</strong> {{ activeScholarship.english_test_required || 'Varies' }}</p>
              <p><strong>GRE/GMAT:</strong> {{ activeScholarship.gre_required || 'Not required' }}</p>
              <p><strong>Application Fee:</strong> {{ activeScholarship.application_fee || 'None' }}</p>
              <p><strong>Interview:</strong> {{ activeScholarship.interview_required || 'Varies' }}</p>
              <p><strong>Language:</strong> {{ activeScholarship.application_language || 'English' }}</p>
            </div>
            <div class="detail-block" v-if="parsedDocuments.length > 0">
              <h4>Required Documents</h4>
              <ul class="docs-list">
                <li v-for="(doc, idx) in parsedDocuments" :key="idx">{{ doc }}</li>
              </ul>
            </div>
            <div class="detail-block">
              <h4>Timeline</h4>
              <p><strong>Deadline:</strong> {{ activeScholarship.deadline_start }} - {{ activeScholarship.deadline_end }}</p>
              <p><strong>Duration:</strong> {{ activeScholarship.duration }}</p>
              <p><strong>Notification:</strong> {{ activeScholarship.notification_date }}</p>
              <p><strong>Competition:</strong> {{ activeScholarship.competitiveness }}</p>
            </div>
            <div class="detail-block full-width" v-if="activeScholarship.strategy_notes">
              <h4>Strategy</h4>
              <p class="strategy-box">{{ activeScholarship.strategy_notes }}</p>
            </div>
            <div class="detail-block full-width">
              <h4>Links</h4>
              <div class="links-row">
                <a :href="activeScholarship.application_portal" target="_blank" class="action-link">Application Portal ↗</a>
                <a :href="activeScholarship.official_url" target="_blank" class="action-link">Official Website ↗</a>
              </div>
            </div>
          </div>
        </div>

        <!-- STEPS TAB -->
        <div v-if="activeSubTab === 'steps'" class="tab-content">
          <div class="steps-progress-header">
            <div class="steps-stat">
              <span class="steps-stat-num">{{ activeScholarship.completed_steps }}/{{ activeScholarship.total_steps }}</span>
              <span class="steps-stat-label">steps done</span>
            </div>
            <div class="steps-bar">
              <div class="steps-bar-fill" :style="{ width: stepProgressPercent(activeScholarship) + '%' }"></div>
            </div>
          </div>
          <div class="roadmap">
            <div v-for="(phase, pIdx) in phases" :key="phase" class="phase-section">
              <div class="phase-banner" :class="'phase-' + phase.toLowerCase()">
                <span class="phase-icon">{{ phaseIcons[phase] }}</span>
                <span class="phase-label">{{ phase }}</span>
                <span class="phase-step-count">{{ filteredSteps(phase).length }} step{{ filteredSteps(phase).length !== 1 ? 's' : '' }}</span>
              </div>
              <div class="phase-steps">
                <div v-for="(item, sIdx) in filteredSteps(phase)" :key="item.id" class="step-card" :class="{ done: item.completed }">
                  <div class="step-connector">
                    <div class="step-dot" :class="{ checked: item.completed }">
                      <span v-if="!item.completed" class="step-num">{{ sIdx + 1 }}</span>
                      <span v-else class="step-check-icon">✓</span>
                    </div>
                    <div v-if="sIdx < filteredSteps(phase).length - 1" class="step-line"></div>
                  </div>
                  <div class="step-card-body" @click="toggleStep(item)">
                    <div class="step-card-header">
                      <strong class="step-title">{{ item.title }}</strong>
                      <div class="step-badges">
                        <span v-if="item.is_critical" class="badge-critical">Critical</span>
                        <span v-if="item.timeline" class="badge-timeline">{{ item.timeline }}</span>
                      </div>
                    </div>
                    <p class="step-desc">{{ item.description }}</p>
                    <div v-if="item.tips" class="step-tips-toggle" @click.stop="toggleTips($event, item)">
                      <span class="tips-trigger" :class="{ expanded: expandedTips[item.id] }">
                        💡 Tips
                        <svg class="chevron" :class="{ open: expandedTips[item.id] }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                      </span>
                      <p v-show="expandedTips[item.id]" class="step-tips-text">{{ item.tips }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- APPLICANTS TAB -->
        <div v-if="activeSubTab === 'applicants'" class="tab-content">
          <div class="applicant-filter-bar" v-if="activeScholarship.applicants && activeScholarship.applicants.length > 0">
            <label class="toggle-container">
              <input type="checkbox" v-model="applicantFilterReal" />
              <span class="toggle-slider"></span>
              <span class="toggle-label">Real Profiles Only</span>
            </label>
            <span class="applicant-count">{{ filteredApplicants.length }} profile{{ filteredApplicants.length !== 1 ? 's' : '' }}</span>
          </div>
          <p v-if="!activeScholarship.applicants || activeScholarship.applicants.length === 0" class="empty-message">
            No applicant profiles loaded yet. Click "Refresh Data" to scrape stories.
          </p>
          <div v-for="a in filteredApplicants" :key="a.id" class="applicant-card">
              <div class="applicant-header">
                <div class="applicant-avatar">{{ a.name ? a.name[0] : '?' }}</div>
                <div>
                  <h4>{{ a.name || 'Anonymous Applicant' }}</h4>
                  <p class="applicant-meta">{{ a.field_of_study || '' }} · {{ a.country || '' }}</p>
                  <span class="source-badge" :class="a.source_type || 'seed'">
                    {{ (a.source_type || 'seed') === 'real' ? '🌐 Real Profile' : '📝 Example Profile' }}
                  </span>
                </div>
              </div>
            <div class="applicant-details">
              <div v-if="a.background" class="app-detail"><strong>Background:</strong> {{ a.background }}</div>
              <div v-if="a.test_scores" class="app-detail"><strong>Test Scores:</strong> {{ a.test_scores }}</div>
              <div v-if="a.work_experience" class="app-detail"><strong>Experience:</strong> {{ a.work_experience }}</div>
              <div v-if="a.publications" class="app-detail"><strong>Publications:</strong> {{ a.publications }}</div>
              <div v-if="a.application_strategy" class="app-detail strategy"><strong>Strategy:</strong> {{ a.application_strategy }}</div>
              <div v-if="a.what_worked" class="app-detail highlight"><strong>What Worked:</strong> {{ a.what_worked }}</div>
              <div v-if="a.advice" class="app-detail advice"><strong>Advice:</strong> {{ a.advice }}</div>
              <a v-if="a.source_url" :href="a.source_url" target="_blank" class="source-link">
                🌐 Original Profile ↗
              </a>
            </div>
          </div>
        </div>

        <!-- TIPS TAB -->
        <div v-if="activeSubTab === 'tips'" class="tab-content">
          <p v-if="!activeScholarship.tips || activeScholarship.tips.length === 0" class="empty-message">
            No tips loaded yet. Click "Refresh Data" to scrape tips.
          </p>
          <div v-for="cat in tipCategories" :key="cat" class="tip-group">
            <h4 class="tip-category">{{ cat }}</h4>
            <div v-for="tip in filteredTips(cat)" :key="tip.id" class="tip-item" :class="tip.priority">
              <span class="tip-priority-badge" :class="tip.priority">{{ tip.priority }}</span>
              <p class="tip-text">{{ tip.tip }}</p>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  name: 'ScholarshipMastery',
  data() {
    return {
      scholarships: [],
      selectedScholarship: null,
      loading: true,
      detailLoading: false,
      expandedSlug: null,
      activeSubTab: 'overview',
      scanStatus: { running: false, progress: '', done: false },
      pollInterval: null,
      followedNames: new Set(),
      filters: {
        search: '',
        country: '',
        coverage: '',
        onlyFollowed: false,
      },
      applicantFilterReal: false,
      subTabs: [
        { id: 'overview', name: 'Overview', icon: '📋' },
        { id: 'steps', name: 'Steps', icon: '✅' },
        { id: 'applicants', name: 'Applicants', icon: '👤' },
        { id: 'tips', name: 'Tips', icon: '💡' },
      ],
      phases: ['Preparation', 'Application', 'Post-Application'],
      phaseIcons: {
        Preparation: '📋',
        Application: '📤',
        'Post-Application': '🎯',
      },
      expandedTips: {},
    }
  },
  computed: {
    activeScholarship() {
      return this.selectedScholarship
    },
    overallProgress() {
      let total = 0, completed = 0
      for (const s of this.scholarships) {
        total += s.total_steps || 0
        completed += s.completed_steps || 0
      }
      return total > 0 ? (completed / total) * 100 : 0
    },
    circumference() {
      return 2 * Math.PI * 20
    },
    progressOffset() {
      return this.circumference - (this.overallProgress / 100) * this.circumference
    },
    tipCategories() {
      if (!this.activeScholarship || !this.activeScholarship.tips) return []
      return [...new Set(this.activeScholarship.tips.map(t => t.category))]
    },
    filteredScholarships() {
      let list = [...this.scholarships]
      const q = this.filters.search.toLowerCase()
      if (q) {
        list = list.filter(s =>
          s.name.toLowerCase().includes(q) ||
          (s.provider || '').toLowerCase().includes(q) ||
          (s.country || '').toLowerCase().includes(q)
        )
      }
      if (this.filters.country) {
        list = list.filter(s => s.country === this.filters.country)
      }
      if (this.filters.coverage) {
        list = list.filter(s => (s.coverage_type || '').toLowerCase().includes(this.filters.coverage.toLowerCase()))
      }
      if (this.filters.onlyFollowed) {
        list = list.filter(s => this.followedNames.has(s.name))
      }
      return list
    },
    uniqueCountries() {
      return [...new Set(this.scholarships.map(s => s.country).filter(Boolean))].sort()
    },
    parsedDocuments() {
      if (!this.activeScholarship || !this.activeScholarship.required_documents) return []
      try {
        const parsed = JSON.parse(this.activeScholarship.required_documents)
        return Array.isArray(parsed) ? parsed : []
      } catch (e) {
        return this.activeScholarship.required_documents.split(',').map(d => d.trim().replace(/^["\[]|["\]]$/g, ''))
      }
    },
    filteredApplicants() {
      if (!this.activeScholarship || !this.activeScholarship.applicants) return []
      let list = this.activeScholarship.applicants
      if (this.applicantFilterReal) {
        list = list.filter(a => a.source_type === 'real')
      }
      return list
    },
  },
  mounted() {
    this.fetchData()
    this.fetchFollowed()
    this.checkScanStatus()
  },
  methods: {
    fetchData() {
      this.loading = true
      fetch('/api/mastery')
        .then(res => res.json())
        .then(data => {
          this.scholarships = data
          this.loading = false
          if (this.expandedSlug) {
            this.refreshDetail()
          }
        })
        .catch(err => {
          console.error('Failed to fetch mastery data:', err)
          this.loading = false
        })
    },
    matchClass(match) {
      if (match >= 90) return 'match-high'
      if (match >= 70) return 'match-medium'
      return 'match-low'
    },
    stepProgressPercent(s) {
      if (!s.total_steps || s.total_steps === 0) return 0
      return (s.completed_steps || 0) / s.total_steps * 100
    },
    filteredSteps(phase) {
      if (!this.activeScholarship || !this.activeScholarship.steps) return []
      return this.activeScholarship.steps.filter(s => s.phase === phase)
    },
    filteredTips(category) {
      if (!this.activeScholarship || !this.activeScholarship.tips) return []
      return this.activeScholarship.tips.filter(t => t.category === category)
    },
    openDetail(slug) {
      if (this.expandedSlug === slug) {
        this.closeDetail()
        return
      }
      this.expandedSlug = slug
      this.detailLoading = true
      this.activeSubTab = 'overview'
      fetch(`/api/mastery/${slug}`)
        .then(res => res.json())
        .then(data => {
          this.selectedScholarship = data
          this.detailLoading = false
        })
        .catch(err => {
          console.error('Failed to fetch detail:', err)
          this.detailLoading = false
        })
    },
    closeDetail() {
      this.expandedSlug = null
      this.selectedScholarship = null
    },
    toggleStep(item) {
      fetch(`/api/mastery/${this.expandedSlug}/checklist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step_id: item.id, completed: !item.completed }),
      })
        .then(res => res.json())
        .then(() => {
          item.completed = !item.completed
          this.refreshDetail()
          this.fetchData()
        })
        .catch(err => console.error('Failed to update checklist:', err))
    },
    toggleTips(event, item) {
      this.expandedTips = { ...this.expandedTips, [item.id]: !this.expandedTips[item.id] }
    },
    refreshDetail() {
      if (!this.expandedSlug) return
      fetch(`/api/mastery/${this.expandedSlug}`)
        .then(res => res.json())
        .then(data => {
          this.selectedScholarship = data
        })
        .catch(err => console.error('Failed to refresh detail:', err))
    },
    deadlineCountdown(s) {
      const raw = s.deadline_end
      if (!raw || raw === 'Varies') return ''
      const monthMap = {
        january: 0, february: 1, march: 2, april: 3, may: 4, june: 5,
        july: 6, august: 7, september: 8, october: 9, november: 10, december: 11
      }
      const lower = raw.toLowerCase().trim()
      let targetDate = null
      if (monthMap[lower] !== undefined) {
        const year = new Date().getFullYear()
        targetDate = new Date(year, monthMap[lower], 15)
        if (targetDate < new Date()) targetDate.setFullYear(year + 1)
      } else {
        const parsed = new Date(raw)
        if (!isNaN(parsed)) targetDate = parsed
      }
      if (!targetDate) return ''
      const diff = Math.ceil((targetDate - new Date()) / (1000 * 60 * 60 * 24))
      if (diff < 0) return `${Math.abs(diff)} days ago`
      if (diff === 0) return 'Due today!'
      return `${diff} days left`
    },
    deadlineUrgencyClass(s) {
      const raw = s.deadline_end
      if (!raw || raw === 'Varies') return ''
      const text = this.deadlineCountdown(s)
      if (!text) return ''
      if (text.includes('ago')) return 'urgency-past'
      if (text.includes('today')) return 'urgency-today'
      const days = parseInt(text)
      if (isNaN(days)) return ''
      if (days <= 7) return 'urgency-critical'
      if (days <= 30) return 'urgency-urgent'
      if (days <= 90) return 'urgency-soon'
      return 'urgency-far'
    },
    toggleFollow(name) {
      const isAdding = !this.followedNames.has(name)
      fetch('/api/followed')
        .then(r => r.json())
        .then(data => {
          let scholarships = data.scholarships || []
          if (isAdding) {
            scholarships.push(name)
          } else {
            scholarships = scholarships.filter(s => s !== name)
          }
          return fetch('/api/followed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scholarships })
          })
        })
        .then(r => r.json())
        .then(() => {
          this.fetchFollowed()
        })
        .catch(err => console.error('Toggle follow error:', err))
    },
    fetchFollowed() {
      fetch('/api/followed')
        .then(r => r.json())
        .then(data => {
          this.followedNames = new Set(data.scholarships || [])
        })
        .catch(err => console.error('Fetch followed error:', err))
    },
    checkScanStatus() {
      fetch('/api/mastery/scan-status')
        .then(res => res.json())
        .then(status => {
          this.scanStatus = status
          if (status.running) this.startPolling()
        })
        .catch(err => console.error(err))
    },
    triggerScan() {
      this.scanStatus.running = true
      this.scanStatus.progress = 'Searching for new applicant profiles...'
      fetch('/api/mastery/refresh', { method: 'POST' })
        .then(() => this.startPolling())
        .catch(err => {
          this.scanStatus.running = false
          console.error(err)
        })
    },
    startPolling() {
      if (this.pollInterval) clearInterval(this.pollInterval)
      this.pollInterval = setInterval(() => {
        fetch('/api/mastery/scan-status')
          .then(res => res.json())
          .then(status => {
            this.scanStatus = status
            if (status.done || !status.running) {
              clearInterval(this.pollInterval)
              this.pollInterval = null
              this.fetchData()
            }
          })
          .catch(err => {
            clearInterval(this.pollInterval)
            this.pollInterval = null
          })
      }, 1500)
    },
  },
}
</script>

<style scoped>
.mastery-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.mastery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.mastery-title {
  font-family: 'Outfit', sans-serif;
  font-weight: 800;
  font-size: 1.45rem;
  color: white;
}

.mastery-desc {
  font-size: 0.8rem;
  color: #9ca3af;
  margin-top: 0.1rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.overall-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-ring {
  position: relative;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress-text {
  position: absolute;
  font-size: 0.7rem;
  font-weight: 700;
  color: #cbd5e1;
}

.progress-label {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 600;
}

.rescan-btn {
  padding: 0.5rem 1.2rem;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.25);
  color: #60a5fa;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.rescan-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.2);
}

.rescan-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.scan-icon-spin {
  display: inline-block;
}

.scan-icon-spin.spinning {
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4rem;
  color: #9ca3af;
  gap: 1rem;
}

.loader {
  border: 3px solid rgba(255,255,255,0.04);
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  animation: spin 1s linear infinite;
}

.mastery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1rem;
}

.mastery-card {
  background: rgba(30, 41, 59, 0.45);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 1.2rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.mastery-card:hover {
  background: rgba(30, 41, 59, 0.65);
  border-color: rgba(99, 102, 241, 0.35);
  transform: translateY(-2px);
}

.mastery-card.expanded {
  border-color: rgba(99, 102, 241, 0.5);
  background: rgba(30, 41, 59, 0.8);
}

.card-top-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.card-country {
  font-size: 0.7rem;
  text-transform: uppercase;
  font-weight: 700;
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.12);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  letter-spacing: 0.5px;
}

.card-match {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.match-high { color: #34d399; background: rgba(16, 185, 129, 0.15); }
.match-medium { color: #fbbf24; background: rgba(245, 158, 11, 0.15); }
.match-low { color: #a5b4fc; background: rgba(99, 102, 241, 0.15); }

.card-name {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: white;
  margin-bottom: 0.2rem;
  line-height: 1.3;
}

.card-provider {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-bottom: 0.8rem;
}

.card-summary-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.8rem;
}

.summary-chip {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.summary-chip.coverage { background: rgba(99, 102, 241, 0.12); color: #a5b4fc; }
.summary-chip.amount { background: rgba(56, 189, 248, 0.12); color: #38bdf8; }
.summary-chip.deadline { background: rgba(248, 113, 113, 0.12); color: #f87171; }

.card-progress-bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.progress-track {
  flex: 1;
  height: 4px;
  background: rgba(255,255,255,0.05);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #6366f1);
  border-radius: 2px;
  transition: width 0.4s ease;
}

.progress-num {
  font-size: 0.7rem;
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

/* Detail Panel */
.detail-panel {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.back-btn {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  color: #94a3b8;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
}

.back-btn:hover {
  color: white;
  background: rgba(255,255,255,0.08);
}

.panel-header h3 {
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  color: white;
  font-size: 1.15rem;
}

.panel-subtitle {
  font-size: 0.8rem;
  color: #64748b;
}

.panel-match {
  margin-left: auto;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.9rem;
}

.sub-tabs {
  display: flex;
  gap: 0.25rem;
  padding: 0.75rem 1.5rem;
  background: rgba(0,0,0,0.15);
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.sub-tab {
  padding: 0.5rem 1rem;
  background: none;
  border: none;
  color: #64748b;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.sub-tab:hover { color: #cbd5e1; background: rgba(255,255,255,0.03); }
.sub-tab.active { background: rgba(59, 130, 246, 0.12); color: #60a5fa; }

.tab-content {
  padding: 1.5rem;
  max-height: 60vh;
  overflow-y: auto;
}

/* Overview Tab */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.2rem;
}

.full-width { grid-column: span 2; }

.detail-block h4 {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #818cf8;
  font-weight: 700;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}

.detail-block p {
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.5;
  margin-bottom: 0.25rem;
}

.detail-block p strong { color: #cbd5e1; }

.highlight-box {
  background: rgba(99, 102, 241, 0.05);
  border-left: 3px solid #6366f1;
  padding: 0.6rem 0.8rem;
  border-radius: 0 6px 6px 0;
  color: #e2e8f0 !important;
}

.strategy-box {
  background: rgba(167, 139, 250, 0.08) !important;
  border-left: 3px solid #a78bfa !important;
  padding: 0.6rem 0.8rem !important;
  border-radius: 0 6px 6px 0 !important;
  color: #d8b4fe !important;
  font-style: italic;
}

.links-row {
  display: flex;
  gap: 0.6rem;
}

.action-link {
  padding: 0.4rem 1rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 600;
  transition: all 0.2s;
}

.action-link:hover {
  background: #3b82f6;
  color: white;
}

/* Steps Tab - Roadmap */
.steps-progress-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  padding: 0.8rem 1rem;
}

.steps-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 60px;
}

.steps-stat-num {
  font-size: 1.1rem;
  font-weight: 800;
  color: #34d399;
  line-height: 1.2;
}

.steps-stat-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  color: #6b7280;
  letter-spacing: 0.5px;
}

.steps-bar {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.05);
  border-radius: 3px;
  overflow: hidden;
}

.steps-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 3px;
  transition: width 0.4s ease;
}

.roadmap { padding-left: 0; }

.phase-section {
  margin-bottom: 1.5rem;
  position: relative;
}

.phase-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.8rem;
  border-radius: 8px;
  margin-bottom: 0.8rem;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.phase-banner.phase-preparation {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.05));
  color: #818cf8;
}

.phase-banner.phase-application {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05));
  color: #fbbf24;
}

.phase-banner.phase-post-application {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05));
  color: #34d399;
}

.phase-icon { font-size: 1rem; }

.phase-label { font-size: 0.75rem; }

.phase-step-count {
  margin-left: auto;
  font-size: 0.65rem;
  font-weight: 600;
  opacity: 0.6;
}

.phase-steps {
  padding-left: 1.2rem;
}

.step-card {
  display: flex;
  gap: 0.8rem;
  position: relative;
  cursor: pointer;
}

.step-card.done .step-title {
  text-decoration: line-through;
  color: #6b7280;
}

.step-card.done .step-card-body {
  opacity: 0.65;
}

.step-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 28px;
  flex-shrink: 0;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  background: rgba(99, 102, 241, 0.15);
  border: 2px solid rgba(99, 102, 241, 0.3);
  color: #818cf8;
  transition: all 0.2s;
  flex-shrink: 0;
  z-index: 1;
}

.step-dot.checked {
  background: #10b981;
  border-color: #10b981;
  color: white;
}

.step-check-icon { font-size: 0.7rem; }

.step-line {
  width: 2px;
  flex: 1;
  min-height: 20px;
  background: rgba(255,255,255,0.06);
  margin: 2px 0;
}

.step-card-body {
  flex: 1;
  background: rgba(15, 23, 42, 0.25);
  border: 1px solid rgba(255,255,255,0.03);
  border-radius: 8px;
  padding: 0.7rem 0.8rem;
  margin-bottom: 0.5rem;
  transition: all 0.2s;
}

.step-card-body:hover {
  border-color: rgba(99, 102, 241, 0.15);
  background: rgba(15, 23, 42, 0.35);
}

.step-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}

.step-title { font-size: 0.85rem; color: #e2e8f0; line-height: 1.3; }

.step-badges {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.badge-critical {
  font-size: 0.6rem;
  font-weight: 700;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  white-space: nowrap;
}

.badge-timeline {
  font-size: 0.6rem;
  font-weight: 600;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  white-space: nowrap;
}

.step-desc {
  font-size: 0.78rem;
  color: #94a3b8;
  line-height: 1.5;
  margin: 0;
}

.step-tips-toggle { margin-top: 0.3rem; }

.tips-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.7rem;
  font-weight: 600;
  color: #a78bfa;
  cursor: pointer;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  background: rgba(167, 139, 250, 0.06);
  transition: all 0.15s;
  user-select: none;
}

.tips-trigger:hover {
  background: rgba(167, 139, 250, 0.12);
}

.chevron {
  transition: transform 0.2s;
}

.chevron.open {
  transform: rotate(180deg);
}

.step-tips-text {
  font-size: 0.75rem;
  color: #c4b5fd;
  line-height: 1.5;
  margin: 0.4rem 0 0 0;
  padding: 0.4rem;
  background: rgba(167, 139, 250, 0.05);
  border-radius: 6px;
  border-left: 2px solid rgba(167, 139, 250, 0.2);
}

/* Applicants Tab */
.applicant-card {
  background: rgba(15, 23, 42, 0.3);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.applicant-header {
  display: flex;
  gap: 0.8rem;
  align-items: center;
  margin-bottom: 1rem;
}

.applicant-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: white;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.applicant-header h4 { font-size: 0.95rem; color: white; }
.applicant-meta { font-size: 0.75rem; color: #64748b; }

.applicant-details { display: flex; flex-direction: column; gap: 0.4rem; }

.app-detail {
  font-size: 0.8rem;
  color: #94a3b8;
  line-height: 1.4;
}

.app-detail.highlight {
  background: rgba(16, 185, 129, 0.05);
  border-left: 3px solid #10b981;
  padding: 0.4rem 0.6rem;
  border-radius: 0 4px 4px 0;
}

.app-detail.advice {
  background: rgba(167, 139, 250, 0.05);
  border-left: 3px solid #a78bfa;
  padding: 0.4rem 0.6rem;
  border-radius: 0 4px 4px 0;
  font-style: italic;
}

.source-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
  display: inline-block;
  margin-top: 0.15rem;
}

.source-badge.real {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.15);
}

.source-badge.seed {
  background: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.source-link {
  font-size: 0.75rem;
  color: #60a5fa;
  text-decoration: none;
  margin-top: 0.4rem;
  display: inline-block;
}

/* Tips Tab */
.tip-group { margin-bottom: 1.2rem; }

.tip-category {
  font-size: 0.8rem;
  text-transform: uppercase;
  color: #818cf8;
  font-weight: 700;
  letter-spacing: 0.5px;
  margin-bottom: 0.6rem;
}

.tip-item {
  display: flex;
  gap: 0.6rem;
  align-items: flex-start;
  padding: 0.6rem 0.8rem;
  background: rgba(15, 23, 42, 0.3);
  border: 1px solid rgba(255,255,255,0.03);
  border-radius: 8px;
  margin-bottom: 0.4rem;
}

.tip-priority-badge {
  font-size: 0.6rem;
  font-weight: 800;
  text-transform: uppercase;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.tip-priority-badge.high { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.tip-priority-badge.medium { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
.tip-priority-badge.low { background: rgba(99, 102, 241, 0.12); color: #a5b4fc; }

.tip-text {
  font-size: 0.85rem;
  color: #cbd5e1;
  line-height: 1.4;
}

.applicant-filter-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.applicant-count {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 600;
}

.empty-message {
  color: #64748b;
  text-align: center;
  padding: 2rem;
  font-size: 0.9rem;
}

/* Filter Bar */
.mastery-filter-bar {
  margin-bottom: 1rem;
}

/* Card follow button */
.card-actions-top {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 2;
}

.mastery-card {
  position: relative;
}

.card-follow-btn {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  color: #64748b;
}

.card-follow-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.25);
  color: #ef4444;
}

.card-follow-btn.followed {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.2);
}

.mastery-card.is-followed {
  border-color: rgba(239, 68, 68, 0.15);
}

/* Deadline countdown on card */
.card-deadline-countdown {
  margin-bottom: 0.6rem;
}

.countdown-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.5rem;
  border-radius: 4px;
  display: inline-block;
}

.countdown-badge.urgency-past { background: rgba(239, 68, 68, 0.12); color: #f87171; }
.countdown-badge.urgency-today { background: rgba(255, 69, 0, 0.15); color: #ff6347; animation: pulse 1.5s infinite; }
.countdown-badge.urgency-critical { background: rgba(248, 113, 113, 0.12); color: #f87171; }
.countdown-badge.urgency-urgent { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
.countdown-badge.urgency-soon { background: rgba(59, 130, 246, 0.12); color: #60a5fa; }
.countdown-badge.urgency-far { background: rgba(16, 185, 129, 0.12); color: #34d399; }

/* Required Documents List */
.docs-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.docs-list li {
  font-size: 0.85rem;
  color: #94a3b8;
  padding: 0.25rem 0;
  padding-left: 1rem;
  position: relative;
  line-height: 1.4;
}

.docs-list li::before {
  content: "•";
  position: absolute;
  left: 0;
  color: #6366f1;
  font-weight: 700;
}

/* Strategy detail in applicant */
.app-detail.strategy {
  background: rgba(59, 130, 246, 0.05);
  border-left: 3px solid #3b82f6;
  padding: 0.4rem 0.6rem;
  border-radius: 0 4px 4px 0;
}

/* Empty results */
.empty-results {
  text-align: center;
  padding: 4rem;
  color: #9ca3af;
  border: 1px dashed rgba(255,255,255,0.08);
  border-radius: 12px;
}

/* Toggle from deadlines tab */
.toggle-container {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  cursor: pointer;
  user-select: none;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
}

.toggle-container input { display: none; }

.toggle-slider {
  position: relative;
  width: 36px;
  height: 20px;
  background-color: rgba(255, 255, 255, 0.1);
  transition: .3s;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .3s;
  border-radius: 50%;
}

.toggle-container input:checked + .toggle-slider {
  background-color: #3b82f6;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.35);
}

.toggle-container input:checked + .toggle-slider:before {
  transform: translateX(16px);
}

.toggle-label {
  font-size: 0.85rem;
  color: #cbd5e1;
  font-weight: 600;
}

.filter-search-container {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}

.search-icon-inside {
  position: absolute;
  left: 1rem;
  color: #9ca3af;
  font-size: 0.9rem;
}

.filter-search-container .search-input {
  padding-left: 2.5rem;
  width: 100%;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.6; }
}

@media (max-width: 768px) {
  .detail-grid { grid-template-columns: 1fr; }
  .full-width { grid-column: span 1; }
  .mastery-grid { grid-template-columns: 1fr; }
  .mastery-header { flex-direction: column; align-items: flex-start; }
  .mastery-filter-bar { flex-direction: column; }
}
</style>
