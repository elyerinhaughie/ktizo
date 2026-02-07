<template>
  <div class="terminal-page">
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
    this.initTerminal()
    this.connect()

    // Use a debounced resize observer to prevent excessive resizing
    let resizeTimeout
    this.resizeObserver = new ResizeObserver(() => {
      clearTimeout(resizeTimeout)
      resizeTimeout = setTimeout(() => {
        if (this.fitAddon && this.$refs.terminalContainer) {
          // Ensure container has dimensions before fitting
          const rect = this.$refs.terminalContainer.getBoundingClientRect()
          if (rect.width > 0 && rect.height > 0) {
            this.fitAddon.fit()
          }
        }
      }, 100)
    })
    this.resizeObserver.observe(this.$refs.terminalContainer)
    
    // Also observe the main content area in case it changes
    const mainContent = document.querySelector('.main-content')
    if (mainContent) {
      this.resizeObserver.observe(mainContent)
    }
  },
  beforeUnmount() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
    }
    if (this.ws) {
      this.ws.close()
    }
    if (this.term) {
      this.term.dispose()
    }
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
      
      // Fit terminal after a short delay to ensure container has dimensions
      this.$nextTick(() => {
        setTimeout(() => {
          if (this.fitAddon && this.$refs.terminalContainer) {
            const rect = this.$refs.terminalContainer.getBoundingClientRect()
            if (rect.width > 0 && rect.height > 0) {
              this.fitAddon.fit()
            }
          }
        }, 100)
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
        // Send initial size
        if (this.fitAddon) {
          this.fitAddon.fit()
          const dims = this.fitAddon.proposeDimensions()
          if (dims) {
            this.ws.send(JSON.stringify({ type: 'resize', cols: dims.cols, rows: dims.rows }))
          }
        }
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
  width: 100%;
  min-width: 0;
  overflow: hidden;
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
  min-width: 0;
  min-height: 0;
  position: relative;
}

.terminal-container :deep(.xterm) {
  height: 100%;
  width: 100%;
}

.terminal-container :deep(.xterm-viewport) {
  width: 100% !important;
}

.terminal-container :deep(.xterm-screen) {
  width: 100% !important;
}
</style>
