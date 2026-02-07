<template>
  <div v-if="isActive" class="terminal-page">
    <div class="terminal-header">
      <span class="terminal-title">Terminal</span>
      <span :class="['status-dot', connectionStatus]"></span>
      <span class="status-text">{{ statusText }}</span>
      <button v-if="connectionStatus === 'disconnected'" @click="connect" class="reconnect-btn">
        Reconnect
      </button>
    </div>
    <div ref="terminalContainer" class="terminal-container"></div>
  </div>
</template>

<script>
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

export default {
  name: 'TerminalView',
  data() {
    return {
      connectionStatus: 'connecting',
      term: null,
      fitAddon: null,
      ws: null,
      resizeObserver: null,
      isFitting: false,
      fitTimeout: null,
      handleResize: null,
      isActive: true,
    }
  },
  computed: {
    statusText() {
      switch (this.connectionStatus) {
        case 'connected': return 'Connected'
        case 'connecting': return 'Connecting...'
        case 'disconnected': return 'Disconnected'
        default: return ''
      }
    }
  },
  mounted() {
    // Only initialize if we're actually on the terminal route
    if (this.$route.path === '/terminal') {
      this.isActive = true
      this.initTerminal()
      this.connect()

      // Wait for layout to stabilize before setting up resize observer
      this.$nextTick(() => {
        setTimeout(() => {
          this.setupResizeObserver()
        }, 300)
      })
    } else {
      this.isActive = false
    }
  },
  watch: {
    '$route'(to, from) {
      // Hide terminal when navigating away
      if (to.path !== '/terminal') {
        this.isActive = false
        this.cleanup()
      } else if (to.path === '/terminal' && from.path !== '/terminal') {
        // Show and initialize when navigating to terminal
        this.isActive = true
        this.$nextTick(() => {
          if (!this.term) {
            this.initTerminal()
            this.connect()
            setTimeout(() => {
              this.setupResizeObserver()
            }, 300)
          }
        })
      }
    }
  },
  beforeUnmount() {
    this.cleanup()
  },
  methods: {
    initTerminal() {
      this.term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, 'Courier New', monospace",
        theme: {
          background: '#1a1b26',
          foreground: '#c0caf5',
          cursor: '#c0caf5',
          selectionBackground: '#33467c',
          black: '#15161e',
          red: '#f7768e',
          green: '#9ece6a',
          yellow: '#e0af68',
          blue: '#7aa2f7',
          magenta: '#bb9af7',
          cyan: '#7dcfff',
          white: '#a9b1d6',
          brightBlack: '#414868',
          brightRed: '#f7768e',
          brightGreen: '#9ece6a',
          brightYellow: '#e0af68',
          brightBlue: '#7aa2f7',
          brightMagenta: '#bb9af7',
          brightCyan: '#7dcfff',
          brightWhite: '#c0caf5',
        },
      })

      this.fitAddon = new FitAddon()
      this.term.loadAddon(this.fitAddon)
      this.term.open(this.$refs.terminalContainer)
      
      // Fit terminal after layout stabilizes - use requestAnimationFrame for better timing
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            // Force full viewport width (minus sidebar)
            if (this.$refs.terminalContainer) {
              const container = this.$refs.terminalContainer
              const sidebar = document.querySelector('.sidebar')
              const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250
              const viewportWidth = window.innerWidth
              const availableWidth = viewportWidth - sidebarWidth
              
              // Set terminal page and container to full available width
              const terminalPage = container.closest('.terminal-page')
              if (terminalPage) {
                terminalPage.style.width = `${availableWidth}px`
                terminalPage.style.minWidth = `${availableWidth}px`
                terminalPage.style.maxWidth = `${availableWidth}px`
              }
              
              container.style.width = `${availableWidth}px`
              container.style.minWidth = `${availableWidth}px`
              container.style.maxWidth = `${availableWidth}px`
            }
            this.safeFit()
          })
        })
      })

      this.term.onData((data) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'input', data }))
        }
      })

      this.term.onResize(({ cols, rows }) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'resize', cols, rows }))
        }
      })
    },
    connect() {
      this.connectionStatus = 'connecting'

      const hostname = window.location.hostname || 'localhost'
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      this.ws = new WebSocket(`${wsProtocol}//${hostname}:8000/ws/terminal`)

      this.ws.onopen = () => {
        this.connectionStatus = 'connected'
        // Send initial size after a brief delay
        setTimeout(() => {
          this.safeFit()
          if (this.fitAddon) {
            const dims = this.fitAddon.proposeDimensions()
            if (dims) {
              this.ws.send(JSON.stringify({ type: 'resize', cols: dims.cols, rows: dims.rows }))
            }
          }
        }, 100)
      }

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'output') {
          this.term.write(msg.data)
        }
      }

      this.ws.onclose = () => {
        this.connectionStatus = 'disconnected'
      }

      this.ws.onerror = () => {
        this.connectionStatus = 'disconnected'
      }
    },
    setupResizeObserver() {
      // Use a debounced resize observer with guard to prevent loops
      this.resizeObserver = new ResizeObserver((entries) => {
        if (this.isFitting) return
        
        clearTimeout(this.fitTimeout)
        this.fitTimeout = setTimeout(() => {
          if (!this.isFitting && this.fitAddon && this.$refs.terminalContainer) {
            // Recalculate width on resize
            const sidebar = document.querySelector('.sidebar')
            const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250
            const viewportWidth = window.innerWidth
            const availableWidth = viewportWidth - sidebarWidth
            
            const container = this.$refs.terminalContainer
            const terminalPage = container.closest('.terminal-page')
            if (terminalPage) {
              terminalPage.style.width = `${availableWidth}px`
              terminalPage.style.minWidth = `${availableWidth}px`
              terminalPage.style.maxWidth = `${availableWidth}px`
            }
            
            container.style.width = `${availableWidth}px`
            container.style.minWidth = `${availableWidth}px`
            container.style.maxWidth = `${availableWidth}px`
            
            const rect = container.getBoundingClientRect()
            // Only fit if container has reasonable dimensions
            if (rect.width > 100 && rect.height > 100) {
              this.safeFit()
            }
          }
        }, 200)
      })
      
      // Observe window resize
      this.handleResize = () => {
        if (this.$refs.terminalContainer && !this.isFitting) {
          const sidebar = document.querySelector('.sidebar')
          const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250
          const viewportWidth = window.innerWidth
          const availableWidth = viewportWidth - sidebarWidth
          
          const container = this.$refs.terminalContainer
          const terminalPage = container.closest('.terminal-page')
          if (terminalPage) {
            terminalPage.style.width = `${availableWidth}px`
            terminalPage.style.minWidth = `${availableWidth}px`
            terminalPage.style.maxWidth = `${availableWidth}px`
          }
          
          container.style.width = `${availableWidth}px`
          container.style.minWidth = `${availableWidth}px`
          container.style.maxWidth = `${availableWidth}px`
          
          this.safeFit()
        }
      }
      
      window.addEventListener('resize', this.handleResize)
      
      const mainContent = document.querySelector('.main-content')
      if (mainContent) {
        this.resizeObserver.observe(mainContent)
      }
    },
    cleanup() {
      // Hide terminal immediately
      this.isActive = false
      
      // Clean up all resources when leaving the terminal page
      if (this.fitTimeout) {
        clearTimeout(this.fitTimeout)
        this.fitTimeout = null
      }
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      if (this.term) {
        this.term.dispose()
        this.term = null
      }
      if (this.fitAddon) {
        this.fitAddon = null
      }
      
      // Remove window resize listener if it exists
      if (this.handleResize) {
        window.removeEventListener('resize', this.handleResize)
        this.handleResize = null
      }
      
      // Force cleanup of terminal container
      if (this.$refs.terminalContainer) {
        const container = this.$refs.terminalContainer
        if (container) {
          container.innerHTML = ''
        }
      }
    },
    safeFit() {
      if (this.isFitting || !this.fitAddon || !this.$refs.terminalContainer) {
        return
      }
      
      this.isFitting = true
      const container = this.$refs.terminalContainer
      
      // Calculate full available width (viewport - sidebar)
      const sidebar = document.querySelector('.sidebar')
      const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250
      const viewportWidth = window.innerWidth
      const availableWidth = viewportWidth - sidebarWidth
      
      // Force full width
      const terminalPage = container.closest('.terminal-page')
      if (terminalPage) {
        terminalPage.style.width = `${availableWidth}px`
        terminalPage.style.minWidth = `${availableWidth}px`
        terminalPage.style.maxWidth = `${availableWidth}px`
      }
      
      container.style.width = `${availableWidth}px`
      container.style.minWidth = `${availableWidth}px`
      container.style.maxWidth = `${availableWidth}px`
      
      const rect = container.getBoundingClientRect()
      
      if (rect.width > 100 && rect.height > 100) {
        try {
          this.fitAddon.fit()
        } catch (e) {
          console.warn('Terminal fit error:', e)
        }
      }
      
      // Reset flag after a brief delay
      setTimeout(() => {
        this.isFitting = false
      }, 50)
    },
  },
}
</script>

