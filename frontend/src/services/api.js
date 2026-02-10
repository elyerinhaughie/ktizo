import axios from 'axios'
import ws from './websocket.js'

// HTTP client kept for health check and binary downloads
function getApiBaseUrl() {
  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    if (hostname && hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return `${protocol}//${hostname}:8000`
    }
  }
  if (import.meta.env.VITE_API_URL) {
    const envUrl = import.meta.env.VITE_API_URL
    if (!envUrl.includes('localhost') && !envUrl.includes('127.0.0.1')) {
      return envUrl
    }
  }
  if (typeof window !== 'undefined' && window.location) {
    return `${window.location.protocol}//${window.location.hostname}:8000`
  }
  return 'http://localhost:8000'
}

const httpClient = axios.create({ headers: { 'Content-Type': 'application/json' } })
httpClient.interceptors.request.use(config => {
  config.baseURL = getApiBaseUrl()
  return config
})

export default {
  // Health check stays HTTP (needed before WS is up)
  async getStatus() {
    const r = await httpClient.get('/')
    return r.data
  },

  // --- Network ---
  getNetworkSettings: () => ws.request('network.get'),
  getNetworkInterfaces: () => ws.request('network.interfaces'),
  detectNetworkConfig: (iface) => ws.request('network.detect', { interface: iface }),
  createNetworkSettings: (s) => ws.request('network.create', s),
  updateNetworkSettings: (id, s) => ws.request('network.update', { settings_id: id, ...s }),
  applyNetworkSettings: () => ws.request('network.apply'),

  // --- Cluster ---
  getClusterSettings: () => ws.request('cluster.get'),
  createClusterSettings: (s) => ws.request('cluster.create', s),
  updateClusterSettings: (id, s) => ws.request('cluster.update', { settings_id: id, ...s }),
  generateClusterSecrets: (name) => ws.request('cluster.generate_secrets', { cluster_name: name }),
  bootstrapCluster: () => ws.request('cluster.bootstrap'),

  // Kubeconfig stays HTTP (binary file download)
  async downloadKubeconfig() {
    const r = await httpClient.get('/api/v1/cluster/kubeconfig', { responseType: 'blob' })
    return r.data
  },

  // --- Devices ---
  getDevices: (status) => ws.request('devices.list', status ? { status } : {}),
  getDevice: (id) => ws.request('devices.get', { device_id: id }),
  createDevice: (d) => ws.request('devices.create', d),
  updateDevice: (id, d) => ws.request('devices.update', { device_id: id, ...d }),
  getApprovalSuggestions: (id) => ws.request('devices.approval_suggestions', { device_id: id }),
  approveDevice: (id, data) => ws.request('devices.approve', { device_id: id, ...data }),
  rejectDevice: (id) => ws.request('devices.reject', { device_id: id }),
  deleteDevice: (id) => ws.request('devices.delete', { device_id: id }),
  regenerateConfigs: () => ws.request('devices.regenerate'),
  getDeviceHealth: () => ws.request('devices.health'),
  shutdownDevice: (id) => ws.request('devices.shutdown', { device_id: id }),
  wakeDevice: (id) => ws.request('devices.wake', { device_id: id }),

  // --- Volumes ---
  getVolumeConfigs: () => ws.request('volumes.list'),
  getVolumeConfig: (id) => ws.request('volumes.get', { volume_id: id }),
  getVolumeConfigByName: (name) => ws.request('volumes.get_by_name', { name }),
  createVolumeConfig: (c) => ws.request('volumes.create', c),
  updateVolumeConfig: (id, c) => ws.request('volumes.update', { volume_id: id, ...c }),
  deleteVolumeConfig: (id) => ws.request('volumes.delete', { volume_id: id }),

  // --- Talos ---
  getTalosSettings: () => ws.request('talos.get'),
  updateTalosSettings: (s) => ws.request('talos.update', s),

  // --- Versions ---
  getTalosVersions: () => ws.request('versions.talos'),
  getKubernetesVersions: () => ws.request('versions.kubernetes'),

  // --- Devices (extra) ---
  rebootDevice: (id) => ws.request('devices.reboot', { device_id: id }),
  rollingRefreshWorkers: (deviceIds, opts = {}) => ws.request('devices.rolling_refresh', {
    ...(deviceIds ? { device_ids: deviceIds } : {}),
    ...opts,
  }),
  cancelRollingRefresh: () => ws.request('devices.rolling_refresh_cancel'),
  getRollingRefreshStatus: () => ws.request('devices.rolling_refresh_status'),

  // --- Modules ---
  getModuleCatalog: () => ws.request('modules.catalog'),
  getModules: () => ws.request('modules.list'),
  getModule: (id) => ws.request('modules.get', { release_id: id }),
  installModule: (params) => ws.request('modules.install', params),
  importModule: (params) => ws.request('modules.import', params),
  upgradeModule: (id, params) => ws.request('modules.upgrade', { release_id: id, ...params }),
  cancelModule: (id) => ws.request('modules.cancel', { release_id: id }),
  forceDeleteModule: (id) => ws.request('modules.force_delete', { release_id: id }),
  uninstallModule: (id) => ws.request('modules.uninstall', { release_id: id }),
  getModuleLog: (id) => ws.request('modules.log', { release_id: id }),
  getHelmRepos: () => ws.request('modules.repos.list'),
  addHelmRepo: (params) => ws.request('modules.repos.add', params),
  deleteHelmRepo: (id) => ws.request('modules.repos.delete', { repo_id: id }),

  // --- Longhorn ---
  longhornNodes: () => ws.request('longhorn.nodes'),
  longhornDiscoverDisks: (nodeName) => ws.request('longhorn.discover_disks', { node_name: nodeName }),
  longhornAddDisk: (params) => ws.request('longhorn.add_disk', params),
  longhornRemoveDisk: (params) => ws.request('longhorn.remove_disk', params),
  longhornUseAllDisks: (nodeName) => ws.request('longhorn.use_all_disks', { node_name: nodeName }),
  longhornAutoConfig: (params) => ws.request('longhorn.auto_config', params),

  // --- Metrics ---
  getMetrics: () => ws.request('metrics.get'),

  // --- CI/CD Runners ---
  cicdFull: () => ws.request('cicd.full'),
  cicdOverview: () => ws.request('cicd.overview'),
  cicdRunners: (scaleSetName) => ws.request('cicd.runners', scaleSetName ? { scale_set_name: scaleSetName } : {}),
  cicdListeners: () => ws.request('cicd.listeners'),

  // --- Audit ---
  getAuditLogs: (params) => ws.request('audit.list', params || {}),
  clearAuditLogs: () => ws.request('audit.clear'),

  // --- RBAC ---
  rbacNamespaces: () => ws.request('rbac.namespaces'),
  rbacServiceAccounts: (params) => ws.request('rbac.serviceaccounts.list', params || {}),
  rbacCreateServiceAccount: (params) => ws.request('rbac.serviceaccounts.create', params),
  rbacDeleteServiceAccount: (params) => ws.request('rbac.serviceaccounts.delete', params),
  rbacRoles: (params) => ws.request('rbac.roles.list', params || {}),
  rbacGetRole: (params) => ws.request('rbac.roles.get', params),
  rbacCreateRole: (params) => ws.request('rbac.roles.create', params),
  rbacDeleteRole: (params) => ws.request('rbac.roles.delete', params),
  rbacClusterRoles: (params) => ws.request('rbac.clusterroles.list', params || {}),
  rbacGetClusterRole: (params) => ws.request('rbac.clusterroles.get', params),
  rbacCreateClusterRole: (params) => ws.request('rbac.clusterroles.create', params),
  rbacDeleteClusterRole: (params) => ws.request('rbac.clusterroles.delete', params),
  rbacRoleBindings: (params) => ws.request('rbac.rolebindings.list', params || {}),
  rbacCreateRoleBinding: (params) => ws.request('rbac.rolebindings.create', params),
  rbacDeleteRoleBinding: (params) => ws.request('rbac.rolebindings.delete', params),
  rbacClusterRoleBindings: (params) => ws.request('rbac.clusterrolebindings.list', params || {}),
  rbacCreateClusterRoleBinding: (params) => ws.request('rbac.clusterrolebindings.create', params),
  rbacDeleteClusterRoleBinding: (params) => ws.request('rbac.clusterrolebindings.delete', params),
  rbacPresets: () => ws.request('rbac.presets.list'),
  rbacWizardCreate: (params) => ws.request('rbac.wizard.create', params),

  // --- Workloads ---
  workloadsList: (params) => ws.request('workloads.list', params || {}),

  // --- Troubleshooting ---
  troubleshootStatus: () => ws.request('troubleshoot.status'),
  troubleshootFixKubeconfig: () => ws.request('troubleshoot.fix_kubeconfig'),
  troubleshootFixTalosconfig: () => ws.request('troubleshoot.fix_talosconfig'),
  troubleshootRegenConfigs: () => ws.request('troubleshoot.regen_configs'),
  troubleshootRegenDnsmasq: () => ws.request('troubleshoot.regen_dnsmasq'),
  troubleshootRestartDnsmasq: () => ws.request('troubleshoot.restart_dnsmasq'),
  troubleshootDownloadTalosctl: (version) => ws.request('troubleshoot.download_talosctl', version ? { version } : {}),
  troubleshootDownloadKubectl: (version) => ws.request('troubleshoot.download_kubectl', version ? { version } : {}),
  troubleshootDownloadTalosFiles: (version) => ws.request('troubleshoot.download_talos_files', version ? { version } : {}),
  troubleshootReinstallCni: () => ws.request('troubleshoot.reinstall_cni'),
}
