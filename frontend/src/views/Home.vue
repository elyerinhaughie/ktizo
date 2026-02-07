<template>
  <div class="home">
    <div class="hero">
      <h1>Ktizo</h1>
      <p class="subtitle">Fast PXE-based deployment for Talos Linux on Kubernetes</p>
      <p class="description">
        Ktizo (Greek: "to create," "to found," or "to form") provides an extremely fast
        network boot provisioning solution for deploying Talos Linux clusters.
      </p>
    </div>

    <div class="content-wrapper">
      <aside class="toc">
        <h3>Table of Contents</h3>
        <nav>
          <ul>
            <li><a href="#step-1" @click.prevent="scrollTo('step-1')">1. Understanding the Technologies</a></li>
            <li><a href="#step-2" @click.prevent="scrollTo('step-2')">2. Configure Network Settings</a></li>
            <li><a href="#step-3" @click.prevent="scrollTo('step-3')">3. Configure Cluster Settings</a></li>
            <li><a href="#step-4" @click.prevent="scrollTo('step-4')">4. Boot and Approve Devices</a></li>
            <li><a href="#step-5" @click.prevent="scrollTo('step-5')">5. Add More Nodes</a></li>
            <li><a href="#step-6" @click.prevent="scrollTo('step-6')">6. Bootstrap the Cluster</a></li>
            <li><a href="#next-steps" @click.prevent="scrollTo('next-steps')">Next Steps</a></li>
          </ul>
        </nav>
      </aside>

      <div class="guide-section">
      <h2>Getting Started Guide</h2>
      <p class="intro">
        This guide will walk you through setting up Ktizo to automatically deploy Talos Linux
        on bare metal servers using network boot (PXE). No manual installation required—just
        configure Ktizo and boot your servers!
      </p>

      <div class="step" id="step-1">
        <div class="step-header">
          <span class="step-number">1</span>
          <h3>Understanding the Technologies</h3>
        </div>
        <div class="step-content">
          <div class="tech-explanation">
            <h4>What is Talos Linux?</h4>
            <p>
              Talos is a modern Linux distribution designed specifically to run Kubernetes.
              Unlike traditional Linux, it has no SSH access, no shell, and is managed entirely
              through an API. This makes it more secure and reliable for Kubernetes clusters.
            </p>
          </div>
          <div class="tech-explanation">
            <h4>What is PXE Boot?</h4>
            <p>
              PXE (Preboot Execution Environment) allows computers to boot from the network
              instead of a local disk. When a server powers on, it can download an operating
              system directly from a server on your network—no USB drives or manual installation needed.
            </p>
          </div>
          <div class="tech-explanation">
            <h4>How Does Ktizo Work?</h4>
            <p>
              Ktizo acts as a PXE server that automatically provides Talos Linux to any machine
              that boots from the network. It handles DHCP (IP address assignment), serves boot
              files via TFTP, and generates custom Talos configurations for each machine.
            </p>
          </div>
        </div>
      </div>

      <div class="step" id="step-2">
        <div class="step-header">
          <span class="step-number">2</span>
          <h3>Configure Network Settings</h3>
        </div>
        <div class="step-content">
          <p>
            First, you need to tell Ktizo about your network so it can assign IP addresses to
            your servers and configure the DHCP/PXE boot services.
          </p>
          <ol class="detailed-steps">
            <li>
              <strong>Go to Network Settings</strong>
              <p>Click "Network Settings" in the navigation bar above.</p>
            </li>
            <li>
              <strong>Enter Your Network Details:</strong>
              <ul>
                <li><strong>External Subnet:</strong> Your network's IP range (e.g., 10.0.128.0/24).
                This is the subnet where your servers will get their IP addresses.</li>
                <li><strong>Gateway:</strong> Your network's router IP (e.g., 10.0.128.254).
                This allows your servers to access the internet.</li>
                <li><strong>DNS Servers:</strong> DNS server IPs (e.g., 8.8.8.8, 1.1.1.1).
                These help your servers resolve domain names.</li>
                <li>
                  <strong>ProxyDHCP Mode:</strong> Enable this if you already have a DHCP server
                  on your network. Ktizo will work alongside it. If disabled, Ktizo will be your
                  only DHCP server.
                  <div class="info-box" style="margin-top: 0.5rem;">
                    <strong>💡 ProxyDHCP Explained:</strong>
                    <p>
                      If you have an existing DHCP server (like your router), enable ProxyDHCP mode.
                      Your existing DHCP server will continue to assign IP addresses, while Ktizo will
                      only provide PXE boot information. If you don't have a DHCP server, leave it
                      disabled and Ktizo will handle everything.
                    </p>
                  </div>
                </li>
                <li><strong>Strict Boot Mode:</strong> When enabled, unapproved devices will exit
                to the next boot device. When disabled, they may attempt local boot which could
                trigger Talos auto-wipe if no OS is found.</li>
              </ul>
            </li>
            <li>
              <strong>Save Settings</strong>
              <p>Click "Save" and then "Apply Network Settings" to activate the DHCP/PXE services.</p>
            </li>
          </ol>
        </div>
      </div>

      <div class="step" id="step-3">
        <div class="step-header">
          <span class="step-number">3</span>
          <h3>Configure Cluster Settings</h3>
        </div>
        <div class="step-content">
          <p>
            Next, configure your Kubernetes cluster settings. This tells Talos how to set up
            your cluster and how nodes should communicate with each other.
          </p>
          <ol class="detailed-steps">
            <li>
              <strong>Go to Cluster Settings</strong>
              <p>Click "Cluster Settings" in the navigation bar.</p>
            </li>
            <li>
              <strong>Enter Cluster Details:</strong>
              <ul>
                <li><strong>Cluster Name:</strong> A name for your cluster (e.g., "my-cluster").
                This is used to identify your cluster.</li>
                <li><strong>Cluster Endpoint:</strong> The IP address or domain name where your
                Kubernetes API will be accessible (e.g., 10.0.128.1 or cluster.example.com).
                Your first control plane node will use this IP.</li>
                <li><strong>Talos Version:</strong> The version of Talos Linux to deploy
                (e.g., v1.8.4). Ktizo will automatically download this version.</li>
              </ul>
            </li>
            <li>
              <strong>Generate Secrets</strong>
              <p>
                Click "Generate Cluster Secrets". This creates cryptographic keys and certificates
                that secure communication between Talos nodes in your cluster. These secrets are
                generated once and shared across all nodes.
              </p>
            </li>
            <li>
              <strong>Save Settings</strong>
              <p>Click "Save" to store your cluster configuration.</p>
            </li>
          </ol>
          <div class="warning-box">
            <strong>⚠️ Important:</strong>
            <p>
              Generate cluster secrets BEFORE approving any devices. Once generated, these
              secrets will be used in all device configurations. If you regenerate them later,
              you'll need to re-approve all devices.
            </p>
          </div>
        </div>
      </div>

      <div class="step" id="step-4">
        <div class="step-header">
          <span class="step-number">4</span>
          <h3>Boot and Approve Devices</h3>
        </div>
        <div class="step-content">
          <p>
            Now you're ready to boot your servers! When a server boots from the network,
            it will automatically register with Ktizo and wait for approval.
          </p>
          <ol class="detailed-steps">
            <li>
              <strong>Configure Server BIOS/UEFI for Network Boot</strong>
              <p>
                On each server, enter the BIOS/UEFI settings (usually by pressing F2, F12,
                Del, or Esc during startup). Enable "Network Boot," "PXE Boot," or "Boot from LAN"
                and set it as the first boot option.
              </p>
            </li>
            <li>
              <strong>Connect Server to Network</strong>
              <p>
                Plug the server into the same network where Ktizo is running. Make sure the
                network cable is connected to the network interface you enabled for PXE boot.
              </p>
            </li>
            <li>
              <strong>Power On the Server</strong>
              <p>
                Start the server. You should see it attempt to boot from the network. It will
                load iPXE, then Talos Linux. You'll see a notification in Ktizo when the device
                is discovered.
              </p>
            </li>
            <li>
              <strong>Go to Device Management</strong>
              <p>Click "Device Management" in the navigation bar. You should see your new device
              with status "pending".</p>
            </li>
            <li>
              <strong>Approve the Device</strong>
              <p>
                Click the green checkmark (✓) button next to the device. You'll be prompted to:
              </p>
              <ul>
                <li><strong>Hostname:</strong> A name for this server (e.g., "controlplane-01"
                or "worker-01")</li>
                <li><strong>IP Address:</strong> The static IP this server should use. The first
                device must use your cluster endpoint IP.</li>
                <li><strong>Role:</strong> Choose "Control Plane" for Kubernetes master nodes
                (runs the Kubernetes API) or "Worker" for nodes that run your applications.</li>
              </ul>
            </li>
            <li>
              <strong>Device Downloads Configuration</strong>
              <p>
                Once approved, the device will automatically download its Talos configuration
                and reboot. Talos will install itself to disk and configure Kubernetes based
                on its role.
              </p>
            </li>
          </ol>
          <div class="info-box">
            <strong>💡 First Device Requirements:</strong>
            <p>
              Your first device MUST be a Control Plane node and MUST use the cluster endpoint
              IP you configured. This node will initialize your Kubernetes cluster. After the
              first node is approved, you can add more control planes and workers.
            </p>
          </div>
        </div>
      </div>

      <div class="step" id="step-5">
        <div class="step-header">
          <span class="step-number">5</span>
          <h3>Add More Nodes</h3>
        </div>
        <div class="step-content">
          <p>
            Repeat step 4 for each additional server you want to add to your cluster. You can add:
          </p>
          <ul class="node-types">
            <li><strong>More Control Plane Nodes:</strong> For high availability (typically 3 or 5
            total for production). These run the Kubernetes control plane and can survive node failures.</li>
            <li><strong>Worker Nodes:</strong> For running your applications. Add as many as you need
            based on your workload requirements.</li>
          </ul>
          <p>
            Each device will automatically join your cluster after approval and configuration download.
            There's no limit to how many nodes you can add—simply boot them from the network and
            approve them in Device Management.
          </p>
        </div>
      </div>

      <div class="step" id="step-6">
        <div class="step-header">
          <span class="step-number">6</span>
          <h3>Bootstrap the Cluster</h3>
        </div>
        <div class="step-content">
          <p>
            After your first control plane node finishes installing Talos, you need to bootstrap
            the Kubernetes cluster. This is a one-time operation that initializes Kubernetes.
          </p>
          <ol class="detailed-steps">
            <li>
              <strong>Install talosctl</strong>
              <p>
                Download the Talos CLI tool from
                <a href="https://github.com/siderolabs/talos/releases" target="_blank">GitHub</a>.
                This tool lets you interact with your Talos nodes.
              </p>
            </li>
            <li>
              <strong>Configure talosctl</strong>
              <p>
                Download the talosconfig file from Ktizo (available in Cluster Settings or Device
                Management) and save it to ~/.talos/config.
              </p>
            </li>
            <li>
              <strong>Bootstrap Kubernetes</strong>
              <p>Run the following command to initialize your cluster:</p>
              <code>talosctl bootstrap -n &lt;first-node-ip&gt;</code>
              <p>Replace &lt;first-node-ip&gt; with your first control plane node's IP address.</p>
            </li>
            <li>
              <strong>Get kubeconfig</strong>
              <p>
                After bootstrap completes (takes a few minutes), retrieve your Kubernetes
                configuration:
              </p>
              <code>talosctl kubeconfig -n &lt;first-node-ip&gt;</code>
              <p>This saves the kubeconfig to ~/.kube/config, allowing kubectl to connect to your cluster.</p>
            </li>
            <li>
              <strong>Verify Cluster</strong>
              <p>Check that your cluster is running:</p>
              <code>kubectl get nodes</code>
              <p>You should see all your approved nodes in the list.</p>
            </li>
          </ol>
        </div>
      </div>

      <div class="success-box">
        <h3>🎉 Congratulations!</h3>
        <p>
          Your Talos Kubernetes cluster is now running! You can deploy applications using kubectl,
          and add more nodes at any time by booting them from the network and approving them in
          Device Management.
        </p>
      </div>

      <div class="next-steps" id="next-steps">
        <h3>Next Steps</h3>
        <ul>
          <li>Deploy applications to your cluster using kubectl</li>
          <li>Set up persistent storage for your applications</li>
          <li>Configure monitoring and logging</li>
          <li>Review the <a href="https://www.talos.dev/docs/" target="_blank">Talos documentation</a>
          for advanced configuration</li>
        </ul>
      </div>

      <div class="cta-section">
        <router-link to="/network" class="cta-button">
          Start: Configure Network Settings
        </router-link>
      </div>
      </div>
    </div>

    <div class="status" v-if="apiStatus">
      <h3>API Status</h3>
      <p>{{ apiStatus.message }} - Version {{ apiStatus.version }}</p>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'

