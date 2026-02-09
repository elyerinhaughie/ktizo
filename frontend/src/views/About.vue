<template>
  <div class="max-w-[1000px] mx-auto py-8 px-6">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">About</h2>
        <p class="text-gray-500 mt-1 mb-0">Project information and technology overview</p>
      </div>
    </div>

    <!-- Hero -->
    <div class="bg-white rounded-lg shadow-md p-8 mb-8 text-center">
      <h3 class="text-3xl font-bold text-sidebar-dark mb-2">Ktizo</h3>
      <p class="text-lg text-gray-500 italic mb-4">From Greek "ktizo" — to build, to found, to create</p>
      <p class="text-gray-600 leading-relaxed max-w-[700px] mx-auto">
        Ktizo is a bare-metal Kubernetes provisioning system. It lets you boot physical servers over the network
        and automatically set up a Kubernetes cluster using Talos Linux — no manual OS installation, no USB drives,
        no clicking through installers. Just plug in a machine, approve it, and it joins your cluster.
      </p>
    </div>

    <!-- Tech Stack -->
    <h2 class="text-xl font-semibold text-sidebar-dark mb-4">Technology Stack</h2>
    <div class="grid grid-cols-2 gap-4 mb-8 max-lg:grid-cols-1">
      <div class="bg-white rounded-lg shadow-md p-5">
        <div class="flex items-center gap-3 mb-2">
          <span class="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm">
            <font-awesome-icon :icon="['fas', 'desktop']" />
          </span>
          <h3 class="font-semibold text-sidebar-dark">Frontend</h3>
        </div>
        <p class="text-gray-600 text-sm leading-relaxed">
          Built with Vue 3 and Tailwind CSS. Communicates with the backend entirely over WebSocket
          for real-time updates — when something changes on one screen, every connected browser sees it instantly.
        </p>
      </div>

      <div class="bg-white rounded-lg shadow-md p-5">
        <div class="flex items-center gap-3 mb-2">
          <span class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm">
            <font-awesome-icon :icon="['fas', 'cog']" />
          </span>
          <h3 class="font-semibold text-sidebar-dark">Backend</h3>
        </div>
        <p class="text-gray-600 text-sm leading-relaxed">
          Python FastAPI server with SQLite database. Handles device management, configuration generation,
          and orchestrates the entire boot process. Provides both a WebSocket API for the UI and a REST API for automation.
        </p>
      </div>

      <div class="bg-white rounded-lg shadow-md p-5">
        <div class="flex items-center gap-3 mb-2">
          <span class="w-8 h-8 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center text-sm">
            <font-awesome-icon :icon="['fas', 'globe']" />
          </span>
          <h3 class="font-semibold text-sidebar-dark">Boot Services</h3>
        </div>
        <p class="text-gray-600 text-sm leading-relaxed">
          Uses dnsmasq for DHCP and TFTP network services, and iPXE as the network bootloader.
          Together they allow any machine on the network to boot directly from Ktizo without any
          local storage or pre-installed software.
        </p>
      </div>

      <div class="bg-white rounded-lg shadow-md p-5">
        <div class="flex items-center gap-3 mb-2">
          <span class="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-sm">
            <font-awesome-icon :icon="['fas', 'hard-drive']" />
          </span>
          <h3 class="font-semibold text-sidebar-dark">Target OS</h3>
        </div>
        <p class="text-gray-600 text-sm leading-relaxed">
          Deploys Talos Linux — a minimal, immutable operating system purpose-built for Kubernetes.
          There's no SSH, no shell, no package manager. The entire OS is managed through an API,
          making it extremely secure and consistent across all nodes.
        </p>
      </div>
    </div>

    <!-- How It Works -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 class="text-xl font-semibold text-sidebar-dark mb-3">How It Works</h2>
      <p class="text-gray-600 leading-relaxed mb-4">
        Ktizo runs on a server in your network and acts as the central control point for building
        your Kubernetes cluster. Here's the basic flow:
      </p>
      <ol class="text-gray-600 leading-relaxed space-y-2 list-decimal list-inside">
        <li>You configure your network and cluster settings through the web interface</li>
        <li>A new machine boots up and requests a network address (PXE boot)</li>
        <li>Ktizo sends it a small boot program over the network</li>
        <li>The machine registers itself with Ktizo and appears in the dashboard</li>
        <li>You approve the machine, assign it a name, IP address, and role</li>
        <li>On its next boot, the machine receives Talos Linux and its personalized configuration</li>
        <li>Once the first control plane node is running, you bootstrap the cluster</li>
        <li>Additional machines join the cluster automatically after approval</li>
      </ol>
    </div>

    <!-- Developer -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 class="text-xl font-semibold text-sidebar-dark mb-3">Developer</h2>
      <p class="text-gray-600 leading-relaxed mb-3">
        Made with love in Seattle by
        <a href="https://github.com/elyerinhaughie" target="_blank" rel="noopener noreferrer"
           class="text-primary hover:text-primary-hover font-medium">Ely Erin Haughie</a>.
      </p>
      <p class="text-gray-600 leading-relaxed mb-3">
        Developed in my spare time as a hobby project in an attempt to make Kubernetes less painful.
      </p>
      <p class="text-gray-400 text-sm italic">
        Provided without support or warranty other than on a best effort basis.
      </p>
    </div>

    <!-- Links -->
    <div class="flex gap-4 max-lg:flex-col">
      <router-link to="/wiki"
        class="flex-1 bg-white rounded-lg shadow-md p-5 text-center hover:shadow-lg transition-shadow no-underline">
        <font-awesome-icon :icon="['fas', 'book']" class="text-2xl text-primary mb-2" />
        <p class="font-semibold text-sidebar-dark">Documentation</p>
        <p class="text-sm text-gray-500">Read the Wiki for detailed guides and reference</p>
      </router-link>
      <a href="https://github.com/elyerinhaughie/ktizo" target="_blank" rel="noopener noreferrer"
        class="flex-1 bg-white rounded-lg shadow-md p-5 text-center hover:shadow-lg transition-shadow no-underline">
        <font-awesome-icon :icon="['fas', 'rocket']" class="text-2xl text-primary mb-2" />
        <p class="font-semibold text-sidebar-dark">GitHub</p>
        <p class="text-sm text-gray-500">View the source code and contribute</p>
      </a>
    </div>
  </div>
</template>

<script>
export default { name: 'About' }
</script>
