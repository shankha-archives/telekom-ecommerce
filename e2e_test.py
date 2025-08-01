#!/usr/bin/env python
"""
End-to-End Testing for Telekom E-commerce Context-Aware Chat System

This script tests the entire flow of the application from frontend to backend,
simulating real user interactions and validating the complete system integration.
"""

import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configuration
DEFAULT_FRONTEND_URL = "http://localhost:3000"
DEFAULT_BACKEND_URL = "http://localhost:8001"
TEST_TIMEOUT = 60  # seconds for browser operations
REQUEST_TIMEOUT = 10  # seconds for API requests
HEADLESS = False  # Set to True to run browser in headless mode

# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Budget Phone Search",
        "steps": [
            {"action": "chat", "input": "I need a phone under 600 euros", "wait_for": "recommendations"},
            {"action": "chat", "input": "I want good battery life", "wait_for": "recommendations"},
            {"action": "chat", "input": "Show me Samsung options", "wait_for": "recommendations"},
            {"action": "verify_preferences", "expected": {"brand": "Samsung", "price_max": 600}}
        ]
    },
    {
        "name": "Plan Comparison",
        "steps": [
            {"action": "chat", "input": "I need a mobile plan with lots of data", "wait_for": "recommendations"},
            {"action": "chat", "input": "Can you compare the options?", "wait_for": "comparison"},
            {"action": "chat", "input": "Which one has international roaming?", "wait_for": "response"}
        ]
    },
    {
        "name": "Full Shopping Journey",
        "steps": [
            {"action": "chat", "input": "I want to upgrade my iPhone", "wait_for": "recommendations"},
            {"action": "chat", "input": "Show me options with 256GB storage", "wait_for": "recommendations"},
            {"action": "preferences", "set": {"device_preferences": {"color": ["Black"]}}},
            {"action": "chat", "input": "What plans go well with this phone?", "wait_for": "recommendations"},
            {"action": "add_to_cart", "item_index": 0, "type": "device"},
            {"action": "verify_cart", "expected_count": 1}
        ]
    }
]

# Results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "scenarios": []
}

