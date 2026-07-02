<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': !sidebarOpen }">
    <!-- Sidebar Navigation -->
    <aside class="app-sidebar" :class="{ collapsed: !sidebarOpen }">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-icon">🎓</span>
          <span class="logo-text" v-show="sidebarOpen">Scholar<span class="highlight">AI</span></span>
        </div>
        <span class="version-badge" v-show="sidebarOpen">v{{ version }}</span>
        <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen" :title="sidebarOpen ? 'Collapse' : 'Expand'">
          <span v-if="sidebarOpen">◀</span>
          <span v-else>▶</span>
        </button>
      </div>

      <!-- Profile Avatar Panel -->
      <div class="profile-card" v-if="data.profile" v-show="sidebarOpen">
        <div class="profile-avatar">{{ initials }}</div>
        <div class="profile-info">
          <h4 class="profile-name">{{ data.profile.name }}</h4>
          <p class="profile-education">{{ data.profile.current_education }}</p>
          <div class="profile-stats">
            <span class="gpa-pill">GPA {{ data.profile.gpa }}</span>
            <span class="country-pill">Target: {{ data.profile.target_countries?.join(', ') }}</span>
          </div>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <nav class="sidebar-menu">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="menu-item"
          :class="{ 'active': activeTab === tab.id }"
          @click="selectTab(tab.id)"
          :title="tab.name"
        >
          <span class="menu-icon">{{ tab.icon }}</span>
          <span class="menu-label" v-show="sidebarOpen">{{ tab.name }}</span>
          <span class="menu-badge" v-if="tab.id === 'following' && totalFollowed > 0" v-show="sidebarOpen">
            {{ totalFollowed }}
          </span>
          <span class="menu-badge warning-badge" v-if="tab.id === 'deadlines' && deadlineMetrics.critical > 0" v-show="sidebarOpen">
            {{ deadlineMetrics.critical }}
          </span>
        </button>
      </nav>

      <!-- Sidebar Footer -->
      <div class="sidebar-footer" v-show="sidebarOpen">
        <button 
          class="scan-action-btn" 
          :disabled="loading || scanStatus.running" 
          @click="triggerScan"
          :class="{ 'running': scanStatus.running }"
        >
          <span class="scan-icon" :class="{ 'spin': scanStatus.running }">⟳</span>
          <span class="scan-text">
            {{ scanStatus.running ? 'Scanning...' : 'Scan Database' }}
          </span>
        </button>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="app-body">
      <!-- Top header displaying active tab description and scan progress -->
      <header class="body-header">
        <div class="header-title">
          <h2>{{ activeTabName }}</h2>
          <p class="tab-desc">{{ activeTabDesc }}</p>
        </div>

        <div class="scan-progress-banner" v-if="scanStatus.progress">
          <span class="progress-dot" :class="{ 'pulse': scanStatus.running, 'done': scanStatus.done }"></span>
          <span class="progress-txt">{{ scanStatus.progress }}</span>
        </div>
      </header>

      <main class="body-content">
        <!-- Loading State -->
        <div v-if="loading" class="loading-overlay">
          <div class="loader"></div>
          <p>Connecting to ScholarAI database...</p>
        </div>

        <div v-else class="tab-pane-container">
          <!-- 1. DASHBOARD TAB -->
          <div v-if="activeTab === 'dashboard'" class="tab-pane dashboard-pane">
            
            <!-- Metrics row -->
            <div class="metrics-grid">
              <div class="metric-card" @click="activeTab = 'scholarships'">
                <span class="metric-icon">🎓</span>
                <div class="metric-info">
                  <h3>{{ data.scholarships.length }}</h3>
                  <p>Scholarships Found</p>
                </div>
              </div>
              <div class="metric-card" @click="activeTab = 'universities'">
                <span class="metric-icon">🏢</span>
                <div class="metric-info">
                  <h3>{{ data.universities.length }}</h3>
                  <p>MSc Programs</p>
                </div>
              </div>
              <div class="metric-card" @click="activeTab = 'professors'">
                <span class="metric-icon">🔬</span>
                <div class="metric-info">
                  <h3>{{ data.professors.length }}</h3>
                  <p>Faculty Advisors</p>
                </div>
              </div>
              <div class="metric-card" @click="activeTab = 'following'">
                <span class="metric-icon loved">♥</span>
                <div class="metric-info">
                  <h3>{{ totalFollowed }}</h3>
                  <p>Tracked Targets</p>
                </div>
              </div>
            </div>

            <!-- Double-column dashboard detail layout -->
            <div class="dashboard-columns">
              <!-- Left Col: Roadmap & Checklist -->
              <div class="dashboard-col main-col">
                <div class="panel-card">
                  <h3 class="panel-header-title">📅 Admission Roadmap Milestones</h3>
                  <div class="milestones-timeline">
                    <div 
                      v-for="(m, idx) in data.timeline" 
                      :key="idx" 
                      class="timeline-block"
                      :class="{ 'critical': m.priority.toLowerCase() === 'critical', 'high': m.priority.toLowerCase() === 'high' }"
                    >
                      <div class="block-header">
                        <span class="priority-label">{{ m.priority }}</span>
                        <h4 class="phase-title">{{ m.phase }}</h4>
                        <span class="period-text">{{ m.period }}</span>
                      </div>
                      <ul class="task-bullets">
                        <li v-for="(task, tIdx) in m.tasks" :key="tIdx">
                          {{ task }}
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Right Col: Match fit scores -->
              <div class="dashboard-col side-col">
                <div class="panel-card">
                  <h3 class="panel-header-title">⚡ High-Probability Matches</h3>
                  <div class="dashboard-scores">
                    <div v-for="(score, sIdx) in sortedScores" :key="sIdx" class="score-card-item">
                      <div class="score-meta">
                        <span class="score-name">{{ score.name }}</span>
                        <span class="score-badge" :class="getScoreClass(score.overall)">
                          {{ score.overall }}/10
                        </span>
                      </div>
                      <div class="bar-outer">
                        <div class="bar-inner" :class="getScoreClass(score.overall)" :style="{ width: (score.overall * 10) + '%' }"></div>
                      </div>
                      <p class="score-rec">{{ score.recommendation }}</p>
                      <p class="score-notes">{{ score.notes }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Cost Comparison panel -->
            <div class="panel-card cost-comparison-panel" v-if="data.costs && data.costs.length > 0">
              <h3 class="panel-header-title">💵 Student Living Cost Metrics</h3>
              <div class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Country</th>
                      <th>City</th>
                      <th>Target Universities</th>
                      <th>Tuition / Sem</th>
                      <th>Rent / Mo</th>
                      <th>Blocked Account / Yr</th>
                      <th>Verdict</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(cost, cIdx) in sortedCosts" :key="cIdx">
                      <td>
                        <span class="country-pill" :class="(cost.country || '').toLowerCase()">
                          {{ cost.country }}
                        </span>
                      </td>
                      <td><strong>{{ cost.city }}</strong></td>
                      <td>{{ cost.university }}</td>
                      <td>{{ cost.tuition === 0 ? 'FREE' : currencySymbol(cost.tuition_currency) + cost.tuition }}</td>
                      <td>{{ currencySymbol(cost.tuition_currency) }}{{ cost.rent }}</td>
                      <td>{{ cost.blocked_account > 0 ? currencySymbol(cost.tuition_currency) + cost.blocked_account.toLocaleString() : 'Not Required' }}</td>
                      <td class="verdict-note"><strong>{{ cost.total_yearly_note }}</strong></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          <!-- 1b. DEADLINES TAB -->
          <div v-if="activeTab === 'deadlines'" class="tab-pane deadlines-pane">
            
            <!-- Metrics Row -->
            <div class="metrics-grid">
              <div class="metric-card" @click="filters.deadlines.status = ''">
                <span class="metric-icon">📅</span>
                <div class="metric-info">
                  <h3>{{ deadlineMetrics.total }}</h3>
                  <p>Total Events</p>
                </div>
              </div>
              <div class="metric-card" @click="filters.deadlines.status = 'critical'">
                <span class="metric-icon">💥</span>
                <div class="metric-info">
                  <h3>{{ deadlineMetrics.critical }}</h3>
                  <p>Critical (&le;7 days)</p>
                </div>
              </div>
              <div class="metric-card" @click="filters.deadlines.status = 'urgent'">
                <span class="metric-icon">⚠️</span>
                <div class="metric-info">
                  <h3>{{ deadlineMetrics.urgent }}</h3>
                  <p>Urgent (&le;30 days)</p>
                </div>
              </div>
              <div class="metric-card" @click="filters.deadlines.status = 'overdue'">
                <span class="metric-icon">❌</span>
                <div class="metric-info">
                  <h3>{{ deadlineMetrics.overdue }}</h3>
                  <p>Past Due</p>
                </div>
              </div>
            </div>

            <!-- Interactive Filters -->
            <div class="filter-bar border-glass">
              <div class="filter-search-container">
                <span class="search-icon-inside">🔍</span>
                <input 
                  type="text" 
                  v-model="filters.deadlines.search" 
                  placeholder="Search events, programs, countries..."
                  class="search-input"
                />
              </div>
              <select v-model="filters.deadlines.type" class="filter-select">
                <option value="">All Categories</option>
                <option value="scholarship">Scholarships</option>
                <option value="university">University Intakes</option>
              </select>
              <select v-model="filters.deadlines.status" class="filter-select">
                <option value="">All Statuses</option>
                <option value="overdue">Past Due</option>
                <option value="critical">Critical (&le;7 days)</option>
                <option value="urgent">Urgent (&le;30 days)</option>
                <option value="upcoming">Upcoming (&gt;30 days)</option>
              </select>
              <label class="toggle-container">
                <input type="checkbox" v-model="filters.deadlines.onlyFollowed" />
                <span class="toggle-slider"></span>
                <span class="toggle-label">Tracked Only</span>
              </label>
            </div>

            <!-- Deadlines List -->
            <div class="deadlines-list" v-if="filteredDeadlines.length > 0">
              <div 
                v-for="d in filteredDeadlines" 
                :key="d.name + d.deadline" 
                class="deadline-row-card"
                :class="d.status"
              >
                <div class="deadline-main-info">
                  <div class="deadline-meta-top">
                    <span class="deadline-badge-pill" :class="d.status">
                      {{ getUrgencyLabel(d) }}
                    </span>
                    <span class="deadline-type-tag" :class="d.type">
                      {{ d.type === 'scholarship' ? '🎓 Scholarship' : '🏢 University' }}
                    </span>
                    <span class="deadline-country-tag">
                      📍 {{ d.country }}
                    </span>
                  </div>
                  <h3 class="deadline-name">{{ d.name }}</h3>
                  
                  <div class="deadline-details">
                    <span v-if="d.type === 'scholarship' && d.amount" class="deadline-detail-item">
                      <strong>Coverage:</strong> {{ d.amount }}
                    </span>
                    <span v-if="d.type === 'university' && d.program" class="deadline-detail-item">
                      <strong>Program:</strong> {{ d.program }}
                    </span>
                    <span class="deadline-detail-item date-item">
                      <strong>Deadline:</strong> {{ d.deadline }} ({{ formatDate(d.deadline_date) }})
                    </span>
                  </div>
                </div>

                <div class="deadline-countdown-section">
                  <div class="days-remaining" :class="d.status">
                    <span class="days-num">{{ Math.abs(d.remaining_days) }}</span>
                    <span class="days-label">{{ d.remaining_days < 0 ? 'days ago' : 'days left' }}</span>
                  </div>
                  
                  <div class="deadline-actions">
                    <a v-if="d.portal || d.url"
                      :href="d.portal || d.url"
                      target="_blank"
                      class="deadline-apply-btn"
                      title="Apply now"
                    >
                      Apply ↗
                    </a>
                    <button 
                      class="deadline-follow-btn"
                      :class="{ 'is-followed': isDeadlineFollowed(d) }"
                      @click="toggleFollowDeadline(d)"
                      :title="isDeadlineFollowed(d) ? 'Unfollow target' : 'Follow target'"
                    >
                      <span class="heart-icon">{{ isDeadlineFollowed(d) ? '♥' : '♡' }}</span>
                      {{ isDeadlineFollowed(d) ? 'Tracked' : 'Track' }}
                    </button>
                  </div>
                </div>

              </div>
            </div>
            <div v-else class="empty-results border-glass">
              No upcoming events match your filtering criteria.
            </div>

          </div>

          <!-- 2. SCHOLARSHIPS TAB -->
          <div v-if="activeTab === 'scholarships'" class="tab-pane">
            <div class="filter-bar">
              <input 
                type="text" 
                v-model="filters.scholarships.search" 
                placeholder="Search scholarship names, providers..."
                class="search-input"
              />
              <select v-model="filters.scholarships.country" class="filter-select">
                <option value="">All Countries</option>
                <option v-for="c in uniqueScholarshipCountries" :key="c" :value="c">
                  {{ c }}
                </option>
              </select>
              <select v-model="filters.scholarships.coverage" class="filter-select">
                <option value="">All Coverage</option>
                <option value="Full-Ride">Full-Ride Only</option>
                <option value="Full Tuition">Full Tuition Only</option>
                <option value="Partial">Partial Only</option>
              </select>
            </div>

            <div class="cards-grid" v-if="filteredScholarships.length > 0">
              <scholarship-card 
                v-for="s in filteredScholarships" 
                :key="s.name"
                :scholarship="s"
                :is-followed="data.followed.scholarships?.includes(s.name)"
                @toggle-follow="onToggleFollowScholarship"
              />
            </div>
            <div v-else class="empty-results">
              No scholarships match your search query.
            </div>
          </div>

          <!-- 3. UNIVERSITIES TAB -->
          <div v-if="activeTab === 'universities'" class="tab-pane">
            <div class="filter-bar">
              <input 
                type="text" 
                v-model="filters.universities.search" 
                placeholder="Search universities, cities, program names..."
                class="search-input"
              />
              <select v-model="filters.universities.country" class="filter-select">
                <option value="">All Countries</option>
                <option v-for="c in uniqueUniversityCountries" :key="c" :value="c">
                  {{ c }}
                </option>
              </select>
            </div>

            <div class="cards-grid" v-if="filteredUniversities.length > 0">
              <university-card 
                v-for="u in filteredUniversities" 
                :key="u.name"
                :university="u"
                :is-followed="data.followed.universities?.includes(u.name)"
                :is-wishlist-target="isUniversityInWishlist(u.name)"
                @toggle-follow="onToggleFollowUniversity"
              />
            </div>
            <div v-else class="empty-results">
              No universities match your search query.
            </div>
          </div>

          <!-- 4. PROFESSORS TAB -->
          <div v-if="activeTab === 'professors'" class="tab-pane">
            <div class="filter-bar">
              <input 
                type="text" 
                v-model="filters.professors.search" 
                placeholder="Search names, interests, target universities..."
                class="search-input"
              />
              <select v-model="filters.professors.country" class="filter-select">
                <option value="">All Countries</option>
                <option v-for="c in uniqueProfessorCountries" :key="c" :value="c">
                  {{ c }}
                </option>
              </select>
            </div>

            <div class="cards-grid" v-if="filteredProfessors.length > 0">
              <professor-card 
                v-for="p in filteredProfessors" 
                :key="p.name"
                :professor="p"
                :is-followed="data.followed.professors?.includes(p.name)"
                :is-wishlist-target="isUniversityInWishlist(p.university)"
                @toggle-follow="onToggleFollowProfessor"
              />
            </div>
            <div v-else class="empty-results">
              No professor profiles match your search query.
            </div>
          </div>

          <!-- 5. FOLLOWING TAB -->
          <div v-if="activeTab === 'following'" class="tab-pane">
            <following-section 
              :scholarships="data.scholarships"
              :professors="data.professors"
              :universities="data.universities"
              :followed-names="data.followed"
              @toggle-follow-scholarship="onToggleFollowScholarship"
              @toggle-follow-professor="onToggleFollowProfessor"
              @toggle-follow-university="onToggleFollowUniversity"
              @refresh-data="refreshData"
            />
          </div>

          <!-- 6. DOCUMENTS TAB -->
          <div v-if="activeTab === 'documents'" class="tab-pane">
            <documents-section />
          </div>

          <!-- 7. SCHOLARSHIP MASTERY TAB -->
          <div v-if="activeTab === 'mastery'" class="tab-pane">
            <scholarship-mastery />
          </div>

          <!-- 8. MY DOCS TAB -->
          <div v-if="activeTab === 'my-docs'" class="tab-pane">
            <MyDocsSection />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import ScholarshipCard from './components/ScholarshipCard.vue';
import ProfessorCard from './components/ProfessorCard.vue';
import UniversityCard from './components/UniversityCard.vue';
import FollowingSection from './components/FollowingSection.vue';
import ScholarshipMastery from './components/ScholarshipMastery.vue';
import DocumentsSection from './components/DocumentsSection.vue';
import MyDocsSection from './components/MyDocsSection.vue';

async function safeFetch(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export default {
  name: 'App',
  components: {
    ScholarshipCard,
    ProfessorCard,
    UniversityCard,
    FollowingSection,
    ScholarshipMastery,
    DocumentsSection,
    MyDocsSection
  },
  data() {
    return {
      version: '1.2.0',
      sidebarOpen: true,
      activeTab: 'dashboard',
      loading: true,
      tabs: [
        { id: 'dashboard', name: 'Dashboard', icon: '📊' },
        { id: 'deadlines', name: 'Deadlines', icon: '📅' },
        { id: 'scholarships', name: 'Scholarships', icon: '🎓' },
        { id: 'universities', name: 'Universities', icon: '🏢' },
        { id: 'professors', name: 'Professors', icon: '🔬' },
        { id: 'following', name: 'Saved Targets', icon: '♥' },
        { id: 'documents', name: 'Documents', icon: '📄' },
        { id: 'mastery', name: 'Scholarship Mastery', icon: '🎯' },
        { id: 'my-docs', name: 'My Docs', icon: '📝' }
      ],
      scanStatus: {
        running: false,
        progress: '',
        done: false
      },
      data: {
        scholarships: [],
        universities: [],
        professors: [],
        scores: [],
        timeline: [],
        costs: [],
        deadlines: [],
        followed: { scholarships: [], professors: [], universities: [] },
        profile: null
      },
      filters: {
        scholarships: { search: '', country: '', coverage: '' },
        universities: { search: '', country: '' },
        professors: { search: '', country: '' },
        deadlines: { search: '', type: '', status: '', onlyFollowed: false }
      },
      pollInterval: null,
    
    }
  },
  computed: {
    activeTabName() {
      return this.tabs.find(t => t.id === this.activeTab)?.name || '';
    },
    activeTabDesc() {
      const descriptions = {
        dashboard: 'Consolidated milestones, match fits, and living costs.',
        deadlines: 'Track critical application deadlines and intake schedules.',
        scholarships: 'Explore and match full-ride scholarships.',
        universities: 'Target English-taught master programs in AI/ML.',
        professors: 'Identify research advisors and view publication papers.',
        following: 'Your custom tracking list for priority updates.',
        documents: 'Real SOPs, CVs, and recommendation letters from scholarship winners worldwide.',
        mastery: 'Deep-dive guidance for your 8 target scholarships.',
        'my-docs': 'Generate and manage personalized application documents (SOP, CV, Research Proposal, LOR, Diversity, Essay, Personal History).'
      };
      return descriptions[this.activeTab] || '';
    },
    deadlineMetrics() {
      const deadlines = this.data.deadlines || [];
      let overdue = 0;
      let critical = 0;
      let urgent = 0;
      let active = 0;
      
      deadlines.forEach(d => {
        if (d.remaining_days < 0) {
          overdue++;
        } else {
          active++;
          if (d.remaining_days <= 7) {
            critical++;
          } else if (d.remaining_days <= 30) {
            urgent++;
          }
        }
      });
      
      return {
        total: deadlines.length,
        active,
        overdue,
        critical,
        urgent
      };
    },
    filteredDeadlines() {
      if (!this.data.deadlines) return [];
      return this.data.deadlines.filter(d => {
        const query = this.filters.deadlines.search.toLowerCase();
        const matchesSearch = !query || 
          (d.name || '').toLowerCase().includes(query) ||
          (d.program && d.program.toLowerCase().includes(query)) ||
          (d.country && d.country.toLowerCase().includes(query));
          
        const matchesType = !this.filters.deadlines.type || 
          d.type === this.filters.deadlines.type;
          
        let matchesStatus = true;
        if (this.filters.deadlines.status) {
          if (this.filters.deadlines.status === 'overdue') {
            matchesStatus = d.remaining_days < 0;
          } else if (this.filters.deadlines.status === 'critical') {
            matchesStatus = d.remaining_days >= 0 && d.remaining_days <= 7;
          } else if (this.filters.deadlines.status === 'urgent') {
            matchesStatus = d.remaining_days > 7 && d.remaining_days <= 30;
          } else if (this.filters.deadlines.status === 'upcoming') {
            matchesStatus = d.remaining_days > 30;
          }
        }
        
        let matchesFollowed = true;
        if (this.filters.deadlines.onlyFollowed) {
          matchesFollowed = this.isDeadlineFollowed(d);
        }
        
        return matchesSearch && matchesType && matchesStatus && matchesFollowed;
      });
    },
    totalFollowed() {
      return (
        (this.data.followed.scholarships?.length || 0) +
        (this.data.followed.professors?.length || 0) +
        (this.data.followed.universities?.length || 0)
      );
    },
    initials() {
      if (!this.data.profile || !this.data.profile.name) return 'S';
      const parts = this.data.profile.name.split(' ');
      if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
      }
      return this.data.profile.name[0].toUpperCase();
    },
    sortedScores() {
      if (!this.data.scores) return [];
      return [...this.data.scores].sort((a, b) => b.overall - a.overall).slice(0, 5);
    },
    sortedCosts() {
      if (!this.data.costs) return [];
      return [...this.data.costs].sort((a, b) => {
        if (a.country !== b.country) return a.country.localeCompare(b.country);
        return a.living - b.living;
      });
    },
    filteredScholarships() {
      return this.data.scholarships.filter(s => {
        const query = this.filters.scholarships.search.toLowerCase();
        const matchesSearch = !query || 
          (s.name || '').toLowerCase().includes(query) ||
          (s.provider && s.provider.toLowerCase().includes(query)) ||
          (s.country || '').toLowerCase().includes(query);
        const matchesCountry = !this.filters.scholarships.country || 
          (s.country || '').toLowerCase() === this.filters.scholarships.country.toLowerCase();
        const cov = this.filters.scholarships.coverage;
        let matchesCoverage = true;
        if (cov === 'Full-Ride') {
          matchesCoverage = (s.coverage_type && s.coverage_type.toLowerCase().includes('full')) || 
            (s.coverage && (s.coverage.toLowerCase().includes('full') || s.coverage.toLowerCase().includes('tuition waiver')));
        } else if (cov === 'Full Tuition') {
          matchesCoverage = (s.coverage_type && s.coverage_type.toLowerCase().includes('tuition'));
        } else if (cov === 'Partial') {
          matchesCoverage = (s.coverage_type && s.coverage_type.toLowerCase().includes('partial'));
        }
        return matchesSearch && matchesCountry && matchesCoverage;
      });
    },
    filteredUniversities() {
      return this.data.universities.filter(u => {
        const query = this.filters.universities.search.toLowerCase();
        const matchesSearch = !query || 
          (u.name || '').toLowerCase().includes(query) ||
          (u.program || '').toLowerCase().includes(query) ||
          (u.location || '').toLowerCase().includes(query);
        const matchesCountry = !this.filters.universities.country || 
          (u.country || '').toLowerCase() === this.filters.universities.country.toLowerCase();
        return matchesSearch && matchesCountry;
      });
    },
    filteredProfessors() {
      return this.data.professors.filter(p => {
        const query = this.filters.professors.search.toLowerCase();
        const matchesSearch = !query || 
          (p.name || '').toLowerCase().includes(query) ||
          (p.university || '').toLowerCase().includes(query) ||
          (p.interests || '').toLowerCase().includes(query);
        const matchesCountry = !this.filters.professors.country || 
          (p.country || '').toLowerCase() === this.filters.professors.country.toLowerCase();
        return matchesSearch && matchesCountry;
      });
    },
    uniqueScholarshipCountries() {
      const countries = this.data.scholarships.map(s => s.country).filter(Boolean);
      return [...new Set(countries)].sort();
    },
    uniqueUniversityCountries() {
      const countries = this.data.universities.map(u => u.country).filter(Boolean);
      return [...new Set(countries)].sort();
    },
    uniqueProfessorCountries() {
      const countries = this.data.professors.map(p => p.country).filter(Boolean);
      return [...new Set(countries)].sort();
    }
  },
  mounted() {
    this.fetchData();
    this.checkScanStatus();
    
    setInterval(() => {
      if (!this.scanStatus.running) {
        this.fetchData(false);
      }
    }, 45000);
  },
  methods: {
    selectTab(id) {
      this.activeTab = id;
      this.sidebarOpen = false;
    },

    isUniversityInWishlist(name) {
      if (!name || !this.data.profile || !this.data.profile.target_universities) return false;
      const nameLower = name.toLowerCase().trim();
      return this.data.profile.target_universities.some(u => {
        const uLower = u.toLowerCase().trim();
        return nameLower.includes(uLower) || uLower.includes(nameLower);
      });
    },
    refreshData() {
      this.fetchData(false);
    },
    fetchData(showLoading = true) {
      if (showLoading) this.loading = true;
      safeFetch('/api/data')
        .then(resData => {
          this.data = {
            scholarships: resData.scholarships || [],
            universities: resData.universities || [],
            professors: resData.professors || [],
            scores: resData.scores || [],
            timeline: resData.timeline || [],
            costs: resData.costs || [],
            deadlines: resData.deadlines || [],
            followed: resData.followed || { scholarships: [], professors: [], universities: [] },
            profile: resData.profile || null
          };
          this.loading = false;
        })
        .catch(err => {
          console.error('Failed to fetch data:', err);
          this.loading = false;
        });
    },
    isDeadlineFollowed(d) {
      if (d.type === 'scholarship') {
        return this.data.followed.scholarships?.includes(d.name);
      } else if (d.type === 'university') {
        const baseName = d.name.split(' (')[0];
        return this.data.followed.universities?.includes(baseName);
      }
      return false;
    },
    toggleFollowDeadline(d) {
      if (d.type === 'scholarship') {
        this.onToggleFollowScholarship(d.name);
      } else if (d.type === 'university') {
        const baseName = d.name.split(' (')[0];
        this.onToggleFollowUniversity(baseName);
      }
    },
    getUrgencyLabel(d) {
      if (d.remaining_days < 0) return '❌ PAST DUE';
      if (d.remaining_days === 0) return '🔥 DUE TODAY';
      if (d.remaining_days <= 7) return '💥 IMMEDIATE';
      if (d.remaining_days <= 30) return '⚠️ URGENT';
      if (d.remaining_days <= 90) return '🕒 SOON';
      return '📅 FAR';
    },
    currencySymbol(currency) {
      const symbols = { EUR: '€', USD: '$', GBP: '£', CAD: '$', CHF: 'CHF ', SGD: 'S$', AUD: 'A$' };
      return symbols[currency] || currency + ' ';
    },
    formatDate(dateStr) {
      if (!dateStr) return '';
      try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      } catch (e) {
        return dateStr;
      }
    },
    checkScanStatus() {
      safeFetch('/api/scan-status')
        .then(status => {
          this.scanStatus = status;
          if (status.running) {
            this.startPollingScanStatus();
          }
        })
        .catch(err => console.error('Error fetching scan status:', err));
    },
    triggerScan() {
      this.scanStatus.running = true;
      this.scanStatus.progress = 'Starting live scraper agents...';
      safeFetch('/api/scan', { method: 'POST' })
        .then(() => {
          this.startPollingScanStatus();
        })
        .catch(err => {
          this.scanStatus.running = false;
          this.scanStatus.progress = `Failed: ${err.message || err}`;
        });
    },
    startPollingScanStatus() {
      if (this.pollInterval) clearInterval(this.pollInterval);
      this.pollInterval = setInterval(() => {
        safeFetch('/api/scan-status')
          .then(status => {
            this.scanStatus = status;
            if (status.done || !status.running) {
              clearInterval(this.pollInterval);
              this.pollInterval = null;
              this.fetchData(false);
            }
          })
          .catch(err => {
            console.error('Scan polling error:', err);
            clearInterval(this.pollInterval);
            this.pollInterval = null;
          });
      }, 3000);
    },
    onToggleFollowScholarship(name) {
      if (!this.data.followed.scholarships) this.data.followed.scholarships = [];
      const index = this.data.followed.scholarships.indexOf(name);
      const newFollowed = { ...this.data.followed };
      
      if (index > -1) {
        newFollowed.scholarships.splice(index, 1);
      } else {
        newFollowed.scholarships.push(name);
      }
      this.saveFollowed(newFollowed);
    },
    onToggleFollowProfessor(name) {
      if (!this.data.followed.professors) this.data.followed.professors = [];
      const index = this.data.followed.professors.indexOf(name);
      const newFollowed = { ...this.data.followed };
      
      if (index > -1) {
        newFollowed.professors.splice(index, 1);
      } else {
        newFollowed.professors.push(name);
      }
      this.saveFollowed(newFollowed);
    },
    onToggleFollowUniversity(name) {
      if (!this.data.followed.universities) this.data.followed.universities = [];
      const index = this.data.followed.universities.indexOf(name);
      const newFollowed = { ...this.data.followed };
      
      if (index > -1) {
        newFollowed.universities.splice(index, 1);
      } else {
        newFollowed.universities.push(name);
      }
      this.saveFollowed(newFollowed);
    },
    saveFollowed(newFollowed) {
      this.data.followed = newFollowed;
      safeFetch('/api/followed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newFollowed)
      })
        .then(res => {
          if (res.status !== 'ok') {
            this.fetchData(false);
          }
        })
        .catch(err => {
          console.error('Save followed error:', err);
          this.fetchData(false);
        });
    },
    getScoreClass(score) {
      if (score >= 8.5) return 'score-high';
      if (score >= 7.0) return 'score-medium';
      return 'score-low';
    }
  }
}
</script>

