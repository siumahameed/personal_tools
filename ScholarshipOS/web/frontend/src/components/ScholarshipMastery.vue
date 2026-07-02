<template>
  <div class="mastery-hub">
    <!-- Hero Header -->
    <div class="hub-hero">
      <div class="hero-main">
        <div class="hero-text">
          <h1 class="hero-title">Scholarship Mastery Hub</h1>
          <p class="hero-sub">Comprehensive guidance for your fully funded scholarship journey</p>
        </div>
        <div class="hero-metrics">
          <div class="hero-metric">
            <span class="metric-val">{{ overview.programs_count }}</span>
            <span class="metric-lbl">Programs</span>
          </div>
          <div class="hero-metric">
            <span class="metric-val">{{ overview.guides_count }}</span>
            <span class="metric-lbl">Guides</span>
          </div>
          <div class="hero-metric">
            <span class="metric-val">{{ scholarships.length }}</span>
            <span class="metric-lbl">Targets</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Sub-navigation -->
    <div class="hub-nav">
      <button v-for="tab in tabs" :key="tab.id" class="hub-nav-btn"
        :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">
        <span class="nav-icon">{{ tab.icon }}</span>
        <span class="nav-lbl">{{ tab.label }}</span>
        <span v-if="tab.count" class="nav-count">{{ tab.count }}</span>
      </button>
    </div>

    <!-- ==================== OVERVIEW TAB ==================== -->
    <div v-if="activeTab === 'overview'" class="tab-content">
      <div class="ov-grid">
        <div class="ov-card hero-card" @click="activeTab = 'programs'">
          <div class="ov-card-icon">&#x1F4DA;</div>
          <h3>{{ overview.programs_count }} Program Guides</h3>
          <p>Detailed information on Erasmus Mundus, MBZUAI, DAAD, Fulbright, Chevening, Commonwealth and more.</p>
          <span class="ov-cta">Browse Programs &rarr;</span>
        </div>
        <div class="ov-card hero-card" @click="activeTab = 'guides'">
          <div class="ov-card-icon">&#x1F4DD;</div>
          <h3>{{ overview.guides_count }} Application Guides</h3>
          <p>Step-by-step application walkthroughs, document checklists, motivation letter templates, and master timelines.</p>
          <span class="ov-cta">View Guides &rarr;</span>
        </div>
        <div class="ov-card hero-card" @click="activeTab = 'timeline'">
          <div class="ov-card-icon">&#x1F4C5;</div>
          <h3>Application Timeline</h3>
          <p>Month-by-month plan from Jun 2026 to Sep 2027 covering all scholarship deadlines, IELTS, visa, and departure.</p>
          <span class="ov-cta">View Timeline &rarr;</span>
        </div>
        <div class="ov-card hero-card" @click="activeTab = 'compare'">
          <div class="ov-card-icon">&#x2696;&#xFE0F;</div>
          <h3>Scholarship Comparison</h3>
          <p>Side-by-side comparison of stipends, duration, deadlines, and fit scores across all target scholarships.</p>
          <span class="ov-cta">Compare &rarr;</span>
        </div>
      </div>

      <div class="ov-section">
        <h2 class="ov-section-title">Your Profile Fit</h2>
        <div class="ov-fit-grid">
          <div class="ov-fit-item">
            <span class="fit-label">Education</span>
            <span class="fit-val">BSc Statistics (3.25/4.00), Dhaka College</span>
          </div>
          <div class="ov-fit-item">
            <span class="fit-label">Experience</span>
            <span class="fit-val">Aspirant Machine Learning Engineer</span>
          </div>
          <div class="ov-fit-item">
            <span class="fit-label">Skills</span>
            <span class="fit-val">Python, TensorFlow, PyTorch, FastAPI, Streamlit, Scikit-learn</span>
          </div>
          <div class="ov-fit-item">
            <span class="fit-label">Nationality</span>
            <span class="fit-val">Bangladeshi (Partner Country for Erasmus Mundus)</span>
          </div>
          <div class="ov-fit-item">
            <span class="fit-label">Key Advantage</span>
            <span class="fit-val highlight-val">Statistics degree + ML engineering = strong quantitative + practical profile</span>
          </div>
          <div class="ov-fit-item">
            <span class="fit-label">Top Recommendation</span>
            <span class="fit-val highlight-val">Erasmus Mundus EMAI (AI) &rarr; InterMaths &rarr; DEAI + MBZUAI (rolling)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== PROGRAMS TAB ==================== -->
    <div v-if="activeTab === 'programs'" class="tab-content">
      <div class="prog-subs">
        <button v-for="s in programSubTabs" :key="s.id" class="prog-sub-btn"
          :class="{ active: activeProgSub === s.id }" @click="activeProgSub = s.id">
          {{ s.label }}
        </button>
      </div>

      <!-- ALL PROGRAMS -->
      <div v-if="activeProgSub === 'all'">
        <div class="hub-filter-bar" style="margin-bottom:1rem">
          <div class="filter-search">
            <span class="filter-search-icon">&#x1F50D;</span>
            <input type="text" v-model="progFilter" placeholder="Search programs..." class="filter-input" />
          </div>
        </div>
        <div v-if="filteredPrograms.length === 0" class="empty-state"><p>No programs match.</p></div>
        <div v-else class="prog-grid">
          <div v-for="p in filteredPrograms" :key="p.slug" class="prog-card"
            @click="openProgram(p)" :class="{ loading: loadingSlug === p.slug }">
            <div class="prog-card-top">
              <span class="prog-badge" :class="badgeClass(p)">{{ p.category || 'Program' }}</span>
              <span v-if="p.match" class="prog-match-pill" :class="matchClass(p.match)">{{ p.match }}% Match</span>
            </div>
            <h3 class="prog-card-title">{{ p.title }}</h3>
            <p class="prog-card-sub" v-if="p.subtitle">{{ p.subtitle }}</p>
            <div class="prog-card-footer">
              <span class="prog-read-link">{{ p.hasGuide ? 'View Details' : 'Quick Info' }} &rarr;</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ERASMUS MUNDUS -->
      <div v-if="activeProgSub === 'erasmus'">
        <div v-if="erasmusPrograms.length === 0" class="empty-state"><p>Loading Erasmus Mundus programs...</p></div>
        <div v-else class="prog-grid">
          <div v-for="p in erasmusPrograms" :key="p.slug" class="prog-card"
            @click="openProgram(p)" :class="{ loading: loadingSlug === p.slug }">
            <div class="prog-card-top">
              <span class="prog-badge badge-erasmus">Erasmus Mundus</span>
              <span v-if="p.match" class="prog-match-pill" :class="matchClass(p.match)">{{ p.match }}% Match</span>
            </div>
            <h3 class="prog-card-title">{{ p.title }}</h3>
            <p class="prog-card-sub" v-if="p.subtitle">{{ p.subtitle }}</p>
            <div class="prog-card-footer">
              <span class="prog-read-link">View Details &rarr;</span>
            </div>
          </div>
        </div>
      </div>

      <!-- MBZUAI TAB -->
      <div v-if="activeProgSub === 'mbzuai'" class="sch-detail-card">
        <div v-if="schDetailLoading" class="modal-loading">
          <div class="loader"></div>
          <p>Loading details...</p>
        </div>
        <div v-else-if="schDetail.mbzuai" class="sch-detail-rendered" v-html="schDetail.mbzuai"></div>
        <div v-else class="sch-detail-fallback">
          <h2>{{ schTabLabels.mbzuai }}</h2>
          <div class="sch-detail-meta">
            <div class="sch-detail-stat"><span class="stat-lbl">Match Score</span><span class="stat-val" :class="matchClass(schMatch('mbzuai'))">{{ schMatch('mbzuai') }}%</span></div>
            <div class="sch-detail-stat"><span class="stat-lbl">Category</span><span class="stat-val">{{ schCat('mbzuai') }}</span></div>
            <div class="sch-detail-stat"><span class="stat-lbl">Programs</span><span class="stat-val">MSc in ML, CV, NLP, Robotics</span></div>
          </div>
          <p style="color:#94a3b8;font-size:0.85rem;margin-top:0.8rem">Detailed guide content not yet available. Use the Comparison tab for side-by-side overview or visit the official website.</p>
        </div>
      </div>

      <!-- DAAD TAB -->
      <div v-if="activeProgSub === 'daad'" class="sch-detail-card">
        <div class="sch-detail-fallback">
          <h2>{{ schTabLabels.daad }}</h2>
          <div class="sch-detail-meta" style="margin-bottom:1.2rem">
            <div class="sch-detail-stat"><span class="stat-lbl">Stipend</span><span class="stat-val" style="color:#34d399">&euro;992/mo (+ &euro;234 insurance)</span></div>
            <div class="sch-detail-stat"><span class="stat-lbl">Duration</span><span class="stat-val">12-36 months</span></div>
            <div class="sch-detail-stat"><span class="stat-lbl">Main Deadline</span><span class="stat-val">Aug-Sep (for Oct start)</span></div>
            <div class="sch-detail-stat"><span class="stat-lbl">Countries</span><span class="stat-val" style="color:#34d399">Germany</span></div>
          </div>

          <!-- Step-by-Step Process -->
          <div class="daad-section">
            <h3 class="daad-section-title">Application Process</h3>
            <p style="color:#94a3b8;font-size:0.85rem;margin-bottom:1rem">Complete guide to winning a DAAD Study Scholarship for your Master's in Germany (2026-2027 cycle)</p>

            <div class="daad-steps">
              <div class="daad-step" v-for="(step, si) in daadSteps" :key="si">
                <div class="daad-step-num">{{ step.num }}</div>
                <div class="daad-step-body">
                  <div class="daad-step-icon">{{ step.icon }}</div>
                  <div class="daad-step-content">
                    <h4 class="daad-step-title">{{ step.title }}</h4>
                    <p class="daad-step-desc">{{ step.desc }}</p>
                    <ul v-if="step.tips" class="daad-step-tips">
                      <li v-for="(tip, ti) in step.tips" :key="ti">{{ tip }}</li>
                    </ul>
                    <div v-if="step.extra" class="daad-step-extra">
                      <div v-for="(item, ei) in step.extra" :key="ei" class="daad-extra-item">
                        <strong>{{ item.label }}:</strong> {{ item.val }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- DAAD Scholarship Program Types -->
          <div class="daad-section">
            <h3 class="daad-section-title">DAAD Scholarship Programs</h3>
            <p style="color:#94a3b8;font-size:0.85rem;margin-bottom:1rem">Which DAAD program fits your profile best?</p>
            <div class="daad-sch-grid">
              <div v-for="(prog, pi) in daadScholarships" :key="pi" class="daad-sch-card">
                <div class="daad-sch-header">
                  <h4 class="daad-sch-name">{{ prog.name }}</h4>
                  <span class="daad-sch-badge" :class="'badge-' + prog.fit">{{ prog.fitLabel }}</span>
                </div>
                <div class="daad-sch-body">
                  <div class="daad-sch-row"><strong>Stipend:</strong> {{ prog.stipend }}</div>
                  <div class="daad-sch-row"><strong>Duration:</strong> {{ prog.duration }}</div>
                  <div class="daad-sch-row"><strong>Deadline:</strong> {{ prog.deadline }}</div>
                  <p class="daad-sch-desc">{{ prog.desc }}</p>
                  <div v-if="prog.eligible" class="daad-sch-eligible">
                    <strong>Eligible programs:</strong> {{ prog.eligible }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Recommended Programs -->
          <div class="daad-section">
            <h3 class="daad-section-title">Top German Programs for Your Profile</h3>
            <p style="color:#94a3b8;font-size:0.85rem;margin-bottom:1rem">If awarded a DAAD scholarship, these programs at German public universities offer the best fit for your Statistics + ML background. DAAD covers living costs at any of them.</p>
            <div class="daad-grid">
              <div v-for="(p, i) in daadPrograms" :key="i" class="daad-card">
                <div class="daad-card-header">
                  <span class="daad-rank">{{ i + 1 }}</span>
                  <div class="daad-card-titles">
                    <h4 class="daad-prog-name">{{ p.program }}</h4>
                    <span class="daad-uni-name">{{ p.uni }}</span>
                  </div>
                  <span class="daad-match" :class="matchClass(p.match)">{{ p.match }}%</span>
                </div>
                <div class="daad-card-body">
                  <div class="daad-meta-row">
                    <span class="daad-meta-item"><strong>Duration:</strong> {{ p.duration }}</span>
                    <span class="daad-meta-item"><strong>Fee:</strong> {{ p.fee }}</span>
                    <span class="daad-meta-item"><strong>Language:</strong> {{ p.lang }}</span>
                  </div>
                  <div class="daad-deadline-row"><strong>Deadline:</strong> {{ p.deadline }}</div>
                  <p class="daad-why">{{ p.why }}</p>
                </div>
                <div class="daad-card-footer">
                  <a :href="p.url" target="_blank" rel="noopener" class="daad-link">View Details &rarr;</a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- FULBRIGHT, CHEVENING, COMMONWEALTH TABS -->
      <div v-for="sch in ['fulbright', 'chevening', 'commonwealth']" :key="sch">
        <div v-if="activeProgSub === sch" class="sch-detail-card">
          <div v-if="schDetailLoading" class="modal-loading">
            <div class="loader"></div>
            <p>Loading details...</p>
          </div>
          <div v-else-if="schDetail[sch]" class="sch-detail-rendered" v-html="schDetail[sch]"></div>
          <div v-else class="sch-detail-fallback">
            <h2>{{ schTabLabels[sch] }}</h2>
            <div class="sch-detail-meta">
              <div class="sch-detail-stat"><span class="stat-lbl">Match Score</span><span class="stat-val" :class="matchClass(schMatch(sch))">{{ schMatch(sch) }}%</span></div>
              <div class="sch-detail-stat"><span class="stat-lbl">Category</span><span class="stat-val">{{ schCat(sch) }}</span></div>
              <div class="sch-detail-stat"><span class="stat-lbl">Programs</span><span class="stat-val">Varies by university</span></div>
            </div>
            <p style="color:#94a3b8;font-size:0.85rem;margin-top:0.8rem">Detailed guide content not yet available. Use the Comparison tab for side-by-side overview or visit the official website.</p>
          </div>
        </div>
      </div>

      <!-- Program Detail Modal -->
      <transition name="modal-fade">
        <div v-if="activeProgram" class="modal-overlay" @click.self="closeProgram">
          <div class="modal-container">
            <div class="modal-header">
              <div>
                <h2 class="modal-title">{{ activeProgram.title }}</h2>
                <p class="modal-subtitle" v-if="activeProgram.subtitle">{{ activeProgram.subtitle }}</p>
              </div>
              <button class="modal-close-btn" @click="closeProgram">&times;</button>
            </div>
            <div class="modal-body" v-if="programContent">
              <div class="modal-rendered" v-html="programContent.html"></div>
            </div>
            <div v-else-if="loadingProgram" class="modal-loading">
              <div class="loader"></div>
              <p>Loading program details...</p>
            </div>
            <div class="modal-footer">
              <button class="modal-back-btn" @click="closeProgram">Close</button>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- ==================== GUIDES TAB ==================== -->
    <div v-if="activeTab === 'guides'" class="tab-content">
      <div class="hub-filter-bar">
        <div class="filter-search">
          <span class="filter-search-icon">&#x1F50D;</span>
          <input type="text" v-model="guideFilter" placeholder="Search guides..." class="filter-input" />
        </div>
      </div>

      <div v-if="filteredGuides.length === 0" class="empty-state">
        <p>No guides match your search.</p>
      </div>
      <div v-else class="guide-grid">
        <div v-for="g in filteredGuides" :key="g.slug" class="guide-card"
          @click="openGuide(g)" :class="{ loading: loadingGuideSlug === g.slug }">
          <div class="guide-card-body">
            <div class="guide-icon">{{ guideIcon(g.slug) }}</div>
            <h3 class="guide-title">{{ g.title }}</h3>
            <p class="guide-meta">{{ g.read_time || '—' }} min read &middot; {{ (g.word_count || 0).toLocaleString() }} words</p>
          </div>
          <div class="guide-card-footer">
            <span class="guide-read-link">Read Guide &rarr;</span>
          </div>
        </div>
      </div>

      <!-- Guide Detail Modal -->
      <transition name="modal-fade">
        <div v-if="activeGuide" class="modal-overlay" @click.self="closeGuide">
          <div class="modal-container modal-wide">
            <div class="modal-header">
              <h2 class="modal-title">{{ activeGuide.title }}</h2>
              <button class="modal-close-btn" @click="closeGuide">&times;</button>
            </div>
            <div class="modal-body" v-if="guideContent">
              <div class="modal-rendered" v-html="guideContent.html"></div>
            </div>
            <div v-else-if="loadingGuide" class="modal-loading">
              <div class="loader"></div>
              <p>Loading guide...</p>
            </div>
            <div class="modal-footer">
              <button class="modal-back-btn" @click="closeGuide">Close</button>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- ==================== TIMELINE TAB ==================== -->
    <div v-if="activeTab === 'timeline'" class="tab-content">
      <div class="tl-filters">
        <button v-for="tl in timelineKeys" :key="tl.key" class="tl-filter-btn"
          :class="{ active: activeTimeline === tl.key }" @click="activeTimeline = tl.key">
          {{ tl.label }}
        </button>
      </div>

      <div v-if="timelineData.length === 0" class="empty-state">
        <p>No timeline data available.</p>
      </div>
      <div v-else class="tl-list">
        <div v-for="(item, idx) in timelineData" :key="idx" class="tl-item">
          <div class="tl-marker">
            <div class="tl-dot"></div>
            <div v-if="idx < timelineData.length - 1" class="tl-line"></div>
          </div>
          <div class="tl-card">
            <div class="tl-card-header">
              <span class="tl-date">{{ item.date }}</span>
              <h3 class="tl-title">{{ item.title }}</h3>
            </div>
            <p class="tl-desc">{{ item.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== COMPARISON TAB ==================== -->
    <div v-if="activeTab === 'compare'" class="tab-content">
      <p class="cmp-intro">Side-by-side comparison of your target fully funded scholarships</p>
      <div class="cmp-table-wrap">
        <table class="cmp-table">
          <thead>
            <tr>
              <th>Scholarship</th>
              <th>Monthly Stipend</th>
              <th>Duration</th>
              <th>Countries</th>
              <th>Deadline</th>
              <th>Fit</th>
              <th>Difficulty</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in comparisonData" :key="row.name">
              <td class="cmp-name">
                <strong>{{ row.name }}</strong>
                <span class="cmp-subname">{{ row.subname }}</span>
              </td>
              <td class="cmp-stipend">{{ row.stipend }}</td>
              <td>{{ row.duration }}</td>
              <td>{{ row.countries }}</td>
              <td class="cmp-deadline">{{ row.deadline }}</td>
              <td>
                <span class="cmp-stars">{{ row.fitStars }}</span>
              </td>
              <td>
                <span class="cmp-diff" :class="row.difficultyClass">{{ row.difficulty }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="cmp-strategy">
        <h3>Recommended Strategy</h3>
        <div class="cmp-strategy-steps">
          <div class="cmp-strategy-step" v-for="(step, idx) in strategySteps" :key="idx">
            <span class="step-num">{{ idx + 1 }}</span>
            <div>
              <strong>{{ step.title }}</strong>
              <p>{{ step.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ScholarshipMastery',
  data() {
    return {
      activeTab: 'overview',
      tabs: [
        { id: 'overview', label: 'Overview', icon: '\u{1F4CA}' },
        { id: 'programs', label: 'Programs', icon: '\u{1F4DA}', count: null },
        { id: 'guides', label: 'Guides', icon: '\u{1F4DD}', count: null },
        { id: 'timeline', label: 'Timeline', icon: '\u{1F4C5}' },
        { id: 'compare', label: 'Comparison', icon: '\u{2696}\uFE0F' },
      ],
      overview: { programs_count: 0, guides_count: 0 },
      programs: [],
      guides: [],
      dashboardData: null,
      scholarships: [],

      // Filters
      progFilter: '',
      guideFilter: '',

      // Program sub-tabs
      activeProgSub: 'all',
      programSubTabs: [
        { id: 'all', label: 'All' },
        { id: 'erasmus', label: 'Erasmus Mundus' },
        { id: 'mbzuai', label: 'MBZUAI' },
        { id: 'daad', label: 'DAAD' },
        { id: 'fulbright', label: 'Fulbright' },
        { id: 'chevening', label: 'Chevening' },
        { id: 'commonwealth', label: 'Commonwealth' },
      ],
      schDetail: {},
      schDetailLoading: false,
      schTabLabels: {
        mbzuai: 'MBZUAI — Mohamed Bin Zayed University of AI',
        daad: 'DAAD — German Government Scholarship',
        fulbright: 'Fulbright — US Government Scholarship',
        chevening: 'Chevening — UK Government Scholarship',
        commonwealth: 'Commonwealth — UK CSC Scholarship',
      },
      daadSteps: [
        {
          num: 1, icon: '\u{1F50D}',
          title: 'Identify Your DAAD Programme',
          desc: 'Choose between the main DAAD Study Scholarship (open to all fields) or a specialised programme like EPOS (development-related courses) or Helmut Schmidt (public policy).',
          tips: [
            'For Statistics + ML profile: apply for the "Study Scholarships - Master Studies for All Academic Disciplines" — it is open to all subjects',
            'EPOS requires applying to a specific list of development-related programmes — check if your target programme is on the EPOS list',
            'Helmut Schmidt is for Public Policy / Governance — less relevant for your ML focus',
          ],
        },
        {
          num: 2, icon: '\u{1F4CB}',
          title: 'Prepare Required Documents',
          desc: 'DAAD requires a comprehensive application dossier. Start gathering these 4-6 months before the deadline.',
          extra: [
            { label: 'CV', val: 'Europass format, max 3 pages, include publications if any' },
            { label: 'Motivation Letter', val: '2-3 pages explaining why Germany, why this programme, why you — connect to development goals for your home country (Bangladesh)' },
            { label: 'Letter of Recommendation', val: '2 academic references from professors — ideally one from Statistics dept, one from CS/ML' },
            { label: 'Academic Transcripts', val: 'Certified copies + translations (German/English) of your BSc Statistics marksheets and degree certificate' },
            { label: 'Language Proof', val: 'IELTS overall 6.5+ or TOEFL 88+ (DAAD minimum); German A1/A2 recommended but not mandatory for English programmes' },
            { label: 'Statement of Purpose', val: 'Detailed research/study plan — what you want to learn in Germany and how you will apply it back in Bangladesh' },
            { label: 'University Admission Letter', val: 'For Study Scholarship: conditional or unconditional admission from a German university. For EPOS: apply to the programme first, then use their confirmation' },
          ],
        },
        {
          num: 3, icon: '\u{1F3EB}',
          title: 'Secure University Admission',
          desc: 'DAAD Study Scholarships require admission to a German university. You must apply separately to universities and get an offer.',
          tips: [
            'Apply to 3-5 German universities (use the recommended list below)',
            'Most programmes start in Winter (Oct 2027) — apply to universities by May-Jul 2027',
            'Some programmes have their own DAAD EPOS status — applying to those gives you two chances: programme admission + DAAD funding',
            'If you have a conditional offer, DAAD can award the scholarship conditionally — you must meet conditions before the programme starts',
          ],
        },
        {
          num: 4, icon: '\u{1F4DD}',
          title: 'Write a Strong Research Proposal',
          desc: 'This is the most critical part of your DAAD application. Unlike Erasmus Mundus (which emphasises grades), DAAD cares most about your motivation, plan, and future impact.',
          tips: [
            'Structure: (1) Your academic background, (2) Why Germany & this programme, (3) Specific courses/professors you want to study with, (4) Your career plan, (5) How you will contribute to Bangladesh\'s development',
            'For ML focus: connect your study plan to Bangladesh\'s digital transformation, AI for social good, or data-driven policy making',
            'Reference specific professors and research groups at your target universities',
            'DAAD reviewers look for a clear "home-country connection" — show how you will use your degree to solve problems in Bangladesh',
          ],
        },
        {
          num: 5, icon: '\u{1F50D}',
          title: 'Find Academic References',
          desc: 'Two letters of recommendation from university professors. These must be on official letterhead, signed, and recent (within 6 months of deadline).',
          tips: [
            'Ask professors who know your research or project work best',
            'Provide them with your CV, draft motivation letter, and the list of programmes you are applying to',
            'Give them at least 4 weeks before the deadline',
            'Follow up with a reminder 2 weeks before, then 1 week before',
          ],
        },
        {
          num: 6, icon: '\u{1F4E8}',
          title: 'Submit DAAD Portal Application',
          desc: 'DAAD uses the DAAD Portal for submissions. Create an account early — do not wait until the last day.',
          tips: [
            'Portal opens ~6 weeks before the deadline',
            'Upload all documents as PDF (max 10 MB each, merged where possible)',
            'Double-check that certified translations are included for non-English/German documents',
            'Submit before 23:59 CET on the deadline day',
            'Print the confirmation page after submission',
          ],
        },
        {
          num: 7, icon: '\u{23F3}',
          title: 'Wait & Prepare for Interview',
          desc: 'The selection process takes 3-5 months. Shortlisted candidates may be invited for an interview (in-person at the German Embassy in Dhaka or via video call).',
          tips: [
            'Review your motivation letter and research proposal thoroughly before the interview',
            'Prepare answers about: why Germany, why this programme, your future plans, Bangladesh\'s development needs',
            'Mention specific German companies, research institutes (Max Planck, Fraunhofer, DFKI) you want to collaborate with',
            'Show awareness of German culture, language basics (even A1 helps), and current events',
          ],
        },
        {
          num: 8, icon: '\u{2708}\uFE0F',
          title: 'Visa & Pre-Departure',
          desc: 'After receiving the scholarship award letter, apply for a German student visa at the Embassy in Dhaka. DAAD scholars get expedited processing.',
          tips: [
            'DAAD provides a "Scholarship Award Letter" — use this for visa application (no need for blocked account)',
            'Apply for visa at least 8 weeks before the programme start date',
            'Book flights through the DAAD-recommended travel agency for the travel allowance',
            'Attend DAAD\'s pre-departure orientation (usually online in Aug-Sep)',
          ],
        },
      ],

      daadScholarships: [
        {
          name: 'Study Scholarships — Master Studies for All Academic Disciplines',
          stipend: '\u20AC992/mo + \u20AC234 insurance + travel',
          duration: '12-36 months (full Master\'s)',
          deadline: 'August-September 2027 (exact TBD)',
          desc: 'The main DAAD scholarship for Master\'s in any subject. Covers full living costs, health insurance, and a travel allowance. You can study at ANY German public university.',
          fit: 'high',
          fitLabel: 'Best Fit',
          eligible: 'Any Master\'s programme at a German public university — ideal for MSc Data Science, AI, Statistics programmes',
        },
        {
          name: 'EPOS — Development-Related Postgraduate Courses',
          stipend: '\u20AC992/mo + \u20AC234 insurance + family + travel',
          duration: '12-36 months (specific courses only)',
          deadline: 'Varies by course (Aug-Oct)',
          desc: 'Fully funded scholarships for specific development-related Master\'s programmes. Requires 2 years of professional experience. Strong home-country development focus.',
          fit: 'medium',
          fitLabel: 'Good Fit',
          eligible: 'Specific programmes on the EPOS list (e.g., development economics, public health, environmental science — limited ML options)',
        },
        {
          name: 'Helmut Schmidt Programme',
          stipend: '\u20AC992/mo + \u20AC234 insurance + travel',
          duration: '12-24 months',
          deadline: 'June-July 2027',
          desc: 'For future leaders in public policy, governance, and administration. Target: professionals from developing countries who will work in government/NGOs.',
          fit: 'low',
          fitLabel: 'Lower Fit',
          eligible: 'Master\'s in Public Policy, Governance, Administration, Law — less relevant for ML/Data Science focus',
        },
        {
          name: 'DAAD WISE — Working Internships in Science & Engineering',
          stipend: '\u20AC992/mo + travel',
          duration: '3-6 months (summer internship)',
          deadline: 'November-December 2027',
          desc: 'Summer research internship programme for students from developing countries. Spend 3-6 months at a German research institute working on a project. Apply during your Bachelor\'s or gap year.',
          fit: 'high',
          fitLabel: 'Best Fit',
          eligible: 'Research internships at German universities/institutes — great for ML research experience before Master\'s',
        },
        {
          name: 'DAAD Research Grants — Short-Term',
          stipend: '\u20AC992/mo + travel + research allowance',
          duration: '1-6 months',
          deadline: 'May / November 2027',
          desc: 'Short-term research stays for PhD students and postdocs. Not applicable for Master\'s, but plan this for your PhD stage later.',
          fit: 'low',
          fitLabel: 'Future Use',
          eligible: 'For doctoral candidates and postdoctoral researchers — bookmark for PhD phase',
        },
      ],

      daadPrograms: [
        { cat: 'Data Science, AI & ML', uni: 'LMU Munich', program: 'MSc Statistics & Data Science', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: 'Check website', why: 'PERFECT match — Statistics + Data Science at Germany\'s top university', url: 'https://www.lmu.de/en/study/all-degrees-and-programs/degree-programs-a-to-z/statistics-and-data-science-master/', match: 97 },
        { cat: 'Data Science, AI & ML', uni: 'TU Dortmund University', program: 'MSc Data Science', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: '15 Jul (WS) / 15 Jan (SS)', why: 'Joint Statistics, CS & Math depts — designed for your Statistics background', url: 'https://www2.daad.de/deutschland/studienangebote/international-programmes/en/detail/8951/', match: 95 },
        { cat: 'Data Science, AI & ML', uni: 'Saarland University', program: 'MSc Data Science & AI', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: '15 May', why: 'DFKI & Max Planck — world-class AI research campus', url: 'https://www2.daad.de/deutschland/studienangebote/international-programmes/en/detail/6296/', match: 93 },
        { cat: 'Data Science, AI & ML', uni: 'University of Oldenburg', program: 'MSc Data Science & ML', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: '30 Apr (non-EU)', why: 'Theoretical ML foundations + 3 specialisations — small cohort (30/yr)', url: 'https://www2.daad.de/deutschland/studienangebote/international-programmes/en/detail/9906/', match: 92 },
        { cat: 'Economics & Business Analytics', uni: 'University of Cologne', program: 'MSc Business Analytics & Econometrics', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: '15 Jun', why: 'Statistics + econometrics + ML with Python/R — excellent alternative path', url: 'https://www2.daad.de/deutschland/studienangebote/international-programmes/en/detail/8423/', match: 92 },
        { cat: 'Data Science, AI & ML', uni: 'University of Trier', program: 'MSc Data Science', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: 'Check website', why: 'Multidisciplinary — CS + Math + Statistics with double degree options', url: 'https://www2.daad.de/deutschland/studienangebote/international-programmes/en/detail/5351/', match: 90 },
        { cat: 'Data Science, AI & ML', uni: 'TU Darmstadt', program: 'MSc AI & Machine Learning', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: '15 Jul', why: 'Top AI hub — hessian.AI + DFKI — world-class faculty', url: 'https://www2.daad.de/deutschland/studienangebote/international-programmes/en/detail/4258/', match: 88 },
        { cat: 'Data Science, AI & ML', uni: 'FAU Erlangen-Nuremberg', program: 'MSc Artificial Intelligence', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: '31 May', why: 'Broad AI curriculum — oral exam possible for non-CS graduates', url: 'https://www2.daad.de/deutschland/studienangebote/international-programmes/en/detail/7657/', match: 85 },
        { cat: 'Data Science, AI & ML', uni: 'Free University Berlin', program: 'MSc Data Science', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: '31 May', why: 'Requires 20CP Math + 10CP CS — your Statistics easily covers math req', url: 'https://www.fu-berlin.de/en/studium/angebot/master/data-science/index.html', match: 83 },
        { cat: 'Automotive & Autonomous Systems', uni: 'TU Chemnitz', program: 'MSc Automotive Software Engineering', duration: '4 semesters', fee: 'Free', lang: 'English', deadline: '20 Sep', why: 'ML + software for autonomous vehicles — bridges AI to automotive', url: 'https://www.tu-chemnitz.de/studium/studienangebot/automotive_software_engineering_master.php', match: 82 },
      ],

      // Program detail
      activeProgram: null,
      programContent: null,
      loadingProgram: false,
      loadingSlug: null,

      // Guide detail
      activeGuide: null,
      guideContent: null,
      loadingGuide: false,
      loadingGuideSlug: null,

      // Timeline
      activeTimeline: 'all',
      timelineData: [],

      comparisonData: [],
      strategySteps: [],
    }
  },
  computed: {
    allPrograms() {
      const map = {}
      // Add markdown programs
      for (const p of this.programs) {
        const key = (p.code || p.slug).toLowerCase()
        map[key] = {
          ...p,
          hasGuide: true,
          category: p.category || 'Erasmus Mundus',
          match: this.dashboardProgMap[key]?.match || null,
        }
      }
      // Add dashboard-only programs (non-Erasmus: MBZUAI, DAAD, Fulbright, Chevening, Commonwealth)
      if (this.dashboardData && this.dashboardData.programs) {
        for (const dp of this.dashboardData.programs) {
          const key = dp.id.toLowerCase()
          // Skip Erasmus — all 7 are already loaded with full detail from markdown files
          if (!map[key] && dp.category !== 'Erasmus Mundus') {
            map[key] = {
              slug: dp.id,
              title: dp.full_name || dp.name,
              code: dp.name,
              subtitle: '',
              category: dp.category || 'Scholarship',
              match: dp.match,
              hasGuide: false,
              filename: null,
            }
          }
        }
      }
      return Object.values(map)
    },
    filteredPrograms() {
      let list = [...this.allPrograms]
      const q = this.progFilter.toLowerCase()
      if (!q) return list
      return list.filter(p =>
        p.title.toLowerCase().includes(q) ||
        p.code.toLowerCase().includes(q) ||
        (p.subtitle || '').toLowerCase().includes(q)
      )
    },
    erasmusPrograms() {
      return this.allPrograms.filter(p =>
        (p.category || '').toLowerCase().includes('erasmus')
      )
    },
    filteredGuides() {
      const q = this.guideFilter.toLowerCase()
      if (!q) return this.guides
      return this.guides.filter(g => g.title.toLowerCase().includes(q) || g.slug.toLowerCase().includes(q))
    },
    timelineKeys() {
      const keys = [
        { key: 'all', label: 'All Scholarships' },
        { key: 'erasmus', label: 'Erasmus Mundus' },
        { key: 'mbzuai', label: 'MBZUAI' },
        { key: 'daad', label: 'DAAD' },
        { key: 'fulbright', label: 'Fulbright' },
        { key: 'chevening', label: 'Chevening' },
        { key: 'commonwealth', label: 'Commonwealth' },
      ]
      if (!this.dashboardData || !this.dashboardData.timelines) return keys
      return keys.filter(k => this.dashboardData.timelines[k.key])
    },
    dashboardProgMap() {
      const map = {}
      if (this.dashboardData && this.dashboardData.programs) {
        for (const p of this.dashboardData.programs) {
          map[p.id] = p
          // Alias: map common names for match score lookups
          const nameLower = (p.name || '').toLowerCase()
          if (nameLower) map[nameLower] = p
        }
      }
      return map
    },
  },
  mounted() {
    this.fetchOverview()
    this.fetchPrograms()
    this.fetchGuides()
    this.fetchDashboard()
    this.fetchMastery()
  },
  methods: {
    async fetchOverview() {
      try {
        const res = await fetch('/api/mastery-content/overview')
        const data = await res.json()
        this.overview = data
        this.tabs.find(t => t.id === 'programs').count = data.programs_count
        this.tabs.find(t => t.id === 'guides').count = data.guides_count
      } catch (e) {
        console.error('Failed to fetch overview:', e)
      }
    },
    async fetchPrograms() {
      try {
        const res = await fetch('/api/mastery-content/programs')
        const data = await res.json()
        // Detect category from program title/content
        this.programs = (data.programs || []).map(p => {
          const lower = (p.title + ' ' + p.subtitle).toLowerCase()
          let category = 'Scholarship'
          if (lower.includes('erasmus') || lower.includes('emai') || lower.includes('deai') || lower.includes('ediss') || lower.includes('intermaths') || lower.includes('aiss') || lower.includes('maths-disc') || lower.includes('cosse')) {
            category = 'Erasmus Mundus'
          } else if (lower.includes('mbzuai')) {
            category = 'Fellowship'
          } else if (lower.includes('daad') || lower.includes('fulbright') || lower.includes('chevening') || lower.includes('commonwealth')) {
            category = 'Government'
          }
          return { ...p, category }
        })
      } catch (e) {
        console.error('Failed to fetch programs:', e)
      }
    },
    async fetchGuides() {
      try {
        const res = await fetch('/api/mastery-content/guides')
        const data = await res.json()
        this.guides = data.guides || []
      } catch (e) {
        console.error('Failed to fetch guides:', e)
      }
    },
    async fetchDashboard() {
      try {
        const res = await fetch('/api/mastery-content/dashboard')
        const data = await res.json()
        this.dashboardData = data
        if (data.timelines && data.timelines.all) {
          this.timelineData = data.timelines.all
        }
        this.buildComparison(data)
      } catch (e) {
        console.error('Failed to fetch dashboard:', e)
      }
    },
    async fetchMastery() {
      try {
        const res = await fetch('/api/mastery')
        const data = await res.json()
        this.scholarships = data || []
      } catch (e) {
        console.error('Failed to fetch mastery:', e)
      }
    },
    buildComparison(data) {
      this.comparisonData = [
        { name: 'Erasmus Mundus', subname: 'Joint Master\'s', stipend: '\u20AC1,400/mo', duration: '2 years', countries: 'EU (multiple)', deadline: 'Dec 2026 \u2013 Feb 2027', fit: 96, fitStars: '\u2605\u2605\u2605\u2605\u2605', difficulty: 'Very High', difficultyClass: 'diff-vhigh' },
        { name: 'MBZUAI', subname: 'AI University, UAE', stipend: '~ \u20AC3,900/mo', duration: '2 years', countries: 'UAE', deadline: 'Rolling', fit: 95, fitStars: '\u2605\u2605\u2605\u2605\u2605', difficulty: 'Medium', difficultyClass: 'diff-med' },
        { name: 'DAAD', subname: 'German Government', stipend: '\u20AC934/mo', duration: '1\u20132 years', countries: 'Germany', deadline: 'Aug\u2013Sep 2027', fit: 85, fitStars: '\u2605\u2605\u2605\u2605', difficulty: 'High', difficultyClass: 'diff-high' },
        { name: 'Fulbright', subname: 'US Government', stipend: '$1,800\u20132,500/mo', duration: '1\u20132 years', countries: 'USA', deadline: '~11 Jul 2026', fit: 80, fitStars: '\u2605\u2605\u2605\u2605', difficulty: 'Very High', difficultyClass: 'diff-vhigh' },
        { name: 'Chevening', subname: 'UK Government', stipend: '\u00A31,378\u20131,690/mo', duration: '1 year', countries: 'UK', deadline: 'Oct\u2013Nov 2026', fit: 75, fitStars: '\u2605\u2605\u2605', difficulty: 'Very High', difficultyClass: 'diff-vhigh' },
        { name: 'Commonwealth', subname: 'UK CSC', stipend: 'Full + stipend', duration: '1\u20132 years', countries: 'UK', deadline: 'Oct 2026', fit: 70, fitStars: '\u2605\u2605\u2605', difficulty: 'High', difficultyClass: 'diff-high' },
      ]
      this.strategySteps = [
        { title: 'MBZUAI \u2014 Apply NOW', desc: 'Rolling admissions, highest stipend (~\u20AC3,900/mo). Apply today for best chances.' },
        { title: 'Erasmus Mundus \u2014 Oct 2026 \u2013 Feb 2027', desc: 'Choose 3 programs max. EMAI (AI), InterMaths (Statistics), DEAI (Data Eng) are your best fits.' },
        { title: 'DAAD \u2014 Aug\u2013Sep 2027', desc: 'Backup option with later deadline. Tuition-free German universities + \u20AC934/mo stipend.' },
        { title: 'Fulbright & Chevening', desc: 'Apply if you meet work experience requirements (2+ years for Fulbright, 2,800 hrs for Chevening).' },
      ]
    },
    badgeClass(p) {
      if (p.category === 'Erasmus Mundus') return 'badge-erasmus'
      if (p.category === 'Fellowship') return 'badge-fellowship'
      if (p.category === 'Government') return 'badge-government'
      return 'badge-default'
    },
    matchClass(match) {
      if (match >= 90) return 'match-high'
      if (match >= 70) return 'match-medium'
      return 'match-low'
    },
    guideIcon(slug) {
      const icons = {
        'master-timeline': '\u{1F4C5}',
        'step-by-step-application-guide': '\u{1F4CB}',
        'document-checklist': '\u2705',
        'motivation-letter-template': '\u270D\uFE0F',
        'motivation-letter-EMAI': '\u{1F4DD}',
      }
      return icons[slug] || '\u{1F4D6}'
    },
    schMatch(id) {
      if (!this.dashboardData || !this.dashboardData.programs) return null
      const found = this.dashboardData.programs.find(p => p.id === id)
      return found ? found.match : null
    },
    schCat(id) {
      if (!this.dashboardData || !this.dashboardData.programs) return ''
      const found = this.dashboardData.programs.find(p => p.id === id)
      return found ? found.category : ''
    },
    async openProgram(p) {
      this.activeProgram = p
      this.loadingProgram = true
      this.loadingSlug = p.slug
      this.programContent = null
      try {
        const res = await fetch(`/api/mastery-content/programs/${p.slug}`)
        const data = await res.json()
        this.programContent = data
      } catch (e) {
        console.error('Failed to load program:', e)
      }
      this.loadingProgram = false
      this.loadingSlug = null
    },
    closeProgram() {
      this.activeProgram = null
      this.programContent = null
    },
    async openGuide(g) {
      this.activeGuide = g
      this.loadingGuide = true
      this.loadingGuideSlug = g.slug
      this.guideContent = null
      try {
        const res = await fetch(`/api/mastery-content/guides/${g.slug}`)
        const data = await res.json()
        this.guideContent = data
      } catch (e) {
        console.error('Failed to load guide:', e)
      }
      this.loadingGuide = false
      this.loadingGuideSlug = null
    },
    closeGuide() {
      this.activeGuide = null
      this.guideContent = null
    },
  },
  watch: {
    activeTimeline(val) {
      if (this.dashboardData && this.dashboardData.timelines && this.dashboardData.timelines[val]) {
        this.timelineData = this.dashboardData.timelines[val]
      } else {
        this.timelineData = []
      }
    },
    async activeProgSub(val) {
      const individual = ['mbzuai', 'fulbright', 'chevening', 'commonwealth']
      if (!individual.includes(val)) return
      if (this.schDetail[val]) return
      this.schDetailLoading = true
      try {
        // Load the "other scholarships" detail for this section
        const res = await fetch('/api/mastery-content/programs/08-other-scholarships')
        const data = await res.json()
        // Extract just the relevant section for this scholarship
        const html = data.html || ''
        const sections = html.split('<hr>')
        const idx = individual.indexOf(val)
        // Find the matching section by looking for the scholarship name in heading
        const labels = ['MBZUAI', 'Fulbright', 'Chevening', 'Commonwealth']
        let found = ''
        for (const sec of sections) {
          if (sec.includes(labels[idx])) {
            found = sec
            break
          }
        }
        this.schDetail = { ...this.schDetail, [val]: found || html }
      } catch (e) {
        console.error('Failed to load scholarship detail:', e)
        this.schDetail = { ...this.schDetail, [val]: '' }
      }
      this.schDetailLoading = false
    },
  },
}
</script>

<style scoped>
.mastery-hub {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* ===== HERO ===== */
.hub-hero {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(59, 130, 246, 0.04) 50%, rgba(16, 185, 129, 0.04) 100%);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 1.8rem 2rem;
  position: relative;
  overflow: hidden;
}
.hub-hero::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.06) 0%, transparent 70%);
  border-radius: 50%;
}
.hero-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
  position: relative;
  z-index: 1;
}
.hero-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1.6rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.03em;
  margin-bottom: 0.2rem;
}
.hero-sub {
  font-size: 0.85rem;
  color: #94a3b8;
}
.hero-metrics {
  display: flex;
  gap: 1.5rem;
}
.hero-metric {
  text-align: center;
}
.metric-val {
  display: block;
  font-family: 'Outfit', sans-serif;
  font-size: 1.8rem;
  font-weight: 800;
  background: linear-gradient(135deg, #60a5fa, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1.2;
}
.metric-lbl {
  font-size: 0.65rem;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.04em;
  font-weight: 600;
}

/* ===== NAV ===== */
.hub-nav {
  display: flex;
  gap: 0.25rem;
  background: rgba(30, 41, 59, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  padding: 0.35rem;
}
.hub-nav-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.6rem 0.8rem;
  background: none;
  border: none;
  border-radius: 8px;
  color: #64748b;
  font-family: 'Inter', sans-serif;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.hub-nav-btn:hover {
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.03);
}
.hub-nav-btn.active {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.15);
}
.nav-icon { font-size: 1rem; }
.nav-count {
  background: rgba(255, 255, 255, 0.06);
  font-size: 0.65rem;
  padding: 0.05rem 0.4rem;
  border-radius: 8px;
  color: #94a3b8;
}

/* ===== TABS CONTENT ===== */
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  border: 1px dashed rgba(255, 255, 255, 0.06);
  border-radius: 12px;
}

