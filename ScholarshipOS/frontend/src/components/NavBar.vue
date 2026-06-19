<template>
  <header class="navbar">
    <div class="brand">
      <div class="logo">
        <span class="logo-icon">🎓</span>
        <span class="logo-text">Scholar<span class="highlight">AI</span></span>
      </div>
      <span class="version-badge">v{{ version || '1.0.0' }}</span>
    </div>
    
    <div class="profile-summary" v-if="profile">
      <div class="profile-avatar">
        {{ initials }}
      </div>
      <div class="profile-details">
        <div class="profile-name">{{ profile.name }}</div>
        <div class="profile-meta">
          <span>{{ profile.current_education }}</span>
          <span class="dot">•</span>
          <span>GPA {{ profile.gpa }}</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
export default {
  name: 'NavBar',
  props: {
    profile: {
      type: Object,
      default: null
    },
    version: {
      type: String,
      default: '1.0.0'
    }
  },
  computed: {
    initials() {
      if (!this.profile || !this.profile.name) return 'S';
      const parts = this.profile.name.split(' ');
      if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
      }
      return this.profile.name[0].toUpperCase();
    }
  }
}
</script>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.2rem 2rem;
  background: rgba(13, 20, 38, 0.65);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-family: 'Outfit', sans-serif;
  font-weight: 800;
  font-size: 1.5rem;
  color: #ffffff;
  letter-spacing: -0.5px;
}

.logo-icon {
  font-size: 1.8rem;
  filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.5));
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
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 20px;
}

.profile-summary {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 0.4rem 1rem 0.4rem 0.5rem;
  border-radius: 40px;
  max-width: 320px;
}

.profile-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  color: white;
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.35);
}

.profile-details {
  display: flex;
  flex-direction: column;
}

.profile-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #f3f4f6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.profile-meta {
  font-size: 0.7rem;
  color: #9ca3af;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  white-space: nowrap;
}

.dot {
  font-weight: bold;
  color: rgba(255, 255, 255, 0.2);
}
</style>
