/**
 * SessionSync - Utility for synchronizing session state between frontend and backend
 * 
 * This module provides utilities for:
 * 1. Maintaining persistent session IDs between page reloads
 * 2. Syncing session preferences between tabs/windows
 * 3. Reconnecting to existing sessions
 * 4. Handling session expiration
 */

// Constants
const SESSION_ID_KEY = 'telekom_session_id';
const SESSION_TIMESTAMP_KEY = 'telekom_session_timestamp';
const SESSION_SYNC_EVENT = 'telekom_session_sync';
const SESSION_TTL = 24 * 60 * 60 * 1000; // 24 hours
const SYNC_INTERVAL = 60 * 1000; // 1 minute

class SessionSync {
  constructor(apiBaseUrl = 'http://localhost:8001') {
    this.apiBaseUrl = apiBaseUrl;
    this.sessionId = null;
    this.sessionData = null;
    this.broadcastChannel = null;
    this.syncTimer = null;
    
    // Bind methods
    this.getSessionId = this.getSessionId.bind(this);
    this.fetchSessionData = this.fetchSessionData.bind(this);
    this.updateSessionTimestamp = this.updateSessionTimestamp.bind(this);
    this.handleStorageChange = this.handleStorageChange.bind(this);
    this.handleBroadcastMessage = this.handleBroadcastMessage.bind(this);
    this.broadcastSessionUpdate = this.broadcastSessionUpdate.bind(this);
    this.startSessionSync = this.startSessionSync.bind(this);
    this.stopSessionSync = this.stopSessionSync.bind(this);
    this.checkSessionValidity = this.checkSessionValidity.bind(this);
    this.clearExpiredSession = this.clearExpiredSession.bind(this);
  }

  /**
   * Initialize the session sync system
   * @returns {Promise<string>} The session ID
   */
  async initialize() {
    try {
      // Check for expired session
      this.clearExpiredSession();
      
      // Get or create session ID
      this.sessionId = this.getSessionId();
      
      // Setup broadcast channel if supported
      if (typeof BroadcastChannel !== 'undefined') {
        this.broadcastChannel = new BroadcastChannel(SESSION_SYNC_EVENT);
        this.broadcastChannel.onmessage = this.handleBroadcastMessage;
      }
      
      // Add storage event listener for cross-tab sync
      window.addEventListener('storage', this.handleStorageChange);
      
      // Fetch initial session data from backend
      await this.fetchSessionData();
      
      // Start periodic sync
      this.startSessionSync();
      
      return this.sessionId;
    } catch (error) {
      console.error('Failed to initialize session:', error);
      // Create a new session ID if initialization fails
      this.sessionId = this.createNewSessionId();
      return this.sessionId;
    }
  }

  /**
   * Clean up resources and stop syncing
   */
  cleanup() {
    this.stopSessionSync();
    
    if (this.broadcastChannel) {
      this.broadcastChannel.close();
    }
    
    window.removeEventListener('storage', this.handleStorageChange);
  }

  /**
   * Get existing session ID from storage or create a new one
   * @returns {string} Session ID
   */
  getSessionId() {
    const storedId = localStorage.getItem(SESSION_ID_KEY);
    if (storedId) {
      return storedId;
    }
    
    return this.createNewSessionId();
  }

  /**
   * Create a new session ID and store it
   * @returns {string} New session ID
   */
  createNewSessionId() {
    const newId = 'session_' + Math.random().toString(36).substring(2, 15);
    localStorage.setItem(SESSION_ID_KEY, newId);
    this.updateSessionTimestamp();
    return newId;
  }

  /**
   * Update the session timestamp to prevent expiration
   */
  updateSessionTimestamp() {
    localStorage.setItem(SESSION_TIMESTAMP_KEY, Date.now().toString());
  }

  /**
   * Fetch session data from the backend
   * @returns {Promise<Object>} Session data
   */
  async fetchSessionData() {
    try {
      if (!this.sessionId) return null;
      
      const response = await fetch(`${this.apiBaseUrl}/api/session/${this.sessionId}`);
      
      if (response.ok) {
        const data = await response.json();
        this.sessionData = data;
        this.updateSessionTimestamp();
        
        // Broadcast to other tabs
        this.broadcastSessionUpdate({
          type: 'refresh',
          sessionId: this.sessionId
        });
        
        return data;
      } else if (response.status === 404) {
        // Session expired on server, create a new one
        console.warn('Session not found on server, creating a new one');
        this.sessionId = this.createNewSessionId();
        return null;
      } else {
        console.error('Failed to fetch session data:', response.status);
        return null;
      }
    } catch (error) {
      console.error('Error fetching session data:', error);
      return null;
    }
  }

  /**
   * Start periodic session synchronization
   */
  startSessionSync() {
    this.syncTimer = setInterval(async () => {
      await this.fetchSessionData();
      this.checkSessionValidity();
    }, SYNC_INTERVAL);
  }