/* ===== OVERVIEW ===== */
.ov-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
}
.ov-card {
  background: rgba(30, 41, 59, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.ov-card:hover {
  background: rgba(30, 41, 59, 0.45);
  border-color: rgba(99, 102, 241, 0.25);
  transform: translateY(-2px);
}
.ov-card-icon {
  font-size: 1.8rem;
  margin-bottom: 0.6rem;
}
.ov-card h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 0.4rem;
}
.ov-card p {
  font-size: 0.82rem;
  color: #94a3b8;
  line-height: 1.5;
  margin-bottom: 0.8rem;
}
.ov-cta {
  font-size: 0.75rem;
  font-weight: 700;
  color: #60a5fa;
}
.ov-card:hover .ov-cta {
  color: #93c5fd;
}
.ov-section {
  background: rgba(30, 41, 59, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  padding: 1.5rem;
}
.ov-section-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 1rem;
}
.ov-fit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 0.8rem;
}
.ov-fit-item {
  padding: 0.6rem 0.8rem;
  background: rgba(15, 23, 42, 0.3);
  border-radius: 8px;
  border-left: 3px solid rgba(99, 102, 241, 0.3);
}
.fit-label {
  display: block;
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 700;
  color: #818cf8;
  letter-spacing: 0.04em;
  margin-bottom: 0.15rem;
}
.fit-val {
  font-size: 0.85rem;
  color: #cbd5e1;
  line-height: 1.4;
}
.highlight-val {
  color: #34d399;
}

