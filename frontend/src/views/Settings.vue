<template>
  <div class="max-w-[1400px] mx-auto">
    <div class="flex items-center justify-between mb-8 sticky top-0 z-10 bg-[var(--th-bg-page,#f3f4f6)] -mx-8 px-8 py-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 m-0">Settings</h2>
        <p class="text-gray-500 mt-1 mb-0">Application preferences</p>
      </div>
    </div>

    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-1">Theme</h3>
      <p class="text-gray-500 text-sm mb-5">Choose how Ktizo looks to you.</p>

      <div class="grid grid-cols-3 gap-5">
        <!-- Light -->
        <button
          @click="selectTheme('light')"
          class="group relative rounded-lg border-2 p-0 overflow-hidden cursor-pointer transition-all duration-200 bg-transparent"
          :class="current === 'light' ? 'border-primary shadow-md' : 'border-gray-200 hover:border-gray-300'"
        >
          <div class="flex h-[120px]">
            <div class="w-[60px] flex flex-col py-2 px-1.5 gap-1.5" style="background:#2c3e50">
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.3)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.15)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.15)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.15)"></div>
            </div>
            <div class="flex-1 p-2.5 flex flex-col gap-2" style="background:#f3f4f6">
              <div class="h-2 w-3/4 rounded" style="background:#374151"></div>
              <div class="flex-1 rounded" style="background:#ffffff; border:1px solid #e5e7eb"></div>
            </div>
          </div>
          <div class="py-2.5 px-3 text-left flex items-center gap-2 bg-white border-t border-gray-100">
            <span class="text-sm font-medium text-gray-700">Light</span>
            <font-awesome-icon v-if="current === 'light'" :icon="['fas', 'circle-check']" class="text-primary ml-auto text-base" />
          </div>
        </button>

        <!-- Dark -->
        <button
          @click="selectTheme('dark')"
          class="group relative rounded-lg border-2 p-0 overflow-hidden cursor-pointer transition-all duration-200 bg-transparent"
          :class="current === 'dark' ? 'border-primary shadow-md' : 'border-gray-200 hover:border-gray-300'"
        >
          <div class="flex h-[120px]">
            <div class="w-[60px] flex flex-col py-2 px-1.5 gap-1.5" style="background:#0f172a">
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.25)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.1)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.1)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.1)"></div>
            </div>
            <div class="flex-1 p-2.5 flex flex-col gap-2" style="background:#111827">
              <div class="h-2 w-3/4 rounded" style="background:#f3f4f6"></div>
              <div class="flex-1 rounded" style="background:#1f2937; border:1px solid #374151"></div>
            </div>
          </div>
          <div class="py-2.5 px-3 text-left flex items-center gap-2 border-t" style="background:#1f2937; border-color:#374151">
            <span class="text-sm font-medium" style="color:#f3f4f6">Dark</span>
            <font-awesome-icon v-if="current === 'dark'" :icon="['fas', 'circle-check']" class="text-primary ml-auto text-base" />
          </div>
        </button>

        <!-- Moonlight -->
        <button
          @click="selectTheme('moonlight')"
          class="group relative rounded-lg border-2 p-0 overflow-hidden cursor-pointer transition-all duration-200 bg-transparent"
          :class="current === 'moonlight' ? 'border-[#b48ead] shadow-md' : 'border-gray-200 hover:border-gray-300'"
        >
          <div class="flex h-[120px]">
            <div class="w-[60px] flex flex-col py-2 px-1.5 gap-1.5" style="background:#1a1028">
              <div class="h-1.5 w-full rounded" style="background:rgba(180,142,173,0.4)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.1)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.1)"></div>
              <div class="h-1.5 w-full rounded" style="background:rgba(255,255,255,0.1)"></div>
            </div>
            <div class="flex-1 p-2.5 flex flex-col gap-2" style="background:#1a1625">
              <div class="h-2 w-3/4 rounded" style="background:#e2dff0"></div>
              <div class="flex-1 rounded" style="background:#241f31; border:1px solid #3d3554"></div>
            </div>
          </div>
          <div class="py-2.5 px-3 text-left flex items-center gap-2 border-t" style="background:#241f31; border-color:#3d3554">
            <span class="text-sm font-medium" style="color:#e2dff0">Moonlight</span>
            <font-awesome-icon v-if="current === 'moonlight'" :icon="['fas', 'circle-check']" class="text-[#b48ead] ml-auto text-base" />
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import themeService from '../services/theme'

export default {
  name: 'Settings',
  data() {
    return {
      current: themeService.getTheme()
    }
  },
  methods: {
    selectTheme(theme) {
      this.current = theme
      themeService.setTheme(theme)
    }
  }
}
</script>