  /**
   * Stop periodic session synchronization
   */
  stopSessionSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
  }

  /**
   * Check if the session has expired and clear it if needed
   */
  checkSessionValidity() {
    const timestamp = localStorage.getItem(SESSION_TIMESTAMP_KEY);
    
    if (!timestamp) {
      // No timestamp, consider session invalid
      this.clearExpiredSession();
      return false;
    }
    
    const lastActivity = parseInt(timestamp, 10);
    const now = Date.now();
    
    if (now - lastActivity > SESSION_TTL) {
      // Session expired
      this.clearExpiredSession();
      return false;
    }
    
    return true;
  }

  /**
   * Clear an expired session
   */
  clearExpiredSession() {
    const timestamp = localStorage.getItem(SESSION_TIMESTAMP_KEY);
    
    if (!timestamp) {
      // No timestamp, remove session ID
      localStorage.removeItem(SESSION_ID_KEY);
      this.sessionId = null;
      return;
    }
    
    const lastActivity = parseInt(timestamp, 10);
    const now = Date.now();
    
    if (now - lastActivity > SESSION_TTL) {
      // Session expired, remove session data
      localStorage.removeItem(SESSION_ID_KEY);
      localStorage.removeItem(SESSION_TIMESTAMP_KEY);
      this.sessionId = null;
      this.sessionData = null;
    }
  }

  /**
   * Handle storage changes for cross-tab synchronization
   * @param {StorageEvent} event - Storage change event
   */
  handleStorageChange(event) {
    if (event.key === SESSION_ID_KEY) {
      // Session ID changed in another tab
      const newSessionId = event.newValue;
      if (newSessionId !== this.sessionId) {
        this.sessionId = newSessionId;
        this.fetchSessionData();
      }
    }
  }

  /**
   * Handle messages from other tabs via BroadcastChannel
   * @param {MessageEvent} event - Broadcast message event
   */
  handleBroadcastMessage(event) {
    const message = event.data;
    
    if (message.type === 'refresh' && message.sessionId === this.sessionId) {
      // Another tab refreshed the session data
      this.fetchSessionData();
    } else if (message.type === 'update_preferences' && message.sessionId === this.sessionId) {
      // Preferences were updated in another tab
      this.fetchSessionData();
    }
  }

  /**
   * Broadcast a session update to other tabs
   * @param {Object} message - Message to broadcast
   */
  broadcastSessionUpdate(message) {
    if (this.broadcastChannel) {
      this.broadcastChannel.postMessage(message);
    }
  }

  /**
   * Update user preferences and sync to backend
   * @param {Object} preferences - User preferences object
   * @returns {Promise<boolean>} Success status
   */
  async updatePreferences(preferences) {
    if (!this.sessionId) return false;
    
    try {
      const response = await fetch(`${this.apiBaseUrl}/api/session/${this.sessionId}/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferences })
      });
      
      if (response.ok) {
        // Update local session data
        const result = await response.json();
        this.sessionData = result.session_data;
        this.updateSessionTimestamp();
        
        // Broadcast update to other tabs
        this.broadcastSessionUpdate({
          type: 'update_preferences',
          sessionId: this.sessionId
        });
        
        return true;
      } else {
        console.error('Failed to update preferences:', response.status);
        return false;
      }
    } catch (error) {
      console.error('Error updating preferences:', error);
      return false;
    }
  }

  /**
   * Track a product view in the session
   * @param {string} itemType - 'device' or 'plan'
   * @param {string} itemId - ID of the viewed item
   * @param {Object} itemData - Data for the viewed item
   * @returns {Promise<boolean>} Success status
   */
  async trackItemView(itemType, itemId, itemData) {
    if (!this.sessionId) return false;
    
    try {
      // For now, we'll simply update the timestamp
      // In a real implementation, we'd call an API endpoint
      this.updateSessionTimestamp();
      return true;
    } catch (error) {
      console.error('Error tracking item view:', error);
      return false;
    }
  }

  /**
   * Get the current session ID
   * @returns {string|null} Session ID
   */
  getCurrentSessionId() {
    return this.sessionId;
  }

  /**
   * Get current session data
   * @returns {Object|null} Session data
   */
  getSessionData() {
    return this.sessionData;
  }

  /**
   * Track conversion and update backend
   * @param {Object} data - Conversion data
   * @returns {Promise<boolean>} Success status
   */
  async trackConversion(data) {
    if (!this.sessionId) return false;
    
    try {
      const payload = {
        ...data,
        session_id: this.sessionId
      };
      
      const response = await fetch(`${this.apiBaseUrl}/api/analytics/conversion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        return true;
      } else {
        console.error('Failed to track conversion:', response.status);
        return false;
      }
    } catch (error) {
      console.error('Error tracking conversion:', error);
      return false;
    }
  }
}

// Create and export singleton instance
const sessionSync = new SessionSync();
export default sessionSync;