/* ===== FILTER BAR ===== */
.hub-filter-bar {
  display: flex;
  gap: 0.8rem;
  align-items: center;
}
.filter-search {
  position: relative;
  flex: 1;
}
.filter-search-icon {
  position: absolute;
  left: 0.9rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.85rem;
  color: #64748b;
}
.filter-input {
  width: 100%;
  padding: 0.65rem 1rem 0.65rem 2.4rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  color: #e2e8f0;
  font-family: 'Inter', sans-serif;
  font-size: 0.85rem;
  transition: all 0.2s;
}
.filter-input:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.08);
  background: rgba(255, 255, 255, 0.04);
}
.filter-select {
  padding: 0.65rem 1rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  color: #cbd5e1;
  font-family: 'Inter', sans-serif;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}
.filter-select:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.4);
}

/* ===== PROGRAMS GRID ===== */
.prog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}
.prog-card {
  background: rgba(30, 41, 59, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  padding: 1.3rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
}
.prog-card:hover {
  background: rgba(30, 41, 59, 0.45);
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}
.prog-card.loading {
  opacity: 0.6;
  pointer-events: none;
}
.prog-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
}
.prog-badge {
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}
.badge-erasmus { background: rgba(99, 102, 241, 0.12); color: #818cf8; }
.badge-fellowship { background: rgba(16, 185, 129, 0.12); color: #34d399; }
.badge-government { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
.badge-default { background: rgba(255, 255, 255, 0.04); color: #94a3b8; }

.prog-match-pill {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.45rem;
  border-radius: 6px;
}
.prog-match-pill.match-high { background: rgba(16, 185, 129, 0.12); color: #34d399; }
.prog-match-pill.match-medium { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
.prog-match-pill.match-low { background: rgba(99, 102, 241, 0.12); color: #a5b4fc; }

.prog-card-title {
  font-family: 'Outfit', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.3;
  margin-bottom: 0.3rem;
}
.prog-card-sub {
  font-size: 0.75rem;
  color: #64748b;
  margin-bottom: auto;
}
.prog-card-footer {
  margin-top: 0.8rem;
  padding-top: 0.6rem;
  border-top: 1px solid rgba(255, 255, 255, 0.03);
}
.prog-read-link {
  font-size: 0.75rem;
  font-weight: 700;
  color: #60a5fa;
}

/* ===== GUIDES GRID ===== */
.guide-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}
.guide-card {
  background: rgba(30, 41, 59, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  padding: 1.3rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
}
.guide-card:hover {
  background: rgba(30, 41, 59, 0.45);
  border-color: rgba(99, 102, 241, 0.25);
  transform: translateY(-2px);
}
.guide-card.loading {
  opacity: 0.6;
  pointer-events: none;
}
.guide-icon {
  font-size: 2rem;
  margin-bottom: 0.6rem;
}
.guide-title {
  font-family: 'Outfit', sans-serif;
  font-size: 0.9rem;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.3;
  margin-bottom: 0.4rem;
}
.guide-meta {
  font-size: 0.75rem;
  color: #64748b;
  margin-bottom: auto;
}
.guide-card-footer {
  margin-top: 0.8rem;
  padding-top: 0.6rem;
  border-top: 1px solid rgba(255, 255, 255, 0.03);
}
.guide-read-link {
  font-size: 0.75rem;
  font-weight: 700;
  color: #60a5fa;
}

/* ===== MODAL ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(9, 12, 18, 0.88);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}
.modal-container {
  background: #0f1724;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 18px;
  width: 100%;
  max-width: 800px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
}
.modal-wide {
  max-width: 960px;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.5rem 1.8rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  gap: 1rem;
}
.modal-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: #f1f5f9;
}
.modal-subtitle {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 0.2rem;
}
.modal-close-btn {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #64748b;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  font-size: 1.3rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.modal-close-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.8rem;
}
.modal-rendered {
  font-size: 0.88rem;
  line-height: 1.7;
  color: #cbd5e1;
}
.modal-rendered h1 { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; margin: 1.2rem 0 0.6rem; }
.modal-rendered h2 { font-size: 1.2rem; font-weight: 700; color: #e2e8f0; margin: 1rem 0 0.5rem; padding-bottom: 0.3rem; border-bottom: 1px solid rgba(255,255,255,0.04); }
.modal-rendered h3 { font-size: 1rem; font-weight: 700; color: #e2e8f0; margin: 0.8rem 0 0.4rem; }
.modal-rendered h4 { font-size: 0.9rem; font-weight: 700; color: #94a3b8; margin: 0.7rem 0 0.3rem; }
.modal-rendered p { margin: 0.5rem 0; }
.modal-rendered strong { color: #f1f5f9; }
.modal-rendered a { color: #60a5fa; text-decoration: underline; }
.modal-rendered a:hover { color: #93c5fd; }
.modal-rendered code { background: rgba(255,255,255,0.04); color: #f472b6; padding: 0.1rem 0.35rem; border-radius: 3px; font-size: 0.82rem; }
.modal-rendered pre { background: rgba(15,23,42,0.5); border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; padding: 1rem; overflow-x: auto; margin: 0.8rem 0; }
.modal-rendered pre code { background: none; padding: 0; font-size: 0.82rem; color: #cbd5e1; }
.modal-rendered ul { padding-left: 1.2rem; margin: 0.4rem 0; }
.modal-rendered ul li { margin: 0.2rem 0; color: #94a3b8; }
.modal-rendered ul li::marker { color: #6366f1; }
.modal-rendered blockquote { border-left: 3px solid #3b82f6; margin: 0.6rem 0; padding: 0.4rem 1rem; background: rgba(15,23,42,0.3); border-radius: 0 6px 6px 0; color: #94a3b8; }
.modal-rendered hr { border: none; border-top: 1px solid rgba(255,255,255,0.04); margin: 1rem 0; }
.modal-rendered input[type=checkbox] { accent-color: #3b82f6; margin-right: 0.3rem; }
.modal-rendered .mastery-table-wrap { overflow-x: auto; margin: 0.8rem 0; border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; }
.modal-rendered .mastery-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.modal-rendered .mastery-table td { padding: 0.5rem 0.8rem; border-bottom: 1px solid rgba(255,255,255,0.03); color: #cbd5e1; }
.modal-rendered .mastery-table tr:last-child td { border-bottom: none; }
.modal-rendered .mastery-table tr:hover td { background: rgba(255,255,255,0.02); }
.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  color: #64748b;
  gap: 0.8rem;
}
.loader {
  border: 3px solid rgba(255,255,255,0.04);
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.modal-footer {
  padding: 1rem 1.8rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  display: flex;
  justify-content: flex-end;
}
.modal-back-btn {
  padding: 0.5rem 1.2rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #94a3b8;
  border-radius: 8px;
  font-family: 'Inter', sans-serif;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.modal-back-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.25s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}

/* ===== TIMELINE ===== */
.tl-filters {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}
.tl-filter-btn {
  padding: 0.4rem 0.9rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  color: #64748b;
  font-family: 'Inter', sans-serif;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.tl-filter-btn:hover {
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.04);
}
.tl-filter-btn.active {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}
.tl-list {
  position: relative;
  padding-left: 2rem;
}
.tl-item {
  display: flex;
  gap: 1rem;
  position: relative;
}
.tl-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
  margin-left: -2rem;
}
.tl-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid rgba(59, 130, 246, 0.3);
  flex-shrink: 0;
  z-index: 1;
}
.tl-line {
  width: 2px;
  flex: 1;
  min-height: 20px;
  background: rgba(59, 130, 246, 0.1);
}
.tl-card {
  flex: 1;
  background: rgba(30, 41, 59, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  margin-bottom: 1rem;
  transition: all 0.2s;
}
.tl-card:hover {
  background: rgba(30, 41, 59, 0.3);
  border-color: rgba(59, 130, 246, 0.1);
}
.tl-card-header {
  display: flex;
  align-items: baseline;
  gap: 0.8rem;
  margin-bottom: 0.4rem;
}
.tl-date {
  font-size: 0.7rem;
  font-weight: 700;
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.08);
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  white-space: nowrap;
}
.tl-title {
  font-family: 'Outfit', sans-serif;
  font-size: 0.9rem;
  font-weight: 700;
  color: #e2e8f0;
}
.tl-desc {
  font-size: 0.82rem;
  color: #94a3b8;
  line-height: 1.5;
}

/* ===== COMPARISON ===== */
.cmp-intro {
  font-size: 0.85rem;
  color: #64748b;
}
.cmp-table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
}
.cmp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.cmp-table th {
  padding: 0.7rem 1rem;
  background: rgba(15, 23, 42, 0.4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 0.7rem;
  text-transform: uppercase;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.04em;
  text-align: left;
}
.cmp-table td {
  padding: 0.7rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  color: #cbd5e1;
}
.cmp-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}
.cmp-table tr:last-child td {
  border-bottom: none;
}
.cmp-name {
  display: flex;
  flex-direction: column;
}
.cmp-name strong {
  color: #e2e8f0;
  font-family: 'Outfit', sans-serif;
  font-size: 0.9rem;
}
.cmp-subname {
  font-size: 0.7rem;
  color: #64748b;
}
.cmp-stipend {
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  color: #34d399;
}
.cmp-deadline {
  color: #f87171;
}
.cmp-stars {
  color: #fbbf24;
  letter-spacing: 0.1em;
}
.cmp-diff {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
}
.diff-vhigh { background: rgba(239, 68, 68, 0.12); color: #f87171; }
.diff-high { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
.diff-med { background: rgba(16, 185, 129, 0.12); color: #34d399; }

.cmp-strategy {
  background: rgba(30, 41, 59, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  padding: 1.5rem;
}
.cmp-strategy h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 1rem;
}
.cmp-strategy-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.8rem;
}
.cmp-strategy-step {
  display: flex;
  gap: 0.8rem;
  align-items: flex-start;
  padding: 0.8rem;
  background: rgba(15, 23, 42, 0.3);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.03);
}
.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 800;
  flex-shrink: 0;
}
.cmp-strategy-step strong {
  display: block;
  font-size: 0.82rem;
  color: #e2e8f0;
  margin-bottom: 0.2rem;
}
.cmp-strategy-step p {
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.4;
}

/* ===== PROGRAM SUB-TABS ===== */
.prog-subs {
  display: flex;
  gap: 0.2rem;
  margin-bottom: 1rem;
  background: rgba(30, 41, 59, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  padding: 0.3rem;
  flex-wrap: wrap;
}
.prog-sub-btn {
  padding: 0.4rem 0.8rem;
  background: none;
  border: none;
  border-radius: 6px;
  color: #64748b;
  font-family: 'Inter', sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.prog-sub-btn:hover {
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.03);
}
.prog-sub-btn.active {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.15);
}

/* ===== SCHOLARSHIP DETAIL CARD ===== */
.sch-detail-card {
  background: rgba(30, 41, 59, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  padding: 1.5rem;
}
.sch-detail-rendered {
  font-size: 0.88rem;
  line-height: 1.7;
  color: #cbd5e1;
}
.sch-detail-rendered h1,
.sch-detail-rendered h2,
.sch-detail-rendered h3,
.sch-detail-rendered h4 {
  font-family: 'Outfit', sans-serif;
  color: #f1f5f9;
  margin: 1rem 0 0.5rem;
}
.sch-detail-rendered h1 { font-size: 1.3rem; font-weight: 700; }
.sch-detail-rendered h2 { font-size: 1.1rem; font-weight: 700; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 0.3rem; }
.sch-detail-rendered h3 { font-size: 1rem; font-weight: 600; }
.sch-detail-rendered strong { color: #f1f5f9; }
.sch-detail-rendered a { color: #60a5fa; text-decoration: underline; }
.sch-detail-rendered table { width: 100%; border-collapse: collapse; margin: 0.6rem 0; font-size: 0.8rem; }
.sch-detail-rendered td { padding: 0.4rem 0.6rem; border-bottom: 1px solid rgba(255,255,255,0.03); color: #cbd5e1; }
.sch-detail-rendered ul { padding-left: 1.2rem; }
.sch-detail-rendered li { color: #94a3b8; margin: 0.2rem 0; }
.sch-detail-rendered hr { border: none; border-top: 1px solid rgba(255,255,255,0.04); margin: 1rem 0; }
.sch-detail-fallback h2 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 1rem;
}

/* ===== DAAD PROGRAM CARDS ===== */
.daad-grid {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.daad-card {
  background: rgba(15, 23, 42, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  padding: 0.9rem 1rem;
  transition: border-color 0.2s;
}
.daad-card:hover {
  border-color: rgba(96, 165, 250, 0.15);
}
.daad-card-header {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 0.5rem;
}
.daad-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 800;
  flex-shrink: 0;
}
.daad-card-titles {
  flex: 1;
  min-width: 0;
}
.daad-prog-name {
  font-family: 'Outfit', sans-serif;
  font-size: 0.88rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
  line-height: 1.3;
}
.daad-uni-name {
  font-size: 0.72rem;
  color: #64748b;
}
.daad-match {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}
.daad-card-body {
  font-size: 0.78rem;
  color: #94a3b8;
}
.daad-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem 1rem;
  margin-bottom: 0.25rem;
}
.daad-meta-item strong {
  color: #64748b;
  font-weight: 600;
}
.daad-deadline-row {
  font-size: 0.76rem;
  color: #f87171;
  margin-bottom: 0.35rem;
}
.daad-deadline-row strong {
  color: #64748b;
  font-weight: 600;
}
.daad-why {
  font-size: 0.75rem;
  color: #94a3b8;
  line-height: 1.4;
  margin: 0;
}
.daad-card-footer {
  margin-top: 0.4rem;
  padding-top: 0.4rem;
  border-top: 1px solid rgba(255, 255, 255, 0.03);
}
.daad-link {
  font-size: 0.72rem;
  color: #60a5fa;
  text-decoration: none;
  font-weight: 600;
}
.daad-link:hover {
  text-decoration: underline;
}
/* ===== DAAD SECTION STYLES ===== */
.daad-section {
  background: rgba(15, 23, 42, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  padding: 1.2rem;
  margin-bottom: 1.5rem;
}
.daad-section-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 0.2rem 0;
}
.daad-grid {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.daad-steps {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.daad-step {
  display: flex;
  gap: 0.8rem;
  background: rgba(15, 23, 42, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  padding: 0.9rem;
  transition: border-color 0.2s;
}
.daad-step:hover {
  border-color: rgba(96, 165, 250, 0.12);
}
.daad-step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 800;
  flex-shrink: 0;
  align-self: flex-start;
}
.daad-step-body {
  display: flex;
  gap: 0.6rem;
  flex: 1;
  min-width: 0;
}
.daad-step-icon {
  font-size: 1.3rem;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 0.1rem;
}
.daad-step-content {
  flex: 1;
  min-width: 0;
}
.daad-step-title {
  font-family: 'Outfit', sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 0.2rem 0;
}
.daad-step-desc {
  font-size: 0.75rem;
  color: #94a3b8;
  margin: 0 0 0.3rem 0;
  line-height: 1.4;
}
.daad-step-tips {
  margin: 0;
  padding: 0 0 0 1rem;
  list-style: none;
}
.daad-step-tips li {
  font-size: 0.72rem;
  color: #94a3b8;
  line-height: 1.4;
  margin-bottom: 0.15rem;
  position: relative;
  padding-left: 0.8rem;
}
.daad-step-tips li::before {
  content: '\2713';
  position: absolute;
  left: 0;
  color: #34d399;
  font-size: 0.6rem;
}
.daad-step-extra {
  background: rgba(59, 130, 246, 0.06);
  border-radius: 6px;
  padding: 0.5rem 0.7rem;
  margin-top: 0.3rem;
}
.daad-extra-item {
  font-size: 0.72rem;
  color: #94a3b8;
  line-height: 1.5;
}
.daad-extra-item strong {
  color: #60a5fa;
  font-weight: 600;
}
.daad-sch-grid {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.daad-sch-card {
  background: rgba(15, 23, 42, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  padding: 0.9rem;
  transition: border-color 0.2s;
}
.daad-sch-card:hover {
  border-color: rgba(96, 165, 250, 0.12);
}
.daad-sch-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.4rem;
  gap: 0.5rem;
}
.daad-sch-name {
  font-family: 'Outfit', sans-serif;
  font-size: 0.82rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
  flex: 1;
}
.daad-sch-badge {
  font-size: 0.6rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}
.badge-high {
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
}
.badge-medium {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}
.badge-low {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}
.daad-sch-body {
  font-size: 0.75rem;
  color: #94a3b8;
}
.daad-sch-row {
  line-height: 1.6;
}
.daad-sch-row strong {
  color: #64748b;
  font-weight: 600;
}
.daad-sch-desc {
  margin: 0.3rem 0;
  line-height: 1.4;
}
.daad-sch-eligible {
  background: rgba(99, 102, 241, 0.08);
  border-radius: 6px;
  padding: 0.4rem 0.6rem;
  font-size: 0.72rem;
  color: #c4b5fd;
  margin-top: 0.3rem;
}

.sch-detail-meta {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}
.sch-detail-stat {
  background: rgba(15, 23, 42, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 0.6rem 1rem;
  text-align: center;
  min-width: 120px;
}
.stat-lbl {
  display: block;
  font-size: 0.6rem;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin-bottom: 0.2rem;
}
.stat-val {
  font-family: 'Outfit', sans-serif;
  font-size: 1.2rem;
  font-weight: 800;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 768px) {
  .hero-main { flex-direction: column; align-items: flex-start; }
  .hero-metrics { width: 100%; justify-content: space-around; }
  .hub-nav { flex-wrap: wrap; }
  .hub-nav-btn { flex: none; min-width: calc(50% - 0.25rem); }
  .hub-filter-bar { flex-direction: column; }
  .filter-select { width: 100%; }
  .prog-grid { grid-template-columns: 1fr; }
  .guide-grid { grid-template-columns: 1fr; }
  .modal-container { max-height: 90vh; margin: 0.5rem; }
  .cmp-strategy-steps { grid-template-columns: 1fr; }
}
</style>
