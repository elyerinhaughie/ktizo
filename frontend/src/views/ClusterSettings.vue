<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Cluster Settings</h2>
        <p class="text-gray-500 mt-1 mb-0">Configure Talos Kubernetes cluster parameters</p>
      </div>
      <button @click="saveSettings" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors duration-300 hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed whitespace-nowrap" :disabled="loading || saving">
        {{ saving ? 'Saving...' : 'Save & Apply' }}
      </button>
    </div>

    <div class="flex gap-8 items-start">
      <aside class="sticky top-24 w-[250px] shrink-0 bg-white p-6 rounded-lg shadow-md max-h-[calc(100vh-7rem)] overflow-y-auto">
        <h3 class="mt-0 mb-4 text-sidebar-dark text-lg border-b-2 border-[#42b983] pb-2">Table of Contents</h3>
        <nav>
          <ul class="list-none p-0 m-0">
            <li class="mb-2">
              <a href="#cluster-config" @click.prevent="scrollTo('cluster-config')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Cluster Configuration</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#cluster-name" @click.prevent="scrollTo('cluster-name')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Cluster Name</a></li>
                <li><a href="#external-subnet" @click.prevent="scrollTo('external-subnet')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">External Subnet</a></li>
                <li><a href="#cluster-endpoint" @click.prevent="scrollTo('cluster-endpoint')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Cluster Endpoint</a></li>
                <li><a href="#k8s-version" @click.prevent="scrollTo('k8s-version')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">K8s Version</a></li>
                <li><a href="#installer-image" @click.prevent="scrollTo('installer-image')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Installer Image</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#network-config" @click.prevent="scrollTo('network-config')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Network Configuration</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#pod-subnet" @click.prevent="scrollTo('pod-subnet')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Pod Subnet</a></li>
                <li><a href="#service-subnet" @click.prevent="scrollTo('service-subnet')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Service Subnet</a></li>
                <li><a href="#cni-plugin" @click.prevent="scrollTo('cni-plugin')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">CNI Plugin</a></li>
                <li><a href="#dns-domain" @click.prevent="scrollTo('dns-domain')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">DNS Domain</a></li>
              </ul>
            </li>
            <li class="mb-2">
              <a href="#secrets-config" @click.prevent="scrollTo('secrets-config')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">Cluster Secrets</a>
              <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                <li><a href="#generate-secrets" @click.prevent="scrollTo('generate-secrets')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Generate Secrets</a></li>
                <li><a href="#secrets-yaml" @click.prevent="scrollTo('secrets-yaml')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Secrets YAML</a></li>
              </ul>
            </li>
          </ul>
        </nav>
      </aside>

      <div class="bg-white p-8 rounded-lg shadow-md flex-1 min-w-0">
      <form @submit.prevent="saveSettings">
        <div class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24" id="cluster-config">
          <h3 class="text-sidebar-dark mb-1 text-xl">Cluster Configuration</h3>
          <p class="text-gray-500 text-sm mb-4">
            Core cluster identity, endpoint, and version settings.
            <router-link to="/wiki#cluster-config" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
          </p>

          <div class="grid grid-cols-2 gap-4">
            <div id="cluster-name" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">Cluster Name *</label>
              <input
                v-model="settings.cluster_name"
                type="text"
                required
                placeholder="e.g., my-k8s-cluster"
                :disabled="loading"
                class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <small class="block mt-1 text-gray-500 text-sm">Unique identifier for your Kubernetes cluster</small>
            </div>

            <div id="external-subnet" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">External Cluster Subnet *</label>
              <input
                v-model="settings.external_subnet"
                type="text"
                required
                placeholder="e.g., 10.0.0.0/16"
                :disabled="loading"
                class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <small class="block mt-1 text-gray-500 text-sm">Network range where your physical nodes reside (e.g., 10.0.0.0/16)</small>
            </div>

            <div id="cluster-endpoint" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">Cluster Endpoint *</label>
              <input
                v-model="settings.cluster_endpoint"
                @input="endpointManuallySet = true"
                type="text"
                required
                placeholder="e.g., 10.0.5.100 or k8s.example.com"
                :disabled="loading"
                class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <small class="block mt-1 text-gray-500 text-sm">Usually the first control plane node's IP. Auto-filled from external subnet. Override for HA (VIP/load balancer) or DNS.</small>
            </div>

            <div id="k8s-version" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">Kubernetes Version</label>
              <select
                v-model="settings.kubernetes_version"
                :disabled="loading"
                class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option v-if="settings.kubernetes_version && !kubernetesVersions.includes(settings.kubernetes_version)" :value="settings.kubernetes_version">
                  {{ settings.kubernetes_version }} (current)
                </option>
                <option v-for="v in kubernetesVersions" :key="v" :value="v">{{ v }}</option>
                <option v-if="!kubernetesVersions.length && !loadingVersions" disabled>Failed to load versions</option>
              </select>
              <small class="block mt-1 text-gray-500 text-sm">
                {{ loadingVersions ? 'Loading versions from GitHub...' : 'Also sets kubectl version unless manually changed' }}
              </small>
            </div>

            <div id="installer-image" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">Installer Image</label>
              <input
                v-model="settings.install_image"
                type="text"
                placeholder="factory.talos.dev/installer:latest"
                disabled
                readonly
                class="w-full p-2 border border-gray-200 rounded text-base bg-gray-50 text-gray-600 cursor-not-allowed font-mono text-sm"
              />
              <small class="block mt-1 text-gray-500 text-sm">Auto-managed by <router-link to="/talos" class="text-blue-500 no-underline hover:underline">Talos Settings</router-link> — generated from selected extensions via Factory API</small>
            </div>
          </div>
        </div>

        <div class="mb-8 pb-8 border-b border-gray-200 scroll-mt-24" id="network-config">
          <h3 class="text-sidebar-dark mb-1 text-xl">Network Configuration</h3>
          <p class="text-gray-500 text-sm mb-4">
            Internal Kubernetes networking — separate from your physical network.
            <router-link to="/wiki#cluster-config" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
          </p>

          <div class="grid grid-cols-2 gap-4">
            <div id="pod-subnet" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">Pod Subnet</label>
              <input
                v-model="settings.pod_subnet"
                type="text"
                placeholder="10.244.0.0/16"
                :disabled="loading"
                class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <small class="block mt-1 text-gray-500 text-sm">IP range for pods (default: 10.244.0.0/16). Must not overlap with external or service subnet.</small>
            </div>

            <div id="service-subnet" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">Service Subnet</label>
              <input
                v-model="settings.service_subnet"
                type="text"
                placeholder="10.96.0.0/12"
                :disabled="loading"
                class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <small class="block mt-1 text-gray-500 text-sm">IP range for services (default: 10.96.0.0/12). Must not overlap with pod or external subnet.</small>
            </div>

            <div id="cni-plugin" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">CNI Plugin</label>
              <select v-model="settings.cni" :disabled="loading" class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed">
                <option value="flannel">Flannel</option>
                <option value="calico">Calico</option>
                <option value="cilium">Cilium</option>
              </select>
              <small class="block mt-1 text-gray-500 text-sm">Flannel (simple), Calico (network policies), Cilium (eBPF-based).
                <router-link to="/wiki#cni-explained" class="text-blue-500 no-underline hover:underline">Learn more</router-link>
              </small>
            </div>

            <div id="dns-domain" class="mb-2 scroll-mt-24">
              <label class="block mb-2 text-sidebar-dark font-medium">DNS Domain</label>
              <input
                v-model="settings.dns_domain"
                type="text"
                placeholder="cluster.local"
                :disabled="loading"
                class="w-full p-2 border border-gray-300 rounded text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <small class="block mt-1 text-gray-500 text-sm">Internal domain for service discovery (default: cluster.local)</small>
            </div>
          </div>
        </div>

        <div class="mb-6 scroll-mt-24" id="secrets-config">
          <h3 class="text-sidebar-dark mb-1 text-xl">Cluster Secrets</h3>
          <p class="text-gray-500 text-sm mb-4">
            Cryptographic keys and certificates for cluster security.
            <router-link to="/wiki#cluster-secrets-detail" class="text-blue-500 no-underline hover:underline ml-1">Learn more</router-link>
          </p>

          <div id="generate-secrets" class="mb-4 scroll-mt-24">
            <button
              type="button"
              class="bg-indigo-600 text-white px-6 py-2 border-none rounded cursor-pointer text-[0.9rem] transition-colors duration-300 hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              @click="generateSecrets"
              :disabled="loading || generatingSecrets"
            >
              {{ generatingSecrets ? 'Generating...' : 'Generate Secrets' }}
            </button>
          </div>

          <div id="secrets-yaml" class="mb-4 scroll-mt-24">
            <label class="block mb-2 text-sidebar-dark font-medium">Secrets YAML</label>
            <textarea
              v-model="settings.secrets_file"
              placeholder="Paste secrets YAML or generate new secrets..."
              rows="10"
              :disabled="loading"
              class="w-full p-2 border border-gray-300 rounded font-mono text-sm resize-y disabled:bg-gray-100 disabled:cursor-not-allowed"
            ></textarea>
          </div>
        </div>

      </form>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'