<style>
/* Global CSS variables & reset */
:root {
  --bg-primary: #090d16;
  --bg-secondary: #0f1626;
  --card-bg: rgba(30, 41, 59, 0.45);
  --border-color: rgba(255, 255, 255, 0.05);
  --sidebar-width: 280px;
  
  --primary: #3b82f6;
  --primary-glow: rgba(59, 130, 246, 0.35);
  --secondary: #6366f1;
  --text-main: #f3f4f6;
  --text-muted: #9ca3af;
  
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-display: 'Outfit', sans-serif;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-main);
  font-family: var(--font-sans);
  background-image: 
    radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(59, 130, 246, 0.06) 0px, transparent 50%);
  background-attachment: fixed;
  min-height: 100vh;
}

/* Sidebar Dashboard Grid Layout */
.app-layout {
  display: flex;
  min-height: 100vh;
}

/* App Sidebar styling */
.app-sidebar {
  width: var(--sidebar-width);
  background: rgba(13, 22, 38, 0.95);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  padding: 1.5rem 1rem;
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  left: 0;
  top: 0;
  z-index: 100;
  transition: width 0.25s ease, padding 0.25s ease;
  overflow: hidden;
}
.app-sidebar.collapsed {
  width: 60px;
  padding: 1.5rem 0.5rem;
}
.sidebar-toggle {
  background: none;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px;
  color: #475569;
  cursor: pointer;
  font-size: 0.65rem;
  padding: 0.15rem 0.25rem;
  transition: color 0.15s;
  flex-shrink: 0;
}
.sidebar-toggle:hover { color: #94a3b8; }
.app-sidebar.collapsed .sidebar-toggle {
  margin: 0 auto;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 1.35rem;
  color: #fff;
}

.logo-icon {
  font-size: 1.6rem;
  filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.5));
}

