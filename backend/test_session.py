#!/usr/bin/env python
"""
Simple test script for the session management module
"""
import session_manager
import time
from datetime import datetime

def test_session_creation():
    """Test session creation and retrieval"""
    print("\nTesting session creation...")
    
    # Create a new session
    session_id, session_data = session_manager.get_or_create_session()
    
    print(f"Created session ID: {session_id}")
    print(f"Session data keys: {list(session_data.keys())}")
    
    # Verify session structure
    required_keys = ['created_at', 'last_access', 'conversation_history', 'user_preferences', 'viewed_items', 'search_queries']
    missing_keys = [key for key in required_keys if key not in session_data]
    
    if missing_keys:
        print(f"ERROR: Session is missing required keys: {missing_keys}")
    else:
        print("SUCCESS: Session has all required keys")
    
    return session_id

def test_session_retrieval(session_id):
    """Test retrieving an existing session"""
    print("\nTesting session retrieval...")
    
    # Retrieve the session
    retrieved_id, retrieved_data = session_manager.get_or_create_session(session_id)
    
    if retrieved_id == session_id:
        print(f"SUCCESS: Retrieved correct session ID: {retrieved_id}")
    else:
        print(f"ERROR: Retrieved wrong session ID. Expected: {session_id}, Got: {retrieved_id}")
    
    # Check that the session data is accessible
    if 'created_at' in retrieved_data:
        created_time = retrieved_data['created_at']
        if isinstance(created_time, datetime):
            print(f"SUCCESS: Session has valid created_at timestamp: {created_time}")
        else:
            print(f"WARNING: Session created_at is not a datetime: {type(created_time)}")
    else:
        print("ERROR: Session missing created_at timestamp")
    
    return retrieved_id

def test_session_updates(session_id):
    """Test updating session data"""
    print("\nTesting session updates...")
    
    # Add a search query
    query = "test query for iPhone"
    success = session_manager.add_search_query(session_id, query)
    
    if success:
        print(f"SUCCESS: Added search query to session: {query}")
    else:
        print(f"ERROR: Failed to add search query to session: {query}")
    
    # Add conversation history
    success = session_manager.add_to_conversation_history(session_id, 'user', "I want an iPhone")
    
    if success:
        print(f"SUCCESS: Added conversation message to session")
    else:
        print(f"ERROR: Failed to add conversation message to session")
    
    # Add user preferences
    preferences = {
        'device_preferences': {
            'brand': ['Apple'],
            'price_range': {'min': 800, 'max': 1200}
        }
    }
    
    success = session_manager.update_user_preferences(session_id, preferences)
    
    if success:
        print(f"SUCCESS: Updated user preferences in session")
    else:
        print(f"ERROR: Failed to update user preferences in session")
    
    # Verify updates
    retrieved_data = session_manager.get_session(session_id)
    
    if retrieved_data:
        if len(retrieved_data.get('search_queries', [])) > 0:
            print(f"SUCCESS: Session contains search queries: {retrieved_data['search_queries']}")
        else:
            print(f"ERROR: Session is missing search queries")
        
        if len(retrieved_data.get('conversation_history', [])) > 0:
            print(f"SUCCESS: Session contains conversation history")
        else:
            print(f"ERROR: Session is missing conversation history")
        
        preferences = retrieved_data.get('user_preferences', {}).get('device_preferences', {})
        if preferences and 'brand' in preferences:
            print(f"SUCCESS: Session contains user preferences: {preferences}")
        else:
            print(f"ERROR: Session is missing user preferences")
    else:
        print(f"ERROR: Couldn't retrieve session for verification")

def main():
    print("Running session management tests...")
    
    # Test session creation
    session_id = test_session_creation()
    
    # Test session retrieval
    test_session_retrieval(session_id)
    
    # Test session updates
    test_session_updates(session_id)
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()