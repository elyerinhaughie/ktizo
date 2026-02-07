<template>
  <div id="app">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="logo">Ktizo</h1>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item">
          <span class="nav-icon">🏠</span>
          <span class="nav-text">Home</span>
        </router-link>
        <router-link to="/network" class="nav-item">
          <span class="nav-icon">🌐</span>
          <span class="nav-text">Network Settings</span>
        </router-link>
        <router-link to="/cluster" class="nav-item">
          <span class="nav-icon">⚙️</span>
          <span class="nav-text">Cluster Settings</span>
        </router-link>
        <router-link to="/storage" class="nav-item">
          <span class="nav-icon">💾</span>
          <span class="nav-text">Storage Settings</span>
        </router-link>
        <router-link to="/devices" class="nav-item">
          <span class="nav-icon">🖥️</span>
          <span class="nav-text">Device Management</span>
        </router-link>
        <router-link to="/wiki" class="nav-item">
          <span class="nav-icon">📚</span>
          <span class="nav-text">Wiki</span>
        </router-link>
        <router-link to="/terminal" class="nav-item">
          <span class="nav-icon">💻</span>
          <span class="nav-text">Terminal</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <button @click="downloadKubeconfig" class="download-btn" title="Download Kubeconfig">
          <span class="icon">⬇</span>
          <span class="btn-text">Kubeconfig</span>
        </button>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script>
import websocketService from './services/websocket'

export default {
  name: 'App',
  mounted() {
    // Initialize shared WebSocket connection
    websocketService.connect()
  },
  beforeUnmount() {
    // Disconnect WebSocket when app unmounts
    websocketService.disconnect()
  },
  methods: {
    async downloadKubeconfig() {
      try {
        // Use same hostname as current page, with port 8000
        let apiUrl = import.meta.env.VITE_API_URL
        if (!apiUrl && typeof window !== 'undefined') {
          const protocol = window.location.protocol
          const hostname = window.location.hostname
          apiUrl = `${protocol}//${hostname}:8000`
        }
        if (!apiUrl) {
          apiUrl = 'http://localhost:8000'
        }
        const response = await fetch(`${apiUrl}/api/v1/cluster/kubeconfig`)

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'Failed to download kubeconfig')
        }

        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'kubeconfig.yaml'
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } catch (error) {
        console.error('Failed to download kubeconfig:', error)
        alert(error.message || 'Failed to download kubeconfig. Make sure cluster settings are configured and the cluster is running.')
      }
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: #f5f5f5;
}

#app {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 250px;
  background: #2c3e50;
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 4px rgba(0,0,0,0.1);
  position: fixed;
  height: 100vh;
  overflow-y: auto;
  z-index: 1000;
}

.sidebar-header {
  padding: 1.5rem 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: white;
  margin: 0;
}

.sidebar-nav {
  flex: 1;
  padding: 1rem 0;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  color: rgba(255,255,255,0.8);
  text-decoration: none;
  transition: all 0.3s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: rgba(255,255,255,0.1);
  color: white;
}

.nav-item.router-link-active {
  background: rgba(255,255,255,0.15);
  color: white;
  border-left-color: #42b983;
  font-weight: 500;
}

.nav-icon {
  font-size: 1.2rem;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.nav-text {
  font-size: 0.95rem;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.download-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: rgba(255,255,255,0.1);
  color: white;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s;
}

.download-btn:hover {
  background: rgba(255,255,255,0.2);
  border-color: rgba(255,255,255,0.3);
}

.download-btn .icon {
  font-size: 1.1rem;
}

.main-content {
  flex: 1;
  margin-left: 250px;
  padding: 2rem;
  max-width: calc(100% - 250px);
}

/* Responsive design for smaller screens */
@media (max-width: 768px) {
  .sidebar {
    width: 200px;
  }
  
  .main-content {
    margin-left: 200px;
    max-width: calc(100% - 200px);
    padding: 1rem;
  }
  
  .nav-text {
    font-size: 0.85rem;
  }
}

@media (max-width: 640px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.3s;
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
  
  .main-content {
    margin-left: 0;
    max-width: 100%;
  }
}
</style>
