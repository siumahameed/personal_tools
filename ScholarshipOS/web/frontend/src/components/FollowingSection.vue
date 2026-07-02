<template>
  <div class="following-section">
    <div class="section-header">
      <h2 class="section-title">♥ Your Saved Targets</h2>
      <p class="section-subtitle">
        Track your high-priority scholarships, target universities, and research advisors. Tracked items get priority live updates on the next scan run.
      </p>
    </div>

    <!-- Quick Add Target Widget -->
    <div class="quick-add-widget">
      <h3 class="quick-add-title">➕ Quick Add Target</h3>
      <div class="quick-add-controls">
        <div class="control-group">
          <label>Category</label>
          <select v-model="quickAdd.category" @change="onCategoryChange">
            <option value="scholarships">Scholarship</option>
            <option value="universities">University</option>
            <option value="professors">Professor</option>
          </select>
        </div>
        
        <div class="control-group flex-1">
          <label>Select Item to Track</label>
          <select v-model="quickAdd.selectedName">
            <option value="" disabled>-- Select an item --</option>
            <option 
              v-for="item in availableItems" 
              :key="item.name" 
              :value="item.name"
            >
              {{ item.name }} {{ item.country ? '(' + item.country + ')' : '' }}
            </option>
          </select>
        </div>

        <button 
          class="add-btn" 
          :disabled="!quickAdd.selectedName" 
          @click="addQuickTarget"
        >
          + Track Target
        </button>
      </div>
    </div>

    <!-- Enrich Saved Targets Button -->
    <div class="enrich-section">
      <div class="enrich-controls">
        <button
          class="enrich-btn"
          :disabled="enrichRunning"
          @click="startEnrich"
        >
          {{ enrichRunning ? '⟳ Enriching...' : '🔍 Enrich Saved Targets' }}
        </button>
        <button
          v-if="enrichStuck"
          class="reset-btn"
          @click="resetEnrich"
          title="Reset stuck enrichment status"
        >
          ↺ Reset
        </button>
        <span v-if="enrichProgress" class="enrich-progress" :class="{ 'error': enrichStuck }">{{ enrichProgress }}</span>
      </div>
    </div>

    <!-- 1. Scholarships Block -->
    <div class="sub-section">
      <h3 class="sub-title">Saved Scholarships ({{ followedScholarships.length }})</h3>
      <div v-if="followedScholarships.length === 0" class="empty-state">
        <span class="empty-icon">🎒</span>
        <p>No scholarships followed yet. Go to the "Scholarships" tab and click the heart icon on any program.</p>
      </div>
      <div v-else class="following-grid">
        <div 
          v-for="s in followedScholarships" 
          :key="s.name" 
          class="following-item-card scholarship-card-small"
        >
          <button class="remove-btn" @click="unfollowScholarship(s.name)">✕</button>
          
          <div class="item-header">
            <span class="badge country">{{ s.country }}</span>
            <div class="badge match" :class="getMatchClass(s.match)">{{ s.match || 50 }}% Match</div>
          </div>
          
          <h4 class="item-name">{{ s.name }}</h4>
          <p class="item-provider">{{ s.provider }}</p>
          
          <div class="item-meta">
            <div class="meta-row">
              <span class="meta-label">Coverage:</span>
              <span class="meta-value">{{ s.coverage_type || 'Full-ride' }}</span>
            </div>
            <div class="meta-row" v-if="s.deadline_end">
              <span class="meta-label">Deadline:</span>
              <span class="meta-value text-red">{{ s.deadline_end }}</span>
            </div>
          </div>

          <div class="enriched-section" v-if="s.selection_criteria || s.competition || s.contact_email">
            <h5 class="enriched-title">📋 Enriched Details</h5>
            <div class="enriched-grid">
              <div class="enriched-item" v-if="s.selection_criteria">
                <span class="e-label">Selection Criteria</span>
                <span class="e-value">{{ s.selection_criteria }}</span>
              </div>
              <div class="enriched-item" v-if="s.competition">
                <span class="e-label">Success Rate</span>
                <span class="e-value text-red">{{ s.competition }}</span>
              </div>
              <div class="enriched-item" v-if="s.number_of_awards">
                <span class="e-label">Awards</span>
                <span class="e-value">{{ s.number_of_awards }} scholarships/year</span>
              </div>
              <div class="enriched-item" v-if="s.age_limit">
                <span class="e-label">Age Limit</span>
                <span class="e-value">{{ s.age_limit }}</span>
              </div>
              <div class="enriched-item" v-if="s.bond_requirement">
                <span class="e-label">Bond</span>
                <span class="e-value text-amber">{{ s.bond_requirement }}</span>
              </div>
              <div class="enriched-item" v-if="s.contact_email">
                <span class="e-label">Contact</span>
                <a :href="'mailto:' + s.contact_email" class="e-link">{{ s.contact_email }}</a>
              </div>
            </div>
          </div>

          <div class="strategy-callout" v-if="s.strategy">
            <p>{{ s.strategy }}</p>
          </div>

          <div class="card-actions">
            <a :href="s.url || s.portal" target="_blank" class="action-btn-sm">Official Link ↗</a>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. Universities Block -->
    <div class="sub-section">
      <h3 class="sub-title">Saved Universities & Programs ({{ followedUniversities.length }})</h3>
      <div v-if="followedUniversities.length === 0" class="empty-state">
        <span class="empty-icon">🏢</span>
        <p>No universities followed yet. Go to the "Universities" tab and click the heart icon on any program.</p>
      </div>
      <div v-else class="following-grid">
        <div 
          v-for="u in followedUniversities" 
          :key="u.name" 
          class="following-item-card university-card-small"
        >
          <button class="remove-btn" @click="unfollowUniversity(u.name)">✕</button>

          <div class="item-header">
            <span class="badge country-green">{{ u.country }}</span>
            <div class="badge qs-rank" v-if="u.qs_rank">QS #{{ u.qs_rank }}</div>
          </div>

          <h4 class="item-name">{{ u.name }}</h4>
          <p class="item-provider">🎓 {{ u.program }}</p>

          <div class="item-meta">
            <div class="meta-row">
              <span class="meta-label">Tuition:</span>
              <span class="meta-value text-green">{{ u.tuition === '0' || u.tuition === 0 ? 'FREE' : u.tuition + ' ' + u.currency }}</span>
            </div>
            <div class="meta-row" v-if="u.deadline_winter">
              <span class="meta-label">Winter Deadline:</span>
              <span class="meta-value text-red">{{ u.deadline_winter }}</span>
            </div>
          </div>

          <div class="enriched-section" v-if="u.acceptance_rate || u.living_cost || u.housing_options">
            <h5 class="enriched-title">📋 Enriched Details</h5>
            <div class="enriched-grid">
              <div class="enriched-item" v-if="u.acceptance_rate">
                <span class="e-label">Acceptance Rate</span>
                <span class="e-value text-red">{{ u.acceptance_rate }}</span>
              </div>
              <div class="enriched-item" v-if="u.ra_ta_positions">
                <span class="e-label">RA/TA</span>
                <span class="e-value text-green">{{ u.ra_ta_positions }}</span>
              </div>
              <div class="enriched-item" v-if="u.living_cost">
                <span class="e-label">Monthly Cost</span>
                <span class="e-value">{{ u.living_cost }}</span>
              </div>
              <div class="enriched-item" v-if="u.housing_options">
                <span class="e-label">Housing</span>
                <span class="e-value">{{ u.housing_options }}</span>
              </div>
              <div class="enriched-item" v-if="u.program_structure">
                <span class="e-label">Structure</span>
                <span class="e-value">{{ u.program_structure }}</span>
              </div>
              <div class="enriched-item" v-if="u.prerequisite_courses">
                <span class="e-label">Prerequisites</span>
                <span class="e-value">{{ u.prerequisite_courses }}</span>
              </div>
              <div class="enriched-item" v-if="u.department_contact">
                <span class="e-label">Dept Contact</span>
                <a :href="'mailto:' + u.department_contact" class="e-link">{{ u.department_contact }}</a>
              </div>
            </div>
          </div>

          <div class="strategy-callout" v-if="u.strategy">
            <p>{{ u.strategy }}</p>
          </div>

          <div class="card-actions">
            <a :href="u.portal" target="_blank" class="action-btn-sm">Apply Portal ↗</a>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. Professors Block -->
    <div class="sub-section">
      <h3 class="sub-title">Target Research Advisors ({{ followedProfessors.length }})</h3>
      <div v-if="followedProfessors.length === 0" class="empty-state">
        <span class="empty-icon">🔬</span>
        <p>No professors followed yet. Go to the "Professors" tab and click the heart icon on any advisor.</p>
      </div>
      <div v-else class="following-grid columns-1">
        <div 
          v-for="p in followedProfessors" 
          :key="p.name" 
          class="following-item-card professor-card-wide"
        >
          <button class="remove-btn" @click="unfollowProfessor(p.name)">✕</button>

          <div class="prof-header-row">
            <div class="prof-main-info">
              <span class="badge uni">{{ p.university }}</span>
              <h4 class="prof-name">{{ p.name }}</h4>
              <p class="prof-title">{{ p.title }}</p>
            </div>
            <div class="prof-side-info">
              <div class="badge h-index">h-index: {{ p.h_index || 'N/A' }}</div>
              <a :href="'mailto:' + p.email" class="email-btn" v-if="p.email && p.email.includes('@')">✉ Email Advisor</a>
            </div>
          </div>

          <!-- Enriched Research Details -->
          <div class="enriched-section" v-if="p.open_positions || p.lab_website || p.research_projects || p.past_phd_students">
            <h5 class="enriched-title">🔬 Research & Openings</h5>
            <div class="enriched-grid">
              <div class="enriched-item enriched-full" v-if="p.open_positions">
                <span class="e-label">Open Positions</span>
                <span class="e-value text-green">{{ p.open_positions }}</span>
              </div>
              <div class="enriched-item enriched-full" v-if="p.lab_website">
                <span class="e-label">Lab Website</span>
                <a :href="p.lab_website" target="_blank" class="e-link">{{ p.lab_website }}</a>
              </div>
              <div class="enriched-item enriched-full" v-if="p.research_projects">
                <span class="e-label">Research Projects</span>
                <span class="e-value">{{ p.research_projects }}</span>
              </div>
              <div class="enriched-item enriched-full" v-if="p.past_phd_students">
                <span class="e-label">Past PhD Students</span>
                <span class="e-value">{{ p.past_phd_students }}</span>
              </div>
            </div>
          </div>

          <!-- Deep Publication List -->
          <div class="prof-publications">
            <div class="publications-header-row" @click="togglePapers(p.name)">
              <h5 class="publications-header">Deep Scraped Publications (Top 10)</h5>
              <span class="toggle-icon">{{ expandedPapers === p.name ? '▼' : '▶' }}</span>
            </div>
            <div v-if="expandedPapers === p.name">
              <div v-if="p._deep_papers && p._deep_papers.length > 0">
                <paper-list :papers="p._deep_papers" />
              </div>
              <div v-else class="pending-publications-msg">
                <span class="pending-icon">⟳</span>
                <span>Publications queued. Run "Scan Database Now" to parse publications from Google Scholar.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import PaperList from './PaperList.vue';

