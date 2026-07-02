<template>
  <div class="papers-list-container">
    <div class="papers-table-wrapper">
      <table class="papers-table">
        <thead>
          <tr>
            <th class="col-title">Paper Title & Details</th>
            <th class="col-year">Year</th>
            <th class="col-citations">Citations</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(paper, index) in papers" :key="index" class="paper-row">
            <td class="col-title">
              <div class="paper-title-container">
                <a 
                  v-if="paper.url" 
                  :href="paper.url" 
                  target="_blank" 
                  class="paper-link"
                  title="Open paper on Google Scholar"
                >
                  {{ paper.title }} ↗
                </a>
                <span v-else class="paper-title-text">{{ paper.title }}</span>
                <span class="paper-details">{{ paper.authors_venue }}</span>
              </div>
            </td>
            <td class="col-year">
              <span class="year-badge" v-if="paper.year">{{ paper.year }}</span>
              <span class="no-year" v-else>—</span>
            </td>
            <td class="col-citations">
              <span class="citations-badge" :class="{ 'high-citations': parseInt(String(paper.citations || '0').replace(/,/g, '')) > 100 }">
                {{ paper.citations || 0 }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PaperList',
  props: {
    papers: {
      type: Array,
      required: true,
      default: () => []
    }
  }
}
</script>

<style scoped>
.papers-list-container {
  width: 100%;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  overflow: hidden;
}

.papers-table-wrapper {
  overflow-x: auto;
}

.papers-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.papers-table th {
  padding: 0.6rem 0.8rem;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.papers-table td {
  padding: 0.75rem 0.8rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  vertical-align: middle;
}

.paper-row {
  transition: background-color 0.2s;
}

.paper-row:hover {
  background-color: rgba(255, 255, 255, 0.02);
}

.paper-row:last-child td {
  border-bottom: none;
}

.paper-title-container {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.paper-link {
  font-size: 0.85rem;
  font-weight: 600;
  color: #60a5fa;
  text-decoration: none;
  line-height: 1.3;
  transition: color 0.15s;
  display: inline-block;
}

.paper-link:hover {
  color: #93c5fd;
  text-decoration: underline;
}

.paper-title-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: #cbd5e1;
  line-height: 1.3;
}

.paper-details {
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.3;
}

.col-year {
  width: 80px;
}

.year-badge {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 600;
}

.no-year {
  color: #475569;
  font-size: 0.8rem;
}

.col-citations {
  width: 90px;
}

.citations-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 20px;
  font-size: 0.75rem;
  color: #93c5fd;
  font-weight: 700;
  text-align: center;
  min-width: 32px;
}

.citations-badge.high-citations {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.2);
  color: #34d399;
}
</style>
