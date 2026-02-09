/**
 * Bidirectional WebSocket service.
 *
 * - request(action, params) → Promise  (matched by UUID id)
 * - subscribe(cb) → unsubscribe fn      (broadcast events with "type")
 */

let _counter = 0
function uuid() {
  return `${Date.now()}-${++_counter}-${Math.random().toString(36).slice(2, 8)}`
}

class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectInterval = null
    this.listeners = []          // broadcast listeners (events with "type")
    this.pending = new Map()     // id → { resolve, reject, timer }
    this.reconnectDelay = 3000
    this.requestTimeout = 30000  // 30s per request
    this._queue = []             // messages queued while connecting
    this.connected = false
    this._stateListeners = []    // connection state listeners
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    let apiUrl = import.meta.env.VITE_API_URL
    if (!apiUrl && typeof window !== 'undefined' && window.location) {
      const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
      const hostname = window.location.hostname
      apiUrl = `${protocol}//${hostname}:8000`
    }
    if (!apiUrl) {
      apiUrl = 'http://localhost:8000'
    }
    const wsUrl = apiUrl.replace('http', 'ws').replace('https', 'wss')
    this.ws = new WebSocket(`${wsUrl}/api/v1/ws`)

    this.ws.onopen = () => {
      console.log('[WS] connected')
      this._setConnected(true)
      if (this.reconnectInterval) {
        clearInterval(this.reconnectInterval)
        this.reconnectInterval = null
      }
      // flush queued messages
      while (this._queue.length) {
        this.ws.send(this._queue.shift())
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        console.debug('[WS] ←', msg.id ? `response ${msg.action || msg.id}` : `event ${msg.type}`, msg)

        // Response to a pending request (has id)
        if (msg.id && this.pending.has(msg.id)) {
          const { resolve, reject, timer } = this.pending.get(msg.id)
          this.pending.delete(msg.id)
          clearTimeout(timer)
          if (msg.error) {
            reject(new Error(msg.error))
          } else {
            resolve(msg.data)
          }
          return
        }

        // Broadcast event (has type)
        if (msg.type) {
          this.listeners.forEach(cb => cb(msg))
        }
      } catch (err) {
        console.error('[WS] parse error:', err)
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WS] error:', error)
    }

    this.ws.onclose = () => {
      console.log('[WS] disconnected, reconnecting...')
      this._setConnected(false)
      // Reject all pending requests
      for (const [id, { reject, timer }] of this.pending) {
        clearTimeout(timer)
        reject(new Error('WebSocket disconnected'))
      }
      this.pending.clear()

      if (!this.reconnectInterval) {
        this.reconnectInterval = setInterval(() => {
          this.connect()
        }, this.reconnectDelay)
      }
    }
  }

  disconnect() {
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval)
      this.reconnectInterval = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.listeners = []
    for (const [, { reject, timer }] of this.pending) {
      clearTimeout(timer)
      reject(new Error('WebSocket disconnected'))
    }
    this.pending.clear()
  }

  /**
   * Send a CRUD request over WebSocket and return a Promise.
   * @param {string} action - e.g. "devices.list"
   * @param {object} params - action parameters
   * @returns {Promise<any>}
   */
  request(action, params = {}) {
    return new Promise((resolve, reject) => {
      const id = uuid()
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`WS request timeout: ${action}`))
      }, this.requestTimeout)

      this.pending.set(id, { resolve, reject, timer })

      const payload = JSON.stringify({ id, action, params })
      console.debug('[WS] →', action, params)
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(payload)
      } else {
        // queue and ensure connection
        this._queue.push(payload)
        this.connect()
      }
    })
  }

  /**
   * Register a callback for broadcast events (messages with "type").
   * @param {Function} callback
   * @returns {Function} unsubscribe
   */
  subscribe(callback) {
    this.listeners.push(callback)
    return () => {
      const idx = this.listeners.indexOf(callback)
      if (idx > -1) this.listeners.splice(idx, 1)
    }
  }

  /**
   * Register a callback for connection state changes.
   * @param {Function} callback - receives boolean (true = connected)
   * @returns {Function} unsubscribe
   */
  onStateChange(callback) {
    this._stateListeners.push(callback)
    return () => {
      const idx = this._stateListeners.indexOf(callback)
      if (idx > -1) this._stateListeners.splice(idx, 1)
    }
  }

  _setConnected(value) {
    this.connected = value
    this._stateListeners.forEach(cb => cb(value))
  }
}

export default new WebSocketService()