export default {
  name: 'FollowingSection',
  components: {
    PaperList
  },
  props: {
    scholarships: {
      type: Array,
      required: true
    },
    professors: {
      type: Array,
      required: true
    },
    universities: {
      type: Array,
      required: true
    },
    followedNames: {
      type: Object,
      required: true,
      default: () => ({ scholarships: [], professors: [], universities: [] })
    }
  },
  data() {
    return {
      quickAdd: {
        category: 'scholarships',
        selectedName: ''
      },
      enrichRunning: false,
      enrichProgress: '',
      enrichPollTimer: null,
      enrichStuck: false,
      expandedPapers: ''
    };
  },
  computed: {
    availableItems() {
      if (this.quickAdd.category === 'scholarships') {
        const followed = this.followedNames.scholarships || [];
        return this.scholarships.filter(s => !followed.includes(s.name));
      } else if (this.quickAdd.category === 'universities') {
        const followed = this.followedNames.universities || [];
        return this.universities.filter(u => !followed.includes(u.name));
      } else if (this.quickAdd.category === 'professors') {
        const followed = this.followedNames.professors || [];
        return this.professors.filter(p => !followed.includes(p.name));
      }
      return [];
    },
    followedScholarships() {
      return this.scholarships.filter(s => 
        this.followedNames.scholarships?.includes(s.name)
      );
    },
    followedProfessors() {
      return this.professors.filter(p => 
        this.followedNames.professors?.includes(p.name)
      );
    },
    followedUniversities() {
      return this.universities.filter(u => 
        this.followedNames.universities?.includes(u.name)
      );
    }
  },
  beforeUnmount() {
    if (this.enrichPollTimer) {
      clearInterval(this.enrichPollTimer);
    }
  },
  methods: {
    togglePapers(name) {
      this.expandedPapers = this.expandedPapers === name ? '' : name;
    },
    async startEnrich() {
      if (this.enrichRunning) return;
      this.enrichStuck = false;
      this.enrichRunning = true;
      this.enrichProgress = 'Starting enrichment...';
      try {
        const resp = await fetch('/api/enrich-saved', { method: 'POST' });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          this.enrichProgress = err.error || `Error starting enrichment (${resp.status})`;
          this.enrichRunning = false;
          this.enrichStuck = true;
          return;
        }
        this.pollEnrichStatus();
      } catch (e) {
        this.enrichProgress = 'Network error — backend not reachable';
        this.enrichRunning = false;
        this.enrichStuck = true;
      }
    },
    async resetEnrich() {
      try {
        await fetch('/api/enrich-saved-reset', { method: 'POST' });
        this.enrichProgress = '';
        this.enrichRunning = false;
        this.enrichStuck = false;
      } catch (e) {
        this.enrichProgress = 'Could not reset enrichment status';
      }
    },
    pollEnrichStatus() {
      this.enrichPollTimer = setInterval(async () => {
        try {
          const resp = await fetch('/api/enrich-saved-status');
          const status = await resp.json();
          this.enrichProgress = status.progress || '';
          if (status.done) {
            clearInterval(this.enrichPollTimer);
            this.enrichPollTimer = null;
            this.enrichRunning = false;
            this.$emit('refresh-data');
          }
        } catch (e) {
          clearInterval(this.enrichPollTimer);
          this.enrichPollTimer = null;
          this.enrichRunning = false;
        }
      }, 1000);
    },
    onCategoryChange() {
      this.quickAdd.selectedName = '';
    },
    addQuickTarget() {
      if (!this.quickAdd.selectedName) return;
      if (this.quickAdd.category === 'scholarships') {
        this.$emit('toggle-follow-scholarship', this.quickAdd.selectedName);
      } else if (this.quickAdd.category === 'universities') {
        this.$emit('toggle-follow-university', this.quickAdd.selectedName);
      } else if (this.quickAdd.category === 'professors') {
        this.$emit('toggle-follow-professor', this.quickAdd.selectedName);
      }
      this.quickAdd.selectedName = '';
    },
    unfollowScholarship(name) {
      this.$emit('toggle-follow-scholarship', name);
    },
    unfollowProfessor(name) {
      this.$emit('toggle-follow-professor', name);
    },
    unfollowUniversity(name) {
      this.$emit('toggle-follow-university', name);
    },
    getMatchClass(match = 50) {
      if (match >= 90) return 'match-high';
      if (match >= 70) return 'match-medium';
      return 'match-low';
    }
  }
}
</script>

