<template>
  <div id="app">
    <nav class="navbar">
      <div class="container">
        <h1 class="logo">Ktizo</h1>
        <div class="nav-links">
          <router-link to="/">Home</router-link>
          <router-link to="/network">Network Settings</router-link>
          <router-link to="/cluster">Cluster Settings</router-link>
          <router-link to="/storage">Storage Settings</router-link>
          <router-link to="/devices">Device Management</router-link>
          <router-link to="/wiki">Wiki</router-link>
        </div>
        <div class="nav-actions">
          <button @click="downloadKubeconfig" class="download-btn" title="Download Kubeconfig">
            <span class="icon">⬇</span> Kubeconfig
          </button>
        </div>
      </div>
    </nav>
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
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
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

.navbar {
  background: #2c3e50;
  color: white;
  padding: 1rem 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
}

.nav-links a {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.3s;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  background: rgba(255,255,255,0.1);
}

.nav-actions {
  display: flex;
  gap: 0.5rem;
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
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
  max-width: 1200px;
  margin: 2rem auto;
  padding: 0 1rem;
}
</style>
