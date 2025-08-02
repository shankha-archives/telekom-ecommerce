from datetime import datetime, timedelta
import json
import uuid
import threading
import time
import os

# Configuration
SESSION_TTL_HOURS = 24  # Sessions expire after 24 hours of inactivity
CLEANUP_INTERVAL_MINUTES = 60  # Run cleanup every 60 minutes
SESSION_FILE_DIR = os.path.join(os.path.dirname(__file__), 'sessions')

# Create sessions directory if it doesn't exist
os.makedirs(SESSION_FILE_DIR, exist_ok=True)

# In-memory session store
session_store = {}
session_lock = threading.RLock()

def get_or_create_session(session_id=None):
    """Get existing session or create a new one with TTL"""
    try:
        print(f"DEBUG: get_or_create_session called with session_id: {session_id}")
        with session_lock:
            now = datetime.utcnow()
            
            # If no session_id provided, generate a new one
            if not session_id:
                session_id = str(uuid.uuid4())
                print(f"DEBUG: Generated new session_id: {session_id}")
            
            # Check if session exists and is not expired
            if session_id in session_store:
                print(f"DEBUG: Found existing session: {session_id}")
                session_data = session_store[session_id]
                # Check if session is expired (24 hours TTL)
                if now - session_data.get('last_access', now) < timedelta(hours=SESSION_TTL_HOURS):
                    # Update last access time
                    session_store[session_id]['last_access'] = now
                    return session_id, session_store[session_id]
            
            # Create new session
            print(f"DEBUG: Creating new session: {session_id}")
            session_store[session_id] = {
                'created_at': now,
                'last_access': now,
                'conversation_history': [],
                'user_preferences': {
                    'device_preferences': {},
                    'plan_preferences': {},
                    'demographics': {},
                    'explicit_constraints': []
                },
                'viewed_items': {
                    'devices': {},
                    'plans': {}
                },
                'search_queries': [],
                'inferred_needs': {},
                'cart': []
            }
            
            return session_id, session_store[session_id]
    except Exception as e:
        import traceback
        print(f"DEBUG: Error in get_or_create_session: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        # Return a default session as fallback
        fallback_id = str(uuid.uuid4())
        return fallback_id, {
            'created_at': datetime.utcnow(),
            'last_access': datetime.utcnow(),
            'conversation_history': [],
            'user_preferences': {'device_preferences': {}, 'plan_preferences': {}},
            'viewed_items': {'devices': {}, 'plans': {}},
            'search_queries': [],
            'cart': []
        }

def update_session(session_id, update_data):
    """Update session with new context information"""
    with session_lock:
        if session_id in session_store:
            # Update last access time
            session_store[session_id]['last_access'] = datetime.utcnow()
            
            # For each key in update_data, update the session
            for key, value in update_data.items():
                if key in session_store[session_id]:
                    # If the key exists and is a dict, update the dict
                    if isinstance(value, dict) and isinstance(session_store[session_id][key], dict):
                        session_store[session_id][key].update(value)
                    # Otherwise, replace the value
                    else:
                        session_store[session_id][key] = value
                else:
                    # Add new key if it doesn't exist
                    session_store[session_id][key] = value
            
            return True
    return False

def get_session(session_id):
    """Get a session by ID if it exists and is not expired"""
    with session_lock:
        now = datetime.utcnow()
        if session_id in session_store:
            session_data = session_store[session_id]
            # Check if session is expired
            if now - session_data.get('last_access', now) < timedelta(hours=SESSION_TTL_HOURS):
                # Update last access time
                session_store[session_id]['last_access'] = now
                return session_store[session_id]
    return None

def delete_session(session_id):
    """Delete a session by ID"""
    with session_lock:
        if session_id in session_store:
            del session_store[session_id]
            return True
    return False

def add_to_conversation_history(session_id, message_type, message_content, data=None):
    """Add a message to the conversation history"""
    with session_lock:
        if session_id in session_store:
            # Get current timestamp
            timestamp = datetime.utcnow().isoformat()
            
            # Create message object
            message = {
                'type': message_type,  # 'user' or 'assistant'
                'message': message_content,
                'timestamp': timestamp
            }
            
            # Add additional data if provided
            if data:
                message['data'] = data
            
            # Add to conversation history
            session_store[session_id]['conversation_history'].append(message)
            
            # Update last access time
            session_store[session_id]['last_access'] = datetime.utcnow()
            
            return True
    return False

def add_search_query(session_id, query):
    """Add a search query to the session history"""
    try:
        print(f"DEBUG: add_search_query called with session_id: {session_id}, query: {query}")
        with session_lock:
            if session_id in session_store:
                print(f"DEBUG: Found session, adding query to history")
                
                # Make sure search_queries list exists
                if 'search_queries' not in session_store[session_id]:
                    session_store[session_id]['search_queries'] = []
                
                # Add query to search_queries list
                session_store[session_id]['search_queries'].append(query)
                
                # Update last access time
                session_store[session_id]['last_access'] = datetime.utcnow()
                
                print(f"DEBUG: Successfully added query to session")
                return True
            else:
                print(f"DEBUG: Session {session_id} not found in store")
        return False
    except Exception as e:
        import traceback
        print(f"DEBUG: Error in add_search_query: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return False

def update_viewed_item(session_id, item_type, item_id, item_data=None):
    """Update a viewed item in the session"""
    with session_lock:
        if session_id in session_store:
            # Get current timestamp
            timestamp = datetime.utcnow().isoformat()
            
            # Initialize if not exists
            if item_id not in session_store[session_id]['viewed_items'][item_type]:
                session_store[session_id]['viewed_items'][item_type][item_id] = {
                    'first_viewed': timestamp,
                    'last_viewed': timestamp,
                    'view_count': 1
                }
            else:
                # Update existing item
                session_store[session_id]['viewed_items'][item_type][item_id]['last_viewed'] = timestamp
                session_store[session_id]['viewed_items'][item_type][item_id]['view_count'] += 1
            
            # Add item data if provided
            if item_data:
                session_store[session_id]['viewed_items'][item_type][item_id]['data'] = item_data
            
            # Update last access time
            session_store[session_id]['last_access'] = datetime.utcnow()
            
            return True
    return False

def update_user_preferences(session_id, preferences):
    """Update user preferences in the session"""
    with session_lock:
        if session_id in session_store:
            # For each category in preferences, update the session preferences
            for category in preferences:
                if category in session_store[session_id]['user_preferences']:
                    # If the category exists, update it
                    if isinstance(preferences[category], dict) and isinstance(session_store[session_id]['user_preferences'][category], dict):
                        session_store[session_id]['user_preferences'][category].update(preferences[category])
                    else:
                        session_store[session_id]['user_preferences'][category] = preferences[category]
            
            # Update last access time
            session_store[session_id]['last_access'] = datetime.utcnow()
            
            return True
    return False

def get_recent_conversation(session_id, limit=10):
    """Get the most recent conversation messages"""
    with session_lock:
        if session_id in session_store:
            # Get conversation history
            history = session_store[session_id].get('conversation_history', [])
            
            # Return the most recent messages up to the limit
            return history[-limit:] if history else []
    return []

def _cleanup_expired_sessions():
    """Remove expired sessions from memory"""
    with session_lock:
        now = datetime.utcnow()
        expired_ids = []
        
        # Find expired sessions
        for session_id, session_data in session_store.items():
            if now - session_data.get('last_access', now) >= timedelta(hours=SESSION_TTL_HOURS):
                expired_ids.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_ids:
            del session_store[session_id]
        
        return len(expired_ids)

def _cleanup_worker():
    """Background thread to periodically clean up expired sessions"""
    while True:
        # Sleep for the configured interval
        time.sleep(CLEANUP_INTERVAL_MINUTES * 60)
        
        try:
            # Clean up expired sessions
            expired_count = _cleanup_expired_sessions()
            print(f"Session cleanup: Removed {expired_count} expired sessions")
            
            # Persist sessions to disk for backup
            _persist_sessions_to_disk()
        except Exception as e:
            print(f"Error in session cleanup: {str(e)}")

def _persist_sessions_to_disk():
    """Save all sessions to disk for persistence"""
    try:
        with session_lock:
            for session_id, session_data in session_store.items():
                # Create session file path
                file_path = os.path.join(SESSION_FILE_DIR, f"{session_id}.json")
                
                # Write session data to file
                with open(file_path, 'w') as f:
                    json.dump(session_data, f, default=str)
    except Exception as e:
        print(f"Error persisting sessions to disk: {str(e)}")

def _load_sessions_from_disk():
    """Load sessions from disk at startup"""
    try:
        # Get all session files
        session_files = [f for f in os.listdir(SESSION_FILE_DIR) if f.endswith('.json')]
        
        loaded_count = 0
        with session_lock:
            for file_name in session_files:
                try:
                    # Get session ID from file name
                    session_id = file_name.replace('.json', '')
                    
                    # Read session data from file
                    with open(os.path.join(SESSION_FILE_DIR, file_name), 'r') as f:
                        session_data = json.load(f)
                    
                    # Parse datetime strings
                    if 'created_at' in session_data and isinstance(session_data['created_at'], str):
                        session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                    if 'last_access' in session_data and isinstance(session_data['last_access'], str):
                        session_data['last_access'] = datetime.fromisoformat(session_data['last_access'])
                    
                    # Check if session is expired
                    now = datetime.utcnow()
                    if now - session_data.get('last_access', now) < timedelta(hours=SESSION_TTL_HOURS):
                        # Add to in-memory store
                        session_store[session_id] = session_data
                        loaded_count += 1
                except Exception as e:
                    print(f"Error loading session file {file_name}: {str(e)}")
        
        return loaded_count
    except Exception as e:
        print(f"Error loading sessions from disk: {str(e)}")
        return 0

# Initialize the cleanup thread
cleanup_thread = threading.Thread(target=_cleanup_worker, daemon=True)
cleanup_thread.start()

# Load sessions from disk at startup
loaded_sessions = _load_sessions_from_disk()
print(f"Loaded {loaded_sessions} sessions from disk")