<template>
  <div class="card" :class="{ 'expanded': isExpanded, 'wishlist-card': isWishlistTarget }">
    <button class="heart-btn" :class="{ 'loved': isFollowed }" @click.stop="toggleFollow">
      ♥
    </button>

    <div class="card-header" @click="isExpanded = !isExpanded">
      <div class="header-main">
        <span class="country-tag">{{ university.country }}</span>
        <span class="wishlist-badge" v-if="isWishlistTarget">🎯 TARGET UNI</span>
        <h3 class="name">{{ university.name }}</h3>
        <p class="program-title">🎓 {{ university.program || 'MSc Program' }}</p>
      </div>

      <div class="header-side">
        <div class="qs-badge" v-if="university.qs_rank">
          QS Rank: <strong>#{{ university.qs_rank }}</strong>
        </div>
        <span class="expand-indicator">{{ isExpanded ? '▲' : '▼' }}</span>
      </div>
    </div>

    <div class="card-summary" @click="isExpanded = !isExpanded">
      <div class="summary-item">
        <span class="label">Tuition</span>
        <span class="value" :class="{ 'free-val': isFreeTuition }">
          {{ isFreeTuition ? 'FREE' : formatTuition }}
        </span>
      </div>
      <div class="summary-item">
        <span class="label">Winter Deadline</span>
        <span class="value deadline-val">{{ university.deadline_winter || 'Check website' }}</span>
      </div>
      <div class="summary-item">
        <span class="label">Language</span>
        <span class="value">{{ university.language || 'English' }}</span>
      </div>
    </div>

    <!-- Expanded Body -->
    <transition name="slide-fade">
      <div class="card-body" v-if="isExpanded">
        <div class="details-grid">
          
          <div class="details-section">
            <h4 class="section-title">Overview & Rankings</h4>
            <p class="section-content">
              <strong>Location:</strong> {{ university.location || 'N/A' }}<br />
              <strong>Type:</strong> {{ university.type || 'N/A' }}<br />
              <strong>QS World Rank:</strong> #{{ university.qs_rank || 'N/A' }}<br />
              <strong>THE Rank:</strong> #{{ university.the_rank || 'N/A' }}
            </p>
          </div>

          <div class="details-section">
            <h4 class="section-title">Program Mechanics</h4>
            <p class="section-content">
              <strong>Degree:</strong> {{ university.degree || 'MSc' }}<br />
              <strong>Field:</strong> {{ university.field || 'CS/ML/AI' }}<br />
              <strong>Duration:</strong> {{ university.duration || '4 Semesters' }} ({{ university.ects || '120' }} ECTS)<br />
              <strong>Living Costs:</strong> {{ university.living_cost || 'N/A' }}
            </p>
          </div>

          <div class="details-section full-width" v-if="university.requirements">
            <h4 class="section-title">Admission Requirements</h4>
            <p class="section-content text-highlight">{{ university.requirements }}</p>
          </div>

          <div class="details-section">
            <h4 class="section-title">Test & GPA Requirements</h4>
            <p class="section-content">
              <strong>English Prof.:</strong> {{ university.english || 'IELTS 6.5 / TOEFL 88' }}<br />
              <strong>GRE/GMAT:</strong> {{ university.gre || 'Not required' }}<br />
              <strong>Minimum GPA:</strong> {{ university.min_gpa || 'N/A' }}
            </p>
          </div>

          <div class="details-section">
            <h4 class="section-title">Fees & Deadlines</h4>
            <p class="section-content">
              <strong>Tuition:</strong> {{ university.tuition === '0' ? 'FREE' : formatTuition }}<br />
              <strong>Semester Contribution:</strong> {{ university.semester_fee ? university.semester_fee + ' ' + university.currency : 'Check website' }}<br />
              <strong>Application Fee:</strong> {{ university.app_fee || 'None' }}<br />
              <strong>Deadlines:</strong> Winter: {{ university.deadline_winter || 'Varies' }} | Summer: {{ university.deadline_summer || 'Varies' }}
            </p>
          </div>

          <div class="details-section full-width" v-if="university.research">
            <h4 class="section-title">Research Strengths</h4>
            <p class="section-content">{{ university.research }}</p>
          </div>

          <div class="details-section full-width strategy-notes" v-if="university.strategy">
            <h4 class="section-title">Antigravity Strategy Notes</h4>
            <p class="section-content">{{ university.strategy }}</p>
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
            <a v-if="university.dept_url" :href="university.dept_url" target="_blank" class="action-btn secondary">
              Department Webpage ↗
            </a>
            <a :href="university.portal" target="_blank" class="action-btn secondary">
              Apply Portal ↗
            </a>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  name: 'UniversityCard',
  props: {
    university: {
      type: Object,
      required: true
    },
    isFollowed: {
      type: Boolean,
      default: false
    },
    isWishlistTarget: {
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
    isFreeTuition() {
      return this.university.tuition === '0' || !this.university.tuition || this.university.tuition === 0;
    },
    formatTuition() {
      if (this.isFreeTuition) return 'FREE';
      return `${this.university.currency || 'EUR'} ${this.university.tuition}/sem`;
    }
  },
  methods: {
    toggleFollow() {
      this.$emit('toggle-follow', this.university.name);
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
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.2);
  color: #34d399;
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

.program-title {
  font-size: 0.85rem;
  color: #a5b4fc;
  font-weight: 600;
}

.header-side {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.qs-badge {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  color: #94a3b8;
}

.qs-badge strong {
  color: #fbbf24;
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

.summary-item .value.free-val {
  color: #34d399;
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

.wishlist-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
  margin-left: 0.5rem;
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.15);
}

.card.wishlist-card {
  border-color: rgba(251, 191, 36, 0.25);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15), 0 0 10px rgba(251, 191, 36, 0.05);
}

.card.wishlist-card:hover {
  border-color: rgba(251, 191, 36, 0.5);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2), 0 0 20px rgba(251, 191, 36, 0.2);
}
</style>
