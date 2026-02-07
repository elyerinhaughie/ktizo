<template>
  <div class="cluster-settings">
    <div class="header">
      <h2>Cluster Settings</h2>
      <p class="subtitle">Configure Talos Kubernetes cluster parameters</p>
    </div>

    <div class="content-wrapper">
      <aside class="toc">
        <h3>Table of Contents</h3>
        <nav>
          <ul>
            <li><a href="#cluster-config" @click.prevent="scrollTo('cluster-config')">Cluster Configuration</a></li>
            <li><a href="#network-config" @click.prevent="scrollTo('network-config')">Network Configuration</a></li>
            <li><a href="#secrets-config" @click.prevent="scrollTo('secrets-config')">Cluster Secrets</a></li>
          </ul>
        </nav>
      </aside>

      <div class="form-container">
      <form @submit.prevent="saveSettings">
        <div class="section" id="cluster-config">
          <h3>Cluster Configuration</h3>

          <div class="form-group">
            <label>Cluster Name *</label>
            <input
              v-model="settings.cluster_name"
              type="text"
              required
              placeholder="e.g., my-k8s-cluster"
              :disabled="loading"
            />
            <small>Unique identifier for your Kubernetes cluster</small>
          </div>

          <div class="form-group">
            <label>External Cluster Subnet *</label>
            <input
              v-model="settings.external_subnet"
              type="text"
              required
              placeholder="e.g., 10.0.0.0/16"
              :disabled="loading"
            />
            <div class="info-box">
              <strong>What is this?</strong>
              <p>
                The external cluster subnet is the network range where your physical/bare-metal nodes reside.
                This is the network that your PXE boot server and Talos nodes communicate on.
              </p>
              <p>
                <strong>Example:</strong> If your servers are on 10.0.5.0/24, you might use 10.0.0.0/16 to allow
                for growth. This is separate from pod (10.244.0.0/16) and service (10.96.0.0/12) networks which
                are internal to Kubernetes.
              </p>
            </div>
          </div>

          <div class="form-group">
            <label>Cluster Endpoint *</label>
            <input
              v-model="settings.cluster_endpoint"
              type="text"
              required
              placeholder="e.g., 10.0.5.100 or k8s.example.com"
              :disabled="loading"
            />
            <div class="info-box">
              <strong>What is this?</strong>
              <p>
                The cluster endpoint is the IP address or hostname that all Kubernetes nodes use to communicate
                with the control plane. This should be a stable, highly-available address.
              </p>
              <p>
                <strong>Options:</strong>
              </p>
              <ul>
                <li><strong>Single control plane:</strong> Use the IP of your control plane node (e.g., 10.0.5.100)</li>
                <li><strong>Multiple control planes (HA):</strong> Use a load balancer IP or VIP that distributes traffic across control plane nodes</li>
                <li><strong>DNS-based:</strong> Use a hostname (e.g., k8s-api.example.com) that resolves to your control plane(s)</li>
              </ul>
              <p>
                <strong>Important:</strong> This address must be within your external subnet and reachable by all cluster nodes.
                Worker nodes will use this endpoint to join the cluster and communicate with the API server.
              </p>
            </div>
          </div>

          <div class="form-group">
            <label>Kubernetes Version</label>
            <input
              v-model="settings.kubernetes_version"
              type="text"
              placeholder="1.34.1"
              :disabled="loading"
            />
            <small>Latest stable: 1.34.1</small>
          </div>

          <div class="form-group">
            <label>Installer Image</label>
            <input
              v-model="settings.install_image"
              type="text"
              placeholder="ghcr.io/siderolabs/installer:latest"
              :disabled="loading"
            />
            <small>Talos installer container image (advanced users only, leave default)</small>
          </div>
        </div>

        <div class="section" id="network-config">
          <h3>Network Configuration</h3>
          <p class="info-text">
            Configure the internal Kubernetes networking. These are separate from your physical network
            and define how pods and services communicate within the cluster.
          </p>

          <div class="form-group">
            <label>Pod Subnet</label>
            <input
              v-model="settings.pod_subnet"
              type="text"
              placeholder="10.244.0.0/16"
              :disabled="loading"
            />
            <div class="info-box">
              <strong>What is this?</strong>
              <p>
                The Pod Subnet is the internal IP address range assigned to individual pods (containers) in your cluster.
                Each pod receives an IP from this range. This is completely separate from your physical network.
              </p>
              <p>
                <strong>Default:</strong> 10.244.0.0/16 (provides 65,536 IP addresses for pods)<br>
                <strong>Note:</strong> Ensure this doesn't overlap with your external subnet or service subnet.
              </p>
            </div>
          </div>

          <div class="form-group">
            <label>Service Subnet</label>
            <input
              v-model="settings.service_subnet"
              type="text"
              placeholder="10.96.0.0/12"
              :disabled="loading"
            />
            <div class="info-box">
              <strong>What is this?</strong>
              <p>
                The Service Subnet is the internal IP range for Kubernetes services. Services provide stable
                endpoints for accessing groups of pods. These IPs are virtual and only exist within the cluster.
              </p>
              <p>
                <strong>Default:</strong> 10.96.0.0/12 (provides 1,048,576 IP addresses for services)<br>
                <strong>Note:</strong> Must not overlap with pod subnet or external subnet.
              </p>
            </div>
          </div>

          <div class="form-group">
            <label>CNI Plugin</label>
            <select v-model="settings.cni" :disabled="loading">
              <option value="flannel">Flannel</option>
              <option value="calico">Calico</option>
              <option value="cilium">Cilium</option>
            </select>
            <div class="info-box">
              <strong>What is this?</strong>
              <p>
                The CNI (Container Network Interface) plugin handles pod-to-pod networking within your cluster.
                It manages routing, network policies, and communication between containers.
              </p>
              <p>
                <strong>Flannel:</strong> Simple, reliable overlay network. Good for most use cases.<br>
                <strong>Calico:</strong> Advanced features with network policies, BGP routing, and encryption.<br>
                <strong>Cilium:</strong> eBPF-based networking with observability and security features.
              </p>
              <p>
                <strong>Recommendation:</strong> Start with Flannel for simplicity. Use Calico or Cilium for advanced features.
              </p>
            </div>
          </div>

          <div class="form-group">
            <label>DNS Domain</label>
            <input
              v-model="settings.dns_domain"
              type="text"
              placeholder="cluster.local"
              :disabled="loading"
            />
            <div class="info-box">
              <strong>What is this?</strong>
              <p>
                The DNS Domain is the internal domain suffix used for service discovery within the cluster.
                Services are accessible via DNS names like <code>service-name.namespace.svc.cluster.local</code>
              </p>
              <p>
                <strong>Default:</strong> cluster.local (standard Kubernetes convention)<br>
                <strong>Example:</strong> A service named "redis" in the "default" namespace would be accessible
                at <code>redis.default.svc.cluster.local</code>
              </p>
              <p>
                <strong>Note:</strong> Only change this if you have a specific reason. The default works for most cases.
              </p>
            </div>
          </div>
        </div>

        <div class="section" id="secrets-config">
          <h3>Cluster Secrets</h3>
          <p class="info-text">
            Secrets contain cryptographic keys and certificates for cluster security.
            Generate new secrets or paste existing ones.
          </p>

          <div class="secrets-actions">
            <button
              type="button"
              class="generate-btn"
              @click="generateSecrets"
              :disabled="loading || generatingSecrets"
            >
              {{ generatingSecrets ? 'Generating...' : 'Generate Secrets' }}
            </button>
          </div>

          <div class="form-group">
            <label>Secrets YAML</label>
            <textarea
              v-model="settings.secrets_file"
              placeholder="Paste secrets YAML or generate new secrets..."
              rows="10"
              :disabled="loading"
            ></textarea>
          </div>
        </div>

        <div class="button-group">
          <button type="submit" class="save-btn" :disabled="loading || saving">
            {{ saving ? 'Saving...' : 'Save Settings' }}
          </button>
        </div>

        <div v-if="message" :class="['message', messageType]">
          {{ message }}
        </div>
      </form>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'

