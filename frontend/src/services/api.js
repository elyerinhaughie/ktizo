import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

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