import { useToast } from 'vue-toastification'

export default {
  name: 'ClusterSettings',
  data() {
    return {
      settings: {
        cluster_name: 'my-cluster',
        external_subnet: '10.0.128.0/24',
        cluster_endpoint: '10.0.128.1',
        kubernetes_version: '1.34.1',
        kubectl_version: '',
        install_disk: '/dev/sda',
        install_image: 'ghcr.io/siderolabs/installer:latest',
        pod_subnet: '10.244.0.0/16',
        service_subnet: '10.96.0.0/12',
        cni: 'flannel',
        dns_domain: 'cluster.local',
        secrets_file: ''
      },
      settingsId: null,
      loading: true,
      saving: false,
      generatingSecrets: false,
      endpointManuallySet: false,
      kubernetesVersions: [],
      loadingVersions: false,
    }
  },
  watch: {
    'settings.external_subnet'(val) {
      if (this.loading || this.endpointManuallySet) return
      const ip = this.firstUsableIp(val)
      if (ip) this.settings.cluster_endpoint = ip
    },
  },
  async mounted() {
    this.toast = useToast()
    await this.loadSettings()
    this.fetchKubernetesVersions()
  },
  methods: {
    firstUsableIp(cidr) {
      if (!cidr || !cidr.includes('/')) return null
      const [base, bits] = cidr.split('/')
      const parts = base.split('.')
      if (parts.length !== 4) return null
      // Increment last octet by 1
      const last = parseInt(parts[3], 10)
      parts[3] = String(last + 1)
      return parts.join('.')
    },
    async loadSettings() {
      this.loading = true
      try {
        const response = await apiService.getClusterSettings()
        this.settings = {
          cluster_name: response.cluster_name,
          external_subnet: response.external_subnet || '',
          cluster_endpoint: response.cluster_endpoint,
          kubernetes_version: response.kubernetes_version,
          kubectl_version: response.kubernetes_version,
          install_disk: response.install_disk,
          install_image: response.install_image,
          pod_subnet: response.pod_subnet,
          service_subnet: response.service_subnet,
          cni: response.cni,
          dns_domain: response.dns_domain,
          secrets_file: response.secrets_file || ''
        }
        this.settingsId = response.id
        // If endpoint doesn't match auto-derived value, user has customized it
        const autoIp = this.firstUsableIp(this.settings.external_subnet)
        this.endpointManuallySet = this.settings.cluster_endpoint !== autoIp
      } catch (error) {
        if (error.message?.toLowerCase().includes('not found')) {
          this.toast.info('No cluster settings found — configure and save below')
        } else {
          this.toast.error('Failed to load cluster settings')
        }
      } finally {
        this.loading = false
      }
    },
    async fetchKubernetesVersions() {
      this.loadingVersions = true
      try {
        this.kubernetesVersions = await apiService.getKubernetesVersions()
      } catch (e) {
        // Silently fail — dropdown will show current value
      } finally {
        this.loadingVersions = false
      }
    },
    async saveSettings() {
      if (!this.settings.cluster_name?.trim()) {
        this.toast.error('Cluster name is required')
        return
      }
      this.saving = true
      // kubectl version always matches kubernetes version
      this.settings.kubectl_version = this.settings.kubernetes_version
      try {
        let response
        if (this.settingsId) {
          response = await apiService.updateClusterSettings(this.settingsId, this.settings)
        } else {
          // Try to create, but if settings already exist, fetch and update instead
          try {
            response = await apiService.createClusterSettings(this.settings)
            this.settingsId = response.id
          } catch (createError) {
            // If settings already exist, fetch them and retry with update
            if (createError.message?.includes('already exist')) {
              const existingSettings = await apiService.getClusterSettings()
              this.settingsId = existingSettings.id
              response = await apiService.updateClusterSettings(this.settingsId, this.settings)
            } else {
              throw createError
            }
          }
        }
        this.toast.success('Cluster settings saved and configs regenerated')
      } catch (error) {
        this.toast.error(error.message || 'Failed to save cluster settings')
      } finally {
        this.saving = false
      }
    },
    async generateSecrets() {
      if (!this.settings.cluster_name) {
        this.toast.error('Please enter a cluster name first')
        return
      }

      this.generatingSecrets = true
      try {
        const response = await apiService.generateClusterSecrets(this.settings.cluster_name)
        this.settings.secrets_file = response.secrets
        this.toast.success('Cluster secrets generated successfully')
      } catch (error) {
        this.toast.error(error.message || 'Failed to generate secrets')
      } finally {
        this.generatingSecrets = false
      }
    },
    scrollTo(id) {
      const element = document.getElementById(id)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        element.classList.add('toc-highlight')
        element.addEventListener('animationend', () => element.classList.remove('toc-highlight'), { once: true })
      }
    }
  }
}
</script>