<style scoped>
.terminal-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 4rem);
  min-height: 400px;
  background: #1a1b26;
  margin: -2rem;
  padding: 0;
  width: calc(100vw - 250px);
  min-width: calc(100vw - 250px);
  max-width: calc(100vw - 250px);
  overflow: hidden;
  box-sizing: border-box;
  position: relative;
  z-index: 1;
}

.terminal-page:not(.active) {
  display: none !important;
  visibility: hidden !important;
}

.terminal-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #24283b;
  border-bottom: 1px solid #414868;
  flex-shrink: 0;
}

.terminal-title {
  color: #c0caf5;
  font-weight: 600;
  font-size: 0.9rem;
  margin-right: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connected {
  background: #9ece6a;
}

.status-dot.connecting {
  background: #e0af68;
  animation: pulse 1s infinite;
}

.status-dot.disconnected {
  background: #f7768e;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.status-text {
  color: #a9b1d6;
  font-size: 0.8rem;
}

.reconnect-btn {
  margin-left: auto;
  padding: 0.25rem 0.75rem;
  background: #7aa2f7;
  color: #1a1b26;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
}

.reconnect-btn:hover {
  background: #89b4fa;
}

.terminal-container {
  flex: 1;
  padding: 4px;
  overflow: hidden;
  width: 100%;
  min-width: 100%;
  max-width: 100%;
  min-height: 0;
  position: relative;
  box-sizing: border-box;
}

.terminal-container :deep(.xterm) {
  height: 100% !important;
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
}

.terminal-container :deep(.xterm-viewport) {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
}

.terminal-container :deep(.xterm-screen) {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
}

.terminal-container :deep(.xterm-scroll-area) {
  width: 100% !important;
  max-width: 100% !important;
}

.terminal-container :deep(.xterm-rows) {
  width: 100% !important;
  max-width: 100% !important;
}
</style>
