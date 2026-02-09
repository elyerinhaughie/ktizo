<template>
  <div v-if="isActive" class="flex flex-col h-[calc(100vh-4rem)] min-h-[400px] bg-[#1a1b26] -m-8 p-0 w-[calc(100vw-250px)] min-w-[calc(100vw-250px)] max-w-[calc(100vw-250px)] overflow-hidden box-border relative z-[1]" :class="{ 'hidden-terminal': !isActive }">
    <div class="flex items-center gap-2 px-4 py-2 bg-[#24283b] border-b border-[#414868] shrink-0">
      <span class="text-[#c0caf5] font-semibold text-[0.9rem] mr-2">Terminal</span>
      <span
        class="w-2 h-2 rounded-full"
        :class="{
          'bg-[#9ece6a]': connectionStatus === 'connected',
          'bg-[#e0af68] animate-pulse-terminal': connectionStatus === 'connecting',
          'bg-[#f7768e]': connectionStatus === 'disconnected'
        }"
      ></span>
      <span class="text-[#a9b1d6] text-[0.8rem]">{{ statusText }}</span>
      <button v-if="connectionStatus === 'disconnected'" @click="connect" class="ml-auto px-3 py-1 bg-[#7aa2f7] text-[#1a1b26] border-none rounded cursor-pointer text-[0.8rem] font-semibold hover:bg-[#89b4fa]">
        Reconnect
      </button>
    </div>
    <div ref="terminalContainer" class="flex-1 p-1 overflow-hidden w-full min-w-full max-w-full min-h-0 relative box-border"></div>
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
    if (this.$route.path === '/terminal') {
      this.isActive = true
      this.initTerminal()
      this.connect()
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
    '$route': {
      immediate: true,
      handler(to, from) {
        if (to.path !== '/terminal') {
          this.isActive = false
          this.cleanup()
          this.$nextTick(() => {
            const terminalPage = this.$el
            if (terminalPage && terminalPage.parentElement) {
              terminalPage.style.cssText = 'display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; position: absolute !important; left: -9999px !important;'
            }
          })
        } else if (to.path === '/terminal') {
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

      this.$nextTick(() => {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            if (this.$refs.terminalContainer) {
              const container = this.$refs.terminalContainer
              const sidebar = document.querySelector('aside')
              const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250
              const viewportWidth = window.innerWidth
              const availableWidth = viewportWidth - sidebarWidth

              const terminalPage = container.closest('div')
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
      if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
        return
      }

      this.connectionStatus = 'connecting'

      const hostname = window.location.hostname || 'localhost'
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'

      try {
        this.ws = new WebSocket(`${wsProtocol}//${hostname}:8000/ws/terminal`)

        this.ws.onopen = () => {
          this.connectionStatus = 'connected'
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

        this.ws.onclose = (event) => {
          if (this.connectionStatus === 'connected') {
            this.connectionStatus = 'disconnected'
          } else if (this.connectionStatus === 'connecting') {
            setTimeout(() => {
              if (this.connectionStatus === 'connecting') {
                this.connectionStatus = 'disconnected'
              }
            }, 2000)
          }
        }

        this.ws.onerror = (error) => {
          console.warn('WebSocket error:', error)
          setTimeout(() => {
            if (this.connectionStatus === 'connecting' && (!this.ws || this.ws.readyState === WebSocket.CLOSED)) {
              this.connectionStatus = 'disconnected'
            }
          }, 3000)
        }
      } catch (error) {
        console.error('Failed to create WebSocket:', error)
        setTimeout(() => {
          this.connectionStatus = 'disconnected'
        }, 1000)
      }
    },
    setupResizeObserver() {
      this.resizeObserver = new ResizeObserver((entries) => {
        if (this.isFitting) return

        clearTimeout(this.fitTimeout)
        this.fitTimeout = setTimeout(() => {
          if (!this.isFitting && this.fitAddon && this.$refs.terminalContainer) {
            const sidebar = document.querySelector('aside')
            const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250
            const viewportWidth = window.innerWidth
            const availableWidth = viewportWidth - sidebarWidth

            const container = this.$refs.terminalContainer
            const terminalPage = container.parentElement
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
              this.safeFit()
            }
          }
        }, 200)
      })

      this.handleResize = () => {
        if (this.$refs.terminalContainer && !this.isFitting) {
          const sidebar = document.querySelector('aside')
          const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250
          const viewportWidth = window.innerWidth
          const availableWidth = viewportWidth - sidebarWidth

          const container = this.$refs.terminalContainer
          const terminalPage = container.parentElement
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

      const mainContent = document.querySelector('main')
      if (mainContent) {
        this.resizeObserver.observe(mainContent)
      }
    },
    cleanup() {
      this.isActive = false

      this.$nextTick(() => {
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

      if (this.handleResize) {
        window.removeEventListener('resize', this.handleResize)
        this.handleResize = null
      }

      if (this.$refs.terminalContainer) {
        const container = this.$refs.terminalContainer
        if (container) {
          container.innerHTML = ''
        }
      }
      })
    },
    safeFit() {
      if (this.isFitting || !this.fitAddon || !this.$refs.terminalContainer) {
        return
      }

      this.isFitting = true
      const container = this.$refs.terminalContainer

      const sidebar = document.querySelector('aside')
      const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250
      const viewportWidth = window.innerWidth
      const availableWidth = viewportWidth - sidebarWidth

      const terminalPage = container.parentElement
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

      setTimeout(() => {
        this.isFitting = false
      }, 50)
    },
  },
}
</script>

<style scoped>
/* Hidden terminal state */
.hidden-terminal {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
  position: absolute !important;
  left: -9999px !important;
  top: -9999px !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
}

/* xterm.js overrides - must remain scoped deep */
:deep(.xterm) {
  height: 100% !important;
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
}

:deep(.xterm-viewport) {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
}

:deep(.xterm-screen) {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
}

:deep(.xterm-scroll-area) {
  width: 100% !important;
  max-width: 100% !important;
}

:deep(.xterm-rows) {
  width: 100% !important;
  max-width: 100% !important;
}
</style>
