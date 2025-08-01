# Context-Aware Chat System - Testing & Integration Guide

This document provides guidance on testing, analyzing, and integrating the context-aware chat system in the Telekom E-commerce application.

## Table of Contents

1. [Integration Testing](#integration-testing)
2. [End-to-End Testing](#end-to-end-testing)
3. [Analytics Dashboard](#analytics-dashboard)
4. [Session Synchronization](#session-synchronization)
5. [Debugging Tools](#debugging-tools)

## Integration Testing

The integration test suite helps verify that all system components work together correctly:

```bash
# Run the integration test suite
python backend/integration_test_suite.py
```

### Test Coverage

- Session management functionality
- Preference extraction from conversation
- Recommendation quality based on preferences
- User profile testing with different personas
- Conversation context maintenance
- Cross-component interaction

### Key Files

- `backend/integration_test_suite.py` - Main integration test script
- `backend/test_enhanced_api.py` - Tests for enhanced API endpoints
- `backend/test_session.py` - Tests for session management
- `backend/test_recommendation.py` - Tests for recommendation engine

## End-to-End Testing

End-to-end testing simulates real user interactions with the application:

```bash
# Run the end-to-end test suite
python e2e_test.py
```

For more options:

```bash
python e2e_test.py --help
```

### Test Scenarios

- **Budget Phone Search**: Tests preference extraction and recommendation filtering
- **Plan Comparison**: Tests conversation context and comparison view
- **Full Shopping Journey**: Tests a complete user journey from search to checkout

### Requirements

- Chrome WebDriver for Selenium
- Python packages: selenium, requests

## Analytics Dashboard

The analytics dashboard provides insights into recommendation quality and user behavior.

### Access

```
http://localhost:8001/dashboard
```

### Features

- Real-time system health monitoring
- Recommendation and conversion metrics
- Session activity tracking
- Preference extraction analytics
- Conversion analysis

### Implementation

- Backend dashboard endpoint in `enhanced_api.py`
- Dashboard template in `backend/templates/dashboard.html`
- Analytics data collection in `recommendation_analytics.py`

## Session Synchronization

The session sync system provides persistent sessions across page refreshes and tab synchronization.

### Features

- Cross-tab/window session state synchronization
- Persistent sessions with TTL (Time-To-Live)
- Automatic reconnection to existing sessions
- Local and remote session management

### Implementation

- Frontend synchronization in `frontend/src/utils/SessionSync.js`
- Backend session storage in `backend/session_manager.py`
- Cross-tab communication via BroadcastChannel API
- Local storage for session persistence

### Usage

```javascript
import sessionSync from './utils/SessionSync';

// Initialize session
await sessionSync.initialize();

// Get current session ID
const sessionId = sessionSync.getCurrentSessionId();

// Get full session data
const sessionData = sessionSync.getSessionData();

// Update preferences
await sessionSync.updatePreferences({
  device_preferences: {
    brand: ['Apple']
  }
});

// Track conversions
await sessionSync.trackConversion({
  item_id: 'device_123',
  item_type: 'device',
  conversion_step: 'add_to_cart'
});
```

## Debugging Tools

### Backend Logs

Backend logs are available in the dashboard or through direct console output.

### Session Inspection

View active sessions and their data in the dashboard's "Sessions" tab.

### Analytics Export

To export analytics data for further analysis:

```bash
python backend/export_analytics.py --format csv --output analytics_export.csv
```

### Recommendation Testing Tool

For direct testing of recommendations based on session data:

```bash
python backend/test_recommendation.py --session_id <SESSION_ID> --query "test query"
```

## Environment Configuration

Make sure the required environment variables are set:

- `OPENAI_API_KEY` - Required for LLM-based preference extraction
- `REACT_APP_BACKEND_URL` - Frontend configuration for API URL (default: http://localhost:8001)

## Best Practices

1. Run integration tests after any significant changes to the recommendation system
2. Check analytics regularly to monitor system performance
3. Use the debugging dashboard to investigate issues with specific sessions
4. Test with different user personas to ensure recommendations work for diverse users
5. Monitor conversion rates to gauge the effectiveness of recommendations