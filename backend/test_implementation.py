import requests
import json
import time
from pprint import pprint

# Configuration
BASE_URL = "http://localhost:8001"

def test_session_management():
    """Test session management and persistence"""
    print("\n=== Testing Session Management ===")
    
    # Create a new session via search API
    print("Sending search request to create a session...")
    try:
        response = requests.post(f"{BASE_URL}/api/search", json={
            "query": "I'm looking for an iPhone with good battery life"
        })
        print(f"Response status: {response.status_code}")
    except Exception as e:
        print(f"Exception during request: {str(e)}")
        return
    
    if response.status_code != 200:
        print(f"Failed to search: {response.status_code}")
        try:
            print(f"Response content: {response.text}")
        except:
            pass
        return
    
    try:
        data = response.json()
        print(f"Successfully parsed response JSON")
    except Exception as e:
        print(f"Error parsing response JSON: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        return
        
    session_id = data.get("session_id")
    
    if not session_id:
        print("No session ID returned!")
        return
    
    print(f"Created session ID: {session_id}")
    
    # Retrieve session data
    response = requests.get(f"{BASE_URL}/api/session/{session_id}")
    
    if response.status_code != 200:
        print(f"Failed to get session: {response.status_code}")
        return
    
    session_data = response.json()
    print("Initial session data:")
    pprint(session_data)
    
    # Make another request to add more context
    response = requests.post(f"{BASE_URL}/api/voice-search", json={
        "text": "I want something with at least 128GB of storage",
        "session_id": session_id,
        "language": "en"
    })
    
    if response.status_code != 200:
        print(f"Failed voice search: {response.status_code}")
        return
    
    # Check if preferences were extracted
    time.sleep(1)  # Give some time for async processing
    response = requests.get(f"{BASE_URL}/api/session/{session_id}")
    
    if response.status_code != 200:
        print(f"Failed to get updated session: {response.status_code}")
        return
    
    updated_session = response.json()
    print("\nUpdated session data after voice search:")
    pprint(updated_session)
    
    # Update preferences manually
    new_preferences = {
        "device_preferences": {
            "brand": ["Apple"],
            "price_range": {"min": 800, "max": 1200},
            "storage": ["128GB", "256GB"],
            "color": ["black"]
        },
        "plan_preferences": {
            "data_needs": "high",
            "price_sensitivity": "medium"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/session/{session_id}/preferences", json={
        "preferences": new_preferences
    })
    
    if response.status_code != 200:
        print(f"Failed to update preferences: {response.status_code}")
        return
    
    updated_prefs = response.json()
    print("\nPreferences updated:")
    pprint(updated_prefs)
    
    # Get personalized featured devices
    response = requests.get(f"{BASE_URL}/api/featured-devices?session_id={session_id}")
    
    if response.status_code != 200:
        print(f"Failed to get personalized featured devices: {response.status_code}")
        return
    
    featured_devices = response.json()
    print("\nPersonalized featured devices:")
    for device in featured_devices:
        print(f"- {device.get('name')} ({device.get('brand')})")

def test_recommendation_engine():
    """Test the recommendation engine with search queries"""
    print("\n=== Testing Recommendation Engine ===")
    
    # Create a session with user preferences
    print("Sending search request...")
    try:
        response = requests.post(f"{BASE_URL}/api/search", json={
            "query": "I need a phone with good camera"
        })
        print(f"Response status: {response.status_code}")
    except Exception as e:
        print(f"Exception during request: {str(e)}")
        return
    
    if response.status_code != 200:
        print(f"Failed to search: {response.status_code}")
        try:
            print(f"Response content: {response.text}")
        except:
            pass
        return
    
    try:
        data = response.json()
        print(f"Successfully parsed response JSON")
    except Exception as e:
        print(f"Error parsing response JSON: {str(e)}")
        print(f"Response text: {response.text[:500]}...")
        return
        
    session_id = data.get("session_id")
    
    # Print recommendations and explanations
    print("Search Results:")
    if "devices" in data:
        print("\nRecommended Devices:")
        for device in data.get("devices", []):
            device_id = device.get("id")
            explanations = data.get("device_explanations", {}).get(device_id, [])
            print(f"- {device.get('name')} ({device.get('brand')}):")
            for explanation in explanations:
                print(f"  * {explanation}")
    
    # Test with more specific query
    response = requests.post(f"{BASE_URL}/api/search", json={
        "query": "I want an iPhone with at least 128GB storage and good camera",
        "session_id": session_id
    })
    
    if response.status_code != 200:
        print(f"Failed second search: {response.status_code}")
        return
    
    data = response.json()
    
    # Print recommendations, explanations and preferences
    print("\nSearch Results with More Context:")
    print(f"Recommendation: {data.get('recommendation', '')}")
    
    if "devices" in data:
        print("\nRecommended Devices:")
        for device in data.get("devices", []):
            device_id = device.get("id")
            explanations = data.get("device_explanations", {}).get(device_id, [])
            print(f"- {device.get('name')} ({device.get('brand')}):")
            for explanation in explanations:
                print(f"  * {explanation}")
    
    if "preferences" in data:
        print("\nExtracted Preferences:")
        for pref in data.get("preferences", []):
            print(f"- {pref}")

def test_voice_search():
    """Test voice search with context awareness"""
    print("\n=== Testing Voice Search and Context Awareness ===")
    
    # Create a session and build up context
    session_id = None
    
    # Initial query about phones
    response = requests.post(f"{BASE_URL}/api/voice-search", json={
        "text": "Tell me about iPhone options",
        "language": "en"
    })
    
    if response.status_code != 200:
        print(f"Failed voice search: {response.status_code}")
        return
    
    data = response.json()
    session_id = data.get("session_id")
    print(f"Session ID: {session_id}")
    print(f"Response: {data.get('response')}")
    
    # Follow-up query referring to previously mentioned devices
    response = requests.post(f"{BASE_URL}/api/voice-search", json={
        "text": "What about the Pro model?",
        "session_id": session_id,
        "language": "en"
    })
    
    if response.status_code != 200:
        print(f"Failed follow-up voice search: {response.status_code}")
        return
    
    data = response.json()
    print(f"\nFollow-up Response: {data.get('response')}")
    
    # Third query about plans
    response = requests.post(f"{BASE_URL}/api/voice-search", json={
        "text": "What plans would you recommend for heavy data usage?",
        "session_id": session_id,
        "language": "en"
    })
    
    if response.status_code != 200:
        print(f"Failed third voice search: {response.status_code}")
        return
    
    data = response.json()
    print(f"\nThird Response: {data.get('response')}")
    
    # Check extracted preferences
    response = requests.get(f"{BASE_URL}/api/session/{session_id}")
    
    if response.status_code != 200:
        print(f"Failed to get session: {response.status_code}")
        return
    
    session_data = response.json()
    print("\nExtracted preferences from conversation:")
    pprint(session_data.get("preferences_summary", []))

def run_tests():
    """Run all tests"""
    print("Testing enhanced contextual chat backend...")
    
    # Health check to make sure server is running
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code != 200:
            print(f"Server is not responding correctly: {response.status_code}")
            return
        
        health_data = response.json()
        print("Server health:", health_data)
        
        if health_data.get("openai") != "configured":
            print("Warning: OpenAI API key not configured. Some tests may fail.")
        
    except requests.RequestException as e:
        print(f"Error connecting to server: {e}")
        print("Make sure the server is running at http://localhost:8001")
        return
    
    # Run all tests
    test_session_management()
    test_recommendation_engine()
    test_voice_search()
    
    print("\nTests completed!")

if __name__ == "__main__":
    run_tests()