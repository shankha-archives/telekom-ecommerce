#!/usr/bin/env python
"""
Comprehensive integration test suite for the context-aware chat system

This script tests the full integration of all system components:
- Session management
- Preference extraction
- Recommendation engine
- Enhanced API endpoints
- Frontend API integration

Tests are run in sequence to validate the entire conversation flow.
"""

import os
import sys
import json
import asyncio
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

# Set up API URL and test configuration
API_URL = os.environ.get("API_URL", "http://localhost:8001")
TEST_TIMEOUT = 15  # seconds
VERBOSE = True  # Set to True for detailed output

# Test data
TEST_USER_PROFILES = [
    {
        "name": "Budget-conscious user",
        "messages": [
            "I need a new phone but I'm on a tight budget",
            "I can only spend around 400 euros",
            "I need a plan with at least 10GB of data"
        ],
        "expected_preferences": {
            "device_preferences": {
                "price_range": {"max": 500}
            },
            "plan_preferences": {
                "data_needs": "medium",
                "price_sensitivity": "high"
            }
        }
    },
    {
        "name": "Premium user",
        "messages": [
            "I want the latest iPhone with the best camera",
            "I need unlimited data for streaming",
            "I travel a lot internationally"
        ],
        "expected_preferences": {
            "device_preferences": {
                "brand": ["Apple"],
                "features": ["Good camera"]
            },
            "plan_preferences": {
                "data_needs": "high",
                "international": True
            }
        }
    },
    {
        "name": "Family plan user",
        "messages": [
            "I'm looking for a family plan for 4 people",
            "We need at least 5GB per person",
            "I want Samsung phones for everyone"
        ],
        "expected_preferences": {
            "device_preferences": {
                "brand": ["Samsung"]
            },
            "plan_preferences": {
                "family_plan": True,
                "data_needs": "medium"
            }
        }
    }
]

# Test result tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "details": []
}