.highlight {
  background: linear-gradient(90deg, #60a5fa, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.version-badge {
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: #a5b4fc;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.1rem 0.4rem;
  border-radius: 20px;
}

/* Profile Card in Sidebar */
.profile-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  padding: 0.8rem;
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 2rem;
}

.profile-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  color: white;
  font-size: 0.85rem;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
  flex-shrink: 0;
}

.profile-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.profile-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.profile-education {
  font-size: 0.7rem;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 0.3rem;
}

.profile-stats {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.gpa-pill {
  font-size: 0.65rem;
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  padding: 0.05rem 0.3rem;
  border-radius: 4px;
  font-weight: 700;
}

.country-pill {
  font-size: 0.65rem;
  background: rgba(255, 255, 255, 0.05);
  color: #94a3b8;
  padding: 0.05rem 0.3rem;
  border-radius: 4px;
}

/* Sidebar Menu */
.sidebar-menu {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.menu-item {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  padding: 0.65rem 0.8rem;
  border-radius: 8px;
  color: #94a3b8;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  transition: all 0.2s;
  position: relative;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.03);
  color: white;
}

.menu-item.active {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.2);
}

.menu-badge {
  background: #ef4444;
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: auto;
}

/* Scan action button in Sidebar footer */
.sidebar-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 1rem;
}