<style scoped>
.quick-add-widget {
  background: rgba(30, 41, 59, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 1.2rem;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.quick-add-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 0.8rem;
}

.quick-add-controls {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.control-group.flex-1 {
  flex: 1;
  min-width: 200px;
}

.control-group label {
  font-size: 0.7rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.control-group select {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
  border-radius: 6px;
  padding: 0.4rem 0.6rem;
  font-size: 0.8rem;
  outline: none;
  transition: border-color 0.2s;
  width: 100%;
}

.control-group select:focus {
  border-color: #6366f1;
}

.add-btn {
  padding: 0.4rem 1.2rem;
  background: #6366f1;
  color: white;
  border: 1px solid #6366f1;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-btn:hover:not(:disabled) {
  background: #4f46e5;
  border-color: #4f46e5;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  transform: translateY(-1px);
}

.add-btn:disabled {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.05);
  color: #64748b;
  cursor: not-allowed;
}

/* Enrich section */
.enrich-section {
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 12px;
  padding: 1rem 1.2rem;
}

.enrich-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.enrich-btn {
  padding: 0.5rem 1.2rem;
  background: #6366f1;
  color: white;
  border: 1px solid #6366f1;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.enrich-btn:hover:not(:disabled) {
  background: #4f46e5;
  border-color: #4f46e5;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  transform: translateY(-1px);
}

.enrich-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.enrich-progress {
  color: #a5b4fc;
  font-size: 0.8rem;
  font-style: italic;
}

.enrich-progress.error {
  color: #f87171;
}

.reset-btn {
  padding: 0.5rem 1rem;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: #f87171;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.reset-btn:hover {
  background: rgba(239, 68, 68, 0.25);
  border-color: #ef4444;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.25);
}

/* Main section layout */
.following-section {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
}

.section-header {
  margin-bottom: 0.5rem;
}

.section-title {
  font-family: 'Outfit', sans-serif;
  font-weight: 800;
  font-size: 1.6rem;
  color: #ffffff;
  margin-bottom: 0.4rem;
}

.section-subtitle {
  color: #94a3b8;
  font-size: 0.9rem;
  line-height: 1.5;
}

.sub-section {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.sub-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #e2e8f0;
  border-left: 3px solid #6366f1;
  padding-left: 0.75rem;
  line-height: 1.2;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  background: rgba(30, 41, 59, 0.2);
  border: 1px dashed rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  text-align: center;
  color: #64748b;
  max-width: 600px;
  margin: 0 auto;
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  filter: drop-shadow(0 0 10px rgba(99, 102, 241, 0.15));
}

.empty-state p {
  font-size: 0.85rem;
  line-height: 1.5;
  max-width: 380px;
}

.following-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.2rem;
}

.following-grid.columns-1 {
  grid-template-columns: 1fr;
}

.following-item-card {
  background: rgba(30, 41, 59, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 1.2rem;
  position: relative;
  transition: all 0.2s ease;
}

.following-item-card:hover {
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(30, 41, 59, 0.55);
}

.remove-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #94a3b8;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
  transform: scale(1.1);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.35);
}