export default {
  name: 'Home',
  data() {
    return {
      apiStatus: null
    }
  },
  async mounted() {
    try {
      this.apiStatus = await apiService.getStatus()
    } catch (error) {
      console.error('Failed to fetch API status:', error)
    }
  },
  methods: {
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
.home {
  max-width: 1400px;
  margin: 0 auto;
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

.hero {
  background: white;
  padding: 3rem 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
  text-align: center;
}

.hero h1 {
  font-size: 3rem;
  color: #2c3e50;
  margin-bottom: 1rem;
}

.subtitle {
  font-size: 1.5rem;
  color: #42b983;
  margin-bottom: 1rem;
}

.description {
  font-size: 1.1rem;
  color: #666;
  max-width: 700px;
  margin: 0 auto;
  line-height: 1.6;
}

.guide-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
  text-align: left;
  flex: 1;
  min-width: 0;
}

.guide-section h2 {
  color: #2c3e50;
  font-size: 2rem;
  margin-bottom: 1rem;
  text-align: center;
}

.intro {
  font-size: 1.1rem;
  color: #666;
  line-height: 1.8;
  margin-bottom: 2rem;
  text-align: center;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.step {
  margin-bottom: 2.5rem;
  border-left: 4px solid #42b983;
  padding-left: 1.5rem;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.step-number {
  background: #42b983;
  color: white;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: bold;
  flex-shrink: 0;
}

.step-header h3 {
  color: #2c3e50;
  margin: 0;
  font-size: 1.5rem;
}

.step-content {
  color: #444;
  line-height: 1.8;
}

.step-content > p {
  margin-bottom: 1rem;
}

.node-types {
  margin: 1rem 0 1rem 1.5rem;
  color: #555;
}

.node-types li {
  margin-bottom: 0.75rem;
  line-height: 1.6;
}

.node-types strong {
  color: #2c3e50;
}

.tech-explanation {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.tech-explanation h4 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
  font-size: 1.1rem;
}

.tech-explanation p {
  color: #555;
  margin: 0;
}

.detailed-steps {
  margin-left: 1rem;
  margin-top: 1rem;
}

.detailed-steps li {
  margin-bottom: 1.5rem;
}

.detailed-steps strong {
  color: #2c3e50;
  display: block;
  margin-bottom: 0.5rem;
}

.detailed-steps p {
  margin: 0.5rem 0;
  color: #555;
}

.detailed-steps ul {
  margin-top: 0.5rem;
  margin-left: 1.5rem;
}

.detailed-steps ul li {
  margin-bottom: 0.5rem;
  color: #555;
}

.detailed-steps code {
  display: block;
  background: #f4f4f4;
  padding: 0.75rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  color: #e83e8c;
  margin: 0.5rem 0;
  overflow-x: auto;
}

.info-box,
.warning-box {
  padding: 1rem;
  border-radius: 6px;
  margin-top: 1rem;
}

.info-box {
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
}

.info-box strong {
  color: #1565c0;
  display: block;
  margin-bottom: 0.5rem;
}

.info-box p {
  color: #424242;
  margin: 0;
}

.warning-box {
  background: #fff3cd;
  border-left: 4px solid #ffc107;
}

.warning-box strong {
  color: #856404;
  display: block;
  margin-bottom: 0.5rem;
}

.warning-box p {
  color: #856404;
  margin: 0;
}

.success-box {
  background: #d4edda;
  border-left: 4px solid #28a745;
  padding: 1.5rem;
  border-radius: 6px;
  margin-bottom: 2rem;
}

.success-box h3 {
  color: #155724;
  margin-top: 0;
  margin-bottom: 0.5rem;
}

.success-box p {
  color: #155724;
  margin: 0;
}

.next-steps {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 6px;
  margin-bottom: 2rem;
}

.next-steps h3 {
  color: #2c3e50;
  margin-top: 0;
  margin-bottom: 1rem;
}

.next-steps ul {
  margin-left: 1.5rem;
  color: #555;
}

.next-steps li {
  margin-bottom: 0.5rem;
}

.next-steps a {
  color: #2196f3;
  text-decoration: underline;
}

.cta-section {
  text-align: center;
  margin: 2rem 0;
}

.cta-button {
  display: inline-block;
  background: #42b983;
  color: white;
  padding: 1rem 2rem;
  border-radius: 4px;
  text-decoration: none;
  font-size: 1.1rem;
  transition: background 0.3s;
  font-weight: 500;
}

.cta-button:hover {
  background: #35a372;
}

.status {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
}

.status h3 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.status p {
  color: #42b983;
  font-weight: bold;
}
</style>
