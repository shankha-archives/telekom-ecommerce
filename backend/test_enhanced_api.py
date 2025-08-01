#!/usr/bin/env python
"""
Test script for the enhanced API endpoints
"""

import asyncio
import json
import os
import sys
import requests
from datetime import datetime

# Setup API URL
API_URL = "http://localhost:8001"

async def test_chat_endpoint():
    """Test the chat endpoint with a sample message"""
    print("Testing /api/chat endpoint...")
    
    session_id = None
    
    # First message - asking about phones
    message = "I'm looking for a new smartphone with good battery life"
    
    try:
        response = requests.post(
            f"{API_URL}/api/chat",
            json={
                "message": message,
                "session_id": session_id,
                "language": "en"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get("session_id")
            
            print(f"Session ID: {session_id}")
            print(f"Response: {result.get('response')}")
            
            # Check recommendations
            devices = result.get("recommendations", {}).get("devices", [])
            if devices:
                print(f"Recommended devices: {len(devices)}")
                for device in devices[:2]:  # Show just first 2
                    print(f"- {device.get('name')} (€{device.get('price')})")
            
            # Check follow-up questions
            follow_ups = result.get("follow_up_questions", [])
            if follow_ups:
                print(f"Follow-up questions: {len(follow_ups)}")
                for q in follow_ups:
                    print(f"- {q}")
            
            # Check for preference extraction
            if result.get("preference_summary"):
                print(f"Extracted preferences: {result.get('preference_summary')}")
            
            print("✅ Chat endpoint test passed\n")
            
            # Test follow-up message with session context
            return await test_followup_message(session_id)
        else:
            print(f"❌ Chat endpoint test failed: HTTP {response.status_code}")
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Chat endpoint test failed with error: {str(e)}")
        return False

async def test_followup_message(session_id):
    """Test a follow-up message using session context"""
    print("Testing follow-up message with session context...")
    
    # Follow-up message about price range
    message = "I'd like to spend less than €800"
    
    try:
        response = requests.post(
            f"{API_URL}/api/chat",
            json={
                "message": message,
                "session_id": session_id,
                "language": "en"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"Response: {result.get('response')}")
            
            # Check recommendations
            devices = result.get("recommendations", {}).get("devices", [])
            if devices:
                print(f"Recommended devices: {len(devices)}")
                for device in devices[:2]:  # Show just first 2
                    print(f"- {device.get('name')} (€{device.get('price')})")
                    if device.get('price') > 800:
                        print("❌ Test failed: Received device above price limit")
                        return False
            
            # Check for updated preferences
            if result.get("preference_summary"):
                print(f"Updated preferences: {result.get('preference_summary')}")
                
                # Check if price preference was understood
                if "budget" in json.dumps(result.get("preference_summary", [])).lower():
                    print("✅ Price preference correctly detected")
                else:
                    print("⚠️ Price preference may not have been detected")
            
            print("✅ Follow-up message test passed\n")
            
            # Test session retrieval
            return await test_session_retrieval(session_id)
        else:
            print(f"❌ Follow-up message test failed: HTTP {response.status_code}")
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Follow-up message test failed with error: {str(e)}")
        return False

async def test_session_retrieval(session_id):
    """Test retrieving session data"""
    print("Testing session retrieval...")
    
    try:
        response = requests.get(
            f"{API_URL}/api/session/{session_id}"
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"Session ID: {session_id}")
            print(f"Created at: {result.get('created_at')}")
            print(f"Conversation count: {result.get('conversation_count')}")
            
            # Check preferences
            preferences = result.get("user_preferences", {})
            if preferences:
                print("User preferences:")
                print(json.dumps(preferences, indent=2))
            
            # Test preference update
            return await test_preference_update(session_id)
        else:
            print(f"❌ Session retrieval test failed: HTTP {response.status_code}")
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Session retrieval test failed with error: {str(e)}")
        return False

async def test_preference_update(session_id):
    """Test updating preferences"""
    print("\nTesting preference update...")
    
    try:
        # Define new preferences
        new_preferences = {
            "device_preferences": {
                "brand": ["Samsung", "Google"],
                "price_range": {"min": 300, "max": 700},
                "features": ["Good camera", "Water resistant"],
                "color": ["Black", "Blue"]
            },
            "plan_preferences": {
                "data_needs": "high",
                "price_sensitivity": "medium",
                "international": True
            }
        }
        
        response = requests.post(
            f"{API_URL}/api/session/{session_id}/preferences",
            json={"preferences": new_preferences}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"Success: {result.get('success')}")
            
            # Check preference summary
            if result.get("preferences_summary"):
                print(f"Preference summary: {result.get('preferences_summary')}")
            
            print("✅ Preference update test passed\n")
            
            # Test search after preference update
            return await test_search_with_preferences(session_id)
        else:
            print(f"❌ Preference update test failed: HTTP {response.status_code}")
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Preference update test failed with error: {str(e)}")
        return False

async def test_search_with_preferences(session_id):
    """Test search with updated preferences"""
    print("\nTesting search with updated preferences...")
    
    try:
        response = requests.post(
            f"{API_URL}/api/search",
            json={
                "query": "show me phones",
                "session_id": session_id
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if results match preferences
            devices = result.get("devices", [])
            if devices:
                print(f"Returned {len(devices)} devices")
                
                # Check if preferences influenced results (looking for Samsung or Google)
                brand_matches = [d for d in devices if d.get("brand") in ["Samsung", "Google"]]
                if brand_matches:
                    print(f"✅ Found {len(brand_matches)} devices matching brand preferences")
                else:
                    print("⚠️ No devices match brand preferences")
                
                # Check price range
                price_matches = [d for d in devices if 300 <= d.get("price", 0) <= 700]
                if price_matches:
                    print(f"✅ Found {len(price_matches)} devices in preferred price range")
                else:
                    print("⚠️ No devices in preferred price range")
            
            print("✅ Search with preferences test passed")
            return True
        else:
            print(f"❌ Search test failed: HTTP {response.status_code}")
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Search test failed with error: {str(e)}")
        return False

async def run_all_tests():
    """Run all tests in sequence"""
    print("🧪 Starting enhanced API tests...")
    print("=" * 50)
    
    # Check if server is running
    try:
        health_check = requests.get(f"{API_URL}/api/health")
        if health_check.status_code != 200:
            print("❌ API server is not responding. Please start the server.")
            return
        
        print("✅ Server is running")
    except Exception:
        print("❌ API server is not responding. Please start the server.")
        return
    
    # Run tests
    result = await test_chat_endpoint()
    
    # Summary
    print("=" * 50)
    if result:
        print("🎉 All tests passed successfully!")
    else:
        print("❌ Some tests failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(run_all_tests())