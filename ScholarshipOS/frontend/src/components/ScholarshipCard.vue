<template>
  <div class="card" :class="{ 'expanded': isExpanded }">
    <button class="heart-btn" :class="{ 'loved': isFollowed }" @click.stop="toggleFollow">
      ♥
    </button>

    <div class="card-header" @click="isExpanded = !isExpanded">
      <div class="header-main">
        <span class="country-tag">{{ scholarship.country }}</span>
        <h3 class="name">{{ scholarship.name }}</h3>
        <p class="provider">🏛 Provided by {{ scholarship.provider }}</p>
      </div>

      <div class="header-side">
        <div class="match-badge" :class="matchClass">
          {{ scholarship.match || 50 }}% Match
        </div>
        <span class="expand-indicator">{{ isExpanded ? '▲' : '▼' }}</span>
      </div>
    </div>

    <div class="card-summary" @click="isExpanded = !isExpanded">
      <div class="summary-item">
        <span class="label">Coverage</span>
        <span class="value">{{ scholarship.coverage_type || 'Full-ride' }}</span>
      </div>
      <div class="summary-item">
        <span class="label">Amount</span>
        <span class="value highlighting">{{ scholarship.currency }} {{ scholarship.amount }}</span>
      </div>
      <div class="summary-item">
        <span class="label">Deadline End</span>
        <span class="value deadline-val">{{ scholarship.deadline_end || 'Varies' }}</span>
      </div>
    </div>

    <!-- Expanded Body -->
    <transition name="slide-fade">
      <div class="card-body" v-if="isExpanded">
        
        <!-- Detailed Grid Block -->
        <div class="details-grid">
          
          <!-- Coverage -->
          <div class="details-section full-width" v-if="scholarship.coverage">
            <h4 class="section-title">Coverage Details</h4>
            <p class="section-content text-highlight">{{ scholarship.coverage }}</p>
          </div>

          <!-- Academic Eligibility -->
          <div class="details-section">
            <h4 class="section-title">Academic Requirements</h4>
            <p class="section-content">
              {{ scholarship.academics || 'Check official link' }}
            </p>
          </div>

          <!-- Work Experience -->
          <div class="details-section">
            <h4 class="section-title">Work Experience</h4>
            <p class="section-content">
              {{ scholarship.experience || 'Not required / fresh graduates welcome' }}
            </p>
          </div>

          <!-- Nationality & Degree -->
          <div class="details-section">
            <h4 class="section-title">General Eligibility</h4>
            <p class="section-content">
              <strong>Nationality:</strong> {{ scholarship.nationality || 'All international students' }}<br />
              <strong>Degree Level:</strong> {{ scholarship.degree || 'MSc / Masters' }}<br />
              <strong>Target Fields:</strong> {{ scholarship.fields || 'ML, AI, Data Science, Statistics' }}
            </p>
          </div>

          <!-- Application Mechanics -->
          <div class="details-section">
            <h4 class="section-title">Application Requirements</h4>
            <p class="section-content">
              <strong>Application Fee:</strong> {{ scholarship.fee || 'None' }}<br />
              <strong>Application Language:</strong> {{ scholarship.lang_app || 'English' }}<br />
              <strong>English Proficiency:</strong> {{ scholarship.english_test || 'IELTS/TOEFL required' }}<br />
              <strong>GRE/GMAT Test:</strong> {{ scholarship.gre || 'Not required' }}
            </p>
          </div>

          <!-- Application Period -->
          <div class="details-section">
            <h4 class="section-title">Process & Deadlines</h4>
            <p class="section-content">
              <strong>Start Date:</strong> {{ scholarship.deadline_start || 'Check website' }}<br />
              <strong>End Date:</strong> {{ scholarship.deadline_end || 'Check website' }}<br />
              <strong>Duration:</strong> {{ scholarship.duration || 'Check website' }}<br />
              <strong>Interview:</strong> {{ scholarship.interview || 'Varies' }}<br />
              <strong>Competitiveness:</strong> {{ scholarship.competition || 'High' }}
            </p>
          </div>

          <!-- Documents Checklist -->
          <div class="details-section" v-if="scholarship.documents">
            <h4 class="section-title">Required Documents</h4>
            <ul class="documents-list">
              <li v-for="(doc, idx) in parsedDocuments" :key="idx">{{ doc }}</li>
            </ul>
          </div>

          <!-- Strategy Notes -->
          <div class="details-section full-width strategy-notes" v-if="scholarship.strategy">
            <h4 class="section-title">Antigravity Strategy Notes</h4>
            <p class="section-content">{{ scholarship.strategy }}</p>
          </div>
        </div>

        <div class="card-footer">
          <div class="links-group">
            <button 
              class="action-btn tracking" 
              :class="{ 'followed': isFollowed }" 
              @click.stop="toggleFollow"
            >
              {{ isFollowed ? '♥ Saved' : '♡ Save to Tracking' }}
            </button>
            <a :href="scholarship.portal || scholarship.url" target="_blank" class="action-btn secondary" v-if="scholarship.portal">
              Application Portal ↗
            </a>
            <a :href="scholarship.url || scholarship.portal" target="_blank" class="action-btn secondary">
              Official Webpage ↗
            </a>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  name: 'ScholarshipCard',
  props: {
    scholarship: {
      type: Object,
      required: true
    },
    isFollowed: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      isExpanded: false
    }
  },
  computed: {
    matchClass() {
      const match = this.scholarship.match || 50;
      if (match >= 90) return 'match-high';
      if (match >= 70) return 'match-medium';
      return 'match-low';
    },
    parsedDocuments() {
      if (!this.scholarship.documents) return [];
      return this.scholarship.documents.split(/[;|\n]/).map(d => d.trim()).filter(Boolean);
    }
  },
  methods: {
    toggleFollow() {
      this.$emit('toggle-follow', this.scholarship.name);
    }
  }
}
</script>

