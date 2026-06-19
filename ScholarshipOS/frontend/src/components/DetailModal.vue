<template>
  <transition name="modal-fade">
    <div class="modal-overlay" v-if="show" @click.self="close">
      <div class="modal-container">
        <button class="close-btn" @click="close">✕</button>
        
        <div class="modal-header">
          <slot name="header"></slot>
        </div>
        
        <div class="modal-body">
          <slot name="body"></slot>
        </div>
        
        <div class="modal-footer">
          <slot name="footer">
            <button class="btn-close-action" @click="close">Close</button>
          </slot>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
export default {
  name: 'DetailModal',
  props: {
    show: {
      type: Boolean,
      required: true,
      default: false
    }
  },
  methods: {
    close() {
      this.$emit('close');
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(4, 7, 15, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 1.5rem;
}

.modal-container {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 30px rgba(99, 102, 241, 0.15);
  border-radius: 16px;
  width: 100%;
  max-width: 650px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  animation: modal-zoom 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes modal-zoom {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.close-btn {
  position: absolute;
  top: 1rem;
  right: 1.2rem;
  background: none;
  border: none;
  color: #64748b;
  font-size: 1.2rem;
  cursor: pointer;
  z-index: 10;
  transition: color 0.2s;
}

.close-btn:hover {
  color: white;
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 1.2rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: flex-end;
}

.btn-close-action {
  padding: 0.5rem 1.5rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-weight: 600;
  font-size: 0.85rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-close-action:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
}

/* Transitions */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.25s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}
</style>