export default {
  name: 'ClusterSettings',
  data() {
    return {
      settings: {
        cluster_name: 'my-cluster',
        external_subnet: '10.0.128.0/24',
        cluster_endpoint: '10.0.128.1',
        kubernetes_version: '1.34.1',
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
      message: null,
      messageType: 'success'
    }
  },
  async mounted() {
    await this.loadSettings()
  },
  methods: {
    async loadSettings() {
      this.loading = true
      try {
        const response = await apiService.getClusterSettings()
        this.settings = {
          cluster_name: response.cluster_name,
          external_subnet: response.external_subnet || '',
          cluster_endpoint: response.cluster_endpoint,
          kubernetes_version: response.kubernetes_version,
          install_disk: response.install_disk,
          install_image: response.install_image,
          pod_subnet: response.pod_subnet,
          service_subnet: response.service_subnet,
          cni: response.cni,
          dns_domain: response.dns_domain,
          secrets_file: response.secrets_file || ''
        }
        this.settingsId = response.id
        this.showMessage('Settings loaded successfully', 'success')
      } catch (error) {
        if (error.response?.status === 404) {
          this.showMessage('No settings found. Please configure and save.', 'info')
        } else {
          this.showMessage('Failed to load settings', 'error')
        }
      } finally {
        this.loading = false
      }
    },
    async saveSettings() {
      this.saving = true
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
            if (createError.response?.status === 400 && createError.response?.data?.detail?.includes('already exist')) {
              const existingSettings = await apiService.getClusterSettings()
              this.settingsId = existingSettings.id
              response = await apiService.updateClusterSettings(this.settingsId, this.settings)
            } else {
              throw createError
            }
          }
        }
        this.showMessage('Settings saved successfully', 'success')
      } catch (error) {
        this.showMessage(error.response?.data?.detail || 'Failed to save settings', 'error')
      } finally {
        this.saving = false
      }
    },
    async generateSecrets() {
      if (!this.settings.cluster_name) {
        this.showMessage('Please enter a cluster name first', 'error')
        return
      }

      this.generatingSecrets = true
      try {
        const response = await apiService.generateClusterSecrets(this.settings.cluster_name)
        this.settings.secrets_file = response.secrets
        this.showMessage(response.message, 'success')
      } catch (error) {
        this.showMessage(error.response?.data?.detail || 'Failed to generate secrets', 'error')
      } finally {
        this.generatingSecrets = false
      }
    },
    showMessage(text, type) {
      this.message = text
      this.messageType = type
      setTimeout(() => {
        this.message = null
      }, 5000)
    },
    scrollTo(id) {
      const element = document.getElementById(id)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }
  }
}
</script>