<style scoped>
.card {
  background: rgba(30, 41, 59, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 1.2rem;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card:hover {
  background: rgba(30, 41, 59, 0.65);
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2), 0 0 15px rgba(99, 102, 241, 0.1);
  transform: translateY(-2px);
}

.card.expanded {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(99, 102, 241, 0.5);
  transform: none;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.heart-btn {
  position: absolute;
  top: 1.2rem;
  right: 3.5rem;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.2);
  font-size: 1.4rem;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s ease;
  line-height: 1;
}

.heart-btn:hover {
  color: #ef4444;
  transform: scale(1.2);
}

.heart-btn.loved {
  color: #ef4444;
  text-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
  animation: beat 0.3s ease-out;
}

@keyframes beat {
  0% { transform: scale(1); }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  cursor: pointer;
  gap: 1.5rem;
  padding-right: 1.5rem;
}

.header-main {
  flex: 1;
}

.country-tag {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  font-size: 0.7rem;
  font-weight: 600;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}

.name {
  font-family: 'Outfit', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 0.2rem;
  line-height: 1.3;
}

.provider {
  font-size: 0.8rem;
  color: #94a3b8;
  font-weight: 500;
}

.header-side {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.match-badge {
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2px;
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

.expand-indicator {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.3);
  transition: transform 0.3s;
}

.card-summary {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.summary-item .label {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.summary-item .value {
  font-size: 0.85rem;
  font-weight: 600;
  color: #cbd5e1;
}

.summary-item .value.highlighting {
  color: #38bdf8;
}

.summary-item .value.deadline-val {
  color: #f87171;
}

/* Card Body (Expanded) */
.card-body {
  margin-top: 1.2rem;
  padding-top: 1.2rem;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
}

.details-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.2rem;
}

.full-width {
  grid-column: span 2;
}

.details-section {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.section-title {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #818cf8;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.section-content {
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.5;
}

.text-highlight {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.02);
  padding: 0.6rem;
  border-radius: 6px;
  border-left: 3px solid #6366f1;
}

.documents-list {
  padding-left: 1.2rem;
  margin: 0;
}

.documents-list li {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 0.25rem;
}

.strategy-notes {
  background: rgba(99, 102, 241, 0.05);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 8px;
  padding: 0.8rem 1rem;
}

.strategy-notes .section-title {
  color: #a78bfa;
}

.strategy-notes .section-content {
  color: #d8b4fe;
  font-style: italic;
}

.card-footer {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
}

.links-group {
  display: flex;
  gap: 0.6rem;
}

.action-btn {
  display: inline-block;
  padding: 0.5rem 1.2rem;
  background: #3b82f6;
  color: white;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 600;
  transition: all 0.2s;
  cursor: pointer;
}

.action-btn:hover {
  background: #2563eb;
  border-color: #2563eb;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
}

.action-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
  box-shadow: none;
}

.action-btn.tracking {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.action-btn.tracking:hover {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.35);
}

.action-btn.tracking.followed {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
}

/* Animations */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

@media (max-width: 768px) {
  .details-grid {
    grid-template-columns: 1fr;
  }
  .full-width {
    grid-column: span 1;
  }
  .card-summary {
    flex-wrap: wrap;
    gap: 1rem;
  }
}
</style>
