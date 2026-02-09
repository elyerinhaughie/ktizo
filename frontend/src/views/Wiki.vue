<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="mb-8">
      <h2 class="text-2xl font-bold text-gray-900 m-0">Wiki</h2>
      <p class="text-gray-500 mt-1 mb-0">Documentation and reference for Ktizo PXE boot system</p>
    </div>

    <div class="flex gap-8 items-start">
      <aside class="sticky top-24 w-[250px] shrink-0 bg-white p-6 rounded-lg shadow-md max-h-[calc(100vh-7rem)] overflow-y-auto">
        <h3 class="m-0 mb-4 text-sidebar-dark text-lg border-b-2 border-primary pb-2">Table of Contents</h3>
        <nav>
          <div class="mb-6">
            <h4 class="m-0 mb-2 text-primary text-[0.95rem] font-semibold">Overview</h4>
            <ul class="list-none p-0 m-0">
              <li class="mb-1.5">
                <a href="#introduction" @click.prevent="scrollTo('introduction')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Introduction</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#key-features" @click.prevent="scrollTo('key-features')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Key Features</a></li>
                </ul>
              </li>
              <li class="mb-1.5"><a href="#architecture" @click.prevent="scrollTo('architecture')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Architecture</a></li>
              <li class="mb-1.5"><a href="#workflow" @click.prevent="scrollTo('workflow')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Boot Workflow</a></li>
            </ul>
          </div>

          <div class="mb-6">
            <h4 class="m-0 mb-2 text-primary text-[0.95rem] font-semibold">Getting Started</h4>
            <ul class="list-none p-0 m-0">
              <li class="mb-1.5"><a href="#gs-network" @click.prevent="scrollTo('gs-network')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Step 1: Network Settings</a></li>
              <li class="mb-1.5"><a href="#gs-cluster" @click.prevent="scrollTo('gs-cluster')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Step 2: Cluster Settings</a></li>
              <li class="mb-1.5"><a href="#gs-secrets" @click.prevent="scrollTo('gs-secrets')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Step 3: Generate Secrets</a></li>
              <li class="mb-1.5"><a href="#gs-devices" @click.prevent="scrollTo('gs-devices')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Step 4: Boot &amp; Approve</a></li>
              <li class="mb-1.5"><a href="#gs-bootstrap" @click.prevent="scrollTo('gs-bootstrap')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Step 5: Bootstrap Cluster</a></li>
              <li class="mb-1.5"><a href="#gs-expand" @click.prevent="scrollTo('gs-expand')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Step 6: Add More Nodes</a></li>
            </ul>
          </div>

          <div class="mb-6">
            <h4 class="m-0 mb-2 text-primary text-[0.95rem] font-semibold">Core Components</h4>
            <ul class="list-none p-0 m-0">
              <li class="mb-1.5">
                <a href="#backend" @click.prevent="scrollTo('backend')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Backend API</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#api-endpoints" @click.prevent="scrollTo('api-endpoints')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">API Endpoints</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#frontend" @click.prevent="scrollTo('frontend')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Frontend UI</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#frontend-pages" @click.prevent="scrollTo('frontend-pages')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Pages</a></li>
                  <li><a href="#live-updates" @click.prevent="scrollTo('live-updates')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Live Updates</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#dnsmasq" @click.prevent="scrollTo('dnsmasq')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">dnsmasq Service</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#dnsmasq-modes" @click.prevent="scrollTo('dnsmasq-modes')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Modes of Operation</a></li>
                  <li><a href="#dnsmasq-services" @click.prevent="scrollTo('dnsmasq-services')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Services Provided</a></li>
                </ul>
              </li>
            </ul>
          </div>

          <div class="mb-6">
            <h4 class="m-0 mb-2 text-primary text-[0.95rem] font-semibold">Services</h4>
            <ul class="list-none p-0 m-0">
              <li class="mb-1.5">
                <a href="#config-generator" @click.prevent="scrollTo('config-generator')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Config Generator</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#config-how" @click.prevent="scrollTo('config-how')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">How It Works</a></li>
                  <li><a href="#config-naming" @click.prevent="scrollTo('config-naming')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">File Naming</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#ipxe-generator" @click.prevent="scrollTo('ipxe-generator')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">iPXE Generator</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#ipxe-logic" @click.prevent="scrollTo('ipxe-logic')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Boot Script Logic</a></li>
                  <li><a href="#device-matching" @click.prevent="scrollTo('device-matching')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Device Matching</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#template-service" @click.prevent="scrollTo('template-service')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Template Service</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#templates" @click.prevent="scrollTo('templates')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Templates</a></li>
                  <li><a href="#template-recompile" @click.prevent="scrollTo('template-recompile')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">When Recompiled</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#websocket" @click.prevent="scrollTo('websocket')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">WebSocket Service</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#ws-events" @click.prevent="scrollTo('ws-events')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Event Types</a></li>
                </ul>
              </li>
            </ul>
          </div>

          <div class="mb-6">
            <h4 class="m-0 mb-2 text-primary text-[0.95rem] font-semibold">Boot Process</h4>
            <ul class="list-none p-0 m-0">
              <li class="mb-1.5">
                <a href="#pxe-boot" @click.prevent="scrollTo('pxe-boot')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">PXE Boot</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#pxe-how" @click.prevent="scrollTo('pxe-how')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">How It Works</a></li>
                  <li><a href="#firmware-detection" @click.prevent="scrollTo('firmware-detection')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Firmware Detection</a></li>
                  <li><a href="#boot-files" @click.prevent="scrollTo('boot-files')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Boot File Locations</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#ipxe-chain" @click.prevent="scrollTo('ipxe-chain')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">iPXE Chainloading</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#two-stage" @click.prevent="scrollTo('two-stage')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Two-Stage Boot</a></li>
                  <li><a href="#avoiding-loops" @click.prevent="scrollTo('avoiding-loops')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Avoiding Loops</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#talos-boot" @click.prevent="scrollTo('talos-boot')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Talos Boot</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#talos-params" @click.prevent="scrollTo('talos-params')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Startup Parameters</a></li>
                  <li><a href="#talos-download" @click.prevent="scrollTo('talos-download')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Config Download</a></li>
                  <li><a href="#talos-install" @click.prevent="scrollTo('talos-install')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Installation</a></li>
                </ul>
              </li>
            </ul>
          </div>

          <div class="mb-6">
            <h4 class="m-0 mb-2 text-primary text-[0.95rem] font-semibold">Configuration</h4>
            <ul class="list-none p-0 m-0">
              <li class="mb-1.5">
                <a href="#network-config" @click.prevent="scrollTo('network-config')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Network Settings</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#server-config" @click.prevent="scrollTo('server-config')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Server Config</a></li>
                  <li><a href="#dhcp-config" @click.prevent="scrollTo('dhcp-config')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">DHCP Config</a></li>
                  <li><a href="#dns-config" @click.prevent="scrollTo('dns-config')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">DNS Config</a></li>
                  <li><a href="#tftp-config" @click.prevent="scrollTo('tftp-config')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">TFTP Config</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#cluster-config" @click.prevent="scrollTo('cluster-config')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Cluster Settings</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#cluster-basic" @click.prevent="scrollTo('cluster-basic')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Basic Settings</a></li>
                  <li><a href="#cluster-network-layers" @click.prevent="scrollTo('cluster-network-layers')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Network Layers</a></li>
                  <li><a href="#cluster-versions" @click.prevent="scrollTo('cluster-versions')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Version Settings</a></li>
                  <li><a href="#cluster-secrets-detail" @click.prevent="scrollTo('cluster-secrets-detail')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Cluster Secrets</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#device-config" @click.prevent="scrollTo('device-config')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Device Management</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#approval-params" @click.prevent="scrollTo('approval-params')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Approval Parameters</a></li>
                  <li><a href="#first-device" @click.prevent="scrollTo('first-device')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">First Device</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#storage-config" @click.prevent="scrollTo('storage-config')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Storage Settings</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#storage-disk-layout" @click.prevent="scrollTo('storage-disk-layout')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Disk Layout</a></li>
                  <li><a href="#storage-ephemeral" @click.prevent="scrollTo('storage-ephemeral')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">EPHEMERAL Partition</a></li>
                  <li><a href="#storage-rook-ceph" @click.prevent="scrollTo('storage-rook-ceph')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Rook/Ceph Integration</a></li>
                </ul>
              </li>
            </ul>
          </div>

          <div class="mb-0">
            <h4 class="m-0 mb-2 text-primary text-[0.95rem] font-semibold">Advanced Topics</h4>
            <ul class="list-none p-0 m-0">
              <li class="mb-1.5">
                <a href="#cni-explained" @click.prevent="scrollTo('cni-explained')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">CNI Plugins</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#cni-what" @click.prevent="scrollTo('cni-what')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">What is a CNI?</a></li>
                  <li><a href="#cni-flannel" @click.prevent="scrollTo('cni-flannel')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Flannel</a></li>
                  <li><a href="#cni-calico" @click.prevent="scrollTo('cni-calico')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Calico</a></li>
                  <li><a href="#cni-cilium" @click.prevent="scrollTo('cni-cilium')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Cilium</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#proxydhcp" @click.prevent="scrollTo('proxydhcp')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">ProxyDHCP Mode</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#proxy-how" @click.prevent="scrollTo('proxy-how')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">How It Works</a></li>
                  <li><a href="#proxy-advantages" @click.prevent="scrollTo('proxy-advantages')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Advantages</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#strict-mode" @click.prevent="scrollTo('strict-mode')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">Strict Boot Mode</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#strict-enabled" @click.prevent="scrollTo('strict-enabled')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Enabled</a></li>
                  <li><a href="#strict-disabled" @click.prevent="scrollTo('strict-disabled')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Disabled</a></li>
                </ul>
              </li>
              <li class="mb-1.5">
                <a href="#file-structure" @click.prevent="scrollTo('file-structure')" class="text-gray-600 no-underline text-[0.9rem] block py-1 px-2 rounded transition-all duration-200 hover:bg-gray-100 hover:text-sidebar-dark hover:pl-3">File Structure</a>
                <ul class="list-none p-0 m-0 ml-3 mt-1 border-l border-gray-200 pl-2">
                  <li><a href="#project-structure" @click.prevent="scrollTo('project-structure')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Project Structure</a></li>
                  <li><a href="#compiled-output" @click.prevent="scrollTo('compiled-output')" class="text-gray-400 no-underline text-[0.8rem] block py-0.5 transition-colors duration-200 hover:text-[#42b983]">Compiled Output</a></li>
                </ul>
              </li>
            </ul>
          </div>
        </nav>
      </aside>

      <main class="bg-white p-10 rounded-lg shadow-md min-h-[80vh]">
        <h1 class="text-sidebar-dark m-0 mb-4 text-4xl">Ktizo Wiki</h1>
        <p class="text-lg text-gray-500 mb-8 pb-8 border-b-2 border-gray-200">
          Complete documentation for Ktizo &mdash; a system that automatically installs and sets up servers over the network so you can build a cluster without touching each machine by hand.
        </p>

        <!-- ============================================================ -->
        <!-- OVERVIEW SECTION -->
        <!-- ============================================================ -->

        <section id="introduction" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Introduction</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Ktizo is a tool that lets you set up a group of servers (called a "cluster") without manually installing an operating system on each one. Instead of walking up to every machine with a USB drive, you simply plug them into the network, turn them on, and Ktizo takes care of the rest.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Behind the scenes, Ktizo uses a technology called <strong class="text-sidebar-dark">PXE boot</strong> (think of it as "booting from the network instead of a hard drive") to deliver an operating system called <strong class="text-sidebar-dark">Talos Linux</strong> to each machine. Talos Linux is a special-purpose operating system designed solely to run Kubernetes &mdash; a popular system for managing applications across many servers.
          </p>
          <h3 id="key-features" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Key Features</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Hands-Free Setup:</strong> Servers boot from the network and automatically check in with Ktizo. No USB drives or manual installs needed.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Centralized Control Panel:</strong> A web-based dashboard where you approve new machines, configure settings, and monitor your cluster &mdash; all from your browser.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Works With Your Existing Network:</strong> Ktizo can operate alongside your current router and DHCP server, or it can act as its own DHCP server if you prefer.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Live Updates:</strong> The dashboard updates in real time when devices appear, get approved, or download their configuration &mdash; no need to refresh the page.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Template-Based Configuration:</strong> Settings files are generated from templates, making it easy to customize behavior for different environments.</li>
          </ul>
        </section>

        <section id="architecture" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Architecture</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Ktizo is made up of three main pieces that work together. Think of it like a restaurant: the frontend is the menu and ordering system customers see, the backend is the kitchen that prepares everything, and dnsmasq is the delivery service that gets the food to the right table.
          </p>
          <div class="grid grid-cols-3 gap-4 my-6 max-lg:grid-cols-1">
            <div class="bg-white rounded-lg shadow-md p-5 text-center border-2 border-primary">
              <h4 class="text-primary m-0 mb-2">Frontend (Vue 3)</h4>
              <p class="text-gray-500 text-[0.9rem] m-0">The web dashboard you interact with. Built with Vue 3 and served by Vite on port 5173 during development.</p>
            </div>
            <div class="bg-white rounded-lg shadow-md p-5 text-center border-2 border-primary">
              <h4 class="text-primary m-0 mb-2">Backend (FastAPI)</h4>
              <p class="text-gray-500 text-[0.9rem] m-0">The Python server that handles all the logic &mdash; device tracking, config generation, and file serving. Runs on port 8000.</p>
            </div>
            <div class="bg-white rounded-lg shadow-md p-5 text-center border-2 border-primary">
              <h4 class="text-primary m-0 mb-2">dnsmasq</h4>
              <p class="text-gray-500 text-[0.9rem] m-0">A lightweight network service that tells booting machines where to find their operating system files.</p>
            </div>
          </div>
          <p class="text-gray-600 leading-[1.8] mb-4">
            All three components run directly on an <strong class="text-sidebar-dark">Alpine Linux virtual machine</strong> managed by OpenRC (Alpine's service manager). The backend generates configuration files that dnsmasq uses to serve boot instructions to your machines. There are no Docker containers involved &mdash; everything runs natively on the VM for simplicity and performance.
          </p>
          <div class="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-md my-4">
            <strong class="text-blue-800 block mb-2">Tip:</strong>
            <p class="text-blue-800 m-0">
              The typical deployment uses a VM at a dedicated IP address on your network (for example, 10.0.42.2). This VM runs both the Ktizo backend and dnsmasq, while you access the frontend from your own computer's browser.
            </p>
          </div>
        </section>

        <section id="workflow" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Boot Workflow</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Here is what happens from the moment you turn on a server to the point where it is running as part of your cluster. Think of it as an assembly line &mdash; each step feeds into the next automatically.
          </p>
          <ol class="bg-gray-50 py-6 px-6 pl-10 rounded-md border-l-4 border-primary">
            <li class="mb-4"><strong class="text-sidebar-dark">Machine Powers On:</strong> The server is set to boot from the network (instead of its hard drive). It sends out a message asking "Is there a boot server on this network?"</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Network Responds:</strong> dnsmasq hears the request and replies with "Yes, here is where to find boot files."</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Boot Program Downloads:</strong> The machine downloads a small boot program (called iPXE) over the network using a simple file transfer protocol (TFTP).</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Boot Script Runs:</strong> iPXE loads a script from Ktizo that contains the boot logic &mdash; essentially a set of instructions that say "check if this machine is allowed to proceed."</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Device Registers:</strong> The machine announces itself to Ktizo using its unique hardware address (MAC address). It shows up in your dashboard as a new device.</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Approval Check:</strong> The boot script checks whether you have approved this device. If not, it either waits or exits, depending on your settings.</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Operating System Loads:</strong> Once approved, the machine downloads the Talos Linux kernel and initial boot image over the network.</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Configuration Downloads:</strong> Talos fetches its specific settings file from Ktizo &mdash; things like its hostname, IP address, and role in the cluster.</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Installation:</strong> Talos installs itself onto the machine's hard drive and reboots.</li>
            <li class="mb-4"><strong class="text-sidebar-dark">Joins the Cluster:</strong> After rebooting, the machine connects to the cluster and starts participating as either a manager (control plane) or a worker.</li>
          </ol>
        </section>

        <!-- ============================================================ -->
        <!-- GETTING STARTED SECTION -->
        <!-- ============================================================ -->

        <section id="gs-network" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Getting Started &mdash; Step 1: Configure Network Settings</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Before anything else, Ktizo needs to know about your network. Go to the <strong class="text-sidebar-dark">Network Settings</strong> page from the sidebar.
          </p>
          <div class="bg-white rounded-lg shadow-md p-5 my-4">
            <h4 class="text-sidebar-dark m-0 mb-3">What to configure:</h4>
            <ul class="text-gray-600 leading-[1.8] my-2 ml-6">
              <li class="mb-2"><strong class="text-sidebar-dark">Server IP:</strong> The IP address of the machine running Ktizo. This is how booting devices will find it on your network.</li>
              <li class="mb-2"><strong class="text-sidebar-dark">DHCP Mode:</strong> Choose <em>ProxyDHCP</em> if you already have a router handing out IP addresses (most home and office networks do). Choose <em>Full DHCP</em> only if there is no other DHCP server on your network.</li>
              <li class="mb-2"><strong class="text-sidebar-dark">Network Interface:</strong> If the Ktizo machine has multiple network connections, specify which one to use. You can leave this blank if there is only one.</li>
            </ul>
          </div>
          <p class="text-gray-600 leading-[1.8] mb-4">
            After filling in these fields, click <strong class="text-sidebar-dark">Apply</strong>. This generates the dnsmasq configuration and restarts the network boot service.
          </p>
          <div class="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-md my-4">
            <strong class="text-blue-800 block mb-2">Tip:</strong>
            <p class="text-blue-800 m-0">
              ProxyDHCP mode is the safest choice. It works alongside your existing router without interfering. Your router keeps assigning IP addresses; Ktizo only adds boot instructions.
            </p>
          </div>
        </section>

        <section id="gs-cluster" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Getting Started &mdash; Step 2: Configure Cluster Settings</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Next, tell Ktizo about the cluster you want to build. Go to the <strong class="text-sidebar-dark">Cluster Settings</strong> page.
          </p>
          <div class="bg-white rounded-lg shadow-md p-5 my-4">
            <h4 class="text-sidebar-dark m-0 mb-3">What to configure:</h4>
            <ul class="text-gray-600 leading-[1.8] my-2 ml-6">
              <li class="mb-2"><strong class="text-sidebar-dark">Cluster Name:</strong> A friendly name for your cluster (for example, "homelab" or "production"). This is used internally to identify the cluster.</li>
              <li class="mb-2"><strong class="text-sidebar-dark">Cluster Endpoint:</strong> The IP address (or domain name) that your first control plane machine will use. Other machines connect to the cluster through this address. It is typically the IP you plan to assign to your first server.</li>
              <li class="mb-2"><strong class="text-sidebar-dark">Kubernetes Version:</strong> Which version of Kubernetes to install (for example, 1.30.0). This determines compatibility with the applications you will run.</li>
              <li class="mb-2"><strong class="text-sidebar-dark">Talos Version:</strong> Which version of Talos Linux to deploy. Ktizo automatically downloads the right boot files for the version you pick.</li>
            </ul>
          </div>
        </section>

        <section id="gs-secrets" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Getting Started &mdash; Step 3: Generate Cluster Secrets</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Before any machines can join the cluster, you need to create a set of <strong class="text-sidebar-dark">security keys</strong>. These are like the locks and keys for your cluster &mdash; they ensure that only authorized machines can communicate with each other.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            On the Cluster Settings page, click the <strong class="text-sidebar-dark">Generate Cluster Secrets</strong> button. This creates certificates, tokens, and encryption keys that will be embedded into every machine's configuration.
          </p>
          <div class="bg-amber-50 border-l-4 border-amber-400 p-4 rounded-md my-4">
            <strong class="text-amber-800 block mb-2"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> Important:</strong>
            <p class="text-amber-800 m-0">
              You must generate secrets <em>before</em> approving any devices. If you regenerate secrets after devices have already been approved, you will need to re-approve every device so they receive updated security keys.
            </p>
          </div>
        </section>

        <section id="gs-devices" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Getting Started &mdash; Step 4: Boot and Approve Devices</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Now it is time to turn on the machines you want in your cluster. Make sure each machine is set to <strong class="text-sidebar-dark">boot from the network</strong> (this is usually a BIOS/UEFI setting called "PXE boot" or "Network boot"). Plug them into the same network as Ktizo, and power them on.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Each machine will automatically appear in the <strong class="text-sidebar-dark">Device Management</strong> page with a status of "Pending." For each device, click <strong class="text-sidebar-dark">Approve</strong> and fill in:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Hostname:</strong> A unique name for this machine (for example, "controlplane-01" or "worker-01").</li>
            <li class="mb-2"><strong class="text-sidebar-dark">IP Address:</strong> The static IP this machine should use.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Role:</strong> Either <em>Control Plane</em> (manages the cluster) or <em>Worker</em> (runs your applications).</li>
          </ul>
          <div class="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-md my-4">
            <strong class="text-blue-800 block mb-2">Tip:</strong>
            <p class="text-blue-800 m-0">
              Your very first device must be a Control Plane node, and its IP address should match the Cluster Endpoint you configured in Step 2. This machine will become the initial brain of the cluster.
            </p>
          </div>
        </section>

        <section id="gs-bootstrap" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Getting Started &mdash; Step 5: Bootstrap the Cluster</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            After your first control plane device has been approved and has booted into Talos Linux, you need to <strong class="text-sidebar-dark">bootstrap</strong> it. Bootstrapping is the one-time step that initializes the cluster &mdash; think of it as flipping the "on" switch for the entire cluster.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            In the Device Management page, you will see a <strong class="text-sidebar-dark">Bootstrap</strong> button next to your first control plane node. Ktizo first checks that the machine is ready (it must be reachable on the network), then sends the bootstrap command. This takes a minute or two.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Once bootstrapping completes, your cluster is alive and running. The Kubernetes API is now available at your cluster endpoint address.
          </p>
        </section>

        <section id="gs-expand" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Getting Started &mdash; Step 6: Add More Nodes</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            With the cluster running, you can add more machines at any time. Simply boot them from the network, approve them in the dashboard, and assign them a role:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Additional Control Plane nodes</strong> add redundancy &mdash; if one goes down, the others keep the cluster running. Three control plane nodes is a common choice for high availability.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Worker nodes</strong> add capacity &mdash; more workers means more resources for running your applications.</li>
          </ul>
          <p class="text-gray-600 leading-[1.8] mb-4">
            New nodes automatically join the existing cluster after they boot and download their configuration. No additional bootstrapping is required &mdash; that was a one-time step.
          </p>
        </section>

        <!-- ============================================================ -->
        <!-- CORE COMPONENTS SECTION -->
        <!-- ============================================================ -->

        <section id="backend" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Backend API</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The backend is the "brain" of Ktizo. It is a Python server built with a framework called FastAPI, and it handles all the behind-the-scenes work: keeping track of devices, generating configuration files, and serving boot files to machines on the network.
          </p>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">What It Does</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">Keeps a database of every device that has checked in, along with its approval status, hostname, IP, and role.</li>
            <li class="mb-2">Manages your network and cluster settings.</li>
            <li class="mb-2">Generates unique configuration files for each approved device, tailored to its role and network details.</li>
            <li class="mb-2">Creates the boot script that tells machines what to do when they start up.</li>
            <li class="mb-2">Renders templates (fills in variables in configuration file blueprints) for dnsmasq, iPXE, and Talos.</li>
            <li class="mb-2">Provides a bidirectional WebSocket connection so the frontend can send requests and receive live event updates.</li>
            <li class="mb-2">Serves downloadable files like boot programs and operating system images.</li>
          </ul>
          <h3 id="api-endpoints" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">API Endpoints</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The backend exposes a set of URLs (called "endpoints") that the frontend and booting devices use to communicate with it. Here are the main ones:
          </p>
          <pre class="bg-sidebar-darker text-green-400 p-4 rounded-lg text-sm overflow-x-auto">GET  /api/v1/devices              # List all registered devices
POST /api/v1/devices              # Manually add a device
POST /api/v1/devices/register     # Device self-registration (during boot)
POST /api/v1/devices/{id}/approve # Approve a device for provisioning
POST /api/v1/devices/{id}/reject  # Reject a device
DELETE /api/v1/devices/{id}       # Remove a device

GET  /api/v1/network/settings     # Get current network configuration
POST /api/v1/network/settings/apply # Apply and activate network settings

GET  /api/v1/cluster/settings     # Get current cluster configuration
POST /api/v1/cluster/secrets/generate # Generate security keys

GET  /api/v1/talos/configs/{mac}.yaml # Serve a device's configuration file</pre>
        </section>

        <section id="frontend" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Frontend UI</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The frontend is the web dashboard you see in your browser. It is a single-page application built with Vue 3 that gives you a visual interface for everything Ktizo can do &mdash; no command-line knowledge required.
          </p>
          <h3 id="frontend-pages" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Pages</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Home:</strong> A quick overview and getting-started guide.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Network Settings:</strong> Configure how Ktizo communicates on your network (IP address, DHCP mode, network interface).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Cluster Settings:</strong> Set up your cluster's name, endpoint, versions, and generate security keys.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Device Management:</strong> View all discovered machines, approve or reject them, assign roles and IPs, and bootstrap the cluster.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Storage Settings:</strong> Configure storage volumes and persistent storage options for cluster nodes.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Terminal:</strong> A built-in web terminal for running commands directly on the Ktizo server.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Audit Log:</strong> A chronological record of every action taken in Ktizo &mdash; who did what and when.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Wiki:</strong> This documentation page.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">About:</strong> Version information and project details.</li>
          </ul>
          <h3 id="live-updates" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Live Updates</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The frontend maintains a persistent WebSocket connection to the backend. This means the page updates automatically without you needing to hit refresh. When a new device boots, gets approved, or downloads its configuration, you will see a notification pop up in the bottom-right corner and the relevant tables will update instantly.
          </p>
        </section>

        <section id="dnsmasq" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">dnsmasq Service</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            dnsmasq is a small, efficient program that provides three essential network services for booting machines. Think of it as the "traffic controller" that directs machines to the right boot files when they turn on.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Ktizo generates dnsmasq's configuration file automatically based on your Network Settings. You never need to edit dnsmasq's config by hand.
          </p>
          <h3 id="dnsmasq-modes" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Modes of Operation</h3>
          <div class="grid grid-cols-2 gap-4 my-6 max-lg:grid-cols-1">
            <div class="bg-white rounded-lg shadow-md p-5 border-l-4 border-blue-500">
              <h4 class="text-blue-500 m-0 mb-3">ProxyDHCP Mode (Recommended)</h4>
              <p class="m-0 text-[0.95rem] text-gray-600">
                Works alongside your existing router. Your router continues giving out IP addresses as usual, and dnsmasq only adds boot instructions on top. This is the safest option because it does not change how your network currently works.
              </p>
            </div>
            <div class="bg-white rounded-lg shadow-md p-5 border-l-4 border-blue-500">
              <h4 class="text-blue-500 m-0 mb-3">Full DHCP Server Mode</h4>
              <p class="m-0 text-[0.95rem] text-gray-600">
                dnsmasq takes over the job of assigning IP addresses <em>and</em> providing boot instructions. Only use this if you do not have another DHCP server on your network. Running two DHCP servers at the same time will cause problems.
              </p>
            </div>
          </div>
          <h3 id="dnsmasq-services" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Services Provided</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">DHCP:</strong> In proxy mode, it only sends boot information. In full mode, it also assigns IP addresses to devices.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">TFTP:</strong> A simple file transfer service that delivers boot programs and operating system files to machines during startup. Think of it like a basic file server optimized for boot files.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">DNS:</strong> Optional name resolution for your local network (translating names like "server1.local" into IP addresses).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">PXE:</strong> Automatically detects whether a machine uses legacy BIOS or modern UEFI firmware and serves the correct boot program.</li>
          </ul>
        </section>

        <!-- ============================================================ -->
        <!-- SERVICES SECTION -->
        <!-- ============================================================ -->

        <section id="config-generator" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Config Generator Service</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The Config Generator is the part of Ktizo that creates a unique settings file for each machine you approve. Every machine in your cluster needs its own configuration &mdash; specifying its name, IP address, role, and the security keys it uses to talk to other machines. The Config Generator builds all of this automatically.
          </p>
          <h3 id="config-how" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">How It Works</h3>
          <ol class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">Loads a base template (a blueprint) for Talos configuration from the <code>templates/talos/</code> directory.</li>
            <li class="mb-2">Fills in the cluster's security keys (certificates, tokens, encryption keys).</li>
            <li class="mb-2">Fills in the device-specific values you chose during approval (hostname, IP address, role).</li>
            <li class="mb-2">Adds network details (subnet, gateway, DNS server).</li>
            <li class="mb-2">Saves the finished file to <code>~/.ktizo/compiled/talos/configs/{mac-address}.yaml</code>.</li>
          </ol>
          <h3 id="config-naming" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">File Naming</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Every configuration file is named after the machine's MAC address &mdash; a unique hardware identifier that looks like <code>aa:bb:cc:dd:ee:ff</code>. This ensures each machine always gets the right file, even if it reboots or moves around the network.
          </p>
          <h3 id="config-when" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">When Configs Are Generated</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">When you approve a device in the dashboard.</li>
            <li class="mb-2">When you change cluster settings (so all configs stay up to date).</li>
            <li class="mb-2">When you manually trigger regeneration.</li>
          </ul>
        </section>

        <section id="ipxe-generator" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">iPXE Generator Service</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The iPXE Generator creates the "boot script" &mdash; a small set of instructions that every machine runs when it starts up from the network. This script is the gatekeeper: it checks whether a machine is approved before allowing it to load the operating system.
          </p>
          <h3 id="ipxe-logic" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">What the Boot Script Does</h3>
          <pre class="bg-sidebar-darker text-green-400 p-4 rounded-lg text-sm overflow-x-auto">1. Machine boots and loads the iPXE boot program
2. iPXE downloads the boot script (boot.ipxe) from Ktizo
3. Script looks up the machine's hardware address (MAC)
4. If approved  -->  Load the Talos operating system (kernel + boot image)
5. If NOT approved and strict mode is on  -->  Stop and try the next boot device
6. If NOT approved and strict mode is off  -->  Try to boot from local disk</pre>
          <h3 id="device-matching" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Device Matching</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The boot script contains a list of every approved device's MAC address. When a machine boots, the script compares the machine's MAC against this list. If there is a match, it proceeds to load Talos. If not, it follows the fallback behavior you configured (strict mode or local boot).
          </p>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">Strict Boot Mode</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            When strict mode is enabled, unapproved machines immediately stop the network boot and try the next option in their boot order (usually the local hard drive). This prevents accidental installs. See the <a href="#strict-mode" @click.prevent="scrollTo('strict-mode')" class="text-blue-500 no-underline hover:underline">Strict Boot Mode</a> section for more details.
          </p>
        </section>

        <section id="template-service" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Template Service</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The Template Service is responsible for turning "blueprints" into actual configuration files. Ktizo stores templates &mdash; files with placeholder variables &mdash; and the Template Service fills in those variables with your actual settings. This is done using a system called Jinja2, which is a popular templating language in Python.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Think of it like a mail merge: you have a letter template with blanks for the recipient's name and address, and the Template Service fills in each blank with real data.
          </p>
          <h3 id="templates" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Templates</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">dnsmasq.conf.j2:</strong> The blueprint for dnsmasq's configuration. It gets filled in with your network settings (IP address, DHCP mode, interface, etc.).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">boot.ipxe.j2:</strong> The blueprint for the iPXE boot script. It gets filled in with the list of approved devices and their boot parameters.</li>
          </ul>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">What Gets Filled In</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">Network settings (server IP, subnet, gateway, DNS servers)</li>
            <li class="mb-2">DHCP configuration (mode, IP range, lease options)</li>
            <li class="mb-2">The list of approved devices with their MAC addresses and hostnames</li>
            <li class="mb-2">Talos version and file paths for the operating system images</li>
            <li class="mb-2">Whether strict boot mode is enabled or disabled</li>
          </ul>
          <h3 id="template-recompile" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">When Templates Are Recompiled</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">Templates are automatically rebuilt when:</p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">You update and apply network settings.</li>
            <li class="mb-2">A device is approved, rejected, or deleted (because the boot script needs to update its device list).</li>
            <li class="mb-2">You manually trigger regeneration.</li>
          </ul>
        </section>

        <section id="websocket" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">WebSocket Service</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The WebSocket Service is what makes the Ktizo dashboard feel "live." Instead of the traditional approach where your browser has to ask the server for updates repeatedly (like refreshing a page), WebSocket creates a persistent two-way connection. Both the browser and the server can send messages to each other at any time.
          </p>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">How It Works</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The frontend opens a single WebSocket connection when you load the dashboard. This connection is <strong class="text-sidebar-dark">bidirectional</strong>:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Frontend to Backend:</strong> The dashboard sends CRUD requests (create, read, update, delete) over the WebSocket and receives responses &mdash; similar to normal API calls but faster because the connection is already open.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Backend to Frontend:</strong> The server broadcasts event notifications to all connected browsers whenever something important happens (a new device appears, a device gets approved, etc.).</li>
          </ul>
          <h3 id="ws-events" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Event Types</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">device_discovered:</strong> A new machine has booted and registered with Ktizo.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">device_approved:</strong> A machine has been approved for provisioning.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">device_rejected:</strong> A machine has been rejected.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">device_deleted:</strong> A machine has been removed from the system.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">config_downloaded:</strong> A machine has fetched its Talos configuration file.</li>
          </ul>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">Notifications</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            When the backend sends an event, the frontend compares the updated device list with what it had before to figure out exactly what changed. It then shows a toast notification in the bottom-right corner of the screen describing the event, and automatically refreshes any visible tables.
          </p>
        </section>

        <!-- ============================================================ -->
        <!-- BOOT PROCESS SECTION -->
        <!-- ============================================================ -->

        <section id="pxe-boot" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">PXE Boot</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            PXE (pronounced "pixie") stands for Preboot Execution Environment. In plain terms, it is a way for a computer to start up by downloading its operating system from the network instead of from a local hard drive or USB stick. This is the foundational technology that makes Ktizo possible.
          </p>
          <h3 id="pxe-how" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">How It Works</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Imagine a computer with no operating system installed. When it turns on, it looks for something to boot from. If PXE is enabled, it essentially shouts onto the network: "Does anyone have an operating system I can use?" Here is what happens step by step:
          </p>
          <ol class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">The computer sends a broadcast message asking for network configuration and boot instructions.</li>
            <li class="mb-2">dnsmasq responds with: "Here is your IP address, and here is where to download a boot program."</li>
            <li class="mb-2">The computer downloads the boot program (a small file, just a few hundred kilobytes) using TFTP.</li>
            <li class="mb-2">The boot program (iPXE) starts running and takes over from there.</li>
          </ol>
          <h3 id="firmware-detection" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Firmware Detection</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Computers come in two flavors when it comes to their startup firmware: older <strong class="text-sidebar-dark">BIOS</strong> systems and newer <strong class="text-sidebar-dark">UEFI</strong> systems. Ktizo detects which type each machine is and sends the right boot program:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">BIOS systems:</strong> Receive <code>undionly.kpxe</code> (a boot program designed for legacy hardware).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">UEFI systems (32-bit and 64-bit):</strong> Receive <code>ipxe.efi</code> (a boot program for modern hardware).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">ARM UEFI systems:</strong> Also receive <code>ipxe.efi</code> (the ARM-compatible version).</li>
          </ul>
          <h3 id="boot-files" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Boot File Locations</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            All boot files are served from <code>/var/lib/tftpboot</code> on the Ktizo server. This directory contains everything a machine needs to start up:
          </p>
          <pre class="bg-sidebar-darker text-green-400 p-4 rounded-lg text-sm overflow-x-auto">~/.ktizo/compiled/
  pxe/
    undionly.kpxe                  # Boot program for BIOS machines
    undionly-chainboot.kpxe        # Chainboot variant for BIOS
    ipxe.efi                       # Boot program for UEFI machines
    boot.ipxe                      # The boot script (decision logic)
    talos/
      vmlinuz-amd64-*              # Talos Linux kernel
      initramfs-amd64-*            # Talos initial boot image
  dnsmasq/
    dnsmasq.conf                   # dnsmasq configuration</pre>
        </section>

        <section id="ipxe-chain" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">iPXE Chainloading</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            iPXE is an enhanced network boot program that adds powerful features on top of basic PXE. Where standard PXE can only download a single file over a simple protocol, iPXE can run scripts, make decisions based on conditions, and download files over HTTP. Ktizo uses iPXE to implement its "approve before booting" logic.
          </p>
          <h3 id="two-stage" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Two-Stage Boot Process</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The boot happens in two stages, which is why it is called "chainloading" (one program loads another in a chain):
          </p>
          <ol class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Stage 1 &mdash; PXE Boot:</strong> The machine's built-in firmware loads the iPXE boot program from the network via TFTP. This is the basic PXE step.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Stage 2 &mdash; iPXE Script:</strong> iPXE then loads and runs the <code>boot.ipxe</code> script, which contains the smart logic for deciding what to do next.</li>
          </ol>
          <h3 id="avoiding-loops" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Avoiding Infinite Loops</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            A common problem with chainloading is that iPXE might try to PXE boot again, which downloads iPXE again, which PXE boots again, and so on forever. Ktizo avoids this by using <strong class="text-sidebar-dark">special marker variables</strong> and <strong class="text-sidebar-dark">tagged PXE service entries</strong>. When dnsmasq sees that a machine is already running iPXE (rather than basic PXE firmware), it sends the boot script directly instead of the iPXE program. Some virtual machines (like those in Proxmox) have iPXE built into their firmware, so they skip Stage 1 entirely.
          </p>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">What the Boot Script Can Do</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">Identify the machine by its unique hardware address (MAC address).</li>
            <li class="mb-2">Decide whether to boot the operating system based on approval status.</li>
            <li class="mb-2">Load the Talos Linux kernel and initial boot image for approved machines.</li>
            <li class="mb-2">Pass startup parameters to the operating system (like where to find its configuration file).</li>
            <li class="mb-2">Handle errors gracefully and fall back to local disk boot when appropriate.</li>
          </ul>
        </section>

        <section id="talos-boot" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Talos Boot</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Once a machine is approved and iPXE has loaded the Talos kernel and initial boot image, Talos Linux takes over. Talos is a minimal, security-focused operating system that exists solely to run Kubernetes. It has no SSH, no shell, no package manager &mdash; it is managed entirely through its API and configuration files.
          </p>
          <h3 id="talos-params" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Startup Parameters</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            When iPXE loads the Talos kernel, it passes along two critical pieces of information:
          </p>
          <pre class="bg-sidebar-darker text-green-400 p-4 rounded-lg text-sm overflow-x-auto">talos.platform=metal                                          # "I'm running on a physical machine"
talos.config=http://SERVER_IP:8000/api/v1/talos/configs/MAC.yaml  # "Fetch my config from this URL"</pre>
          <h3 id="talos-download" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Configuration Download</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            During startup, Talos reaches out to Ktizo's backend to download its unique configuration file. This file tells Talos everything it needs to know:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Role:</strong> Whether this machine is a control plane (cluster manager) or worker (runs applications).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Network identity:</strong> Hostname, static IP address, gateway, and DNS servers.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Cluster membership:</strong> Security certificates, tokens, and the cluster endpoint to connect to.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Installation target:</strong> Which disk to install Talos onto.</li>
          </ul>
          <h3 id="talos-install" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Installation Process</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">After downloading its configuration, Talos goes through these steps:</p>
          <ol class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">Boots into memory (RAM) from the kernel and initial boot image downloaded over the network.</li>
            <li class="mb-2">Downloads its configuration file from Ktizo.</li>
            <li class="mb-2">Validates the configuration to make sure everything looks correct.</li>
            <li class="mb-2">Installs Talos Linux onto the machine's hard drive.</li>
            <li class="mb-2">Writes the configuration to disk so it persists across reboots.</li>
            <li class="mb-2">Reboots from the hard drive (no longer needs the network to start up).</li>
            <li class="mb-2">Connects to the cluster and starts running as its assigned role.</li>
          </ol>
        </section>

        <!-- ============================================================ -->
        <!-- CONFIGURATION SECTION -->
        <!-- ============================================================ -->

        <section id="network-config" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Network Settings</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Network Settings control how Ktizo interacts with your local network. These settings determine how machines find Ktizo when they boot up, and how network addresses are managed.
          </p>
          <h3 id="server-config" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Server Configuration</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Server IP:</strong> The IP address of the machine running Ktizo. Booting devices use this address to find boot files and download their configuration. This must be reachable from the network where your servers are connected.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Network Interface:</strong> If the Ktizo server has multiple network adapters (for example, one for management and one for the server network), you can specify which adapter to use. Leave blank to use all available interfaces.</li>
          </ul>
          <h3 id="dhcp-config" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">DHCP Configuration</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">DHCP Mode:</strong> ProxyDHCP (recommended, works with your existing router) or Full DHCP Server (replaces your existing DHCP).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">DHCP Network/Netmask:</strong> The network range that DHCP operates on (for example, 10.0.42.0 with netmask 255.255.255.0).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">DHCP Range:</strong> (Full DHCP mode only) The range of IP addresses dnsmasq is allowed to hand out (for example, 10.0.42.100 to 10.0.42.200).</li>
          </ul>
          <h3 id="dns-config" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">DNS Configuration</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">DNS Port:</strong> The port dnsmasq listens on for DNS queries. Set to 0 to disable DNS entirely (useful if you already have a DNS server).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">DNS Server:</strong> Which upstream DNS server to forward queries to. Defaults to the Ktizo server's own IP.</li>
          </ul>
          <h3 id="tftp-config" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">TFTP Configuration</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">TFTP Root:</strong> The directory where boot files are stored. Fixed at <code>/var/lib/tftpboot</code> and not configurable.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">TFTP Secure Mode:</strong> When enabled, restricts file access so that only files inside the TFTP root directory can be served. This prevents accidental exposure of other files on the server.</li>
          </ul>
        </section>

        <section id="cluster-config" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Cluster Settings</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Cluster Settings define the Kubernetes cluster that your machines will form. A cluster is a group of machines working together as a single system &mdash; you can think of it like turning many individual computers into one powerful computer.
          </p>

          <h3 id="cluster-basic" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Basic Settings</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Cluster Name:</strong> A human-readable name for your cluster, like "homelab" or "production." This is used internally for identification.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Cluster Endpoint:</strong> The IP address or hostname that all nodes use to reach the Kubernetes API server. For a single control plane, this is the control plane node's IP. For high availability, use a load balancer VIP or DNS name that fronts multiple control plane nodes. The first device you approve <strong>must</strong> be assigned this address.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">External Subnet:</strong> The physical network range your bare-metal machines live on. This is your <em>real</em> network &mdash; the one your switch, router, and Ktizo server are connected to. See "Network Layers" below for how this differs from internal Kubernetes subnets.</li>
          </ul>

          <h3 id="cluster-network-layers" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Understanding the Three Network Layers</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            A Kubernetes cluster operates on <strong>three completely separate network layers</strong>. Even though the default examples all start with <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.x.x.x</code>, they do not conflict because they exist at different levels of the networking stack and are never routed to each other.
          </p>

          <div class="my-6 p-5 bg-gray-50 rounded-lg">
            <h4 class="text-gray-600 mb-4 text-base">Network Layer Diagram</h4>
            <div class="space-y-3">
              <div class="flex items-stretch rounded overflow-hidden shadow-sm">
                <div class="bg-blue-600 text-white font-semibold text-sm flex items-center justify-center px-4 py-3 w-[180px] shrink-0">
                  <span>PHYSICAL NETWORK</span>
                </div>
                <div class="border-l-4 border-blue-600 bg-[var(--th-bg-card,white)] flex-1 px-4 py-3 text-sm text-gray-600">
                  Your real switch/router network. Ktizo, your nodes, and your workstation are all here.<br>
                  <strong>Example:</strong> <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">192.168.1.0/24</code> or <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.0.42.0/24</code>
                </div>
              </div>
              <div class="flex items-stretch rounded overflow-hidden shadow-sm">
                <div class="bg-emerald-600 text-white font-semibold text-sm flex items-center justify-center px-4 py-3 w-[180px] shrink-0">
                  <span>POD NETWORK</span>
                </div>
                <div class="border-l-4 border-emerald-600 bg-[var(--th-bg-card,white)] flex-1 px-4 py-3 text-sm text-gray-600">
                  Virtual network for containers. Only exists inside the cluster, managed by the CNI plugin.<br>
                  <strong>Default:</strong> <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.244.0.0/16</code>
                </div>
              </div>
              <div class="flex items-stretch rounded overflow-hidden shadow-sm">
                <div class="bg-violet-600 text-white font-semibold text-sm flex items-center justify-center px-4 py-3 w-[180px] shrink-0">
                  <span>SERVICE NETWORK</span>
                </div>
                <div class="border-l-4 border-violet-600 bg-[var(--th-bg-card,white)] flex-1 px-4 py-3 text-sm text-gray-600">
                  Virtual IPs for Kubernetes services. Exist only in iptables/eBPF rules, never on a real interface.<br>
                  <strong>Default:</strong> <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.96.0.0/12</code>
                </div>
              </div>
            </div>
          </div>

          <p class="text-gray-600 leading-[1.8] mb-4">
            <strong class="text-sidebar-dark">Physical / External Network</strong> &mdash; This is the network your machines are physically plugged into. It is the same network that your Ktizo server (e.g., <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.0.42.2</code>), your router, and your workstation live on. The <em>External Subnet</em> in Cluster Settings tells Ktizo which IP range belongs to this physical network. Packets on this network travel over real Ethernet cables and switches.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            <strong class="text-sidebar-dark">Pod Network (internal)</strong> &mdash; A completely virtual overlay network that exists only inside the cluster. When Kubernetes creates a container (pod), the CNI plugin assigns it an IP from this range (default <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.244.0.0/16</code>). These IPs are encapsulated inside tunnels (VXLAN, WireGuard, etc.) between nodes &mdash; your physical switch never sees them. You cannot ping a pod IP from your laptop unless you are inside the cluster.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            <strong class="text-sidebar-dark">Service Network (internal)</strong> &mdash; Even more virtual than the pod network. Service IPs (default <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.96.0.0/12</code>) don't exist on any network interface at all. They are purely iptables/eBPF rules that redirect traffic to the right pods. When you access <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">redis.default.svc.cluster.local</code>, Kubernetes resolves it to a service IP, which then gets rewritten to an actual pod IP.
          </p>

          <div class="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-md my-4">
            <strong class="text-blue-800 block mb-2"><font-awesome-icon :icon="['fas', 'circle-info']" /> Why can they all use 10.x.x.x?</strong>
            <p class="text-gray-700 m-0 text-[0.9rem] leading-relaxed">
              The pod and service networks are virtual &mdash; they never appear on your physical switch or router. Since they live in different network layers (encapsulated tunnels and iptables rules respectively), there is no routing conflict even if the IP ranges look similar. However, the three ranges <strong>must not overlap with each other</strong>. For example, if your physical network is <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">192.168.1.0/24</code>, you can safely use <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.244.0.0/16</code> for pods and <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.96.0.0/12</code> for services with no issues. If your physical network <em>is</em> in the <code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em] text-pink-600">10.x</code> range, just ensure the CIDR blocks don't overlap.
            </p>
          </div>

          <h4 class="text-sidebar-dark text-base mt-6 mb-3">Subnet Settings Quick Reference</h4>
          <div class="overflow-x-auto">
            <table class="w-full text-sm border-collapse">
              <thead>
                <tr class="bg-gray-50">
                  <th class="text-left p-2 border border-gray-200 font-semibold text-sidebar-dark">Setting</th>
                  <th class="text-left p-2 border border-gray-200 font-semibold text-sidebar-dark">Layer</th>
                  <th class="text-left p-2 border border-gray-200 font-semibold text-sidebar-dark">Default</th>
                  <th class="text-left p-2 border border-gray-200 font-semibold text-sidebar-dark">Purpose</th>
                </tr>
              </thead>
              <tbody class="text-gray-600">
                <tr>
                  <td class="p-2 border border-gray-200 font-medium">External Subnet</td>
                  <td class="p-2 border border-gray-200">Physical</td>
                  <td class="p-2 border border-gray-200"><code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em]">varies</code></td>
                  <td class="p-2 border border-gray-200">Your real LAN &mdash; where nodes, Ktizo, and your router live</td>
                </tr>
                <tr class="bg-gray-50">
                  <td class="p-2 border border-gray-200 font-medium">Pod Subnet</td>
                  <td class="p-2 border border-gray-200">Virtual (overlay)</td>
                  <td class="p-2 border border-gray-200"><code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em]">10.244.0.0/16</code></td>
                  <td class="p-2 border border-gray-200">IPs assigned to individual containers, tunneled between nodes</td>
                </tr>
                <tr>
                  <td class="p-2 border border-gray-200 font-medium">Service Subnet</td>
                  <td class="p-2 border border-gray-200">Virtual (iptables)</td>
                  <td class="p-2 border border-gray-200"><code class="bg-gray-100 px-1 py-0.5 rounded font-mono text-[0.85em]">10.96.0.0/12</code></td>
                  <td class="p-2 border border-gray-200">Stable virtual IPs for services, rewritten to pod IPs by kube-proxy</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3 id="cluster-versions" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Version Settings</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Kubernetes Version:</strong> The version of the Kubernetes system to install. Different versions support different features.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Talos Version:</strong> The version of Talos Linux to deploy on each machine. Ktizo automatically downloads the correct boot files (kernel and initial boot image) for the version you select.</li>
          </ul>
          <h3 id="cluster-secrets-detail" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Cluster Secrets</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Cluster secrets are a set of cryptographic keys and certificates that secure communication within your cluster. They are like digital ID cards and locks &mdash; every machine must have the right keys to prove it belongs to the cluster and to encrypt its conversations with other machines. These include:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">Cluster certificate authority (the "master key" that signs other certificates)</li>
            <li class="mb-2">Kubernetes certificate authority (secures Kubernetes-internal communication)</li>
            <li class="mb-2">Aggregator certificate authority (secures API extensions)</li>
            <li class="mb-2">Service account key (authenticates running services)</li>
            <li class="mb-2">Bootstrap tokens (used during initial cluster setup)</li>
            <li class="mb-2">AES-CBC encryption secret (encrypts sensitive data stored in the cluster)</li>
          </ul>
          <div class="bg-amber-50 border-l-4 border-amber-400 p-4 rounded-md my-4">
            <strong class="text-amber-800 block mb-2"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> Important:</strong>
            <p class="text-amber-800 m-0">
              Always generate cluster secrets before approving any devices. If you regenerate secrets later, every previously approved device will need to be re-approved so it receives the new security keys.
            </p>
          </div>
        </section>

        <section id="device-config" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Device Management</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The Device Management page is where you see every machine that has booted from the network and registered with Ktizo. Each device goes through a lifecycle: it starts as "Pending," and you decide whether to approve or reject it.
          </p>
          <h3 id="approval-params" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Approval Parameters</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">When you approve a device, you set three things:</p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Hostname:</strong> A unique, descriptive name for the machine (for example, "controlplane-01" or "worker-03"). This becomes the machine's name in the cluster.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">IP Address:</strong> A static (fixed) IP address for the machine. Unlike dynamic IPs that can change, static IPs ensure the machine is always reachable at the same address.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Role:</strong> Either <em>Control Plane</em> (manages the cluster, runs the Kubernetes brain) or <em>Worker</em> (runs your actual applications and workloads).</li>
          </ul>
          <h3 id="first-device" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">First Device Requirements</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The very first device you approve has special requirements because it will initialize the cluster:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">It <strong class="text-sidebar-dark">must</strong> be assigned the Control Plane role.</li>
            <li class="mb-2">Its IP address <strong class="text-sidebar-dark">must</strong> match the Cluster Endpoint you set in Cluster Settings.</li>
            <li class="mb-2">After it boots and installs Talos, you will use the Bootstrap button to start the cluster.</li>
          </ul>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">What Gets Generated</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">When you approve a device, Ktizo automatically generates a Talos configuration file containing:</p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">Machine type (control plane or worker)</li>
            <li class="mb-2">Network identity (hostname, IP address, gateway, DNS)</li>
            <li class="mb-2">Cluster credentials (endpoint address, certificates, tokens)</li>
            <li class="mb-2">Kubelet settings (the Kubernetes agent that runs on each machine)</li>
            <li class="mb-2">Installation target disk</li>
          </ul>
        </section>

        <section id="storage-config" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Storage Settings</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The Storage Settings page controls how Talos partitions disks when it installs on a machine. By default, Talos uses all remaining disk space for its EPHEMERAL partition. These settings let you limit that, leaving room for distributed storage systems.
          </p>
          <h3 id="storage-disk-layout" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Disk Layout</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            When Talos installs, it automatically creates four partitions on the target disk:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">EFI (~100MB):</strong> The boot partition used by UEFI firmware to start the operating system.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">META (~1MB):</strong> A small metadata partition that stores machine identity and upgrade information.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">STATE (~100MB):</strong> Stores the machine's configuration and state. This is where Talos keeps the config file it downloads during PXE boot.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">EPHEMERAL (rest of disk):</strong> The main working partition. Stores container images, running container data, logs, and the etcd database on control plane nodes.</li>
          </ul>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The <strong>Install Disk</strong> setting (e.g., <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">/dev/sda</code>) determines which physical disk receives these partitions. Common values are <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">/dev/sda</code> for SATA drives, <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">/dev/nvme0n1</code> for NVMe, and <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[0.85em] text-pink-600">/dev/vda</code> for virtual machines.
          </p>
          <h3 id="storage-ephemeral" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">EPHEMERAL Partition</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            By default, the EPHEMERAL partition expands to fill all remaining disk space. This is fine for simple setups, but problematic if you want to run distributed storage like Rook/Ceph alongside Talos.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            By enabling the EPHEMERAL size limit and setting a maximum (e.g., 100GB), you cap how much space Talos claims. The remaining unpartitioned space is then available for other systems to use. Recommended sizes:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Control Plane nodes:</strong> 50–100GB (the etcd database needs room to grow)</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Worker nodes:</strong> 50–200GB (depends on how many container images and how much log data you expect)</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Minimum:</strong> 20GB for basic operation</li>
          </ul>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The optional <strong>Disk Selector</strong> field accepts a CEL (Common Expression Language) expression to target a specific disk for the EPHEMERAL partition when you have multiple disks in a machine. Most users should leave this blank.
          </p>
          <h3 id="storage-rook-ceph" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Rook/Ceph Integration</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Rook deploys Ceph on Kubernetes to provide distributed block, object, and file storage. Ceph needs raw, unpartitioned disk space to create its Object Storage Devices (OSDs).
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            For example, on a 1TB disk with EPHEMERAL limited to 100GB, approximately 900GB remains unpartitioned. Rook/Ceph can automatically discover and claim this space. This is the primary reason to limit the EPHEMERAL partition size in Ktizo.
          </p>
        </section>

        <!-- ============================================================ -->
        <!-- ADVANCED TOPICS SECTION -->
        <!-- ============================================================ -->

        <section id="cni-explained" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">CNI Plugins</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            When you run applications in Kubernetes, each application gets its own private network address. A CNI (Container Network Interface) plugin is the piece of software responsible for making those private addresses actually work &mdash; allowing applications to find and talk to each other, even when they're running on different physical machines.
          </p>

          <h3 id="cni-what" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">What is a CNI?</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Think of your Kubernetes cluster as an apartment building. Each apartment (container) has its own internal phone number (IP address), but those numbers only work inside the building &mdash; you can't dial them from outside. The CNI is like the building's internal phone system: it makes sure that when apartment 3A calls apartment 7B, the call gets routed correctly, even if they're on different floors (different physical machines).
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Behind the scenes, the CNI creates a private virtual network that sits on top of your real network. When a container on Machine 1 needs to talk to a container on Machine 2, the CNI wraps that message inside a normal network packet, sends it across your real network to Machine 2, and unwraps it on the other side. Your router and switch only ever see traffic between the machines themselves &mdash; the container-to-container communication is invisible to them.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            The CNI handles three main jobs:
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Assigning addresses:</strong> Giving each container its own unique private address and reclaiming it when the container is removed.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Traffic rules:</strong> Optionally controlling which containers are allowed to talk to each other &mdash; like a firewall between different parts of your application.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Delivery:</strong> Making sure messages actually arrive at the right container on the right machine.</li>
          </ul>

          <h3 id="cni-flannel" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Flannel</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Flannel is the simplest option. It creates a basic private network where every container can talk to every other container. There are no traffic rules or restrictions &mdash; it just works.
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Strengths:</strong> Easy to set up, uses very little memory and CPU, reliable, and widely used. If something goes wrong, it's straightforward to troubleshoot.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Limitations:</strong> No traffic rules &mdash; every container can talk to every other container freely. There's no way to say "only the web app can talk to the database." Adds a tiny bit of overhead to each message (about 50 extra bytes).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Best for:</strong> Homelabs, learning, and small clusters where simplicity is more important than fine-grained control.</li>
          </ul>

          <h3 id="cni-calico" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Calico</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Calico adds traffic rules on top of networking. You can define policies like "only the web frontend can talk to the API, and only the API can talk to the database." It also tries to be smarter about routing &mdash; instead of wrapping every message, it teaches your machines how to route container traffic directly when possible, which is faster.
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Strengths:</strong> Full traffic rule support, faster than Flannel in many cases (less wrapping/unwrapping), can encrypt traffic between machines using WireGuard.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Limitations:</strong> Harder to troubleshoot when something goes wrong. The smart routing doesn't work on every network, in which case it falls back to wrapping like Flannel.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Best for:</strong> Production clusters where you need to control which applications can communicate with each other.</li>
          </ul>

          <h3 id="cni-cilium" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Cilium</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Cilium is the most advanced option. It uses a technology called eBPF that runs small programs directly inside the operating system's core (the kernel), making networking very fast. Beyond just connecting containers, Cilium can inspect the actual content of messages &mdash; for example, it can create a rule like "only allow GET requests to /api/users, but block DELETE requests."
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Strengths:</strong> Very fast, traffic rules that understand HTTP (not just IP addresses), a built-in dashboard called Hubble that shows you a visual map of all traffic flowing between your applications, and built-in encryption.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Limitations:</strong> Uses more memory than Flannel. More complex to understand and debug when things go wrong. Requires a modern Linux kernel (Talos includes one, so this is not an issue here).</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Best for:</strong> Production clusters where you want visibility into traffic patterns, HTTP-level rules, or high-performance networking at scale.</li>
          </ul>

          <h4 class="text-sidebar-dark text-base mt-6 mb-3">Quick Comparison</h4>
          <div class="overflow-x-auto">
            <table class="w-full text-sm border-collapse">
              <thead>
                <tr class="bg-gray-50">
                  <th class="text-left p-2 border border-gray-200 font-semibold text-sidebar-dark"></th>
                  <th class="text-left p-2 border border-gray-200 font-semibold text-sidebar-dark">Flannel</th>
                  <th class="text-left p-2 border border-gray-200 font-semibold text-sidebar-dark">Calico</th>
                  <th class="text-left p-2 border border-gray-200 font-semibold text-sidebar-dark">Cilium</th>
                </tr>
              </thead>
              <tbody class="text-gray-600">
                <tr>
                  <td class="p-2 border border-gray-200 font-medium">Setup difficulty</td>
                  <td class="p-2 border border-gray-200">Easy</td>
                  <td class="p-2 border border-gray-200">Moderate</td>
                  <td class="p-2 border border-gray-200">Moderate</td>
                </tr>
                <tr class="bg-gray-50">
                  <td class="p-2 border border-gray-200 font-medium">Traffic rules</td>
                  <td class="p-2 border border-gray-200">None</td>
                  <td class="p-2 border border-gray-200">By IP / port</td>
                  <td class="p-2 border border-gray-200">By IP / port / HTTP path</td>
                </tr>
                <tr>
                  <td class="p-2 border border-gray-200 font-medium">Encryption</td>
                  <td class="p-2 border border-gray-200">No</td>
                  <td class="p-2 border border-gray-200">Yes (WireGuard)</td>
                  <td class="p-2 border border-gray-200">Yes (WireGuard / IPsec)</td>
                </tr>
                <tr class="bg-gray-50">
                  <td class="p-2 border border-gray-200 font-medium">Traffic visibility</td>
                  <td class="p-2 border border-gray-200">Basic logs</td>
                  <td class="p-2 border border-gray-200">Flow logs</td>
                  <td class="p-2 border border-gray-200">Visual dashboard (Hubble)</td>
                </tr>
                <tr>
                  <td class="p-2 border border-gray-200 font-medium">Resource usage</td>
                  <td class="p-2 border border-gray-200">Low</td>
                  <td class="p-2 border border-gray-200">Medium</td>
                  <td class="p-2 border border-gray-200">Medium</td>
                </tr>
                <tr class="bg-gray-50">
                  <td class="p-2 border border-gray-200 font-medium">Best for</td>
                  <td class="p-2 border border-gray-200">Getting started</td>
                  <td class="p-2 border border-gray-200">Production + rules</td>
                  <td class="p-2 border border-gray-200">Advanced / visibility</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section id="proxydhcp" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">ProxyDHCP Mode</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            ProxyDHCP is a clever networking trick that lets Ktizo provide boot instructions to machines <em>without replacing your existing network setup</em>. Normally, a network has one DHCP server (usually your router) that hands out IP addresses. ProxyDHCP adds a second "helper" that only provides PXE boot information, while your router keeps doing its job.
          </p>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Think of it like two receptionists at a hotel: one gives you your room key (IP address), and the other gives you a map of the building (boot instructions). They do not interfere with each other.
          </p>
          <h3 id="proxy-how" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">How It Works</h3>
          <ol class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">A machine turns on and sends a broadcast asking for network configuration.</li>
            <li class="mb-2">Your existing router responds with an IP address, gateway, and DNS settings.</li>
            <li class="mb-2">Ktizo's dnsmasq <em>also</em> responds, but only with boot instructions ("download your boot program from this address").</li>
            <li class="mb-2">The machine uses the IP from your router and the boot info from Ktizo.</li>
            <li class="mb-2">The machine downloads the boot program from Ktizo and proceeds to boot.</li>
          </ol>
          <div class="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-md my-4">
            <strong class="text-blue-800 block mb-2">Tip:</strong>
            <p class="text-blue-800 m-0">
              In proxy DHCP mode, the <code>pxe-service</code> directive in dnsmasq is the primary mechanism that tells booting machines what to download. The <code>dhcp-boot</code> directive alone is not sufficient &mdash; PXE service discovery specifically uses <code>pxe-service</code> entries. Ktizo handles this automatically, but it is good to understand if you are troubleshooting.
            </p>
          </div>
          <h3 id="proxy-advantages" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Advantages</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">No changes to your existing router or DHCP server required.</li>
            <li class="mb-2">No risk of conflicting with your existing network infrastructure.</li>
            <li class="mb-2">Easy to enable or disable PXE boot without affecting normal network traffic.</li>
            <li class="mb-2">Works with any router, including consumer home routers.</li>
          </ul>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">When to Use Full DHCP Mode Instead</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">Use Full DHCP Server mode only when:</p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2">You do not have an existing DHCP server on the network.</li>
            <li class="mb-2">You can safely disable your existing DHCP server.</li>
            <li class="mb-2">You want Ktizo to manage all network services (IP assignment + boot) in one place.</li>
          </ul>
          <div class="bg-amber-50 border-l-4 border-amber-400 p-4 rounded-md my-4">
            <strong class="text-amber-800 block mb-2"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> Warning:</strong>
            <p class="text-amber-800 m-0">
              Never run two full DHCP servers on the same network. This causes "DHCP conflicts" where machines get confused about which server to listen to, leading to connection problems across your entire network.
            </p>
          </div>
        </section>

        <section id="strict-mode" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">Strict Boot Mode</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Strict Boot Mode is a safety feature that controls what happens when a machine that has <em>not</em> been approved tries to boot from the network. It is like a bouncer at a club &mdash; if your name is not on the list, you are not getting in.
          </p>
          <h3 id="strict-enabled" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Enabled (Recommended)</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            When strict mode is on, unapproved machines are immediately told to stop the network boot and try the next option in their boot order. This usually means they will boot from their local hard drive if one is present.
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Advantage:</strong> Safe. Machines that already have an operating system installed will not be affected &mdash; they simply boot from their own disk as usual.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Consideration:</strong> If a machine has no operating system installed and is not approved, it will not boot at all (it will just stop at the firmware screen).</li>
          </ul>
          <h3 id="strict-disabled" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Disabled</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            When strict mode is off, unapproved machines may attempt to boot from their local disk. This sounds harmless, but there is a catch: if Talos Linux was previously installed on that machine and detects that its configuration is invalid or missing, it may automatically wipe the disk and try a fresh installation.
          </p>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">Advantage:</strong> Machines can boot even without explicit approval.</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Risk:</strong> Existing Talos installations may be wiped if they cannot find a valid configuration.</li>
          </ul>
          <div class="bg-amber-50 border-l-4 border-amber-400 p-4 rounded-md my-4">
            <strong class="text-amber-800 block mb-2"><font-awesome-icon :icon="['fas', 'triangle-exclamation']" /> Recommendation:</strong>
            <p class="text-amber-800 m-0">
              Keep strict mode enabled unless you have a specific reason to disable it. This prevents accidental data loss from Talos's automatic disk-wipe behavior on machines that have not been properly approved.
            </p>
          </div>
        </section>

        <section id="file-structure" class="mb-12 scroll-mt-8">
          <h2 class="text-2xl font-bold text-sidebar-dark pb-3 mb-6 border-b-2 border-primary">File Structure</h2>
          <p class="text-gray-600 leading-[1.8] mb-4">
            Understanding where files live helps with troubleshooting. Ktizo has two types of files: <strong class="text-sidebar-dark">source files</strong> (the code and templates that make up the project) and <strong class="text-sidebar-dark">compiled files</strong> (generated configuration and boot files that get served to machines).
          </p>
          <h3 id="project-structure" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Project Structure</h3>
          <pre class="bg-sidebar-darker text-green-400 p-4 rounded-lg text-sm overflow-x-auto">ktizo/
  backend/                       # The Python backend server
    app/
      api/                       # API endpoint definitions
      crud/                      # Database read/write operations
      db/                        # Database table definitions
      schemas/                   # Data validation rules
      services/                  # Core business logic
      utils/                     # Shared helper functions
    requirements.txt             # Python package list
  frontend/                      # The Vue 3 web dashboard
    src/
      services/                  # API client, WebSocket service
      views/                     # Page components (one per page)
      App.vue                    # Root component (sidebar + layout)
    package.json                 # JavaScript package list
  templates/                     # Configuration blueprints (Jinja2)
    network/
      dnsmasq.conf.j2            # dnsmasq config template
    pxe/
      boot.ipxe.j2               # iPXE boot script template
    talos/                       # Talos config templates
  data/                          # Runtime data
    ktizo.db                     # SQLite database</pre>
          <h3 id="compiled-output" class="text-sidebar-dark text-xl mt-6 mb-3 scroll-mt-24">Compiled Output Directory</h3>
          <p class="text-gray-600 leading-[1.8] mb-4">
            All generated files are written to <code>~/.ktizo/compiled/</code> on the Ktizo server. This directory is what dnsmasq's TFTP service points to, so booting machines download files from here.
          </p>
          <pre class="bg-sidebar-darker text-green-400 p-4 rounded-lg text-sm overflow-x-auto">~/.ktizo/compiled/
  dnsmasq/
    dnsmasq.conf                 # Active dnsmasq configuration
  pxe/
    boot.ipxe                    # Active boot script
    undionly.kpxe                # BIOS boot program
    undionly-chainboot.kpxe      # BIOS chainboot variant
    ipxe.efi                     # UEFI boot program
    talos/
      vmlinuz-amd64-*            # Talos Linux kernel
      initramfs-amd64-*          # Talos initial boot image
  talos/
    configs/                     # Per-device configuration files
      aa:bb:cc:dd:ee:ff.yaml     # Named by MAC address</pre>
          <h3 class="text-sidebar-dark text-xl mt-6 mb-3">Key File Locations Summary</h3>
          <ul class="text-gray-600 leading-[1.8] my-4 ml-6">
            <li class="mb-2"><strong class="text-sidebar-dark">dnsmasq config:</strong> <code>~/.ktizo/compiled/dnsmasq/dnsmasq.conf</code> (also copied to <code>/etc/dnsmasq.conf</code> on apply)</li>
            <li class="mb-2"><strong class="text-sidebar-dark">Boot script:</strong> <code>~/.ktizo/compiled/pxe/boot.ipxe</code></li>
            <li class="mb-2"><strong class="text-sidebar-dark">Device configs:</strong> <code>~/.ktizo/compiled/talos/configs/{mac}.yaml</code></li>
            <li class="mb-2"><strong class="text-sidebar-dark">Boot programs:</strong> <code>~/.ktizo/compiled/pxe/*.kpxe</code>, <code>*.efi</code></li>
            <li class="mb-2"><strong class="text-sidebar-dark">Talos images:</strong> <code>~/.ktizo/compiled/pxe/talos/vmlinuz-*</code>, <code>initramfs-*</code></li>
            <li class="mb-2"><strong class="text-sidebar-dark">Database:</strong> <code>data/ktizo.db</code> (SQLite)</li>
          </ul>
        </section>

      </main>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Wiki',
  methods: {
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