<style scoped>
.cluster-settings {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  margin-bottom: 2rem;
}

h2 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 0;
}

.content-wrapper {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}

.toc {
  position: sticky;
  top: 2rem;
  width: 250px;
  flex-shrink: 0;
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
}

.toc h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #2c3e50;
  font-size: 1.1rem;
  border-bottom: 2px solid #42b983;
  padding-bottom: 0.5rem;
}

.toc nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc nav li {
  margin-bottom: 0.75rem;
}

.toc nav a {
  color: #666;
  text-decoration: none;
  font-size: 0.9rem;
  line-height: 1.4;
  display: block;
  padding: 0.25rem 0;
  transition: color 0.2s;
}

.toc nav a:hover {
  color: #42b983;
}

.form-container {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  flex: 1;
  min-width: 0;
}

.section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #eee;
}

.section:last-of-type {
  border-bottom: none;
  margin-bottom: 1.5rem;
}

h3 {
  color: #2c3e50;
  margin-bottom: 1rem;
  font-size: 1.2rem;
}

.info-text {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #2c3e50;
  font-weight: 500;
}

.form-group input[type="text"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group textarea {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  resize: vertical;
}

.form-group input:disabled,
.form-group select:disabled,
.form-group textarea:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: #666;
  font-size: 0.85rem;
}

.info-box {
  margin-top: 0.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-left: 4px solid #5a67d8;
  border-radius: 4px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.info-box strong {
  color: #2c3e50;
  display: block;
  margin-bottom: 0.5rem;
}

.info-box p {
  color: #666;
  margin-bottom: 0.5rem;
}

.info-box p:last-child {
  margin-bottom: 0;
}

.info-box ul {
  margin: 0.5rem 0 0.5rem 1.5rem;
  padding: 0;
  color: #666;
}

.info-box li {
  margin-bottom: 0.25rem;
}

.info-box li:last-child {
  margin-bottom: 0;
}

.info-box code {
  background: #f5f5f5;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  color: #d63384;
}

.secrets-actions {
  margin-bottom: 1rem;
}

.generate-btn {
  background: #5a67d8;
  color: white;
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s;
}

.generate-btn:hover:not(:disabled) {
  background: #4c51bf;
}

.generate-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.button-group {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.save-btn {
  background: #42b983;
  color: white;
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s;
}

.save-btn:hover:not(:disabled) {
  background: #35a372;
}

.save-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.message {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.message.info {
  background: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}
</style>
