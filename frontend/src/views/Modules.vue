<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 pt-4 pb-0 mb-8">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-2xl font-bold text-gray-900 m-0">Modules</h2>
          <p class="text-gray-500 mt-1 mb-0">Deploy and manage Kubernetes applications via Helm charts</p>
        </div>
        <button v-if="activeTab === 'applications'" @click="openGenericModal" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors duration-300 hover:bg-[#35a372]">
          <font-awesome-icon :icon="['fas', 'plus']" class="mr-2" /> Deploy Custom Chart
        </button>
      </div>
      <div class="flex gap-0 border-b border-gray-200">
        <router-link to="/modules/cluster"
          :class="activeTab === 'cluster' ? 'border-[#42b983] text-[#42b983]' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          class="py-2.5 px-5 text-sm font-medium border-b-2 no-underline transition-colors duration-200 -mb-px">
          <font-awesome-icon :icon="['fas', 'cubes']" class="mr-1.5" /> Cluster
        </router-link>
        <router-link to="/modules/applications"
          :class="activeTab === 'applications' ? 'border-[#42b983] text-[#42b983]' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          class="py-2.5 px-5 text-sm font-medium border-b-2 no-underline transition-colors duration-200 -mb-px">
          <font-awesome-icon :icon="['fas', 'cube']" class="mr-1.5" /> Applications
        </router-link>
      </div>
    </div>

    <div class="flex gap-8 items-start">
      <aside class="sticky top-24 w-[250px] shrink-0 bg-white p-6 rounded-lg shadow-md max-h-[calc(100vh-7rem)] overflow-y-auto">
        <h3 class="mt-0 mb-4 text-sidebar-dark text-lg border-b-2 border-[#42b983] pb-2">Table of Contents</h3>
        <nav>
          <ul class="list-none p-0 m-0">
            <li v-for="cat in activeCategories" :key="cat.id" class="mb-1">
              <a :href="'#cat-' + cat.id" @click.prevent="scrollTo('cat-' + cat.id)" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983]">{{ cat.label }}</a>
            </li>
            <li class="mb-1 mt-3 pt-3 border-t border-gray-200">
              <a href="#deployed" @click.prevent="scrollTo('deployed')" class="text-gray-500 no-underline text-[0.9rem] block py-1 transition-colors duration-200 hover:text-[#42b983] font-medium">Deployed Releases</a>
              <ul v-if="Object.keys(releasesByNamespace).length" class="list-none p-0 m-0 ml-3">
                <li v-for="ns in Object.keys(releasesByNamespace)" :key="ns" class="mb-0.5">
                  <a :href="'#ns-' + ns" @click.prevent="scrollTo('ns-' + ns)" class="text-gray-400 no-underline text-xs block py-0.5 transition-colors duration-200 hover:text-[#42b983]">{{ ns }}</a>
                </li>
              </ul>
            </li>
          </ul>
        </nav>
      </aside>

      <div class="flex-1 min-w-0">
        <div v-if="loading" class="bg-white p-8 rounded-lg shadow-md text-center text-gray-500">Loading modules...</div>

        <template v-else>
          <!-- ═══ CLUSTER MODULES ═══ -->
          <div v-if="activeTab === 'cluster'" class="bg-white p-8 rounded-lg shadow-md mb-6">
            <div v-for="(cat, idx) in clusterCategories" :key="cat.id" :id="'cat-' + cat.id"
                 class="scroll-mt-24"
                 :class="idx < clusterCategories.length - 1 ? 'mb-8 pb-8 border-b border-gray-200' : ''">
              <h3 class="text-sidebar-dark mb-1 text-xl">{{ cat.label }}</h3>
              <p class="text-gray-500 text-sm mb-4">{{ cat.description }}</p>

              <div class="space-y-3">
                <div v-for="mod in catalogByCategory[cat.id]" :key="mod.id" class="p-4 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
                  <div class="flex items-start justify-between gap-4">
                    <div class="flex items-start gap-3 flex-1 min-w-0">
                      <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center shrink-0 text-gray-500">
                        <font-awesome-icon :icon="['fas', mod.icon || 'cube']" />
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                          <span class="font-semibold text-sidebar-dark">{{ mod.name }}</span>
                          <span v-if="getClusterRelease(mod.id)" :class="statusBadgeClass(getClusterRelease(mod.id).status)" class="px-2 py-0.5 rounded-full text-xs font-medium">
                            {{ getClusterRelease(mod.id).status }}
                          </span>
                        </div>
                        <p class="text-gray-500 text-sm leading-relaxed m-0">{{ mod.description }}</p>
                        <div v-if="getClusterRelease(mod.id)?.status === 'failed'" class="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                          {{ getClusterRelease(mod.id).status_message }}
                        </div>
                      </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <template v-if="!getClusterRelease(mod.id)">
                        <button @click="openWizard(mod)" class="bg-[#42b983] text-white py-1.5 px-4 border-none rounded text-sm cursor-pointer transition-colors hover:bg-[#35a372]">
                          Install
                        </button>
                      </template>
                      <template v-else-if="['deploying', 'uninstalling', 'failed'].includes(getClusterRelease(mod.id).status)">
                        <button @click="openLogViewer(getClusterRelease(mod.id))" class="bg-gray-500 text-white py-1.5 px-3 border-none rounded text-sm cursor-pointer transition-colors hover:bg-gray-600" title="View Log">
                          <font-awesome-icon :icon="['fas', 'terminal']" />
                        </button>
                        <span v-if="getClusterRelease(mod.id).status !== 'failed'" class="text-gray-400 text-sm italic">{{ getClusterRelease(mod.id).status === 'deploying' ? 'Deploying...' : 'Uninstalling...' }}</span>
                        <button @click="forceDelete(getClusterRelease(mod.id))" class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer text-xs ml-2" title="Force delete">Force Remove</button>
                      </template>
                      <template v-else>
                        <button v-if="getClusterRelease(mod.id).log_output" @click="openLogViewer(getClusterRelease(mod.id))" class="bg-gray-500 text-white py-1.5 px-3 border-none rounded text-sm cursor-pointer transition-colors hover:bg-gray-600" title="View Log">
                          <font-awesome-icon :icon="['fas', 'terminal']" />
                        </button>
                        <button @click="openWizard(mod, true)" class="bg-blue-500 text-white py-1.5 px-3 border-none rounded text-sm cursor-pointer transition-colors hover:bg-blue-600" title="Upgrade">
                          <font-awesome-icon :icon="['fas', 'arrow-right']" />
                        </button>
                        <button @click="confirmUninstall(getClusterRelease(mod.id))" class="bg-red-500 text-white py-1.5 px-3 border-none rounded text-sm cursor-pointer transition-colors hover:bg-red-600" title="Uninstall">
                          <font-awesome-icon :icon="['fas', 'trash']" />
                        </button>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ═══ APPLICATION MODULES ═══ -->
          <div v-if="activeTab === 'applications'" class="bg-white p-8 rounded-lg shadow-md mb-6">
            <div v-for="(cat, idx) in appCategories" :key="cat.id" :id="'cat-' + cat.id"
                 class="scroll-mt-24"
                 :class="idx < appCategories.length - 1 ? 'mb-8 pb-8 border-b border-gray-200' : ''">
              <h3 class="text-sidebar-dark mb-1 text-xl">{{ cat.label }}</h3>
              <p class="text-gray-500 text-sm mb-4">{{ cat.description }}</p>

              <div class="space-y-5">
                <div v-for="mod in catalogByCategory[cat.id]" :key="mod.id" class="p-4 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
                  <div class="flex items-start justify-between gap-4">
                    <div class="flex items-start gap-3 flex-1 min-w-0">
                      <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center shrink-0 text-gray-500">
                        <font-awesome-icon :icon="['fas', mod.icon || 'cube']" />
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                          <span class="font-semibold text-sidebar-dark">{{ mod.name }}</span>
                        </div>
                        <p class="text-gray-500 text-sm leading-relaxed m-0">{{ mod.description }}</p>
                      </div>
                    </div>
                    <div class="shrink-0">
                      <button @click="openWizard(mod)" class="bg-[#42b983] text-white py-1.5 px-4 border-none rounded text-sm cursor-pointer transition-colors hover:bg-[#35a372]">
                        <font-awesome-icon :icon="['fas', 'plus']" class="mr-1" /> Deploy
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Deployed Releases -->
          <div id="deployed" class="scroll-mt-24">
            <h3 class="text-sidebar-dark mb-1 text-xl">Deployed Releases</h3>
            <p class="text-gray-500 text-sm mb-4">{{ activeTab === 'cluster' ? 'Cluster-scoped' : 'Application-scoped' }} Helm releases</p>

            <div v-if="!filteredReleases.length" class="bg-white p-8 rounded-lg shadow-md text-gray-400 text-center">
              {{ activeTab === 'cluster' ? 'No cluster modules deployed yet.' : 'No application modules deployed yet.' }} Install one from the catalog above.
            </div>
            <div v-else>
              <div v-for="(nsReleases, ns, nsIdx) in releasesByNamespace" :key="ns" :id="'ns-' + ns" class="bg-white rounded-lg shadow-md scroll-mt-24 overflow-hidden" :class="nsIdx < Object.keys(releasesByNamespace).length - 1 ? 'mb-4' : ''">
                <div class="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center gap-2">
                  <font-awesome-icon :icon="['fas', 'layer-group']" class="text-gray-400 text-xs" />
                  <code class="bg-gray-700 text-white px-2 py-0.5 rounded text-sm font-semibold">{{ ns }}</code>
                  <span class="text-gray-400 text-xs">{{ nsReleases.length }} release{{ nsReleases.length !== 1 ? 's' : '' }}</span>
                </div>
                <div class="px-6 py-4">
                  <table class="w-full table-fixed border-collapse">
                    <colgroup>
                      <col style="width: 20%" />
                      <col style="width: 50%" />
                      <col style="width: 12%" />
                      <col style="width: 18%" />
                    </colgroup>
                    <thead>
                      <tr class="border-b-2 border-gray-200">
                        <th class="text-left py-2.5 px-3 text-sidebar-dark text-sm font-semibold">Release</th>
                        <th class="text-left py-2.5 px-3 text-sidebar-dark text-sm font-semibold">Chart</th>
                        <th class="text-left py-2.5 px-3 text-sidebar-dark text-sm font-semibold">Status</th>
                        <th class="text-right py-2.5 px-3 text-sidebar-dark text-sm font-semibold">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="rel in nsReleases" :key="rel.id" class="border-b border-gray-100 hover:bg-gray-50">
                        <td class="py-3 px-3 font-medium text-sm truncate">{{ rel.release_name }}</td>
                        <td class="py-3 px-3 text-sm text-gray-600 truncate">{{ rel.chart_name }}</td>
                        <td class="py-3 px-3">
                          <span :class="statusBadgeClass(rel.status)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ rel.status }}</span>
                          <div v-if="rel.status === 'failed' && rel.status_message" class="text-red-500 text-xs mt-1 truncate" :title="rel.status_message">{{ rel.status_message }}</div>
                        </td>
                        <td class="py-3 px-3">
                          <div class="flex gap-2 justify-end">
                            <button v-if="rel.status === 'deploying' || rel.status === 'uninstalling' || rel.log_output" @click="openLogViewer(rel)" class="text-gray-500 hover:text-gray-700 bg-transparent border-none cursor-pointer text-sm" title="View Log">
                              <font-awesome-icon :icon="['fas', 'terminal']" />
                            </button>
                            <button v-if="['deploying', 'uninstalling', 'failed'].includes(rel.status)" @click="forceDelete(rel)" class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer text-xs" title="Force delete">Force Remove</button>
                            <button v-if="rel.status === 'deployed' && getCatalogEntry(rel)" @click="openUpgradeForRelease(rel)" class="text-blue-500 hover:text-blue-700 bg-transparent border-none cursor-pointer text-sm" title="Edit Values">
                              <font-awesome-icon :icon="['fas', 'pen']" />
                            </button>
                            <button v-if="rel.status === 'deployed'" @click="confirmUninstall(rel)" class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer text-sm" title="Uninstall">
                              <font-awesome-icon :icon="['fas', 'trash']" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Wizard Modal -->
    <div v-if="showWizard" class="fixed top-0 bottom-0 right-0 left-[250px] bg-black/50 z-50 flex items-center justify-center">
      <div class="bg-white rounded-lg max-w-[950px] w-[90%] max-h-[90vh] flex flex-col shadow-xl">
        <div class="p-8 pb-4 shrink-0 border-b border-gray-200">
          <h3 class="text-sidebar-dark text-xl mt-0 mb-2">{{ wizardUpgrade ? 'Upgrade' : 'Deploy' }} {{ wizardModule.name }}</h3>
          <p class="text-gray-500 text-sm mb-0">{{ wizardModule.description }}</p>
        </div>
        <form @submit.prevent="deployFromWizard" class="flex flex-col flex-1 min-h-0">
          <div class="flex-1 overflow-y-auto px-8 py-6">
            <!-- Release Name + Namespace -->
            <div class="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label class="block mb-1 text-sidebar-dark font-medium text-sm">Release Name *</label>
                <input v-model="wizardForm.release_name" type="text" required :disabled="wizardUpgrade" :placeholder="wizardModule.scope === 'application' ? 'e.g., cloudpirates-redis' : ''" class="w-full p-2 border border-gray-300 rounded text-sm disabled:bg-gray-100 disabled:cursor-not-allowed" />
                <small v-if="wizardModule.scope === 'application'" class="text-gray-400 text-xs">Unique name for this deployment</small>
              </div>
              <div>
                <label class="block mb-1 text-sidebar-dark font-medium text-sm">Namespace *</label>
                <input v-model="wizardForm.namespace" type="text" required :disabled="wizardUpgrade" :placeholder="wizardModule.scope === 'application' ? 'e.g., cloudpirates' : ''" class="w-full p-2 border border-gray-300 rounded text-sm disabled:bg-gray-100 disabled:cursor-not-allowed" />
                <small v-if="wizardModule.scope === 'application'" class="text-gray-400 text-xs">Namespace for isolation (created if missing)</small>
              </div>
            </div>

            <!-- Version -->
            <div class="mb-6">
              <label class="block mb-1 text-sidebar-dark font-medium text-sm">Chart Version</label>
              <input v-model="wizardForm.chart_version" type="text" placeholder="latest" class="w-full p-2 border border-gray-300 rounded text-sm" />
              <small class="text-gray-400 text-xs">Leave empty for the latest version</small>
            </div>

            <!-- Wizard Fields grouped by section -->
            <div v-for="section in wizardSections" :key="section" class="mb-6">
              <h4 class="text-sidebar-dark text-sm font-semibold uppercase tracking-wider mb-3 text-gray-500 border-b border-gray-200 pb-2">{{ section }}</h4>
              <div class="space-y-4">
                <div v-for="field in wizardFieldsBySection(section)" :key="field.key">
                  <!-- Boolean -->
                  <label v-if="field.type === 'boolean'" class="flex items-start gap-3 p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors">
                    <input type="checkbox" v-model="wizardValues[field.key]" class="mt-0.5 w-auto cursor-pointer" />
                    <div>
                      <div class="font-medium text-sidebar-dark text-sm">{{ field.label }}</div>
                      <div class="text-gray-500 text-xs mt-0.5 leading-relaxed">{{ field.description }}</div>
                    </div>
                  </label>
                  <!-- Select -->
                  <div v-else-if="field.type === 'select'">
                    <label class="block mb-1 text-sidebar-dark font-medium text-sm">{{ field.label }}</label>
                    <select v-model="wizardValues[field.key]" class="w-full p-2 border border-gray-300 rounded text-sm">
                      <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                    <small class="text-gray-500 text-xs mt-1 block">{{ field.description }}</small>
                  </div>
                  <!-- Number -->
                  <div v-else-if="field.type === 'number'">
                    <label class="block mb-1 text-sidebar-dark font-medium text-sm">{{ field.label }}</label>
                    <input type="number" v-model.number="wizardValues[field.key]" class="w-full max-w-[200px] p-2 border border-gray-300 rounded text-sm" />
                    <small class="text-gray-500 text-xs mt-1 block">{{ field.description }}</small>
                  </div>
                  <!-- Textarea -->
                  <div v-else-if="field.type === 'textarea'">
                    <label class="block mb-1 text-sidebar-dark font-medium text-sm">{{ field.label }}</label>
                    <textarea v-model="wizardValues[field.key]" rows="4" class="w-full p-2 border border-gray-300 rounded text-sm font-mono" />
                    <small class="text-gray-500 text-xs mt-1 block">{{ field.description }}</small>
                  </div>
                  <!-- Text (default) -->
                  <div v-else>
                    <label class="block mb-1 text-sidebar-dark font-medium text-sm">{{ field.label }}</label>
                    <input type="text" v-model="wizardValues[field.key]" :placeholder="field.placeholder || ''" :required="field.required" class="w-full p-2 border border-gray-300 rounded text-sm" />
                    <small class="text-gray-500 text-xs mt-1 block">{{ field.description }}</small>
                  </div>
                </div>
              </div>
            </div>

            <!-- Raw Values toggle -->
            <div class="mb-6">
              <button type="button" @click="showRawValues = !showRawValues" class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 bg-transparent border-none cursor-pointer">
                <font-awesome-icon :icon="['fas', showRawValues ? 'chevron-down' : 'chevron-right']" class="text-xs" />
                Advanced: Raw Values YAML
              </button>
              <div v-if="showRawValues" class="mt-2">
                <textarea v-model="wizardForm.raw_values" rows="8" placeholder="# Additional Helm values in YAML format" class="w-full p-3 border border-gray-300 rounded text-sm font-mono" />
                <small class="text-gray-400 text-xs">Merged with wizard field values. Raw values take precedence.</small>
              </div>
            </div>

            <!-- Notes -->
            <div v-if="wizardModule.notes" class="p-4 bg-blue-50 border-l-4 border-blue-500 rounded text-sm text-blue-800 leading-relaxed">
              <strong>Note:</strong> {{ wizardModule.notes }}
            </div>
          </div>

          <!-- Sticky Actions -->
          <div class="flex justify-end gap-3 px-8 py-4 border-t border-gray-200 shrink-0 bg-white rounded-b-lg">
            <button type="button" @click="showWizard = false" class="py-2.5 px-6 border border-gray-300 rounded text-sm cursor-pointer bg-white hover:bg-gray-50">Cancel</button>
            <button type="submit" :disabled="deploying" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed">
              {{ deploying ? 'Deploying...' : (wizardUpgrade ? 'Upgrade' : 'Deploy') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Generic Chart Modal -->
    <div v-if="showGeneric" class="fixed top-0 bottom-0 right-0 left-[250px] bg-black/50 z-50 flex items-center justify-center">
      <div class="bg-white rounded-lg max-w-[950px] w-[90%] max-h-[90vh] flex flex-col shadow-xl">
        <div class="p-8 pb-4 shrink-0 border-b border-gray-200">
          <h3 class="text-sidebar-dark text-xl mt-0 mb-0">Deploy Custom Helm Chart</h3>
        </div>
        <form @submit.prevent="deployGeneric" class="flex flex-col flex-1 min-h-0">
          <div class="flex-1 overflow-y-auto px-8 py-6">
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label class="block mb-1 text-sidebar-dark font-medium text-sm">Repository Name</label>
                <input v-model="genericForm.repo_name" type="text" required placeholder="e.g., bitnami" class="w-full p-2 border border-gray-300 rounded text-sm" />
              </div>
              <div>
                <label class="block mb-1 text-sidebar-dark font-medium text-sm">Repository URL</label>
                <input v-model="genericForm.repo_url" type="text" required placeholder="https://charts.bitnami.com/bitnami" class="w-full p-2 border border-gray-300 rounded text-sm" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label class="block mb-1 text-sidebar-dark font-medium text-sm">Chart Name</label>
                <input v-model="genericForm.chart_name" type="text" required placeholder="e.g., bitnami/redis" class="w-full p-2 border border-gray-300 rounded text-sm" />
              </div>
              <div>
                <label class="block mb-1 text-sidebar-dark font-medium text-sm">Chart Version</label>
                <input v-model="genericForm.chart_version" type="text" placeholder="latest" class="w-full p-2 border border-gray-300 rounded text-sm" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label class="block mb-1 text-sidebar-dark font-medium text-sm">Release Name</label>
                <input v-model="genericForm.release_name" type="text" required placeholder="my-release" class="w-full p-2 border border-gray-300 rounded text-sm" />
              </div>
              <div>
                <label class="block mb-1 text-sidebar-dark font-medium text-sm">Namespace</label>
                <input v-model="genericForm.namespace" type="text" required placeholder="default" class="w-full p-2 border border-gray-300 rounded text-sm" />
              </div>
            </div>
            <div>
              <label class="block mb-1 text-sidebar-dark font-medium text-sm">Values (YAML)</label>
              <textarea v-model="genericForm.values_yaml" rows="8" placeholder="# Helm values in YAML format" class="w-full p-3 border border-gray-300 rounded text-sm font-mono" />
            </div>
          </div>
          <div class="flex justify-end gap-3 px-8 py-4 border-t border-gray-200 shrink-0 bg-white rounded-b-lg">
            <button type="button" @click="showGeneric = false" class="py-2.5 px-6 border border-gray-300 rounded text-sm cursor-pointer bg-white hover:bg-gray-50">Cancel</button>
            <button type="submit" :disabled="deploying" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed">
              {{ deploying ? 'Deploying...' : 'Deploy' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Uninstall Confirmation Modal -->
    <div v-if="showUninstallConfirm" class="fixed top-0 bottom-0 right-0 left-[250px] bg-black/50 z-50 flex items-center justify-center">
      <div class="bg-white p-8 rounded-lg max-w-[450px] w-[90%] shadow-xl">
        <h3 class="text-sidebar-dark text-xl mt-0 mb-2">Uninstall {{ uninstallTarget?.release_name }}?</h3>
        <p class="text-gray-500 text-sm mb-6">
          This will run <code class="bg-gray-100 text-pink-600 px-1 rounded text-xs">helm uninstall</code> and remove all resources created by this release from namespace <code class="bg-gray-100 text-pink-600 px-1 rounded text-xs">{{ uninstallTarget?.namespace }}</code>.
        </p>
        <div class="flex justify-end gap-3">
          <button @click="showUninstallConfirm = false" class="py-2.5 px-6 border border-gray-300 rounded text-sm cursor-pointer bg-white hover:bg-gray-50">Cancel</button>
          <button @click="doUninstall" :disabled="deploying" class="bg-red-600 text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed">
            {{ deploying ? 'Uninstalling...' : 'Uninstall' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Import Existing Release Modal -->
    <div v-if="showImportConfirm" class="fixed top-0 bottom-0 right-0 left-[250px] bg-black/50 z-50 flex items-center justify-center">
      <div class="bg-white p-8 rounded-lg max-w-[500px] w-[90%] shadow-xl">
        <h3 class="text-sidebar-dark text-xl mt-0 mb-2">Release Already Exists in Cluster</h3>
        <p class="text-gray-500 text-sm mb-4">
          <code class="bg-gray-100 text-pink-600 px-1 rounded text-xs">{{ importTarget?.release_name }}</code> is already deployed in namespace
          <code class="bg-gray-100 text-pink-600 px-1 rounded text-xs">{{ importTarget?.namespace }}</code> but is not tracked by Ktizo.
        </p>
        <div class="bg-gray-50 rounded p-4 mb-6 text-sm space-y-1">
          <div><span class="text-gray-500">Chart:</span> <span class="font-medium text-gray-700">{{ importTarget?.chart }}</span></div>
          <div><span class="text-gray-500">Status:</span> <span class="font-medium text-gray-700">{{ importTarget?.status }}</span></div>
          <div><span class="text-gray-500">Revision:</span> <span class="font-medium text-gray-700">{{ importTarget?.revision }}</span></div>
          <div v-if="importTarget?.app_version"><span class="text-gray-500">App Version:</span> <span class="font-medium text-gray-700">{{ importTarget?.app_version }}</span></div>
        </div>
        <p class="text-gray-600 text-sm mb-6">Would you like to import this release so Ktizo can manage it?</p>
        <div class="flex justify-end gap-3">
          <button @click="showImportConfirm = false" class="py-2.5 px-6 border border-gray-300 rounded text-sm cursor-pointer bg-white hover:bg-gray-50">Cancel</button>
          <button @click="doImport" :disabled="deploying" class="bg-[#42b983] text-white py-2.5 px-6 border-none rounded text-sm font-medium cursor-pointer transition-colors hover:bg-[#35a372] disabled:bg-gray-300 disabled:cursor-not-allowed">
            {{ deploying ? 'Importing...' : 'Import Release' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Log Viewer Modal -->
    <div v-if="showLogViewer" class="fixed top-0 bottom-0 right-0 left-[250px] bg-black/50 z-50 flex items-center justify-center" @click.self="showLogViewer = false">
      <div class="bg-white rounded-lg max-w-[800px] w-[90%] max-h-[85vh] flex flex-col shadow-xl">
        <div class="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
          <div>
            <h3 class="text-sidebar-dark text-lg m-0">{{ logViewerTitle }}</h3>
            <span v-if="logViewerStatus" :class="statusBadgeClass(logViewerStatus)" class="px-2 py-0.5 rounded-full text-xs font-medium mt-1 inline-block">{{ logViewerStatus }}</span>
          </div>
          <button @click="showLogViewer = false" class="bg-transparent border-none text-gray-400 hover:text-gray-600 cursor-pointer text-xl leading-none">&times;</button>
        </div>
        <div ref="logContainer" class="flex-1 overflow-y-auto p-4 bg-gray-900 min-h-0">
          <pre class="text-green-400 text-xs font-mono whitespace-pre-wrap m-0 leading-relaxed">{{ logViewerContent || 'No log output available.' }}</pre>
        </div>
        <div class="p-3 border-t border-gray-200 flex justify-end shrink-0">
          <button @click="showLogViewer = false" class="py-2 px-5 border border-gray-300 rounded text-sm cursor-pointer bg-white hover:bg-gray-50">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'
import websocketService from '../services/websocket'
import { useToast } from 'vue-toastification'

export default {
  name: 'Modules',
  data() {
    return {
      loading: true,
      deploying: false,
      catalog: [],
      releases: [],

      // Cluster module categories
      clusterCategories: [
        { id: 'storage', label: 'Storage', description: 'Persistent volume providers for stateful workloads.' },
        { id: 'networking', label: 'Networking', description: 'Load balancers, ingress controllers, and network tools.' },
        { id: 'monitoring', label: 'Monitoring', description: 'Metrics, dashboards, and alerting.' },
        { id: 'security', label: 'Security', description: 'Certificate management and security tools.' },
        { id: 'ci-cd', label: 'CI/CD & GitOps', description: 'Continuous integration, delivery, and GitOps automation.' },
      ],

      // Application module categories
      appCategories: [
        { id: 'databases', label: 'Databases', description: 'Relational and NoSQL databases for application data.' },
        { id: 'ci-cd', label: 'CI/CD', description: 'Self-hosted CI/CD runners and build agents.' },
      ],

      // Wizard modal
      showWizard: false,
      wizardModule: {},
      wizardUpgrade: false,
      wizardUpgradeRelease: null,
      wizardForm: { release_name: '', namespace: '', chart_version: '', raw_values: '' },
      wizardValues: {},
      showRawValues: false,

      // Generic chart modal
      showGeneric: false,
      genericForm: { repo_name: '', repo_url: '', chart_name: '', chart_version: '', release_name: '', namespace: 'default', values_yaml: '' },

      // Uninstall confirmation
      showUninstallConfirm: false,
      uninstallTarget: null,

      // Import existing release
      showImportConfirm: false,
      importTarget: null,
      importParams: null,

      // Log viewer
      showLogViewer: false,
      logViewerTitle: '',
      logViewerContent: '',
      logViewerStatus: '',
      logViewerReleaseId: null,
    }
  },
  computed: {
    activeTab() {
      return this.$route.path.includes('/applications') ? 'applications' : 'cluster'
    },
    activeCategories() {
      return this.activeTab === 'cluster' ? this.clusterCategories : this.appCategories
    },
    filteredReleases() {
      return this.releases.filter(rel => {
        const scope = this.getReleaseScope(rel)
        if (this.activeTab === 'cluster') {
          return scope === 'cluster' || !rel.catalog_id
        }
        return scope === 'application' || (!scope && rel.catalog_id)
      })
    },
    releasesByNamespace() {
      const grouped = {}
      for (const rel of this.filteredReleases) {
        const ns = rel.namespace || 'default'
        if (!grouped[ns]) grouped[ns] = []
        grouped[ns].push(rel)
      }
      // Sort namespaces alphabetically
      const sorted = {}
      for (const ns of Object.keys(grouped).sort()) {
        sorted[ns] = grouped[ns]
      }
      return sorted
    },
    catalogByCategory() {
      const grouped = {}
      const scope = this.activeTab === 'cluster' ? 'cluster' : 'application'
      const cats = this.activeTab === 'cluster' ? this.clusterCategories : this.appCategories
      for (const cat of cats) {
        grouped[cat.id] = this.catalog.filter(m => m.category === cat.id && m.scope === scope)
      }
      return grouped
    },
    wizardSections() {
      if (!this.wizardModule.wizard_fields) return []
      const sections = []
      for (const f of this.wizardModule.wizard_fields) {
        const s = f.section || 'General'
        if (!sections.includes(s)) sections.push(s)
      }
      // Filter out sections where all fields are hidden by show_when
      return sections.filter(s => this.wizardFieldsBySection(s).length > 0)
    },
  },
  async mounted() {
    this.toast = useToast()
    await this.loadData()
    this.subscribeToEvents()
  },
  beforeUnmount() {
    this.unsubscribeWs?.()
  },
  methods: {
    scrollTo(id) {
      const el = document.getElementById(id)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        el.classList.add('toc-highlight')
        el.addEventListener('animationend', () => el.classList.remove('toc-highlight'), { once: true })
      }
    },
    async loadData() {
      this.loading = true
      try {
        const [catalog, releases] = await Promise.all([
          apiService.getModuleCatalog(),
          apiService.getModules(),
        ])
        this.catalog = catalog || []
        this.releases = releases || []
      } catch (e) {
        this.toast.error('Failed to load modules')
      } finally {
        this.loading = false
      }
    },
    // Cluster modules: one release per catalog_id
    getClusterRelease(catalogId) {
      return this.releases.find(r => r.catalog_id === catalogId)
    },
    // Application modules: multiple releases per catalog_id
    getAppReleases(catalogId) {
      return this.releases.filter(r => r.catalog_id === catalogId)
    },
    // Look up scope from catalog for a release
    getReleaseScope(rel) {
      if (!rel.catalog_id) return null
      const entry = this.catalog.find(m => m.id === rel.catalog_id)
      return entry?.scope || null
    },
    getCatalogEntry(rel) {
      if (!rel.catalog_id) return null
      return this.catalog.find(m => m.id === rel.catalog_id) || null
    },
    openUpgradeForRelease(rel) {
      const mod = this.getCatalogEntry(rel)
      if (mod) {
        this.openWizardForRelease(mod, rel)
      }
    },
    statusBadgeClass(status) {
      switch (status) {
        case 'deployed': return 'bg-green-100 text-green-700'
        case 'failed': return 'bg-red-100 text-red-700'
        case 'deploying': return 'bg-blue-100 text-blue-700'
        case 'uninstalling': return 'bg-amber-100 text-amber-700'
        case 'pending': return 'bg-gray-100 text-gray-600'
        default: return 'bg-gray-100 text-gray-600'
      }
    },
    wizardFieldsBySection(section) {
      return (this.wizardModule.wizard_fields || []).filter(f => {
        if ((f.section || 'General') !== section) return false
        if (f.show_when) {
          return this.wizardValues[f.show_when.key] === f.show_when.value
        }
        return true
      })
    },
    openWizard(mod, upgrade = false) {
      this.wizardModule = mod
      this.wizardUpgrade = upgrade
      this.wizardUpgradeRelease = null
      this.showRawValues = false

      if (upgrade && mod.scope !== 'application') {
        // Cluster module upgrade — find the single existing release
        const existing = this.getClusterRelease(mod.id)
        if (existing) {
          this.wizardUpgradeRelease = existing
          this.wizardForm = {
            release_name: existing.release_name,
            namespace: existing.namespace,
            chart_version: existing.chart_version || '',
            raw_values: '',
          }
          let parsed = null
          try {
            parsed = existing.values_json ? JSON.parse(existing.values_json) : null
          } catch {
            parsed = null
          }
          if (parsed && Object.keys(parsed).length > 0) {
            this.wizardValues = parsed
          } else {
            this.wizardValues = {}
            for (const field of (mod.wizard_fields || [])) {
              if (field.default !== undefined && field.default !== null) {
                this.wizardValues[field.key] = field.default
              }
            }
            if (existing.values_yaml) {
              this.wizardForm.raw_values = existing.values_yaml
              this.showRawValues = true
            }
          }
        }
      } else {
        // New install (cluster or application)
        this.wizardForm = {
          release_name: mod.default_release_name || '',
          namespace: mod.default_namespace || '',
          chart_version: '',
          raw_values: '',
        }
        this.wizardValues = {}
        for (const field of (mod.wizard_fields || [])) {
          if (field.default !== undefined && field.default !== null) {
            this.wizardValues[field.key] = field.default
          }
        }
      }
      this.showWizard = true
    },
    openWizardForRelease(mod, rel) {
      // Upgrade a specific release — populate wizard from values_json or fall back to defaults
      this.wizardModule = mod
      this.wizardUpgrade = true
      this.wizardUpgradeRelease = rel
      this.showRawValues = false
      this.wizardForm = {
        release_name: rel.release_name,
        namespace: rel.namespace,
        chart_version: rel.chart_version || '',
        raw_values: '',
      }
      let parsed = null
      try {
        parsed = rel.values_json ? JSON.parse(rel.values_json) : null
      } catch {
        parsed = null
      }
      if (parsed && Object.keys(parsed).length > 0) {
        this.wizardValues = parsed
      } else {
        // No values_json — initialize from wizard field defaults and show raw YAML
        this.wizardValues = {}
        for (const field of (mod.wizard_fields || [])) {
          if (field.default !== undefined && field.default !== null) {
            this.wizardValues[field.key] = field.default
          }
        }
        if (rel.values_yaml) {
          this.wizardForm.raw_values = rel.values_yaml
          this.showRawValues = true
        }
      }
      this.showWizard = true
    },
    buildValuesYaml() {
      const lines = []
      const flat = {}
      for (const [key, value] of Object.entries(this.wizardValues)) {
        if (key.startsWith('_')) continue
        if (value === '' || value === null || value === undefined) continue
        flat[key] = value
      }

      const nested = {}
      for (const [key, value] of Object.entries(flat)) {
        const parts = key.split('.')
        let d = nested
        for (let i = 0; i < parts.length - 1; i++) {
          d = d[parts[i]] = d[parts[i]] || {}
        }
        d[parts[parts.length - 1]] = value
      }

      const defaults = this.wizardModule.default_values || {}
      const merged = { ...defaults }
      this.deepMerge(merged, nested)

      // Metrics Server: build args list from underscore-prefixed wizard fields
      if (this.wizardModule?.id === 'metrics-server') {
        const args = [
          '--cert-dir=/tmp',
          '--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname',
          '--kubelet-use-node-status-port',
          `--metric-resolution=${this.wizardValues._metricResolution || '15s'}`,
        ]
        if (this.wizardValues._kubeletInsecureTls) {
          args.push('--kubelet-insecure-tls')
        }
        merged.args = args
      }

      if (Object.keys(merged).length > 0) {
        lines.push(this.toYaml(merged, 0))
      }

      if (this.wizardForm.raw_values?.trim()) {
        if (lines.length > 0) lines.push('')
        lines.push(this.wizardForm.raw_values.trim())
      }

      return lines.join('\n') || null
    },
    deepMerge(target, source) {
      for (const key of Object.keys(source)) {
        if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key]) &&
            target[key] && typeof target[key] === 'object' && !Array.isArray(target[key])) {
          this.deepMerge(target[key], source[key])
        } else {
          target[key] = source[key]
        }
      }
    },
    toYaml(obj, indent) {
      const lines = []
      const prefix = '  '.repeat(indent)
      for (const [key, value] of Object.entries(obj)) {
        if (value && typeof value === 'object' && !Array.isArray(value)) {
          lines.push(`${prefix}${key}:`)
          lines.push(this.toYaml(value, indent + 1))
        } else if (typeof value === 'boolean') {
          lines.push(`${prefix}${key}: ${value}`)
        } else if (typeof value === 'number') {
          lines.push(`${prefix}${key}: ${value}`)
        } else if (typeof value === 'string') {
          if (value === '' || value === 'true' || value === 'false' || /^\d+$/.test(value)) {
            lines.push(`${prefix}${key}: "${value}"`)
          } else {
            lines.push(`${prefix}${key}: ${value}`)
          }
        } else if (Array.isArray(value)) {
          lines.push(`${prefix}${key}:`)
          for (const item of value) {
            lines.push(`${prefix}  - ${item}`)
          }
        }
      }
      return lines.join('\n')
    },
    async deployFromWizard() {
      this.deploying = true
      try {
        const valuesYaml = this.buildValuesYaml()
        const valuesJson = JSON.stringify(this.wizardValues)

        if (this.wizardUpgrade && this.wizardUpgradeRelease) {
          await apiService.upgradeModule(this.wizardUpgradeRelease.id, {
            chart_version: this.wizardForm.chart_version || null,
            values_yaml: valuesYaml,
            values_json: valuesJson,
          })
          this.toast.info(`Upgrading ${this.wizardForm.release_name}...`)
        } else {
          const installParams = {
            release_name: this.wizardForm.release_name,
            namespace: this.wizardForm.namespace,
            chart_name: this.wizardModule.chart_name,
            chart_version: this.wizardForm.chart_version || null,
            repo_name: this.wizardModule.repo_name,
            repo_url: this.wizardModule.repo_url,
            catalog_id: this.wizardModule.id,
            values_yaml: valuesYaml,
            values_json: valuesJson,
          }
          const result = await apiService.installModule(installParams)

          // Release exists in cluster but not tracked — offer to import
          if (result?.conflict === 'exists_in_cluster') {
            this.importTarget = result
            this.importParams = installParams
            this.showWizard = false
            this.showImportConfirm = true
            return
          }

          this.toast.info(`Deploying ${this.wizardForm.release_name}...`)
        }
        this.showWizard = false
        await this.loadReleases()
      } catch (error) {
        this.toast.error(error.message || 'Deployment failed')
      } finally {
        this.deploying = false
      }
    },
    async doImport() {
      if (!this.importParams) return
      this.deploying = true
      try {
        await apiService.importModule(this.importParams)
        this.toast.success(`Imported ${this.importTarget.release_name} into Ktizo`)
        this.showImportConfirm = false
        this.importTarget = null
        this.importParams = null
        await this.loadReleases()
      } catch (error) {
        this.toast.error(error.message || 'Import failed')
      } finally {
        this.deploying = false
      }
    },
    openGenericModal() {
      this.genericForm = { repo_name: '', repo_url: '', chart_name: '', chart_version: '', release_name: '', namespace: 'default', values_yaml: '' }
      this.showGeneric = true
    },
    async deployGeneric() {
      this.deploying = true
      try {
        const installParams = {
          release_name: this.genericForm.release_name,
          namespace: this.genericForm.namespace,
          chart_name: this.genericForm.chart_name,
          chart_version: this.genericForm.chart_version || null,
          repo_name: this.genericForm.repo_name,
          repo_url: this.genericForm.repo_url,
          values_yaml: this.genericForm.values_yaml || null,
        }
        const result = await apiService.installModule(installParams)

        if (result?.conflict === 'exists_in_cluster') {
          this.importTarget = result
          this.importParams = installParams
          this.showGeneric = false
          this.showImportConfirm = true
          return
        }

        this.toast.info(`Installing ${this.genericForm.release_name}...`)
        this.showGeneric = false
        await this.loadReleases()
      } catch (error) {
        this.toast.error(error.message || 'Deployment failed')
      } finally {
        this.deploying = false
      }
    },
    confirmUninstall(release) {
      this.uninstallTarget = release
      this.showUninstallConfirm = true
    },
    async doUninstall() {
      if (!this.uninstallTarget) return
      this.deploying = true
      try {
        await apiService.uninstallModule(this.uninstallTarget.id)
        this.toast.info(`Uninstalling ${this.uninstallTarget.release_name}...`)
        this.showUninstallConfirm = false
        this.uninstallTarget = null
        await this.loadReleases()
      } catch (error) {
        this.toast.error(error.message || 'Uninstall failed')
      } finally {
        this.deploying = false
      }
    },
    async forceDelete(release) {
      try {
        await apiService.forceDeleteModule(release.id)
        this.toast.warning(`Force-deleted ${release.release_name}`)
        await this.loadReleases()
      } catch (error) {
        this.toast.error(error.message || 'Failed to force-delete')
      }
    },
    async openLogViewer(release) {
      this.logViewerReleaseId = release.id
      this.logViewerTitle = `Log: ${release.release_name}`
      this.logViewerStatus = release.status
      this.logViewerContent = ''
      this.showLogViewer = true

      try {
        const result = await apiService.getModuleLog(release.id)
        if (result && result.log) {
          this.logViewerContent = result.log
          this.$nextTick(() => this.scrollLogToBottom())
        }
      } catch {
        this.logViewerContent = '(No stored log available)'
      }
    },
    scrollLogToBottom() {
      const el = this.$refs.logContainer
      if (el) el.scrollTop = el.scrollHeight
    },
    async loadReleases() {
      try {
        this.releases = await apiService.getModules() || []
      } catch {
        // Silent
      }
    },
    subscribeToEvents() {
      this.unsubscribeWs = websocketService.subscribe((event) => {
        if (event.type === 'module_status_changed') {
          const data = event.data || event
          const idx = this.releases.findIndex(r => r.id === data.id)
          if (this.showLogViewer && this.logViewerReleaseId === data.id) {
            this.logViewerStatus = data.status
          }
          if (data.status === 'uninstalled') {
            if (idx >= 0) this.releases.splice(idx, 1)
            this.toast.success(`${data.release_name || 'Module'} uninstalled`)
          } else if (idx >= 0) {
            this.releases[idx].status = data.status
            this.releases[idx].status_message = data.status_message
            if (data.status === 'deployed') {
              this.toast.success(`${data.release_name || 'Module'} deployed successfully`)
            } else if (data.status === 'failed') {
              this.toast.error(`${data.release_name || 'Module'} failed: ${data.status_message}`)
            }
          } else {
            this.loadReleases()
          }
        } else if (event.type === 'module_installing') {
          this.loadReleases()
        } else if (event.type === 'module_log') {
          const data = event.data || event
          if (this.showLogViewer && this.logViewerReleaseId === data.id) {
            this.logViewerContent = data.log || ''
            this.$nextTick(() => this.scrollLogToBottom())
          }
        }
      })
    },
  },
}
</script>