# Utility functions
def log(message: str, level: str = "info") -> None:
    """Log a message with timestamp and level"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if level == "info":
        print(f"[{timestamp}] INFO: {message}")
    elif level == "error":
        print(f"[{timestamp}] ERROR: {message}")
    elif level == "success":
        print(f"[{timestamp}] ✅ {message}")
    elif level == "warning":
        print(f"[{timestamp}] ⚠️ {message}")
    elif level == "scenario":
        print(f"\n[{timestamp}] 🔍 SCENARIO: {message}")
    elif level == "step":
        print(f"[{timestamp}] 👉 STEP: {message}")

def record_scenario_result(name: str, passed: bool, details: str = None) -> None:
    """Record a test scenario result"""
    result = "PASSED" if passed else "FAILED"
    test_results["scenarios"].append({
        "name": name,
        "result": result,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    
    if passed:
        test_results["passed"] += 1
        log(f"Scenario '{name}': {result}", "success")
    else:
        test_results["failed"] += 1
        log(f"Scenario '{name}': {result} - {details}", "error")

def print_test_summary() -> None:
    """Print a summary of all test results"""
    total = test_results["passed"] + test_results["failed"] + test_results["skipped"]
    print("\n" + "=" * 50)
    print(f"END-TO-END TEST SUMMARY: {total} scenarios run")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⏭️ Skipped: {test_results['skipped']}")
    print("=" * 50)
    
    # Print failed scenarios
    if test_results["failed"] > 0:
        print("\nFailed Scenarios:")
        for test in test_results["scenarios"]:
            if test["result"] == "FAILED":
                print(f"- {test['name']}: {test['details']}")

class E2ETest:
    """End-to-End test runner for the context-aware chat system"""
    
    def __init__(self, frontend_url: str, backend_url: str):
        self.frontend_url = frontend_url
        self.backend_url = backend_url
        self.driver = None
        self.session_id = None
    
    def setup(self) -> bool:
        """Set up the test environment and browser"""
        log("Setting up test environment")
        
        try:
            # Check if backend is running
            response = requests.get(f"{self.backend_url}/api/health", timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                log(f"Backend API not available: HTTP {response.status_code}", "error")
                return False
            
            # Initialize webdriver
            options = webdriver.ChromeOptions()
            if HEADLESS:
                options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            
            try:
                self.driver = webdriver.Chrome(options=options)
                self.driver.implicitly_wait(5)  # seconds
                log("Browser initialized", "success")
            except WebDriverException as e:
                log(f"Failed to initialize browser: {str(e)}", "error")
                return False
            
            return True
            
        except requests.exceptions.RequestException as e:
            log(f"Error connecting to backend: {str(e)}", "error")
            return False
        except Exception as e:
            log(f"Setup error: {str(e)}", "error")
            return False
    
    def teardown(self) -> None:
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
    
    def run_scenario(self, scenario: Dict) -> bool:
        """Run a single test scenario"""
        name = scenario["name"]
        steps = scenario["steps"]
        
        log(f"Running scenario: {name}", "scenario")
        
        try:
            # Open the application
            self.driver.get(self.frontend_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            log("Application loaded", "success")
            
            # Execute each step
            step_results = []
            for i, step in enumerate(steps):
                step_name = f"{step['action']}: {step.get('input', '')}"
                log(f"Step {i+1}/{len(steps)}: {step_name}", "step")
                
                success = self.execute_step(step)
                step_results.append(success)
                
                if not success:
                    log(f"Step {i+1} failed: {step_name}", "error")
                    record_scenario_result(name, False, f"Failed at step {i+1}: {step_name}")
                    return False
                
                log(f"Step {i+1} completed successfully", "success")
                time.sleep(1)  # Small delay between steps
            
            # All steps passed
            record_scenario_result(name, True, "All steps completed successfully")
            return True
            
        except Exception as e:
            log(f"Error in scenario '{name}': {str(e)}", "error")
            record_scenario_result(name, False, f"Exception: {str(e)}")
            return False
    
    def execute_step(self, step: Dict) -> bool:
        """Execute a single test step"""
        action = step["action"]
        
        try:
            if action == "chat":
                return self.send_chat_message(step["input"], step.get("wait_for", "response"))
            elif action == "preferences":
                return self.update_preferences(step["set"])
            elif action == "verify_preferences":
                return self.verify_preferences(step["expected"])
            elif action == "add_to_cart":
                return self.add_to_cart(step["item_index"], step["type"])
            elif action == "verify_cart":
                return self.verify_cart(step["expected_count"])
            else:
                log(f"Unknown action: {action}", "error")
                return False
        except Exception as e:
            log(f"Step execution error: {str(e)}", "error")
            return False
    
    def send_chat_message(self, message: str, wait_for: str) -> bool:
        """Send a message in the chat and wait for the specified response type"""
        try:
            # Click on chat input
            chat_input = None
            
            # First try to find by placeholder
            try:
                chat_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//input[@placeholder='Ask me anything about devices and plans...']")
                    )
                )
            except TimeoutException:
                # If not found, try to find any input field in the chat
                try:
                    chat_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//input[@placeholder='Type your message...']")
                        )
                    )
                except TimeoutException:
                    # Try to find modern chat interface
                    try:
                        # Click to expand chat if minimized
                        self.driver.find_element(By.XPATH, "//button[contains(@class, 'bg-magenta')]").click()
                        time.sleep(1)
                        
                        chat_input = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, "//div[contains(@class, 'chat-container')]//input")
                            )
                        )
                    except (TimeoutException, WebDriverException):
                        log("Could not find chat input field", "error")
                        return False
            
            # Clear any existing text and enter message
            chat_input.clear()
            chat_input.send_keys(message)
            chat_input.send_keys(Keys.RETURN)
            
            log(f"Sent message: '{message}'", "info")
            
            # Wait for response
            if wait_for == "response":
                # Wait for any assistant response
                WebDriverWait(self.driver, TEST_TIMEOUT).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'bg-white border text-gray-800')]")
                    )
                )
            elif wait_for == "recommendations":
                # Wait for product cards to appear
                WebDriverWait(self.driver, TEST_TIMEOUT).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'grid gap-3')]")
                    )
                )
            elif wait_for == "comparison":
                # Wait for comparison table to appear
                WebDriverWait(self.driver, TEST_TIMEOUT).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//table")
                    )
                )
            
            # Check for error messages
            try:
                error = self.driver.find_element(By.XPATH, "//div[contains(text(), 'error') or contains(text(), 'Error')]")
                if error.is_displayed():
                    log(f"Error message found: {error.text}", "error")
                    return False
            except:
                pass  # No error found
            
            # Try to extract session ID from DOM or localStorage
            try:
                self.session_id = self.driver.execute_script(
                    "return window.localStorage.getItem('sessionId') || document.querySelector('div[data-session-id]')?.getAttribute('data-session-id')"
                )
            except:
                pass
            
            return True
        
        except TimeoutException:
            log(f"Timeout waiting for {wait_for} after sending message", "error")
            return False
    
    def update_preferences(self, preferences: Dict) -> bool:
        """Open the preferences dialog and update preferences"""
        try:
            # Find and click the preferences button
            pref_button = WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[.//span[contains(text(), 'Preferences')] or .//svg[contains(@class, 'settings')]]")
                )
            )
            pref_button.click()
            
            # Wait for dialog to appear
            WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'dialog') and .//h2[contains(text(), 'Preferences')]]")
                )
            )
            
            # Process device preferences
            if "device_preferences" in preferences:
                device_prefs = preferences["device_preferences"]
                
                # Ensure we're on the devices tab
                device_tab = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Devices')]")
                device_tab.click()
                
                # Set brand preferences if specified
                if "brand" in device_prefs:
                    for brand in device_prefs["brand"]:
                        try:
                            brand_badge = self.driver.find_element(
                                By.XPATH, f"//div[contains(text(), 'Preferred Brands')]/..//div[contains(@class, 'flex flex-wrap')]//*[contains(text(), '{brand}')]"
                            )
                            brand_badge.click()
                        except:
                            log(f"Could not find brand badge for {brand}", "warning")
                
                # Set color preferences if specified
                if "color" in device_prefs:
                    for color in device_prefs["color"]:
                        try:
                            color_badge = self.driver.find_element(
                                By.XPATH, f"//div[contains(text(), 'Color')]/..//div[contains(@class, 'flex flex-wrap')]//*[contains(text(), '{color}')]"
                            )
                            color_badge.click()
                        except:
                            log(f"Could not find color badge for {color}", "warning")
            
            # Process plan preferences if specified
            if "plan_preferences" in preferences:
                plan_prefs = preferences["plan_preferences"]
                
                # Switch to plans tab
                plan_tab = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Plans')]")
                plan_tab.click()
                
                # Set data needs if specified
                if "data_needs" in plan_prefs:
                    data_need = plan_prefs["data_needs"]
                    try:
                        data_button = self.driver.find_element(
                            By.XPATH, f"//div[contains(text(), 'Data Needs')]/..//button[contains(text(), '{data_need}')]"
                        )
                        data_button.click()
                    except:
                        log(f"Could not find data needs option for {data_need}", "warning")
            
            # Save preferences
            save_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
            save_button.click()
            
            # Wait for dialog to close
            WebDriverWait(self.driver, TEST_TIMEOUT).until_not(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'dialog') and .//h2[contains(text(), 'Preferences')]]")
                )
            )
            
            return True
        
        except TimeoutException:
            log("Timeout while updating preferences", "error")
            return False
        except Exception as e:
            log(f"Error updating preferences: {str(e)}", "error")
            return False
    
    def verify_preferences(self, expected: Dict) -> bool:
        """Verify that preferences are correctly reflected in the context indicator"""
        try:
            # Wait for context indicator to appear
            context = WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'px-4 py-2 border-b bg-gray-50')]")
                )
            )
            
            # Click to expand if not already expanded
            try:
                expand_button = context.find_element(By.XPATH, ".//svg[contains(@class, 'chevron')]")
                expand_button.click()
                time.sleep(0.5)  # Wait for expansion animation
            except:
                pass  # Either already expanded or no expand button
            
            # Check for specific preferences
            all_found = True
            
            # Check for brand
            if "brand" in expected:
                try:
                    self.driver.find_element(
                        By.XPATH, f"//span[contains(text(), 'Brand') and contains(text(), '{expected['brand']}')]"
                    )
                    log(f"Found brand preference: {expected['brand']}", "success")
                except:
                    log(f"Brand preference not found: {expected['brand']}", "warning")
                    all_found = False
            
            # Check for price max
            if "price_max" in expected:
                try:
                    # Look for any budget/price range element
                    price_element = self.driver.find_element(
                        By.XPATH, "//span[contains(text(), 'Budget') or contains(text(), 'Price')]"
                    )
                    
                    # Check if the displayed max is less than or equal to expected max
                    price_text = price_element.text
                    # Extract numeric value from text using regex
                    import re
                    found_prices = re.findall(r'€(\d+)', price_text)
                    
                    if found_prices and len(found_prices) > 1:
                        max_price = int(found_prices[1])  # Second price is usually the max
                        if max_price <= expected["price_max"]:
                            log(f"Found acceptable price range with max {max_price}", "success")
                        else:
                            log(f"Price range max {max_price} exceeds expected {expected['price_max']}", "warning")
                            all_found = False
                    else:
                        log(f"Could not extract price range from: {price_text}", "warning")
                        all_found = False
                except:
                    log(f"Price range preference not found", "warning")
                    all_found = False
            
            return all_found
            
        except TimeoutException:
            log("Timeout waiting for context indicator", "error")
            return False
        except Exception as e:
            log(f"Error verifying preferences: {str(e)}", "error")
            return False
    
    def add_to_cart(self, item_index: int, item_type: str) -> bool:
        """Add an item to the cart"""
        try:
            # Find all product cards
            if item_type == "device":
                xpath = "//div[contains(@class, 'card') and .//button[contains(text(), 'Add to Cart')]]"
            else:
                xpath = "//div[contains(@class, 'card') and .//button[contains(text(), 'Choose Plan')]]"
            
            product_cards = WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_all_elements_located((By.XPATH, xpath))
            )
            
            if not product_cards or item_index >= len(product_cards):
                log(f"No product cards found or index {item_index} out of range", "error")
                return False
            
            # Click the button on the specified card
            button_xpath = ".//button[contains(text(), 'Add to Cart') or contains(text(), 'Choose Plan')]"
            add_button = product_cards[item_index].find_element(By.XPATH, button_xpath)
            add_button.click()
            
            # Wait for cart confirmation
            try:
                confirmation = WebDriverWait(self.driver, TEST_TIMEOUT).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(text(), 'Added') or contains(text(), 'added to cart') or .//span[contains(text(), 'Cart')]/following-sibling::*[contains(@class, 'badge')]]")
                    )
                )
                log("Item added to cart successfully", "success")
                return True
            except TimeoutException:
                log("No confirmation for adding item to cart", "warning")
                # Try to verify by checking cart icon
                try:
                    cart_badge = self.driver.find_element(
                        By.XPATH, "//button[contains(@class, 'relative') and .//svg[contains(@class, 'shopping')]]//span[contains(@class, 'badge')]"
                    )
                    if cart_badge.is_displayed():
                        log("Cart badge found, item likely added", "success")
                        return True
                except:
                    pass
                
                return False
            
        except TimeoutException:
            log("Timeout finding product cards", "error")
            return False
        except Exception as e:
            log(f"Error adding to cart: {str(e)}", "error")
            return False
    
    def verify_cart(self, expected_count: int) -> bool:
        """Verify the cart contents"""
        try:
            # Find and click the cart button
            cart_button = WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[.//svg[contains(@class, 'shopping-cart')] or contains(text(), 'Cart')]")
                )
            )
            cart_button.click()
            
            # Wait for cart view
            cart_view = WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h1[contains(text(), 'Your Cart')]")
                )
            )
            
            # Check if cart is empty
            try:
                empty_cart = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'empty')]")
                if empty_cart.is_displayed() and expected_count > 0:
                    log("Cart is empty but expected items", "error")
                    return False
                elif empty_cart.is_displayed() and expected_count == 0:
                    log("Cart is empty as expected", "success")
                    return True
            except:
                # Cart is not empty
                pass
            
            # Count items in cart
            cart_items = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'space-y-6')]/div[contains(@class, 'card')]")
            
            if len(cart_items) == expected_count:
                log(f"Cart contains {len(cart_items)} items as expected", "success")
                return True
            else:
                log(f"Cart contains {len(cart_items)} items, expected {expected_count}", "error")
                return False
            
        except TimeoutException:
            log("Timeout accessing cart", "error")
            return False
        except Exception as e:
            log(f"Error verifying cart: {str(e)}", "error")
            return False
    
    def verify_session_data(self) -> bool:
        """Verify session data via API if session_id is available"""
        if not self.session_id:
            log("No session ID available to verify", "warning")
            return True  # Not a failure
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/session/{self.session_id}",
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                session_data = response.json()
                
                # Check for key session components
                if not session_data.get("user_preferences"):
                    log("Session has no user preferences", "warning")
                
                # Check conversation history
                conversation_count = session_data.get("conversation_count", 0)
                if conversation_count == 0:
                    log("Session has no conversation history", "warning")
                else:
                    log(f"Session has {conversation_count} conversation messages", "success")
                
                return True
            else:
                log(f"Failed to retrieve session data: HTTP {response.status_code}", "error")
                return False
            
        except requests.exceptions.RequestException as e:
            log(f"Error retrieving session data: {str(e)}", "warning")
            return True  # Not a critical failure

async def run_e2e_tests(frontend_url: str, backend_url: str) -> None:
    """Run all end-to-end test scenarios"""
    print("\n" + "=" * 50)
    print("END-TO-END TESTING FOR CONTEXT-AWARE CHAT SYSTEM")
    print("=" * 50 + "\n")
    
    # Initialize test runner
    e2e = E2ETest(frontend_url, backend_url)
    
    if not e2e.setup():
        print("Failed to set up test environment. Aborting tests.")
        return
    
    try:
        # Run each test scenario
        for scenario in TEST_SCENARIOS:
            e2e.run_scenario(scenario)
            
            # Verify session data after each scenario
            e2e.verify_session_data()
            
            # Short delay between scenarios
            time.sleep(2)
        
        # Print test summary
        print_test_summary()
    
    finally:
        e2e.teardown()

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="End-to-End Tests for Telekom E-commerce")
    parser.add_argument("--frontend", default=DEFAULT_FRONTEND_URL, help=f"Frontend URL (default: {DEFAULT_FRONTEND_URL})")
    parser.add_argument("--backend", default=DEFAULT_BACKEND_URL, help=f"Backend URL (default: {DEFAULT_BACKEND_URL})")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    args = parser.parse_args()
    
    # Update config
    HEADLESS = args.headless
    
    # Run tests
    asyncio.run(run_e2e_tests(args.frontend, args.backend))