import axios from 'axios'

// Determine API base URL
// Priority: 1. Environment variable, 2. Current hostname with port 8000, 3. localhost fallback
function getApiBaseUrl() {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  
  // Use current hostname (works when accessing from remote IP)
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    return `${protocol}//${hostname}:8000`
  }
  
  // Fallback for SSR or when window is not available
  return 'http://localhost:8000'
}

const API_BASE_URL = getApiBaseUrl()

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add response interceptor for better error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    // Log errors for debugging
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.status, error.response.data)
    } else if (error.request) {
      // Request made but no response (network error)
      console.error('Network Error: No response from server', error.request)
      error.message = `Cannot connect to backend at ${API_BASE_URL}. Is the backend running?`
    } else {
      // Something else happened
      console.error('Request Error:', error.message)
    }
    return Promise.reject(error)
  }
)

export default {
  async getStatus() {
    const response = await apiClient.get('/')
    return response.data
  },

  // Network Settings API
  async getNetworkSettings() {
    const response = await apiClient.get('/api/v1/network/settings')
    return response.data
  },

  async createNetworkSettings(settings) {
    const response = await apiClient.post('/api/v1/network/settings', settings)
    return response.data
  },

  async updateNetworkSettings(settingsId, settings) {
    const response = await apiClient.put(`/api/v1/network/settings/${settingsId}`, settings)
    return response.data
  },

  async applyNetworkSettings() {
    const response = await apiClient.post('/api/v1/network/settings/apply')
    return response.data
  },

  // Cluster Settings API
  async getClusterSettings() {
    const response = await apiClient.get('/api/v1/cluster/settings')
    return response.data
  },

  async createClusterSettings(settings) {
    const response = await apiClient.post('/api/v1/cluster/settings', settings)
    return response.data
  },

  async updateClusterSettings(settingsId, settings) {
    const response = await apiClient.put(`/api/v1/cluster/settings/${settingsId}`, settings)
    return response.data
  },

  async generateClusterSecrets(clusterName) {
    const response = await apiClient.post('/api/v1/cluster/secrets/generate', {
      cluster_name: clusterName
    })
    return response.data
  },

  async bootstrapCluster() {
    const response = await apiClient.post('/api/v1/cluster/bootstrap')
    return response.data
  },

  // Device Management API
  async getDevices(status = null) {
    const params = status ? { status } : {}
    const response = await apiClient.get('/api/v1/devices', { params })
    return response.data
  },

  async getDevice(deviceId) {
    const response = await apiClient.get(`/api/v1/devices/${deviceId}`)
    return response.data
  },

  async createDevice(device) {
    const response = await apiClient.post('/api/v1/devices', device)
    return response.data
  },

  async updateDevice(deviceId, device) {
    const response = await apiClient.put(`/api/v1/devices/${deviceId}`, device)
    return response.data
  },

  async getApprovalSuggestions(deviceId) {
    const response = await apiClient.get(`/api/v1/devices/${deviceId}/approval-suggestions`)
    return response.data
  },

  async approveDevice(deviceId, approvalData) {
    const response = await apiClient.post(`/api/v1/devices/${deviceId}/approve`, approvalData)
    return response.data
  },

  async rejectDevice(deviceId) {
    const response = await apiClient.post(`/api/v1/devices/${deviceId}/reject`)
    return response.data
  },

  async deleteDevice(deviceId) {
    const response = await apiClient.delete(`/api/v1/devices/${deviceId}`)
    return response.data
  },

  async getRecentEvents(since = null) {
    const params = since ? { since } : {}
    const response = await apiClient.get('/api/v1/events/recent', { params })
    return response.data
  },

  // Volume Configuration API
  async getVolumeConfigs() {
    const response = await apiClient.get('/api/v1/volumes/configs')
    return response.data
  },

  async getVolumeConfig(volumeId) {
    const response = await apiClient.get(`/api/v1/volumes/configs/${volumeId}`)
    return response.data
  },

  async getVolumeConfigByName(name) {
    const response = await apiClient.get(`/api/v1/volumes/configs/name/${name}`)
    return response.data
  },

  async createVolumeConfig(config) {
    const response = await apiClient.post('/api/v1/volumes/configs', config)
    return response.data
  },

  async updateVolumeConfig(volumeId, config) {
    const response = await apiClient.put(`/api/v1/volumes/configs/${volumeId}`, config)
    return response.data
  },

  async deleteVolumeConfig(volumeId) {
    const response = await apiClient.delete(`/api/v1/volumes/configs/${volumeId}`)
    return response.data
  }
}