.scan-action-btn {
  width: 100%;
  padding: 0.7rem;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border: none;
  border-radius: 8px;
  color: white;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.25s;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.scan-action-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 15px rgba(59, 130, 246, 0.35);
}

.scan-action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

.scan-action-btn.running {
  background: rgba(167, 139, 250, 0.15);
  border: 1px solid rgba(167, 139, 250, 0.3);
  color: #c084fc;
}

.scan-icon.spin {
  animation: spin 1.5s linear infinite;
  display: inline-block;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* App Main Body */
.app-body {
  flex: 1;
  margin-left: var(--sidebar-width);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.25s ease;
}
.sidebar-collapsed .app-body {
  margin-left: 60px;
}

/* Body Header */
.body-header {
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--border-color);
  background: rgba(9, 13, 22, 0.4);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 90;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
}

.header-title h2 {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 1.45rem;
  color: white;
}

.tab-desc {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.1rem;
}

.scan-progress-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  max-width: 450px;
}

.progress-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: #3b82f6;
  flex-shrink: 0;
}

.progress-dot.pulse {
  background-color: #a78bfa;
  animation: pulse 1.5s ease-in-out infinite;
}

.progress-dot.done {
  background-color: #10b981;
}

.progress-txt {
  font-size: 0.75rem;
  color: #cbd5e1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.6; }
}

