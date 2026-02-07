import axios from 'axios'

// Determine API base URL
// Priority: 1. Current hostname (if not localhost), 2. Environment variable (if not localhost), 3. localhost fallback
function getApiBaseUrl() {
  // First, try to detect hostname from window.location
  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    const port = window.location.port
    
    // If hostname is not localhost/127.0.0.1, use it (remote access)
    if (hostname && hostname !== 'localhost' && hostname !== '127.0.0.1') {
      const apiUrl = `${protocol}//${hostname}:8000`
      console.log('[API] Using detected remote hostname:', apiUrl, '(hostname:', hostname, ')')
      return apiUrl
    }
  }
  
  // Check environment variable, but ignore if it's localhost (for remote access)
  if (import.meta.env.VITE_API_URL) {
    const envUrl = import.meta.env.VITE_API_URL
    // Only use env var if it's not localhost (allows override for remote backends)
    if (!envUrl.includes('localhost') && !envUrl.includes('127.0.0.1')) {
      console.log('[API] Using VITE_API_URL (non-localhost):', envUrl)
      return envUrl
    } else {
      console.log('[API] Ignoring VITE_API_URL (localhost):', envUrl, '- will use detected hostname instead')
    }
  }
  
  // Use current hostname (works when accessing from remote IP)
  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    const port = window.location.port
    const apiUrl = `${protocol}//${hostname}:8000`
    
    // Debug logging
    console.log('[API] Window location:', {
      protocol,
      hostname,
      port,
      href: window.location.href
    })
    console.log('[API] Detected API URL:', apiUrl)
    
    // Warn if hostname is localhost but we're on a non-standard port (might indicate proxy/port forwarding)
    if (hostname === 'localhost' && port && port !== '5173' && port !== '8000') {
      console.warn('[API] Warning: hostname is localhost but port is', port, '- API URL will be localhost:8000')
    }
    
    return apiUrl
  }
  
  // Fallback for SSR or when window is not available
  console.warn('[API] Window not available, using localhost fallback')
  return 'http://localhost:8000'
}

// Create axios instance - baseURL will be set dynamically
const apiClient = axios.create({
  headers: {
    'Content-Type': 'application/json'
  }
})

// Set baseURL dynamically on each request to ensure we get current hostname
// This ensures we always use the current hostname, even if accessed from remote IP
apiClient.interceptors.request.use(config => {
  // Always recalculate baseURL to get current hostname
  const apiBaseUrl = getApiBaseUrl()
  config.baseURL = apiBaseUrl
  
  // Ensure URL is absolute (not relative) to bypass Vite proxy
  // If config.url starts with /, make it relative to baseURL
  if (config.url && config.url.startsWith('/')) {
    // URL is already relative, baseURL will be prepended by axios
    // But we want to ensure we're using the full absolute URL
    const fullUrl = apiBaseUrl + config.url
    console.log('API request:', config.method?.toUpperCase(), fullUrl)
  } else {
    console.log('API request:', config.method?.toUpperCase(), config.baseURL + (config.url || ''))
  }
  
  return config
})

// Set initial baseURL (will be overridden by interceptor, but useful for logging)
const API_BASE_URL = getApiBaseUrl()
apiClient.defaults.baseURL = API_BASE_URL
console.log('Axios API client initialized. Base URL will be set dynamically per request.')
console.log('Initial baseURL:', apiClient.defaults.baseURL)

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
      const currentApiUrl = getApiBaseUrl()
      error.message = `Cannot connect to backend at ${currentApiUrl}. Is the backend running?`
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
