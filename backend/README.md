# Enhanced Contextual Chat Backend

This directory contains the backend implementation for the enhanced contextual chat feature of the Telekom Ecommerce application. The backend is built with FastAPI and provides smart, context-aware recommendations for devices and plans.

## Key Components

### 1. Session Management (`session_manager.py`)

Manages user sessions with features including:
- Time-to-live (TTL) expiration mechanism
- In-memory storage with disk persistence
- Conversation history tracking
- Viewed item tracking
- User preference storage

```python
# Example usage
from session_manager import get_or_create_session, update_session

# Get or create a session
session_id, session_data = get_or_create_session(session_id)

# Update viewed items
update_session_viewed_item(session_id, 'devices', device_id, device)

# Add to conversation history
add_to_conversation_history(session_id, 'user', message_text)
```

### 2. User Preference Extraction (`preference_extractor.py`)

Uses LLM to extract and refine user preferences from conversation history:
- Brand preferences
- Price range constraints
- Feature requirements
- Usage patterns
- Explicit constraints

```python
# Example usage
import preference_extractor

# Extract preferences from conversation
preferences = await preference_extractor.extract_user_preferences(conversation_history)

# Refine existing preferences
updated_preferences = await preference_extractor.refine_preferences(
    current_preferences,
    recent_messages
)

# Generate human-readable preference explanations
explanations = await preference_extractor.generate_preference_explanation(preferences)
```

### 3. Weighted Recommendation Algorithm (`recommendation_engine.py`)

Provides personalized recommendations based on multiple factors:
- User preference matching
- Query relevance
- Viewing history
- Item popularity
- Explanation generation

```python
# Example usage
import recommendation_engine

# Generate weighted recommendations
recommendations = recommendation_engine.generate_weighted_recommendations(
    session_data,
    devices,
    plans,
    query
)

# Generate natural language summary
summary = await recommendation_engine.generate_recommendation_summary(
    recommendations,
    preferences,
    query
)
```

### 4. Enhanced API Endpoints (`server.py`)

The server provides several endpoints for contextual chat:
- `/api/search` - Smart search with preference extraction and weighted recommendations
- `/api/voice-search` - Voice assistant with speech error correction and context awareness
- `/api/session/{session_id}` - Get current session data
- `/api/session/{session_id}/preferences` - Update user preferences
- `/api/featured-devices` and `/api/popular-plans` - Personalized recommendations

## API Documentation

### Search API

```
POST /api/search
{
  "query": "iPhone with good camera",
  "session_id": "optional-session-id"
}

Response:
{
  "devices": [...],
  "plans": [...],
  "device_explanations": {...},
  "plan_explanations": {...},
  "recommendation": "Natural language summary",
  "follow_up_questions": [...],
  "session_id": "session-id",
  "preferences": ["You're looking for a phone with good camera", ...]
}
```

### Voice Search API

```
POST /api/voice-search
{
  "text": "Tell me about iPhones",
  "session_id": "optional-session-id",
  "language": "en"
}

Response:
{
  "response": "Conversational response",
  "action": "search",
  "data": {
    "recommended_devices": [...],
    "recommended_plans": [...]
  },
  "follow_up_questions": [...],
  "language": "en",
  "session_id": "session-id",
  "preferences": [...]
}
```

### Session API

```
GET /api/session/{session_id}

Response:
{
  "session_id": "session-id",
  "created_at": "timestamp",
  "last_access": "timestamp",
  "conversation_count": 5,
  "user_preferences": {...},
  "recently_viewed": {...},
  "preferences_summary": [...]
}
```

```
POST /api/session/{session_id}/preferences
{
  "preferences": {
    "device_preferences": {
      "brand": ["Apple"],
      "price_range": {"min": 800, "max": 1200}
    },
    "plan_preferences": {
      "data_needs": "high"
    }
  }
}

Response:
{
  "success": true,
  "preferences": {...},
  "preferences_summary": [...]
}
```

## Testing

A test script (`test_implementation.py`) is included to validate the functionality of the enhanced backend. Run it after starting the server:

```bash
# Terminal 1: Start the server
python server.py

# Terminal 2: Run the tests
python test_implementation.py
```

## Environment Variables

The following environment variables can be configured in `.env`:

```
OPENAI_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
```