/* Body Content */
.body-content {
  flex: 1;
  padding: 2rem;
}

.tab-pane-container {
  width: 100%;
}

/* Filter Bar */
.filter-bar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.search-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 0.7rem 1.2rem;
  color: white;
  font-family: var(--font-sans);
  font-size: 0.9rem;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.15);
}

.filter-select {
  background: #0f1626;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 0.7rem 1rem;
  color: #cbd5e1;
  font-family: var(--font-sans);
  font-size: 0.9rem;
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.5);
}

/* Empty Results & Loader */
.empty-results {
  text-align: center;
  padding: 4rem;
  color: var(--text-muted);
  border: 1px dashed var(--border-color);
  border-radius: 12px;
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6rem;
  color: var(--text-muted);
  gap: 1rem;
}

.loader {
  border: 3px solid rgba(255, 255, 255, 0.04);
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  animation: spin 1s linear infinite;
}

/* Cards Grid Layout */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1.2rem;
}

/* Dashboard Styles */
.dashboard-pane {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.2rem;
}

.metric-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1rem 1.2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.metric-card:hover {
  background: rgba(30, 41, 59, 0.6);
  border-color: rgba(99, 102, 241, 0.25);
  transform: translateY(-1px);
}

.metric-icon {
  font-size: 2rem;
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon.loved {
  color: #ef4444;
}

.metric-info h3 {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 1.3rem;
  color: white;
  line-height: 1.2;
}

.metric-info p {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.dashboard-columns {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 2rem;
}

.panel-card {
  background: rgba(30, 41, 59, 0.25);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem;
}

.panel-header-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.1rem;
  color: white;
  margin-bottom: 1.2rem;
}

/* Timeline */
.milestones-timeline {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.timeline-block {
  background: rgba(15, 23, 42, 0.4);
  border-left: 3px solid rgba(255, 255, 255, 0.1);
  padding: 0.8rem 1.2rem;
  border-radius: 0 8px 8px 0;
}

.timeline-block.critical {
  border-left-color: #f87171;
}

.timeline-block.high {
  border-left-color: #60a5fa;
}

.block-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.5rem;
}

.priority-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  font-weight: 800;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  color: #94a3b8;
}

