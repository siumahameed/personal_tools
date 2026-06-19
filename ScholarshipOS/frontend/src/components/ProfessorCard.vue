<template>
  <div class="card" :class="{ 'expanded': isExpanded, 'wishlist-card': isWishlistTarget }">
    <button class="heart-btn" :class="{ 'loved': isFollowed }" @click.stop="toggleFollow">
      ♥
    </button>

    <div class="card-header" @click="isExpanded = !isExpanded">
      <div class="header-main">
        <span class="uni-tag">{{ professor.university }}</span>
        <span class="wishlist-badge" v-if="isWishlistTarget">🎯 TARGET UNI</span>
        <h3 class="name">{{ professor.name }}</h3>
        <p class="title">{{ professor.title }}</p>
      </div>

      <div class="header-side">
        <div class="h-index-badge">
          h-index: <strong>{{ professor.h_index || 'N/A' }}</strong>
        </div>
        <span class="expand-indicator">{{ isExpanded ? '▲' : '▼' }}</span>
      </div>
    </div>

    <div class="interests-container" @click="isExpanded = !isExpanded">
      <div class="interests-label">Research Areas</div>
      <div class="interests-tags">
        <span v-for="(interest, idx) in parsedInterests" :key="idx" class="interest-tag">
          {{ interest }}
        </span>
      </div>
    </div>

    <!-- Expanded Body -->
    <transition name="slide-fade">
      <div class="card-body" v-if="isExpanded">
        <div class="details-grid">
          
          <div class="details-section">
            <h4 class="section-title">Contact & Office</h4>
            <p class="section-content">
              <strong>Email:</strong> <a :href="'mailto:' + professor.email" class="email-link">{{ professor.email }}</a><br />
              <strong>Phone:</strong> {{ professor.phone || 'N/A' }}<br />
              <strong>Department:</strong> {{ professor.department || 'Computer Science / Statistics' }}<br />
              <strong>Research Group:</strong> {{ professor.group || 'N/A' }}
            </p>
          </div>

          <div class="details-section">
            <h4 class="section-title">Academic & Advising</h4>
            <p class="section-content">
              <strong>Students:</strong> {{ professor.students || 'Check faculty page' }}<br />
              <strong>Courses Taught:</strong> {{ professor.courses || 'N/A' }}<br />
              <strong>Supervisor For:</strong> {{ professor.supervisor_for || 'MSc/PhD' }}
            </p>
          </div>

          <div class="details-section full-width" v-if="professor.funding">
            <h4 class="section-title">Funding & Collaboration</h4>
            <p class="section-content">
              <strong>Funding Available:</strong> {{ professor.funding }}<br />
              <strong>Collaboration:</strong> {{ professor.collab || 'Open to applications' }}<br />
              <strong>Citations Count:</strong> {{ professor.citations || 'Check Google Scholar' }}
            </p>
          </div>

          <div class="details-section full-width strategy-notes" v-if="professor.strategy">
            <h4 class="section-title">Antigravity Strategy Notes</h4>
            <p class="section-content">{{ professor.strategy }}</p>
          </div>

          <!-- Publications -->
          <div class="details-section full-width publications-section">
            <h4 class="section-title">Publications & Research Papers</h4>
            
            <!-- Case 1: Professor is followed, papers are loaded -->
            <div v-if="isFollowed && professor._deep_papers && professor._deep_papers.length > 0">
              <p class="publications-status-msg">✓ Scraped top publications from Google Scholar:</p>
              <paper-list :papers="professor._deep_papers" />
            </div>

            <!-- Case 2: Professor is followed, papers not scraped yet -->
            <div v-else-if="isFollowed" class="scraped-pending-msg">
              <span class="warning-icon">⚠</span>
              <span>Deep publications will be collected on the next scan run. Click "Scan Database Now" to scrape.</span>
            </div>

            <!-- Case 3: Professor is NOT followed, show basic papers text with direct Scholar links -->
            <div v-else>
              <ul class="basic-papers-bullets">
                <li v-for="(paper, idx) in parsedPapers" :key="idx" class="basic-paper-item">
                  <span class="paper-title-text">{{ paper }}</span>
                  <a 
                    :href="'https://scholar.google.com/scholar?q=' + encodeURIComponent(paper)" 
                    target="_blank" 
                    class="paper-scholar-link"
                    title="Search paper on Google Scholar"
                  >
                    Search Scholar ↗
                  </a>
                </li>
              </ul>
              <p class="follow-tip">♥ Follow this professor to auto-scrape their top 10 publications and PDF links on the next scan.</p>
            </div>
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
            <a v-if="professor.scholar_url" :href="professor.scholar_url" target="_blank" class="action-btn secondary">
              Google Scholar Profile ↗
            </a>
            <a :href="professor.profile_url" target="_blank" class="action-btn secondary">
              Faculty Profile ↗
            </a>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import PaperList from './PaperList.vue';

export default {
  name: 'ProfessorCard',
  components: {
    PaperList
  },
  props: {
    professor: {
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
    parsedInterests() {
      if (!this.professor.interests) return [];
      return this.professor.interests.split(',').map(i => i.trim()).filter(Boolean);
    },
    parsedPapers() {
      if (!this.professor.papers) return [];
      return this.professor.papers.split(/[;|\n]/).map(p => p.trim()).filter(Boolean);
    }
  },
  methods: {
    toggleFollow() {
      this.$emit('toggle-follow', this.professor.name);
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

.uni-tag {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: rgba(167, 139, 250, 0.12);
  border: 1px solid rgba(167, 139, 250, 0.2);
  color: #c084fc;
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

.title {
  font-size: 0.8rem;
  color: #94a3b8;
  font-weight: 500;
}

.header-side {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.h-index-badge {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  color: #94a3b8;
}

.h-index-badge strong {
  color: #38bdf8;
}

.expand-indicator {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.3);
  transition: transform 0.3s;
}

.interests-container {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
}

.interests-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-bottom: 0.4rem;
}

.interests-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.interest-tag {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #cbd5e1;
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

.email-link {
  color: #3b82f6;
  text-decoration: none;
}

.email-link:hover {
  text-decoration: underline;
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

.publications-section {
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.03);
  padding: 1rem;
  border-radius: 8px;
}

.publications-status-msg {
  font-size: 0.8rem;
  color: #10b981;
  font-weight: 500;
  margin-bottom: 0.6rem;
}

.scraped-pending-msg {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.06);
  border: 1px solid rgba(245, 158, 11, 0.15);
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
}

.basic-papers-bullets {
  padding-left: 1.2rem;
  margin-bottom: 0.8rem;
}

.basic-paper-item {
  font-size: 0.85rem;
  color: #cbd5e1;
  margin-bottom: 0.4rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.paper-title-text {
  line-height: 1.4;
  flex: 1;
}

.paper-scholar-link {
  color: #60a5fa;
  text-decoration: none;
  font-size: 0.75rem;
  white-space: nowrap;
  border: 1px solid rgba(96, 165, 250, 0.2);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  background: rgba(96, 165, 250, 0.03);
  transition: all 0.2s;
}

.paper-scholar-link:hover {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.follow-tip {
  font-size: 0.75rem;
  color: #818cf8;
  font-style: italic;
  margin-top: 0.5rem;
  border-top: 1px dashed rgba(255, 255, 255, 0.05);
  padding-top: 0.5rem;
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
