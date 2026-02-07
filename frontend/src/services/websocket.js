/**
 * Shared WebSocket service for real-time device updates
 */

class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectInterval = null
    this.listeners = []
    this.reconnectDelay = 5000
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      console.log('WebSocket already connected or connecting')
      return
    }

    // Use same logic as API client to determine WebSocket URL
    let apiUrl = import.meta.env.VITE_API_URL
    if (!apiUrl && typeof window !== 'undefined' && window.location) {
      const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
      const hostname = window.location.hostname
      apiUrl = `${protocol}//${hostname}:8000`
      console.log('WebSocket: Using detected hostname:', hostname, '->', apiUrl)
    }
    if (!apiUrl) {
      apiUrl = 'http://localhost:8000'
      console.warn('WebSocket: Using localhost fallback')
    }
    const wsUrl = apiUrl.replace('http', 'ws').replace('https', 'wss')
    console.log('WebSocket connecting to:', `${wsUrl}/api/v1/events/ws`)
    this.ws = new WebSocket(`${wsUrl}/api/v1/events/ws`)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      if (this.reconnectInterval) {
        clearInterval(this.reconnectInterval)
        this.reconnectInterval = null
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        // Notify all listeners
        this.listeners.forEach(callback => callback(data))
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected. Attempting to reconnect...')
      if (!this.reconnectInterval) {
        this.reconnectInterval = setInterval(() => {
          console.log('Reconnecting WebSocket...')
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
  }

  /**
   * Register a callback to be notified of WebSocket events
   * @param {Function} callback - Function to call when events are received
   * @returns {Function} Unsubscribe function
   */
  subscribe(callback) {
    this.listeners.push(callback)
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(callback)
      if (index > -1) {
        this.listeners.splice(index, 1)
      }
    }
  }
}

// Export singleton instance
export default new WebSocketService()