.critical .priority-label {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.high .priority-label {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.phase-title {
  font-weight: 700;
  font-size: 0.85rem;
  color: #fff;
}

.period-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: auto;
}

.task-bullets {
  padding-left: 1.2rem;
  font-size: 0.8rem;
  color: #cbd5e1;
}

.task-bullets li {
  margin-bottom: 0.25rem;
}

/* Scores List */
.dashboard-scores {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.score-card-item {
  background: rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.03);
  padding: 0.8rem 1rem;
  border-radius: 8px;
}

.score-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.score-name {
  font-weight: 600;
  font-size: 0.85rem;
  color: white;
}

.score-badge {
  font-weight: 700;
  font-size: 0.8rem;
}

.score-high { color: #34d399; }
.score-medium { color: #fbbf24; }
.score-low { color: #a5b4fc; }

.bar-outer {
  height: 4px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 0.6rem;
}

.bar-inner {
  height: 100%;
  border-radius: 2px;
}

.bar-inner.score-high { background-color: #10b981; }
.bar-inner.score-medium { background-color: #f59e0b; }
.bar-inner.score-low { background-color: #6366f1; }

.score-rec {
  font-size: 0.75rem;
  font-weight: 700;
  color: #cbd5e1;
  margin-bottom: 0.2rem;
}

.score-notes {
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.4;
}

/* Cost table */
.cost-comparison-panel {
  width: 100%;
}

.table-container {
  overflow-x: auto;
  margin-bottom: 1.2rem;
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.data-table th {
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 700;
}

.data-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  font-size: 0.8rem;
  color: #cbd5e1;
}

.data-table tr:hover {
  background-color: rgba(255, 255, 255, 0.01);
}

.country-pill {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
}

.country-pill.germany {
  background: rgba(251, 191, 36, 0.12);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.2);
}

.country-pill.usa {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.country-pill.uk {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.country-pill.canada {
  background: rgba(248, 113, 113, 0.12);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.2);
}

.country-pill.switzerland {
  background: rgba(251, 191, 36, 0.12);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.2);
}

.country-pill.singapore {
  background: rgba(167, 139, 250, 0.12);
  color: #a78bfa;
  border: 1px solid rgba(167, 139, 250, 0.2);
}

.country-pill.australia {
  background: rgba(56, 189, 248, 0.12);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.2);
}

.verdict-note {
  color: #38bdf8;
}

.cost-tips {
  font-size: 0.75rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.01);
  padding: 0.75rem;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

/* Responsive adjustment for Mobile */
@media (max-width: 992px) {
  .app-layout {
    flex-direction: column;
  }
  .app-sidebar {
    width: 100%;
    height: auto;
    position: relative;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  .app-body {
    margin-left: 0;
  }
  .dashboard-columns {
    grid-template-columns: 1fr;
  }
  .filter-bar {
    flex-direction: column;
  }
}

/* Deadlines Tab Styles */
.deadlines-pane {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.border-glass {
  background: rgba(30, 41, 59, 0.2);
  border: 1px solid var(--border-color);
  backdrop-filter: blur(8px);
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
  color: var(--text-muted);
  font-size: 0.9rem;
}

.filter-search-container .search-input {
  padding-left: 2.5rem;
  width: 100%;
}

/* Custom switch toggle */
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
  height: 100%;
}

.toggle-container input {
  display: none;
}

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
  background-color: var(--primary);
  box-shadow: 0 0 8px var(--primary-glow);
}

.toggle-container input:checked + .toggle-slider:before {
  transform: translateX(16px);
}

.toggle-label {
  font-size: 0.85rem;
  color: #cbd5e1;
  font-weight: 600;
}

/* Deadlines list */
.deadlines-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.deadline-row-card {
  background: rgba(30, 41, 59, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.2rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
}

.deadline-row-card:hover {
  background: rgba(30, 41, 59, 0.45);
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.1);
}

/* Left indicator border based on status */
.deadline-row-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  transition: all 0.3s;
}

.deadline-row-card.past_due::before { background-color: #ef4444; }
.deadline-row-card.due_today::before { background-color: #ff4500; }
.deadline-row-card.critical::before { background-color: #f87171; }
.deadline-row-card.warning::before { background-color: #f59e0b; }
.deadline-row-card.upcoming::before { background-color: #3b82f6; }
.deadline-row-card.normal::before { background-color: #10b981; }

/* Status-specific card glowing borders */
.deadline-row-card.due_today {
  border-color: rgba(239, 68, 68, 0.25);
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.15);
}
.deadline-row-card.critical {
  border-color: rgba(248, 113, 113, 0.2);
  box-shadow: 0 0 12px rgba(248, 113, 113, 0.1);
}

/* Metadata pills */
.deadline-meta-top {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.6rem;
  flex-wrap: wrap;
}

.deadline-badge-pill {
  font-size: 0.65rem;
  font-weight: 800;
  padding: 0.15rem 0.5rem;
  border-radius: 40px;
  text-transform: uppercase;
}

.deadline-badge-pill.past_due {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.25);
}

.deadline-badge-pill.due_today {
  background: rgba(255, 69, 0, 0.15);
  color: #ff6347;
  border: 1px solid rgba(255, 69, 0, 0.3);
  animation: pulse 1.5s infinite;
}

.deadline-badge-pill.critical {
  background: rgba(248, 113, 113, 0.15);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.25);
}

.deadline-badge-pill.warning {
  background: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.deadline-badge-pill.upcoming {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.deadline-badge-pill.normal {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.deadline-type-tag {
  font-size: 0.7rem;
  font-weight: 700;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.04);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.deadline-country-tag {
  font-size: 0.7rem;
  font-weight: 700;
  color: #94a3b8;
}

.deadline-name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.15rem;
  color: white;
  margin-bottom: 0.6rem;
}

.deadline-details {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.deadline-detail-item {
  font-size: 0.8rem;
  color: #94a3b8;
}

.deadline-detail-item strong {
  color: #cbd5e1;
}

.deadline-detail-item.date-item {
  color: #a5b4fc;
}

/* Countdown & actions column */
.deadline-countdown-section {
  display: flex;
  align-items: center;
  gap: 2rem;
  flex-shrink: 0;
}

.days-remaining {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 90px;
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.days-remaining.past_due {
  background: rgba(239, 68, 68, 0.05);
  border-color: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.days-remaining.critical {
  background: rgba(248, 113, 113, 0.05);
  border-color: rgba(248, 113, 113, 0.15);
  color: #f87171;
}

.days-remaining.warning {
  background: rgba(245, 158, 11, 0.03);
  border-color: rgba(245, 158, 11, 0.1);
  color: #fbbf24;
}

.days-num {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 800;
  line-height: 1.1;
}

.days-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 700;
  opacity: 0.8;
}

.deadline-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.deadline-apply-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #93c5fd;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
  white-space: nowrap;
}

.deadline-apply-btn:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.35);
  color: white;
}

.deadline-follow-btn {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.2s;
}

.deadline-follow-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
}

.deadline-follow-btn.is-followed {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.25);
  color: #fc8181;
}

.deadline-follow-btn.is-followed:hover {
  background: rgba(239, 68, 68, 0.15);
}

.heart-icon {
  font-size: 0.95rem;
}

.menu-badge.warning-badge {
  background: #ff4500;
  box-shadow: 0 0 6px rgba(255, 69, 0, 0.4);
}

@media (max-width: 768px) {
  .deadline-row-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 1.2rem;
  }
  
  .deadline-countdown-section {
    width: 100%;
    justify-content: space-between;
  }
}

/* My Docs Tab Styles */
.my-docs-pane {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.my-docs-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  padding: 0.6rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #c4b5fd;
}

.action-btn {
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border: none;
  color: white;
  padding: 0.7rem 1.5rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--font-sans);
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 15px rgba(59, 130, 246, 0.3);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.small-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #a5b4fc;
  padding: 0.3rem 0.7rem;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--font-sans);
}

.small-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.small-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.my-docs-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 1.2rem;
  min-height: 400px;
}

.my-docs-sidebar {
  background: rgba(30, 41, 59, 0.2);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1rem;
}

.my-docs-scholarship-list {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.my-docs-scholarship-item {
  background: none;
  border: none;
  text-align: left;
  padding: 0.5rem 0.8rem;
  border-radius: 6px;
  color: #94a3b8;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.my-docs-scholarship-item:hover {
  background: rgba(255, 255, 255, 0.03);
  color: white;
}

.my-docs-scholarship-item.active {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
}

.my-docs-viewer {
  background: rgba(30, 41, 59, 0.2);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.2rem;
  overflow: hidden;
}

.my-docs-type-tabs {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.8rem;
}

.my-docs-type-tab {
  background: none;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  color: #94a3b8;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.my-docs-type-tab:hover {
  color: white;
  background: rgba(255, 255, 255, 0.03);
}

.my-docs-type-tab.active {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.my-docs-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 600px;
  overflow-y: auto;
}

.my-docs-section {
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 0.8rem;
}

.my-docs-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.my-docs-section-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.85rem;
  color: #a5b4fc;
}

.my-docs-section-body {
  font-size: 0.8rem;
  color: #cbd5e1;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: var(--font-sans);
  background: none;
  border: none;
  padding: 0;
  margin: 0;
}

@media (max-width: 768px) {
  .my-docs-layout {
    grid-template-columns: 1fr;
  }
}
</style>