/* Scholarship specific */
.item-header {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.8rem;
  padding-right: 1.5rem;
}

.badge {
  padding: 0.15rem 0.5rem;
  font-size: 0.65rem;
  font-weight: 700;
  border-radius: 4px;
  text-transform: uppercase;
}

.badge.country {
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.badge.country-green {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.2);
  color: #34d399;
}

.badge.uni {
  background: rgba(167, 139, 250, 0.12);
  border: 1px solid rgba(167, 139, 250, 0.2);
  color: #c084fc;
}

.badge.h-index {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #38bdf8;
}

.badge.qs-rank {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #fbbf24;
}

.badge.match {
  border-radius: 4px;
}

.match-high {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
}

.match-medium {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #fbbf24;
}

.match-low {
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
}

.item-name {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 0.2rem;
  line-height: 1.3;
}

.item-provider {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 1rem;
}

.item-meta {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-bottom: 1rem;
  background: rgba(0, 0, 0, 0.1);
  padding: 0.6rem;
  border-radius: 6px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
}

.meta-label {
  color: #64748b;
  font-weight: 500;
}

.meta-value {
  color: #cbd5e1;
  font-weight: 600;
}

.meta-value.text-red {
  color: #f87171;
}

.meta-value.text-green {
  color: #34d399;
}

