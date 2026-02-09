<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">RBAC Management</h2>
        <p class="text-gray-500 mt-1 mb-0">Manage Kubernetes service accounts, roles, and bindings</p>
      </div>
      <button @click="openWizard" class="bg-green-600 text-white py-2.5 px-5 rounded border-none cursor-pointer text-[0.9rem] font-medium transition-colors hover:bg-green-700 flex items-center gap-2">
        <font-awesome-icon :icon="['fas', 'user-shield']" /> Create User
      </button>
    </div>

    <!-- Namespace selector + controls -->
    <div class="flex items-center gap-4 mb-6">
      <div class="flex items-center gap-2" v-if="tabNeedsNamespace">
        <label class="font-medium text-gray-700 whitespace-nowrap text-sm">Namespace:</label>
        <select v-model="selectedNamespace" @change="onFilterChange" class="p-2 border border-gray-300 rounded text-sm">
          <option value="">All Namespaces</option>
          <option v-for="ns in namespaces" :key="ns" :value="ns">{{ ns }}</option>
        </select>
      </div>
      <div class="flex items-center gap-2 ml-auto">
        <label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" v-model="showSystem" @change="onFilterChange" class="cursor-pointer" />
          Show system resources
        </label>
      </div>
    </div>

    <!-- Side-by-side layout: list left, graph right -->
    <div class="flex gap-6 items-start">

      <!-- Left: List content -->
      <div class="w-2/5 min-w-0 bg-white rounded-lg shadow-sm p-5 overflow-y-auto" style="max-height: calc(100vh - 220px)">
        <!-- Tabs -->
        <div class="flex border-b border-gray-200 mb-6 gap-1">
          <button v-for="t in tabs" :key="t.key" @click="activeTab = t.key"
            class="py-2.5 px-4 text-sm font-medium border-b-2 transition-colors cursor-pointer bg-transparent"
            :class="activeTab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'">
            {{ t.label }}
            <span v-if="tabCounts[t.key] !== undefined" class="ml-1 text-xs text-gray-400">({{ tabCounts[t.key] }})</span>
          </button>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="text-center py-12 text-gray-500">Loading...</div>

        <!-- Empty state -->
        <div v-else-if="currentItems.length === 0" class="text-center py-12 bg-white rounded-lg shadow-sm">
          <p class="text-gray-500">No {{ activeTabLabel }} found{{ selectedNamespace ? ` in ${selectedNamespace}` : '' }}.</p>
          <p class="text-gray-400 text-sm mt-2" v-if="!showSystem">System resources are hidden. Enable "Show system resources" to see all.</p>
        </div>

        <!-- Service Accounts Tab -->
        <div v-else-if="activeTab === 'serviceaccounts'" class="space-y-3">
          <div v-for="sa in currentItems" :key="`${sa.namespace}/${sa.name}`"
            @click="focusNode(`sa:${sa.namespace}/${sa.name}`)"
            class="bg-white rounded-lg shadow-sm p-4 flex items-center justify-between hover:shadow-md transition-shadow cursor-pointer"
            :class="{
              'ring-2 ring-blue-500': focusedNodeId === `sa:${sa.namespace}/${sa.name}`,
              'bg-blue-50 border border-blue-200': focusedNodeId !== `sa:${sa.namespace}/${sa.name}` && relatedNodeIds.has(`sa:${sa.namespace}/${sa.name}`)
            }">
            <div class="flex items-center gap-4">
              <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                <font-awesome-icon :icon="['fas', 'user-shield']" class="text-sm" />
              </div>
              <div>
                <div class="font-medium text-gray-900">{{ sa.name }}</div>
                <div class="text-xs text-gray-500 mt-0.5">{{ sa.namespace }}</div>
              </div>
              <span v-if="sa.is_system" class="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">system</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xs text-gray-400">{{ formatDate(sa.creation_timestamp) }}</span>
              <button v-if="!sa.is_system" @click="confirmDelete('serviceaccount', sa)"
                class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer p-1" title="Delete">
                <font-awesome-icon :icon="['fas', 'trash']" />
              </button>
            </div>
          </div>
        </div>

        <!-- Roles Tab -->
        <div v-else-if="activeTab === 'roles'" class="space-y-3">
          <div v-for="role in currentItems" :key="`${role.namespace}/${role.name}`"
            @click="focusNode(`role:${role.namespace}/${role.name}`)"
            class="bg-white rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow cursor-pointer"
            :class="{
              'ring-2 ring-purple-500': focusedNodeId === `role:${role.namespace}/${role.name}`,
              'bg-purple-50 border border-purple-200': focusedNodeId !== `role:${role.namespace}/${role.name}` && relatedNodeIds.has(`role:${role.namespace}/${role.name}`)
            }">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4">
                <div class="w-8 h-8 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center">
                  <font-awesome-icon :icon="['fas', 'lock']" class="text-sm" />
                </div>
                <div>
                  <div class="font-medium text-gray-900">{{ role.name }}</div>
                  <div class="text-xs text-gray-500 mt-0.5">{{ role.namespace }} &middot; {{ role.rules.length }} rule{{ role.rules.length !== 1 ? 's' : '' }}</div>
                </div>
                <span v-if="role.is_system" class="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">system</span>
              </div>
              <div class="flex items-center gap-3">
                <button @click="toggleRoleDetail(role)" class="text-blue-500 hover:text-blue-700 bg-transparent border-none cursor-pointer p-1 text-sm">
                  {{ expandedRoles.has(`${role.namespace}/${role.name}`) ? 'Hide' : 'Rules' }}
                </button>
                <button v-if="!role.is_system" @click="confirmDelete('role', role)"
                  class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer p-1" title="Delete">
                  <font-awesome-icon :icon="['fas', 'trash']" />
                </button>
              </div>
            </div>
            <div v-if="expandedRoles.has(`${role.namespace}/${role.name}`)" class="mt-3 pt-3 border-t border-gray-100">
              <div v-for="(rule, idx) in role.rules" :key="idx" class="text-sm text-gray-600 py-1">
                <span class="text-gray-900 font-medium">{{ describeRule(rule) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ClusterRoles Tab -->
        <div v-else-if="activeTab === 'clusterroles'" class="space-y-3">
          <div v-for="cr in currentItems" :key="cr.name"
            @click="focusNode(`clusterrole:${cr.name}`)"
            class="bg-white rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow cursor-pointer"
            :class="{
              'ring-2 ring-amber-500': focusedNodeId === `clusterrole:${cr.name}`,
              'bg-amber-50 border border-amber-200': focusedNodeId !== `clusterrole:${cr.name}` && relatedNodeIds.has(`clusterrole:${cr.name}`)
            }">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4">
                <div class="w-8 h-8 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center">
                  <font-awesome-icon :icon="['fas', 'shield-halved']" class="text-sm" />
                </div>
                <div>
                  <div class="font-medium text-gray-900">{{ cr.name }}</div>
                  <div class="text-xs text-gray-500 mt-0.5">cluster-scoped &middot; {{ cr.rules.length }} rule{{ cr.rules.length !== 1 ? 's' : '' }}</div>
                </div>
                <span v-if="cr.is_system" class="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">system</span>
              </div>
              <div class="flex items-center gap-3">
                <button @click="toggleClusterRoleDetail(cr)" class="text-blue-500 hover:text-blue-700 bg-transparent border-none cursor-pointer p-1 text-sm">
                  {{ expandedClusterRoles.has(cr.name) ? 'Hide' : 'Rules' }}
                </button>
                <button v-if="!cr.is_system" @click="confirmDelete('clusterrole', cr)"
                  class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer p-1" title="Delete">
                  <font-awesome-icon :icon="['fas', 'trash']" />
                </button>
              </div>
            </div>
            <div v-if="expandedClusterRoles.has(cr.name)" class="mt-3 pt-3 border-t border-gray-100">
              <div v-for="(rule, idx) in cr.rules" :key="idx" class="text-sm text-gray-600 py-1">
                <span class="text-gray-900 font-medium">{{ describeRule(rule) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- RoleBindings Tab -->
        <div v-else-if="activeTab === 'rolebindings'" class="space-y-3">
          <div v-for="rb in currentItems" :key="`${rb.namespace}/${rb.name}`"
            @click="focusBindingNodes(rb)"
            class="bg-white rounded-lg shadow-sm p-4 flex items-center justify-between hover:shadow-md transition-shadow cursor-pointer"
            :class="{
              'ring-2 ring-green-500': focusedNodeId === `rb:${rb.namespace}/${rb.name}`,
              'bg-green-50 border border-green-200': focusedNodeId !== `rb:${rb.namespace}/${rb.name}` && relatedNodeIds.has(`rb:${rb.namespace}/${rb.name}`)
            }">
            <div class="flex items-center gap-4">
              <div class="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center">
                <font-awesome-icon :icon="['fas', 'arrow-right']" class="text-sm" />
              </div>
              <div>
                <div class="font-medium text-gray-900">{{ rb.name }}</div>
                <div class="text-xs text-gray-500 mt-0.5">
                  {{ rb.namespace }} &middot;
                  {{ rb.role_ref.kind }}/{{ rb.role_ref.name }}
                  &rarr;
                  {{ rb.subjects.map(s => s.name).join(', ') }}
                </div>
              </div>
              <span v-if="rb.is_system" class="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">system</span>
            </div>
            <button v-if="!rb.is_system" @click="confirmDelete('rolebinding', rb)"
              class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer p-1" title="Delete">
              <font-awesome-icon :icon="['fas', 'trash']" />
            </button>
          </div>
        </div>

        <!-- ClusterRoleBindings Tab -->
        <div v-else-if="activeTab === 'clusterrolebindings'" class="space-y-3">
          <div v-for="crb in currentItems" :key="crb.name"
            @click="focusBindingNodes(crb)"
            class="bg-white rounded-lg shadow-sm p-4 flex items-center justify-between hover:shadow-md transition-shadow cursor-pointer"
            :class="{
              'ring-2 ring-teal-500': focusedNodeId === `crb:${crb.name}`,
              'bg-teal-50 border border-teal-200': focusedNodeId !== `crb:${crb.name}` && relatedNodeIds.has(`crb:${crb.name}`)
            }">
            <div class="flex items-center gap-4">
              <div class="w-8 h-8 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center">
                <font-awesome-icon :icon="['fas', 'arrow-right']" class="text-sm" />
              </div>
              <div>
                <div class="font-medium text-gray-900">{{ crb.name }}</div>
                <div class="text-xs text-gray-500 mt-0.5">
                  {{ crb.role_ref.kind }}/{{ crb.role_ref.name }}
                  &rarr;
                  {{ crb.subjects.map(s => `${s.name}${s.namespace ? ` (${s.namespace})` : ''}`).join(', ') }}
                </div>
              </div>
              <span v-if="crb.is_system" class="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">system</span>
            </div>
            <button v-if="!crb.is_system" @click="confirmDelete('clusterrolebinding', crb)"
              class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer p-1" title="Delete">
              <font-awesome-icon :icon="['fas', 'trash']" />
            </button>
          </div>
        </div>
      </div>

      <!-- Right: Graph -->
      <div class="w-3/5 sticky top-20">
        <RbacGraph
          ref="graph"
          :service-accounts="serviceAccounts"
          :roles="roles"
          :cluster-roles="clusterRoles"
          :role-bindings="roleBindings"
          :cluster-role-bindings="clusterRoleBindings"
          :show-system="showSystem"
          :focus-node-id="focusedNodeId"
          @node-selected="onGraphNodeSelected"
          @related-nodes="onRelatedNodes"
        />
      </div>

    </div>

    <!-- Wizard Modal -->
    <div v-if="wizardOpen" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" @click.self="wizardOpen = false">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <!-- Wizard header -->
        <div class="p-6 border-b border-gray-200">
          <h3 class="text-xl font-bold text-gray-900 m-0">Create User</h3>
          <p class="text-gray-500 text-sm mt-1 mb-0">Set up a Kubernetes ServiceAccount with roles and permissions</p>
          <!-- Step indicator -->
          <div class="flex items-center gap-2 mt-4">
            <div v-for="s in wizardStepCount" :key="s"
              class="h-1.5 flex-1 rounded-full transition-colors"
              :class="s <= wizardStep ? 'bg-blue-600' : 'bg-gray-200'">
            </div>
          </div>
          <div class="text-xs text-gray-400 mt-1">Step {{ wizardStep }} of {{ wizardStepCount }}</div>
        </div>

        <!-- Step 1: Identity -->
        <div v-if="wizardStep === 1" class="p-6 space-y-5">
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
            A <strong>ServiceAccount</strong> is a Kubernetes identity used by applications or users. Think of it as a "user account" within your cluster.
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input v-model="wizard.name" type="text" placeholder="e.g., deploy-bot"
              class="w-full p-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              @input="validateName" />
            <p v-if="wizardNameError" class="text-red-500 text-xs mt-1">{{ wizardNameError }}</p>
            <p class="text-gray-400 text-xs mt-1">Must be lowercase, alphanumeric, and may contain hyphens.</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Namespace</label>
            <select v-model="wizard.namespace" class="w-full p-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="" disabled>Select a namespace</option>
              <option v-for="ns in namespaces" :key="ns" :value="ns">{{ ns }}</option>
            </select>
          </div>
        </div>

        <!-- Step 2: Permissions -->
        <div v-if="wizardStep === 2" class="p-6 space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-3">How do you want to assign permissions?</label>
            <div class="space-y-2">
              <label class="flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors"
                :class="wizard.permMode === 'preset' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'">
                <input type="radio" v-model="wizard.permMode" value="preset" class="accent-blue-600" />
                <div>
                  <div class="font-medium text-sm">Use a preset role</div>
                  <div class="text-xs text-gray-500">Choose from common permission patterns</div>
                </div>
              </label>
              <label class="flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors"
                :class="wizard.permMode === 'existing' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'">
                <input type="radio" v-model="wizard.permMode" value="existing" class="accent-blue-600" />
                <div>
                  <div class="font-medium text-sm">Use an existing role</div>
                  <div class="text-xs text-gray-500">Bind to a Role or ClusterRole already in the cluster</div>
                </div>
              </label>
              <label class="flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors"
                :class="wizard.permMode === 'custom' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'">
                <input type="radio" v-model="wizard.permMode" value="custom" class="accent-blue-600" />
                <div>
                  <div class="font-medium text-sm">Define custom permissions</div>
                  <div class="text-xs text-gray-500">Build rules manually with full control</div>
                </div>
              </label>
            </div>
          </div>

          <!-- Scope toggle -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Scope</label>
            <div class="flex gap-2">
              <button @click="wizard.scope = 'namespace'"
                class="py-2 px-4 rounded-lg text-sm font-medium border transition-colors cursor-pointer"
                :class="wizard.scope === 'namespace' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'">
                Namespace-scoped
              </button>
              <button @click="wizard.scope = 'cluster'"
                class="py-2 px-4 rounded-lg text-sm font-medium border transition-colors cursor-pointer"
                :class="wizard.scope === 'cluster' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'">
                Cluster-wide
              </button>
            </div>
          </div>

          <!-- Preset cards -->
          <div v-if="wizard.permMode === 'preset'" class="space-y-3">
            <div v-for="preset in presets" :key="preset.id"
              @click="wizard.presetId = preset.id; wizard.scope = preset.scope"
              class="p-4 border rounded-lg cursor-pointer transition-all"
              :class="wizard.presetId === preset.id ? 'border-blue-500 bg-blue-50 shadow-sm' : 'border-gray-200 hover:border-gray-300'">
              <div class="flex items-center justify-between">
                <div class="font-medium text-sm text-gray-900">{{ preset.label }}</div>
                <span class="px-2 py-0.5 rounded text-xs"
                  :class="preset.scope === 'cluster' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'">
                  {{ preset.scope }}
                </span>
              </div>
              <div class="text-xs text-gray-500 mt-1">{{ preset.description }}</div>
              <div class="text-xs text-gray-400 mt-2 italic">{{ preset.explanation }}</div>
            </div>
          </div>

          <!-- Existing role picker -->
          <div v-if="wizard.permMode === 'existing'" class="space-y-3">
            <select v-model="wizard.existingRole" class="w-full p-2.5 border border-gray-300 rounded-lg text-sm">
              <option :value="null" disabled>Select a role</option>
              <optgroup label="Roles (namespace-scoped)">
                <option v-for="r in allRoles" :key="`role-${r.namespace}/${r.name}`" :value="{ kind: 'Role', name: r.name, namespace: r.namespace }">
                  {{ r.name }} ({{ r.namespace }})
                </option>
              </optgroup>
              <optgroup label="ClusterRoles (cluster-wide)">
                <option v-for="cr in allClusterRoles" :key="`cr-${cr.name}`" :value="{ kind: 'ClusterRole', name: cr.name }">
                  {{ cr.name }}
                </option>
              </optgroup>
            </select>
          </div>
        </div>

        <!-- Step 3: Custom Rules (only if custom mode) -->
        <div v-if="wizardStep === 3 && wizard.permMode === 'custom'" class="p-6 space-y-4">
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
            Each rule grants access to specific Kubernetes resources. Add one or more rules to define what this user can do.
          </div>
          <div v-for="(rule, idx) in wizard.customRules" :key="idx" class="border border-gray-200 rounded-lg p-4 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-700">Rule {{ idx + 1 }}</span>
              <button v-if="wizard.customRules.length > 1" @click="wizard.customRules.splice(idx, 1)"
                class="text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer text-sm">Remove</button>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">API Groups</label>
              <input v-model="rule.apiGroups" type="text" placeholder='e.g., "", apps, batch'
                class="w-full p-2 border border-gray-300 rounded text-sm" />
              <p class="text-xs text-gray-400 mt-0.5">Comma-separated. Use "" for core API group.</p>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Resources</label>
              <input v-model="rule.resources" type="text" placeholder="e.g., pods, deployments, services"
                class="w-full p-2 border border-gray-300 rounded text-sm" />
              <p class="text-xs text-gray-400 mt-0.5">Comma-separated resource names.</p>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Verbs</label>
              <div class="flex flex-wrap gap-2 mt-1">
                <label v-for="verb in availableVerbs" :key="verb" class="flex items-center gap-1 text-sm cursor-pointer">
                  <input type="checkbox" :value="verb" v-model="rule.verbs" class="accent-blue-600 cursor-pointer" />
                  {{ verb }}
                </label>
              </div>
            </div>
            <div class="text-xs text-gray-500 italic mt-1">{{ describeCustomRule(rule) }}</div>
          </div>
          <button @click="addCustomRule"
            class="text-blue-600 hover:text-blue-700 bg-transparent border border-blue-300 rounded-lg px-4 py-2 text-sm cursor-pointer hover:bg-blue-50 transition-colors">
            <font-awesome-icon :icon="['fas', 'plus']" class="mr-1" /> Add Rule
          </button>
        </div>

        <!-- Step 3 or 4: Review -->
        <div v-if="wizardStep === wizardStepCount" class="p-6 space-y-4">
          <h4 class="text-lg font-semibold text-gray-900 m-0">Review</h4>
          <div class="bg-gray-50 rounded-lg p-4 space-y-3 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-500">ServiceAccount</span>
              <span class="font-medium text-gray-900">{{ wizard.name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">Namespace</span>
              <span class="font-medium text-gray-900">{{ wizard.namespace }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">Scope</span>
              <span class="font-medium text-gray-900">{{ wizard.scope === 'cluster' ? 'Cluster-wide' : 'Namespace-scoped' }}</span>
            </div>
            <div class="flex justify-between" v-if="wizard.permMode === 'preset'">
              <span class="text-gray-500">Role</span>
              <span class="font-medium text-gray-900">{{ wizard.name }}-role (from preset: {{ selectedPreset?.label }})</span>
            </div>
            <div class="flex justify-between" v-if="wizard.permMode === 'existing'">
              <span class="text-gray-500">Existing Role</span>
              <span class="font-medium text-gray-900">{{ wizard.existingRole?.kind }}/{{ wizard.existingRole?.name }}</span>
            </div>
            <div class="flex justify-between" v-if="wizard.permMode === 'custom'">
              <span class="text-gray-500">Role</span>
              <span class="font-medium text-gray-900">{{ wizard.name }}-role (custom, {{ wizard.customRules.length }} rule{{ wizard.customRules.length !== 1 ? 's' : '' }})</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">Binding</span>
              <span class="font-medium text-gray-900">{{ wizard.name }}-binding</span>
            </div>
          </div>

          <!-- Permission summary -->
          <div v-if="reviewRules.length > 0">
            <h5 class="text-sm font-medium text-gray-700 mb-2">Permissions granted:</h5>
            <ul class="list-disc list-inside text-sm text-gray-600 space-y-1">
              <li v-for="(desc, idx) in reviewRules" :key="idx">{{ desc }}</li>
            </ul>
          </div>
        </div>

        <!-- Wizard footer -->
        <div class="p-6 border-t border-gray-200 flex justify-between">
          <button @click="wizardBack"
            class="py-2.5 px-5 rounded-lg text-sm font-medium border border-gray-300 text-gray-600 bg-white hover:bg-gray-50 cursor-pointer transition-colors"
            :class="{ 'invisible': wizardStep === 1 }">
            Back
          </button>
          <div class="flex gap-2">
            <button @click="wizardOpen = false"
              class="py-2.5 px-5 rounded-lg text-sm font-medium border border-gray-300 text-gray-600 bg-white hover:bg-gray-50 cursor-pointer transition-colors">
              Cancel
            </button>
            <button v-if="wizardStep < wizardStepCount" @click="wizardNext"
              class="py-2.5 px-5 rounded-lg text-sm font-medium bg-blue-600 text-white border-none hover:bg-blue-700 cursor-pointer transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              :disabled="!canAdvanceWizard">
              Next
            </button>
            <button v-else @click="submitWizard"
              class="py-2.5 px-5 rounded-lg text-sm font-medium bg-green-600 text-white border-none hover:bg-green-700 cursor-pointer transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              :disabled="wizardSubmitting">
              {{ wizardSubmitting ? 'Creating...' : 'Create' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api'
import websocketService from '../services/websocket'
import { useToast } from 'vue-toastification'
import RbacGraph from './RbacGraph.vue'

export default {
  name: 'RbacManagement',
  components: { RbacGraph },
  data() {
    return {
      loading: true,
      activeTab: 'serviceaccounts',
      selectedNamespace: '',
      showSystem: false,
      namespaces: [],
      serviceAccounts: [],
      roles: [],
      clusterRoles: [],
      roleBindings: [],
      clusterRoleBindings: [],
      expandedRoles: new Set(),
      expandedClusterRoles: new Set(),
      presets: [],
      allRoles: [],
      allClusterRoles: [],

      // Wizard state
      wizardOpen: false,
      wizardStep: 1,
      wizardSubmitting: false,
      wizardNameError: '',
      wizard: this.freshWizard(),

      focusedNodeId: null,
      relatedNodeIds: new Set(),
      availableVerbs: ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete', '*'],
      unsubscribeWs: null,
    }
  },
  computed: {
    tabs() {
      return [
        { key: 'serviceaccounts', label: 'Users' },
        { key: 'roles', label: 'Roles' },
        { key: 'clusterroles', label: 'ClusterRoles' },
        { key: 'rolebindings', label: 'Bindings' },
        { key: 'clusterrolebindings', label: 'ClusterBindings' },
      ]
    },
    activeTabLabel() {
      return this.tabs.find(t => t.key === this.activeTab)?.label || ''
    },
    tabNeedsNamespace() {
      return ['serviceaccounts', 'roles', 'rolebindings'].includes(this.activeTab)
    },
    tabCounts() {
      return {
        serviceaccounts: this.serviceAccounts.length,
        roles: this.roles.length,
        clusterroles: this.clusterRoles.length,
        rolebindings: this.roleBindings.length,
        clusterrolebindings: this.clusterRoleBindings.length,
      }
    },
    currentItems() {
      const map = {
        serviceaccounts: this.serviceAccounts,
        roles: this.roles,
        clusterroles: this.clusterRoles,
        rolebindings: this.roleBindings,
        clusterrolebindings: this.clusterRoleBindings,
      }
      return map[this.activeTab] || []
    },
    wizardStepCount() {
      return this.wizard.permMode === 'custom' ? 4 : 3
    },
    canAdvanceWizard() {
      if (this.wizardStep === 1) {
        return this.wizard.name && this.wizard.namespace && !this.wizardNameError
      }
      if (this.wizardStep === 2) {
        if (this.wizard.permMode === 'preset') return !!this.wizard.presetId
        if (this.wizard.permMode === 'existing') return !!this.wizard.existingRole
        if (this.wizard.permMode === 'custom') return true
        return false
      }
      if (this.wizardStep === 3 && this.wizard.permMode === 'custom') {
        return this.wizard.customRules.length > 0 && this.wizard.customRules.every(r => r.resources && r.verbs.length > 0)
      }
      return true
    },
    selectedPreset() {
      return this.presets.find(p => p.id === this.wizard.presetId)
    },
    reviewRules() {
      let rules = []
      if (this.wizard.permMode === 'preset' && this.selectedPreset) {
        rules = this.selectedPreset.rules
      } else if (this.wizard.permMode === 'custom') {
        rules = this.wizard.customRules.map(r => ({
          apiGroups: this.parseCSV(r.apiGroups),
          resources: this.parseCSV(r.resources),
          verbs: r.verbs,
        }))
      }
      return rules.map(r => this.describeRule(r))
    },
  },
  watch: {
    activeTab() {
      this.loadAllRbacData()
    },
  },
  async mounted() {
    this.toast = useToast()
    await this.loadNamespaces()
    await this.loadAllRbacData()
    this.loadPresets()
    this.unsubscribeWs = websocketService.subscribe((event) => {
      if (event.type === 'rbac_updated') {
        this.loadAllRbacData()
      }
    })
  },
  beforeUnmount() {
    if (this.unsubscribeWs) this.unsubscribeWs()
  },
  methods: {
    freshWizard() {
      return {
        name: '',
        namespace: '',
        scope: 'namespace',
        permMode: 'preset',
        presetId: null,
        existingRole: null,
        customRules: [{ apiGroups: '', resources: '', verbs: [] }],
      }
    },
    async loadNamespaces() {
      try {
        this.namespaces = await apiService.rbacNamespaces()
      } catch {
        this.namespaces = []
      }
    },
    async loadPresets() {
      try {
        this.presets = await apiService.rbacPresets()
      } catch {
        this.presets = []
      }
    },
    onFilterChange() {
      this.loadAllRbacData()
    },
    async loadAllRbacData() {
      this.loading = true
      try {
        const params = { include_system: this.showSystem }
        if (this.selectedNamespace) params.namespace = this.selectedNamespace
        const clusterParams = { include_system: this.showSystem }
        const [sa, roles, cr, rb, crb] = await Promise.all([
          apiService.rbacServiceAccounts(params),
          apiService.rbacRoles(params),
          apiService.rbacClusterRoles(clusterParams),
          apiService.rbacRoleBindings(params),
          apiService.rbacClusterRoleBindings(clusterParams),
        ])
        this.serviceAccounts = sa
        this.roles = roles
        this.clusterRoles = cr
        this.roleBindings = rb
        this.clusterRoleBindings = crb
      } catch (error) {
        console.error('Failed to load RBAC data for graph:', error)
      } finally {
        this.loading = false
      }
    },
    async loadWizardRoles() {
      try {
        const [roles, clusterRoles] = await Promise.all([
          apiService.rbacRoles({ include_system: false }),
          apiService.rbacClusterRoles({ include_system: false }),
        ])
        this.allRoles = roles
        this.allClusterRoles = clusterRoles
      } catch {
        this.allRoles = []
        this.allClusterRoles = []
      }
    },
    toggleRoleDetail(role) {
      const key = `${role.namespace}/${role.name}`
      if (this.expandedRoles.has(key)) {
        this.expandedRoles.delete(key)
      } else {
        this.expandedRoles.add(key)
      }
      this.expandedRoles = new Set(this.expandedRoles)
    },
    toggleClusterRoleDetail(cr) {
      if (this.expandedClusterRoles.has(cr.name)) {
        this.expandedClusterRoles.delete(cr.name)
      } else {
        this.expandedClusterRoles.add(cr.name)
      }
      this.expandedClusterRoles = new Set(this.expandedClusterRoles)
    },
    describeRule(rule) {
      const verbs = (rule.verbs || []).join(', ')
      const resources = (rule.resources || []).join(', ')
      const groups = (rule.apiGroups || []).map(g => g === '' ? 'core' : g).join(', ')

      if (verbs === '*' && resources === '*') return `Full access to all resources in ${groups} API group(s)`
      const verbStr = verbs === '*' ? 'All operations' : `Can ${verbs}`
      return `${verbStr} on ${resources} (${groups})`
    },
    describeCustomRule(rule) {
      const verbs = rule.verbs.join(', ') || 'no verbs'
      const resources = rule.resources || 'no resources'
      const groups = rule.apiGroups || 'core'
      return `${verbs} on ${resources} (${groups})`
    },
    parseCSV(str) {
      return (str || '').split(',').map(s => s.trim()).filter(Boolean)
    },
    formatDate(ts) {
      if (!ts) return ''
      const d = new Date(ts)
      const now = new Date()
      const diffMs = now - d
      const diffDays = Math.floor(diffMs / 86400000)
      if (diffDays === 0) return 'today'
      if (diffDays === 1) return 'yesterday'
      if (diffDays < 30) return `${diffDays}d ago`
      return d.toLocaleDateString()
    },
    validateName() {
      const name = this.wizard.name
      if (!name) {
        this.wizardNameError = ''
        return
      }
      if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(name)) {
        this.wizardNameError = 'Must be lowercase alphanumeric with optional hyphens, cannot start or end with a hyphen.'
      } else if (name.length > 63) {
        this.wizardNameError = 'Must be 63 characters or fewer.'
      } else {
        this.wizardNameError = ''
      }
    },
    openWizard() {
      this.wizard = this.freshWizard()
      this.wizardStep = 1
      this.wizardNameError = ''
      this.wizardSubmitting = false
      this.wizardOpen = true
      this.loadWizardRoles()
    },
    wizardNext() {
      if (!this.canAdvanceWizard) return
      // Skip custom rules step if not in custom mode
      if (this.wizardStep === 2 && this.wizard.permMode !== 'custom') {
        this.wizardStep = this.wizardStepCount
      } else {
        this.wizardStep++
      }
    },
    wizardBack() {
      if (this.wizardStep === this.wizardStepCount && this.wizard.permMode !== 'custom') {
        this.wizardStep = 2
      } else {
        this.wizardStep--
      }
    },
    addCustomRule() {
      this.wizard.customRules.push({ apiGroups: '', resources: '', verbs: [] })
    },
    async submitWizard() {
      this.wizardSubmitting = true
      try {
        const params = {
          name: this.wizard.name,
          namespace: this.wizard.namespace,
          scope: this.wizard.scope,
        }

        if (this.wizard.permMode === 'preset') {
          params.preset_id = this.wizard.presetId
        } else if (this.wizard.permMode === 'existing') {
          params.existing_role = this.wizard.existingRole
        } else {
          params.custom_rules = this.wizard.customRules.map(r => ({
            apiGroups: this.parseCSV(r.apiGroups),
            resources: this.parseCSV(r.resources),
            verbs: r.verbs,
          }))
        }

        await apiService.rbacWizardCreate(params)
        this.toast.success(`User "${this.wizard.name}" created successfully`)
        this.wizardOpen = false
        this.activeTab = 'serviceaccounts'
        this.selectedNamespace = this.wizard.namespace
        await this.loadAllRbacData()
      } catch (error) {
        this.toast.error(error?.message || 'Failed to create user')
      } finally {
        this.wizardSubmitting = false
      }
    },
    focusNode(nodeId) {
      this.focusedNodeId = this.focusedNodeId === nodeId ? null : nodeId
    },
    focusBindingNodes(binding) {
      // For bindings, focus the role they reference
      const roleId = binding.role_ref.kind === 'ClusterRole'
        ? `clusterrole:${binding.role_ref.name}`
        : `role:${binding.namespace}/${binding.role_ref.name}`
      this.focusNode(roleId)
    },
    onGraphNodeSelected(nodeId) {
      this.focusedNodeId = nodeId
    },
    onRelatedNodes(ids) {
      this.relatedNodeIds = ids
    },
    async confirmDelete(kind, item) {
      const name = item.name
      const ns = item.namespace
      const label = {
        serviceaccount: 'ServiceAccount',
        role: 'Role',
        clusterrole: 'ClusterRole',
        rolebinding: 'RoleBinding',
        clusterrolebinding: 'ClusterRoleBinding',
      }[kind]

      if (!confirm(`Delete ${label} "${name}"${ns ? ` from ${ns}` : ''}? This cannot be undone.`)) return

      try {
        switch (kind) {
          case 'serviceaccount':
            await apiService.rbacDeleteServiceAccount({ name, namespace: ns })
            break
          case 'role':
            await apiService.rbacDeleteRole({ name, namespace: ns })
            break
          case 'clusterrole':
            await apiService.rbacDeleteClusterRole({ name })
            break
          case 'rolebinding':
            await apiService.rbacDeleteRoleBinding({ name, namespace: ns })
            break
          case 'clusterrolebinding':
            await apiService.rbacDeleteClusterRoleBinding({ name })
            break
        }
        this.toast.success(`${label} "${name}" deleted`)
        await this.loadAllRbacData()
      } catch (error) {
        this.toast.error(error?.message || `Failed to delete ${label}`)
      }
    },
  },
}
</script>
