<template>
  <div class="scan-container">
    <button 
      class="scan-btn" 
      :disabled="loading || status.running" 
      @click="triggerScan"
      :class="{ 'running': status.running }"
    >
      <span class="btn-icon" :class="{ 'spin': status.running }">⟳</span>
      <span class="btn-text">
        {{ status.running ? 'Scanning Database...' : 'Scan Database Now' }}
      </span>
    </button>
    
    <div class="status-msg" v-if="status.progress">
      <span class="status-indicator" :class="{ 'pulse': status.running, 'done': status.done }"></span>
      <span class="status-text">{{ status.progress }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ScanButton',
  props: {
    status: {
      type: Object,
      required: true,
      default: () => ({
        running: false,
        progress: '',
        done: false
      })
    }
  },
  data() {
    return {
      loading: false
    }
  },
  methods: {
    triggerScan() {
      this.loading = true;
      this.$emit('scan-started');
      fetch('/api/scan', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
          this.loading = false;
          this.$emit('scan-triggered');
        })
        .catch(err => {
          this.loading = false;
          console.error('Scan trigger error:', err);
          this.$emit('scan-failed', err);
        });
    }
  }
}
</script>

<style scoped>
.scan-container {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 0.8rem 1.5rem;
  border-radius: 12px;
  margin-bottom: 2rem;
  width: 100%;
}

.scan-btn {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: white;
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  font-size: 0.9rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.3);
}

.scan-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.45);
}

.scan-btn:active:not(:disabled) {
  transform: translateY(0);
}

.scan-btn:disabled {
  background: rgba(59, 130, 246, 0.2);
  color: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(59, 130, 246, 0.15);
  cursor: not-allowed;
  box-shadow: none;
}

.scan-btn.running {
  background: rgba(167, 139, 250, 0.15);
  border: 1px solid rgba(167, 139, 250, 0.3);
  color: #c084fc;
}

.btn-icon {
  font-size: 1.1rem;
  display: inline-block;
  transition: transform 0.2s;
}

.btn-icon.spin {
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.status-msg {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  color: #9ca3af;
  font-size: 0.85rem;
  flex: 1;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #3b82f6;
  flex-shrink: 0;
}

.status-indicator.pulse {
  animation: pulse 1.5s ease-in-out infinite;
  background-color: #a78bfa;
}

.status-indicator.done {
  background-color: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.status-text {
  font-weight: 500;
  line-height: 1.2;
}

@keyframes pulse {
  0% {
    transform: scale(0.9);
    opacity: 0.6;
    box-shadow: 0 0 0 0 rgba(167, 139, 250, 0.4);
  }
  50% {
    transform: scale(1.15);
    opacity: 1;
    box-shadow: 0 0 0 6px rgba(167, 139, 250, 0);
  }
  100% {
    transform: scale(0.9);
    opacity: 0.6;
    box-shadow: 0 0 0 0 rgba(167, 139, 250, 0);
  }
}
</style>