.enriched-section {
  background: rgba(52, 211, 153, 0.04);
  border: 1px solid rgba(52, 211, 153, 0.12);
  border-radius: 6px;
  padding: 0.6rem;
  margin-bottom: 0.75rem;
}

.enriched-title {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #34d399;
  margin: 0 0 0.4rem 0;
}

.enriched-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.35rem;
}

.enriched-item {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.enriched-item.enriched-full {
  grid-column: 1 / -1;
}

.e-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  font-weight: 600;
}

.e-value {
  font-size: 0.75rem;
  color: #e5e7eb;
  line-height: 1.3;
  word-break: break-word;
}

.e-link {
  font-size: 0.75rem;
  color: #60a5fa;
  text-decoration: underline;
  word-break: break-all;
}

.text-amber {
  color: #f59e0b;
}

.strategy-callout {
  background: rgba(99, 102, 241, 0.05);
  border-left: 2px solid #818cf8;
  padding: 0.5rem;
  border-radius: 0 4px 4px 0;
  margin-bottom: 1rem;
  font-size: 0.75rem;
  color: #a5b4fc;
  line-height: 1.4;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
}

.action-btn-sm {
  padding: 0.35rem 0.8rem;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.25);
  color: #60a5fa;
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.75rem;
  font-weight: 600;
  transition: all 0.2s;
}

.action-btn-sm:hover {
  background: #3b82f6;
  color: white;
}

/* Professor wide card specific */
.prof-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.2rem;
  padding-right: 2rem;
  gap: 1.5rem;
}

.prof-name {
  font-family: 'Outfit', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #ffffff;
  margin-top: 0.3rem;
  margin-bottom: 0.1rem;
}

.prof-title {
  font-size: 0.8rem;
  color: #94a3b8;
}

.prof-side-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
}

.email-btn {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.75rem;
  font-weight: 600;
  transition: all 0.2s;
}

.email-btn:hover {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.25);
}

.prof-publications {
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
  padding-top: 1.2rem;
}

.publications-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: 0.4rem 0;
  margin-bottom: 0.8rem;
  user-select: none;
}

.publications-header-row:hover {
  opacity: 0.8;
}

.publications-header {
  font-family: 'Outfit', sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
  color: #cbd5e1;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.toggle-icon {
  font-size: 0.7rem;
  color: #6b7280;
}

.pending-publications-msg {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.8rem;
  background: rgba(245, 158, 11, 0.04);
  border: 1px solid rgba(245, 158, 11, 0.1);
  color: #fbbf24;
  border-radius: 6px;
  font-size: 0.75rem;
}

.pending-icon {
  animation: spin 3s linear infinite;
  display: inline-block;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .prof-header-row {
    flex-direction: column;
    gap: 1rem;
  }
  .prof-side-info {
    align-items: flex-start;
  }
}
</style>