# Utility functions
def log(message: str, level: str = "info") -> None:
    """Log a message with timestamp and level"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if level == "info" and VERBOSE:
        print(f"[{timestamp}] INFO: {message}")
    elif level == "error":
        print(f"[{timestamp}] ERROR: {message}")
    elif level == "success":
        print(f"[{timestamp}] ✅ {message}")
    elif level == "warning":
        print(f"[{timestamp}] ⚠️ {message}")
    elif level == "test":
        print(f"\n[{timestamp}] 🧪 TEST: {message}")

def record_test_result(name: str, passed: bool, details: str = None) -> None:
    """Record a test result"""
    result = "PASSED" if passed else "FAILED"
    test_results["details"].append({
        "name": name,
        "result": result,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    
    if passed:
        test_results["passed"] += 1
        log(f"{name}: {result}", "success")
    else:
        test_results["failed"] += 1
        log(f"{name}: {result} - {details}", "error")

def print_test_summary() -> None:
    """Print a summary of all test results"""
    total = test_results["passed"] + test_results["failed"] + test_results["skipped"]
    print("\n" + "=" * 50)
    print(f"TEST SUMMARY: {total} tests run")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⏭️ Skipped: {test_results['skipped']}")
    print("=" * 50)
    
    # Print failed tests
    if test_results["failed"] > 0:
        print("\nFailed Tests:")
        for test in test_results["details"]:
            if test["result"] == "FAILED":
                print(f"- {test['name']}: {test['details']}")

# Test functions
async def test_health_check() -> bool:
    """Test if the API server is running and healthy"""
    log("Testing API server health", "test")
    
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            health_data = response.json()
            
            # Check all health components
            all_healthy = True
            for key, value in health_data.items():
                if key != "timestamp" and key != "openai" and key != "data" and key != "sessions":
                    if value != "healthy":
                        all_healthy = False
                        log(f"Health component {key} is not healthy: {value}", "warning")
            
            if all_healthy:
                record_test_result("API Health Check", True, "All components are healthy")
                return True
            else:
                record_test_result("API Health Check", False, f"Some components are unhealthy: {health_data}")
                return False
        else:
            record_test_result("API Health Check", False, f"HTTP {response.status_code}: {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        record_test_result("API Health Check", False, f"Connection error: {str(e)}")
        return False

async def test_session_management() -> Tuple[bool, Optional[str]]:
    """Test session creation, retrieval and update"""
    log("Testing session management", "test")
    
    # Test session creation
    try:
        # Create a new session
        response = requests.post(
            f"{API_URL}/api/chat",
            json={
                "message": "Hello, this is a test",
                "language": "en"
            },
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code != 200:
            record_test_result("Session Creation", False, f"HTTP {response.status_code}: {response.text}")
            return False, None
        
        # Extract session ID
        result = response.json()
        session_id = result.get("session_id")
        
        if not session_id:
            record_test_result("Session Creation", False, "No session_id returned")
            return False, None
        
        # Test session retrieval
        retrieval_response = requests.get(
            f"{API_URL}/api/session/{session_id}",
            timeout=TEST_TIMEOUT
        )
        
        if retrieval_response.status_code != 200:
            record_test_result("Session Retrieval", False, f"HTTP {retrieval_response.status_code}: {retrieval_response.text}")
            return False, session_id
        
        session_data = retrieval_response.json()
        
        # Check for required session data
        required_fields = ["user_preferences", "recently_viewed"]
        missing_fields = [field for field in required_fields if field not in session_data]
        
        if missing_fields:
            record_test_result("Session Data Structure", False, f"Missing fields: {missing_fields}")
            return False, session_id
        
        # Test preference update
        test_preferences = {
            "device_preferences": {
                "brand": ["Apple", "Samsung"],
                "price_range": {"min": 300, "max": 800}
            },
            "plan_preferences": {
                "data_needs": "high"
            }
        }
        
        update_response = requests.post(
            f"{API_URL}/api/session/{session_id}/preferences",
            json={"preferences": test_preferences},
            timeout=TEST_TIMEOUT
        )
        
        if update_response.status_code != 200:
            record_test_result("Preference Update", False, f"HTTP {update_response.status_code}: {update_response.text}")
            return False, session_id
        
        # Check if update was successful
        update_result = update_response.json()
        
        if not update_result.get("success"):
            record_test_result("Preference Update", False, "Update reported as unsuccessful")
            return False, session_id
        
        # Verify preferences were stored
        retrieval_response = requests.get(
            f"{API_URL}/api/session/{session_id}",
            timeout=TEST_TIMEOUT
        )
        
        if retrieval_response.status_code != 200:
            record_test_result("Session Verification", False, f"HTTP {retrieval_response.status_code}: {retrieval_response.text}")
            return False, session_id
        
        updated_data = retrieval_response.json()
        stored_preferences = updated_data.get("user_preferences", {})
        
        # Verify brand preference was stored
        device_prefs = stored_preferences.get("device_preferences", {})
        if not device_prefs.get("brand") or "Apple" not in device_prefs.get("brand", []):
            record_test_result("Preference Storage", False, f"Brand preference not properly stored: {device_prefs}")
            return False, session_id
        
        # All session tests passed
        record_test_result("Session Management", True, f"Session created with ID: {session_id}")
        return True, session_id
    
    except requests.exceptions.RequestException as e:
        record_test_result("Session Management", False, f"Connection error: {str(e)}")
        return False, None

async def test_conversation_context(session_id: str) -> bool:
    """Test if conversation context is maintained and influences recommendations"""
    log("Testing conversation context maintenance", "test")
    
    if not session_id:
        record_test_result("Conversation Context", False, "No session ID provided")
        return False
    
    try:
        # Send a specific query to establish context
        response1 = requests.post(
            f"{API_URL}/api/chat",
            json={
                "message": "I'm looking for an iPhone with at least 128GB storage",
                "session_id": session_id,
                "language": "en"
            },
            timeout=TEST_TIMEOUT
        )
        
        if response1.status_code != 200:
            record_test_result("Context First Message", False, f"HTTP {response1.status_code}: {response1.text}")
            return False
        
        # Send a follow-up that relies on previous context
        response2 = requests.post(
            f"{API_URL}/api/chat",
            json={
                "message": "What colors are available?",
                "session_id": session_id,
                "language": "en"
            },
            timeout=TEST_TIMEOUT
        )
        
        if response2.status_code != 200:
            record_test_result("Context Follow-up", False, f"HTTP {response2.status_code}: {response2.text}")
            return False
        
        # Verify that the response contains iPhone models
        result = response2.json()
        response_text = result.get("response", "").lower()
        recommendations = result.get("recommendations", {})
        devices = recommendations.get("devices", [])
        
        # Check if response or recommendations reference iPhones
        context_maintained = False
        
        if "iphone" in response_text or "apple" in response_text:
            context_maintained = True
        
        if devices:
            for device in devices:
                if "iphone" in device.get("name", "").lower() or device.get("brand", "").lower() == "apple":
                    context_maintained = True
        
        if context_maintained:
            record_test_result("Conversation Context", True, "Context maintained between messages")
            return True
        else:
            record_test_result("Conversation Context", False, "Context lost between messages")
            return False
    
    except requests.exceptions.RequestException as e:
        record_test_result("Conversation Context", False, f"Connection error: {str(e)}")
        return False

async def test_preference_extraction(session_id: str) -> bool:
    """Test if user preferences are correctly extracted from conversation"""
    log("Testing preference extraction from conversation", "test")
    
    if not session_id:
        record_test_result("Preference Extraction", False, "No session ID provided")
        return False
    
    try:
        # Send a message with clear preferences
        response = requests.post(
            f"{API_URL}/api/chat",
            json={
                "message": "I want a Samsung phone under 700 euros with a good camera and at least 128GB storage",
                "session_id": session_id,
                "language": "en"
            },
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code != 200:
            record_test_result("Preference Message", False, f"HTTP {response.status_code}: {response.text}")
            return False
        
        # Wait briefly for preference extraction to complete
        time.sleep(1)
        
        # Get the session data to check preferences
        session_response = requests.get(
            f"{API_URL}/api/session/{session_id}",
            timeout=TEST_TIMEOUT
        )
        
        if session_response.status_code != 200:
            record_test_result("Session Retrieval", False, f"HTTP {session_response.status_code}: {session_response.text}")
            return False
        
        session_data = session_response.json()
        user_preferences = session_data.get("user_preferences", {})
        device_prefs = user_preferences.get("device_preferences", {})
        
        # Check for expected preferences
        extraction_score = 0
        expected_count = 4  # Brand, price, storage, features
        
        # Check brand preference
        if device_prefs.get("brand") and "Samsung" in device_prefs.get("brand", []):
            extraction_score += 1
            log("Correctly extracted brand preference: Samsung", "success")
        else:
            log(f"Failed to extract brand preference. Got: {device_prefs.get('brand')}", "warning")
        
        # Check price preference
        if device_prefs.get("price_range") and device_prefs.get("price_range", {}).get("max", 10000) <= 700:
            extraction_score += 1
            log(f"Correctly extracted price preference: {device_prefs.get('price_range')}", "success")
        else:
            log(f"Failed to extract price preference. Got: {device_prefs.get('price_range')}", "warning")
        
        # Check storage preference
        storage_options = device_prefs.get("storage", [])
        if storage_options and any(opt for opt in storage_options if "128" in opt):
            extraction_score += 1
            log(f"Correctly extracted storage preference: {storage_options}", "success")
        else:
            log(f"Failed to extract storage preference. Got: {storage_options}", "warning")
        
        # Check features preference
        features = device_prefs.get("features", [])
        if features and any(feature for feature in features if "camera" in feature.lower()):
            extraction_score += 1
            log(f"Correctly extracted feature preference: {features}", "success")
        else:
            log(f"Failed to extract features preference. Got: {features}", "warning")
        
        # Calculate extraction accuracy
        accuracy = (extraction_score / expected_count) * 100
        
        if accuracy >= 50:  # At least 2 out of 4 preferences correctly extracted
            record_test_result("Preference Extraction", True, f"Extracted {extraction_score}/{expected_count} preferences ({accuracy:.1f}%)")
            return True
        else:
            record_test_result("Preference Extraction", False, f"Only extracted {extraction_score}/{expected_count} preferences ({accuracy:.1f}%)")
            return False
    
    except requests.exceptions.RequestException as e:
        record_test_result("Preference Extraction", False, f"Connection error: {str(e)}")
        return False

async def test_recommendation_quality(session_id: str) -> bool:
    """Test the quality of recommendations based on preferences"""
    log("Testing recommendation quality", "test")
    
    if not session_id:
        record_test_result("Recommendation Quality", False, "No session ID provided")
        return False
    
    try:
        # First, set very specific preferences
        preferences = {
            "device_preferences": {
                "brand": ["Samsung"],
                "price_range": {"min": 300, "max": 800},
                "storage": ["128GB"],
                "color": ["Black"]
            },
            "plan_preferences": {
                "data_needs": "high",
                "price_sensitivity": "medium"
            }
        }
        
        # Update session preferences
        pref_response = requests.post(
            f"{API_URL}/api/session/{session_id}/preferences",
            json={"preferences": preferences},
            timeout=TEST_TIMEOUT
        )
        
        if pref_response.status_code != 200:
            record_test_result("Preference Setting", False, f"HTTP {pref_response.status_code}: {pref_response.text}")
            return False
        
        # Now search to get recommendations
        search_response = requests.post(
            f"{API_URL}/api/search",
            json={
                "query": "show me phones",
                "session_id": session_id
            },
            timeout=TEST_TIMEOUT
        )
        
        if search_response.status_code != 200:
            record_test_result("Search Request", False, f"HTTP {search_response.status_code}: {search_response.text}")
            return False
        
        # Analyze recommendations
        result = search_response.json()
        devices = result.get("devices", [])
        
        if not devices:
            record_test_result("Recommendation Quality", False, "No device recommendations returned")
            return False
        
        # Check if recommendations match preferences
        match_score = 0
        total_devices = len(devices)
        
        for device in devices:
            device_score = 0
            
            # Check brand
            if device.get("brand") == "Samsung":
                device_score += 1
            
            # Check price
            price = device.get("price", 0)
            if 300 <= price <= 800:
                device_score += 1
            
            # Check storage (where available)
            storage = device.get("storage", "")
            if "128" in storage:
                device_score += 1
            
            # Check color (where available)
            color = device.get("color", "")
            if "Black" in color or "black" in color.lower():
                device_score += 1
            
            # Calculate match percentage for this device
            device_match = (device_score / 4) * 100
            
            if device_match >= 50:  # At least 2 out of 4 criteria matched
                match_score += 1
        
        # Calculate overall recommendation quality
        if total_devices > 0:
            quality_percentage = (match_score / total_devices) * 100
            
            if quality_percentage >= 60:  # At least 60% of devices match preferences
                record_test_result("Recommendation Quality", True, f"{quality_percentage:.1f}% of recommendations match preferences")
                return True
            else:
                record_test_result("Recommendation Quality", False, f"Only {quality_percentage:.1f}% of recommendations match preferences")
                return False
        else:
            record_test_result("Recommendation Quality", False, "No recommendations to evaluate")
            return False
    
    except requests.exceptions.RequestException as e:
        record_test_result("Recommendation Quality", False, f"Connection error: {str(e)}")
        return False

async def test_user_profiles(session_id: Optional[str] = None) -> bool:
    """Test different user profiles to ensure proper preference extraction"""
    log("Testing user profiles", "test")
    
    all_profiles_passed = True
    
    for profile in TEST_USER_PROFILES:
        profile_name = profile["name"]
        log(f"Testing profile: {profile_name}", "test")
        
        # Create a new session for this profile
        try:
            # Send the sequence of messages
            current_session_id = None
            
            for i, message in enumerate(profile["messages"]):
                response = requests.post(
                    f"{API_URL}/api/chat",
                    json={
                        "message": message,
                        "session_id": current_session_id,
                        "language": "en"
                    },
                    timeout=TEST_TIMEOUT
                )
                
                if response.status_code != 200:
                    log(f"Failed to send message {i+1} for profile {profile_name}", "error")
                    all_profiles_passed = False
                    continue
                
                result = response.json()
                current_session_id = result.get("session_id")
                
                # Small delay between messages
                time.sleep(0.5)
            
            # Get the session data to check extracted preferences
            if current_session_id:
                session_response = requests.get(
                    f"{API_URL}/api/session/{current_session_id}",
                    timeout=TEST_TIMEOUT
                )
                
                if session_response.status_code != 200:
                    log(f"Failed to retrieve session for profile {profile_name}", "error")
                    all_profiles_passed = False
                    continue
                
                session_data = session_response.json()
                user_preferences = session_data.get("user_preferences", {})
                
                # Check if expected preferences were extracted
                expected_prefs = profile["expected_preferences"]
                matches = 0
                expected_count = 0
                
                # Check device preferences
                if "device_preferences" in expected_prefs:
                    for key, expected_value in expected_prefs["device_preferences"].items():
                        expected_count += 1
                        actual_value = user_preferences.get("device_preferences", {}).get(key)
                        
                        if actual_value:
                            # Handle different types of values
                            if isinstance(expected_value, list):
                                if any(item in actual_value for item in expected_value):
                                    matches += 1
                                    log(f"Profile {profile_name}: Found expected {key} in {actual_value}", "success")
                            elif isinstance(expected_value, dict):
                                # For price ranges, just check if max is set
                                if "max" in expected_value and "max" in actual_value:
                                    if actual_value["max"] <= expected_value["max"] * 1.5:  # Allow some flexibility
                                        matches += 1
                                        log(f"Profile {profile_name}: Price range acceptable: {actual_value}", "success")
                            else:
                                if expected_value == actual_value:
                                    matches += 1
                                    log(f"Profile {profile_name}: {key} matched exactly", "success")
                
                # Check plan preferences
                if "plan_preferences" in expected_prefs:
                    for key, expected_value in expected_prefs["plan_preferences"].items():
                        expected_count += 1
                        actual_value = user_preferences.get("plan_preferences", {}).get(key)
                        
                        if actual_value:
                            if actual_value == expected_value:
                                matches += 1
                                log(f"Profile {profile_name}: {key} matched exactly", "success")
                            elif isinstance(expected_value, bool) and actual_value == expected_value:
                                matches += 1
                                log(f"Profile {profile_name}: Boolean {key} matched", "success")
                
                # Calculate match percentage
                if expected_count > 0:
                    match_percentage = (matches / expected_count) * 100
                    
                    if match_percentage >= 50:  # At least 50% of expected preferences found
                        log(f"Profile {profile_name}: {match_percentage:.1f}% of expected preferences found", "success")
                    else:
                        log(f"Profile {profile_name}: Only {match_percentage:.1f}% of expected preferences found", "warning")
                        all_profiles_passed = False
                else:
                    log(f"Profile {profile_name}: No expected preferences defined", "warning")
        
        except requests.exceptions.RequestException as e:
            log(f"Error testing profile {profile_name}: {str(e)}", "error")
            all_profiles_passed = False
    
    record_test_result("User Profiles Test", all_profiles_passed, "All profiles extracted preferences correctly" if all_profiles_passed else "Some profiles failed preference extraction")
    return all_profiles_passed

async def run_all_tests() -> None:
    """Run the full test suite"""
    print("\n" + "=" * 50)
    print("CONTEXT-AWARE CHAT SYSTEM: INTEGRATION TEST SUITE")
    print("=" * 50 + "\n")
    
    start_time = time.time()
    
    # Check if server is running
    server_healthy = await test_health_check()
    if not server_healthy:
        log("API server is not healthy. Skipping remaining tests.", "error")
        print_test_summary()
        return
    
    # Test session management
    session_success, session_id = await test_session_management()
    
    if not session_success:
        log("Session management failed. Skipping session-dependent tests.", "error")
        print_test_summary()
        return
    
    # Run remaining tests with the created session
    await test_conversation_context(session_id)
    await test_preference_extraction(session_id)
    await test_recommendation_quality(session_id)
    
    # Test with different user profiles
    await test_user_profiles()
    
    # Print test summary
    print_test_summary()
    
    # Calculate runtime
    runtime = time.time() - start_time
    print(f"\nTest suite completed in {runtime:.2f} seconds.")

if __name__ == "__main__":
    # Run all tests
    asyncio.run(run_all_tests())