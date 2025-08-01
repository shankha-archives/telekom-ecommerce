from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Import our new modules
import session_manager
import preference_extractor
import recommendation_engine
import user_profile_utils
import llm_recommendation_logger
import enhanced_api

load_dotenv()

app = FastAPI(title="Telekom Ecommerce API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Initialize OpenAI client
openai_client = None

def get_openai_client():
    global openai_client
    if OPENAI_API_KEY and openai_client is None:
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return openai_client

# Helper function to find items by ID
def find_by_id(items: List[Dict], item_id: str) -> Optional[Dict]:
    """Find an item in a list by its ID"""
    return next((item for item in items if item["id"] == item_id), None)

# Pydantic models
class Device(BaseModel):
    id: str
    name: str
    brand: str
    price: float
    original_price: Optional[float] = None
    image: str
    description: str
    features: List[str]
    storage: str
    color: str
    category: str = "smartphone"
    in_stock: bool = True
    rating: float = 4.5

class Plan(BaseModel):
    id: str
    name: str
    price: float
    duration: str  # monthly, yearly
    data: str
    minutes: str
    sms: str
    features: List[str]
    popular: bool = False
    category: str = "mobile"

class CartItem(BaseModel):
    device_id: Optional[str] = None
    plan_id: Optional[str] = None
    quantity: int = 1

class SearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None  # Added for personalized recommendations

class VoiceRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None  # Added for personalized recommendations
    language: str = "en"  # en or hi
    last_search_results: Optional[Dict] = None
    chat_history: Optional[List[Dict]] = None

class PreferenceUpdateRequest(BaseModel):
    preferences: Dict[str, Any]

# In-memory storage for devices and plans
devices_store = []
plans_store = []

# Sample data
import csv

def load_devices_from_csv(csv_path):
    devices = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            features = row['features'].split(';') if row['features'] else []
            device = {
                'id': row['id'] or str(uuid.uuid4()),
                'name': row['name'],
                'brand': row['brand'],
                'price': float(row['price']) if row['price'] else None,
                'original_price': float(row['original_price']) if row['original_price'] else None,
                'image': row['image'],
                'description': row['description'],
                'features': features,
                'storage': row['storage'],
                'color': row['color'],
                'rating': float(row['rating']) if row['rating'] else None
            }
            devices.append(device)
    return devices

sample_devices = load_devices_from_csv(os.path.join(os.path.dirname(__file__), 'sample_devices.csv'))

def load_plans_from_csv(csv_path):
    plans = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            features = row['features'].split(';') if row['features'] else []
            plan = {
                'id': row['id'] or str(uuid.uuid4()),
                'name': row['name'],
                'price': float(row['price']) if row['price'] else None,
                'duration': row['duration'],
                'data': row['data'],
                'minutes': row['minutes'],
                'sms': row['sms'],
                'features': features,
                'popular': row['popular'].lower() == 'true' if row['popular'] else False
            }
            plans.append(plan)
    return plans

sample_plans = load_plans_from_csv(os.path.join(os.path.dirname(__file__), 'sample_plans.csv'))

@app.on_event("startup")
async def startup_event():
    """Initialize in-memory storage with sample data"""
    global devices_store, plans_store
    
    try:
        # Initialize devices store
        devices_store = sample_devices.copy()
        print(f"✅ Loaded {len(devices_store)} sample devices")
        
        # Initialize plans store
        plans_store = sample_plans.copy()
        print(f"✅ Loaded {len(plans_store)} sample plans")
        
        # Check OpenAI API key
        if OPENAI_API_KEY:
            print("✅ OpenAI API key configured")
        else:
            print("⚠️  OpenAI API key not configured - AI features will be disabled")
        
        # Setup enhanced API routes
        await enhanced_api.setup_enhanced_routes(app, devices_store, plans_store)
        print("✅ Enhanced API routes configured")
        
        print("✅ Application initialized successfully")
    except Exception as e:
        print(f"❌ Application initialization error: {e}")
        print("⚠️  Server will continue but features may be limited")

@app.get("/api/devices")
async def get_devices():
    """Get all devices (always up-to-date from CSV)"""
    csv_path = os.path.join(os.path.dirname(__file__), 'sample_devices.csv')
    devices = load_devices_from_csv(csv_path)
    return devices

@app.get("/api/devices/{device_id}")
async def get_device(device_id: str, session_id: Optional[str] = None):
    """Get specific device"""
    device = find_by_id(devices_store, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update session with viewed item if session_id is provided
    if session_id:
        session_manager.update_viewed_item(session_id, 'devices', device_id, device)
    
    return device

@app.get("/api/plans")
async def get_plans():
    """Get all plans (always up-to-date from CSV)"""
    csv_path = os.path.join(os.path.dirname(__file__), 'sample_plans.csv')
    plans = load_plans_from_csv(csv_path)
    return plans

@app.get("/api/plans/{plan_id}")
async def get_plan(plan_id: str, session_id: Optional[str] = None):
    """Get specific plan"""
    plan = find_by_id(plans_store, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Update session with viewed item if session_id is provided
    if session_id:
        session_manager.update_viewed_item(session_id, 'plans', plan_id, plan)
    
    return plan

@app.post("/api/search")
async def smart_search(request: SearchRequest):
    """Smart LLM-powered search for devices and plans with contextual awareness"""
    try:
        print(f"DEBUG: Smart search request: {request.query}")
        
        # Load user profile if user_id is provided
        user_profile = None
        if hasattr(request, 'user_id') and request.user_id:
            user_profile = user_profile_utils.get_user_profile(request.user_id)
        
        # Get or create session
        print(f"DEBUG: Getting/creating session for ID: {request.session_id}")
        session_id, session_data = session_manager.get_or_create_session(request.session_id)
        print(f"DEBUG: Session obtained with ID: {session_id}")
        
        # Add search query to session
        session_manager.add_search_query(session_id, request.query)
        
        # Get all devices and plans
        print(f"DEBUG: Loading devices and plans")
        devices = devices_store
        plans = plans_store
        print(f"DEBUG: Loaded {len(devices)} devices and {len(plans)} plans")
        
        if not OPENAI_API_KEY:
            # Fallback to simple text search if no API key
            query_lower = request.query.lower()
            filtered_devices = [
                d for d in devices 
                if query_lower in d["name"].lower() or 
                   query_lower in d["brand"].lower() or 
                   query_lower in d["description"].lower()
            ]
            
            filtered_plans = [
                p for p in plans 
                if query_lower in p["name"].lower() or 
                   any(query_lower in feature.lower() for feature in p["features"])
            ]
            
            return {
                "devices": filtered_devices[:5],
                "plans": filtered_plans[:3],
                "recommendation": f"Found {len(filtered_devices)} devices and {len(filtered_plans)} plans matching '{request.query}'",
                "session_id": session_id
            }
        
        # Use our recommendation engine to generate weighted recommendations
        print(f"DEBUG: Calling recommendation engine")
        try:
            recommendations = recommendation_engine.generate_weighted_recommendations(
                session_data, 
                devices, 
                plans, 
                request.query
            )
            print(f"DEBUG: Recommendation engine returned successfully")
        except Exception as e:
            print(f"DEBUG: Error in recommendation engine: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise
        
        # Extract recommended devices and plans
        recommended_devices = recommendations.get('devices', [])
        recommended_plans = recommendations.get('plans', [])
        device_explanations = recommendations.get('device_explanations', {})
        plan_explanations = recommendations.get('plan_explanations', {})
        print(f"DEBUG: Got {len(recommended_devices)} devices and {len(recommended_plans)} plans")
        
        # Generate recommendation summary
        summary = await recommendation_engine.generate_recommendation_summary(
            recommendations,
            session_data.get('user_preferences', {}),
            request.query
        )
        
        # Update viewed items in session for all recommended items
        for device in recommended_devices:
            session_manager.update_viewed_item(session_id, 'devices', device['id'], device)
        
        for plan in recommended_plans:
            session_manager.update_viewed_item(session_id, 'plans', plan['id'], plan)
        
        # Try to extract preferences from the query
        if len(session_data['conversation_history']) % 3 == 0:  # Every 3 interactions to avoid excessive LLM calls
            # Add the search query to conversation history as a user message
            session_manager.add_to_conversation_history(session_id, 'user', request.query)
            
            # Extract or refine preferences
            if not session_data.get('user_preferences') or len(session_data['user_preferences']) == 0:
                new_preferences = await preference_extractor.extract_user_preferences(
                    session_data['conversation_history']
                )
            else:
                new_preferences = await preference_extractor.refine_preferences(
                    session_data['user_preferences'],
                    session_data['conversation_history']
                )
            
            if new_preferences:
                session_manager.update_user_preferences(session_id, new_preferences)
        
        # Log recommendation
        llm_recommendation_logger.log_llm_recommendation(
            user_id=request.user_id if hasattr(request, 'user_id') else None,
            user_profile=user_profile,
            llm_input={"query": request.query},
            llm_response={
                "recommended_devices": [d['id'] for d in recommended_devices],
                "recommended_plans": [p['id'] for p in recommended_plans],
                "explanation": summary
            },
            context={
                "devices": devices, 
                "plans": plans, 
                "user_profile": user_profile,
                "session_id": session_id,
                "user_preferences": session_data.get('user_preferences', {})
            }
        )
        
        # Generate follow-up questions based on context and recommendations
        follow_up_questions = []
        if recommended_devices and not recommended_plans:
            follow_up_questions.append("What kind of mobile plan would work with this device?")
        if recommended_plans and not recommended_devices:
            follow_up_questions.append("Do you have any device recommendations to go with this plan?")
        if recommended_devices and recommended_plans:
            follow_up_questions.append("Would you like to compare these options?")
        
        return {
            "devices": recommended_devices,
            "plans": recommended_plans,
            "device_explanations": device_explanations,
            "plan_explanations": plan_explanations,
            "recommendation": summary,
            "follow_up_questions": follow_up_questions,
            "session_id": session_id,
            "preferences": await preference_extractor.generate_preference_explanation(
                session_data.get('user_preferences', {})
            )
        }
    
    except Exception as e:
        print(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.post("/api/voice-search")
async def voice_search(request: VoiceRequest):
    """Voice assistant for search and conversation with enhanced context awareness"""
    try:
        # Get or create session
        session_id, session_data = session_manager.get_or_create_session(request.session_id)
        
        # Load user profile if user_id is provided
        user_profile = None
        if hasattr(request, 'user_id') and request.user_id:
            user_profile = user_profile_utils.get_user_profile(request.user_id)
        
        if not OPENAI_API_KEY:
            return {
                "response": f"I heard: '{request.text}'. Voice assistant requires API key configuration.",
                "action": "none",
                "data": {},
                "language": request.language,
                "session_id": session_id
            }
        
        # Get context data
        devices = devices_store
        plans = plans_store
        
        # Add user message to conversation history
        session_manager.add_to_conversation_history(session_id, 'user', request.text)
        
        # Add search query to session
        session_manager.add_search_query(session_id, request.text)
        
        # Create voice assistant LLM chat with enhanced context
        language_context = "Respond in Hindi and English mix" if request.language == "hi" else "Respond in English"
        
        # Build context string including last search results and conversation history
        context_data = f"DEVICES: {devices}\n\nPLANS: {plans}"
        
        # Get recent conversation from session
        conversation_history = session_data.get('conversation_history', [])
        recent_messages = conversation_history[-6:] if conversation_history else []
        
        # Process chat history for better context
        conversation_context = ""
        if recent_messages:
            conversation_context = "\n\nRECENT CONVERSATION:\n"
            for msg in recent_messages:
                if msg.get('type') == 'user':
                    conversation_context += f"User: {msg.get('message', '')}\n"
                elif msg.get('type') == 'assistant':
                    conversation_context += f"Assistant: {msg.get('message', '')}\n"
        
        # Add last search results context
        search_results_context = ""
        viewed_devices = session_data.get('viewed_items', {}).get('devices', {})
        viewed_plans = session_data.get('viewed_items', {}).get('plans', {})
        
        if viewed_devices or viewed_plans:
            search_results_context = "\n\nRECENTLY VIEWED ITEMS:\n"
            
            # Add recently viewed devices
            recent_devices = []
            for device_id, view_data in viewed_devices.items():
                if 'data' in view_data:
                    device_name = view_data['data'].get('name', '')
                    if device_name:
                        recent_devices.append(device_name)
            
            if recent_devices:
                search_results_context += f"Devices viewed: {', '.join(recent_devices[:5])}\n"
            
            # Add recently viewed plans
            recent_plans = []
            for plan_id, view_data in viewed_plans.items():
                if 'data' in view_data:
                    plan_name = view_data['data'].get('name', '')
                    if plan_name:
                        recent_plans.append(plan_name)
            
            if recent_plans:
                search_results_context += f"Plans viewed: {', '.join(recent_plans[:5])}\n"
        
        # Add preferences context
        preferences_context = ""
        user_preferences = session_data.get('user_preferences', {})
        if user_preferences:
            preferences_context = "\n\nUSER PREFERENCES:\n"
            preferences_context += json.dumps(user_preferences, indent=2)
        
        # Create enhanced system message for voice assistant
        system_message = f"""You are a helpful voice assistant for Telekom ecommerce. {language_context}.

Available products:
{context_data}

{preferences_context}

{conversation_context}

{search_results_context}

You are a conversational assistant that remembers context and handles speech recognition errors intelligently.

IMPORTANT: SPEECH RECOGNITION ERROR HANDLING:
- Speech recognition often makes mistakes (e.g., "S plan" becomes "ESP plan", "iPhone" becomes "I phone")
- Always try to understand user intent even with speech errors
- Look for phonetically similar words and correct them based on available products
- Common corrections needed:
  * "ESP plan" or "Yes plan" → "S plan" (MagentaMobil S)
  * "Em plan" or "M plan" → "MagentaMobil M" 
  * "El plan" or "L plan" → "MagentaMobil L"
  * "I phone" or "iphone" → "iPhone"
  * "Samsung galaxy" → "Samsung Galaxy"
  * "Pixel" variations → "Google Pixel"
- If you can reasonably infer what the user meant, proceed with that understanding
- Only say you cannot help if the request is completely unrelated to phones/plans

CONTEXT UNDERSTANDING:
- When users ask follow-up questions like "add to cart" after showing search results, you should know what items were recently viewed
- If the user mentions a specific product name like "iPhone" or "S plan", match it with the previously shown results
- If only one item was shown and user says "add to cart", add that item automatically
- Be smart about understanding references like "add that phone", "I want the cheaper one", etc.

Handle user voice queries for:
1. Product search and recommendations (with error correction)
2. Plan comparisons  
3. Adding items to cart (remember what was previously shown)
4. Checking cart and proceeding to checkout
5. General assistance

Always respond in JSON format:
{{
    "response": "Your conversational response to the user (mention if you corrected their speech)",
    "action": "search|add_to_cart|show_cart|checkout|compare|none",
    "data": {{
        "recommended_devices": [device objects if search],
        "recommended_plans": [plan objects if search],
        "cart_items": [{{id, name, price, type}} if adding to cart],
        "comparison": "comparison details if comparing"
    }},
    "follow_up_questions": ["1-3 relevant follow-up questions"],
    "language": "{request.language}"
}}

Be conversational, helpful, and contextually aware. When you correct speech recognition errors, briefly mention what you understood (e.g., "I understood you're looking for iPhones")."""
        
        # Send user query to OpenAI
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": request.text}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Parse LLM response
        response_content = response.choices[0].message.content
        try:
            result = json.loads(response_content)
            
            # If LLM doesn't return structured data, create a simple response
            if "response" not in result or "action" not in result:
                result = {
                    "response": response_content,
                    "action": "none",
                    "data": {},
                    "language": request.language
                }
            
            # If action is search but no recommendations, use our recommendation engine
            if result.get("action") == "search" and not result.get("data", {}).get("recommended_devices") and not result.get("data", {}).get("recommended_plans"):
                # Use weighted recommendation algorithm
                recommendations = recommendation_engine.generate_weighted_recommendations(
                    session_data,
                    devices,
                    plans,
                    request.text
                )
                
                # Add recommendations to result
                result["data"]["recommended_devices"] = recommendations.get('devices', [])
                result["data"]["recommended_plans"] = recommendations.get('plans', [])
                
                # Add explanations if not present
                if "explanations" not in result["data"]:
                    result["data"]["device_explanations"] = recommendations.get('device_explanations', {})
                    result["data"]["plan_explanations"] = recommendations.get('plan_explanations', {})
            
            # Add assistant response to conversation history
            session_manager.add_to_conversation_history(
                session_id,
                'assistant',
                result.get('response', ''),
                result.get('data', {})
            )
            
            # Extract preferences from conversation periodically
            if len(session_data['conversation_history']) % 3 == 0:  # Every 3 interactions
                if not session_data.get('user_preferences') or len(session_data['user_preferences']) == 0:
                    new_preferences = await preference_extractor.extract_user_preferences(
                        session_data['conversation_history']
                    )
                else:
                    new_preferences = await preference_extractor.refine_preferences(
                        session_data['user_preferences'],
                        session_data['conversation_history'][-5:]  # Use just recent messages for refinement
                    )
                
                if new_preferences:
                    session_manager.update_user_preferences(session_id, new_preferences)
            
            # Update viewed items if search results returned
            if result.get("action") == "search" and "data" in result:
                if "recommended_devices" in result["data"]:
                    for device in result["data"]["recommended_devices"]:
                        if isinstance(device, dict) and "id" in device:
                            session_manager.update_viewed_item(session_id, 'devices', device["id"], device)
                
                if "recommended_plans" in result["data"]:
                    for plan in result["data"]["recommended_plans"]:
                        if isinstance(plan, dict) and "id" in plan:
                            session_manager.update_viewed_item(session_id, 'plans', plan["id"], plan)
            
            # Log LLM recommendation
            llm_recommendation_logger.log_llm_recommendation(
                user_id=request.user_id if hasattr(request, 'user_id') else None,
                user_profile=user_profile,
                llm_input={
                    "text": request.text,
                    "session_id": session_id,
                    "language": request.language
                },
                llm_response=result,
                context={
                    "devices": devices,
                    "plans": plans,
                    "user_profile": user_profile,
                    "session_id": session_id,
                    "conversation_context": conversation_context,
                    "search_results_context": search_results_context,
                    "user_preferences": session_data.get('user_preferences', {})
                }
            )
            
            # Add session_id and preferences to result
            result["session_id"] = session_id
            result["preferences"] = await preference_extractor.generate_preference_explanation(
                session_data.get('user_preferences', {})
            )
            
            return result
        
        except json.JSONDecodeError:
            error_response = {
                "response": "I'm having trouble understanding your request. Could you try again?",
                "action": "none", 
                "data": {},
                "language": request.language,
                "session_id": session_id
            }
            
            # Add error message to conversation history
            session_manager.add_to_conversation_history(
                session_id,
                'assistant',
                error_response['response']
            )
            
            return error_response
    
    except Exception as e:
        print(f"Voice search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Voice search error: {str(e)}")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: str = "en"
    chat_history: Optional[List[Dict]] = None

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint for text-based conversations"""
    try:
        # Get or create session
        session_id, session_data = session_manager.get_or_create_session(request.session_id)
        
        # Add user message to conversation history
        session_manager.add_to_conversation_history(session_id, 'user', request.message)
        
        # Add search query to session
        session_manager.add_search_query(session_id, request.message)
        
        if not OPENAI_API_KEY:
            # Fallback if no API key - use simple search
            search_request = SearchRequest(query=request.message, session_id=session_id)
            search_result = await smart_search(search_request)
            
            response_message = search_result.get("recommendation", "I found some results for you!")
            
            return {
                "response": response_message,
                "session_id": session_id,
                "recommendations": {
                    "devices": search_result.get("devices", []),
                    "plans": search_result.get("plans", [])
                },
                "explanations": {
                    "device_explanations": search_result.get("device_explanations", {}),
                    "plan_explanations": search_result.get("plan_explanations", {})
                },
                "follow_up_questions": search_result.get("follow_up_questions", []),
                "preference_summary": search_result.get("preferences", [])
            }
        
        # Get context data 
        devices = devices_store
        plans = plans_store
        
        # Build conversation context
        conversation_history = session_data.get('conversation_history', [])
        recent_messages = conversation_history[-10:] if conversation_history else []
        
        conversation_context = ""
        if recent_messages:
            conversation_context = "\n\nRECENT CONVERSATION:\n"
            for msg in recent_messages:
                if msg.get('type') == 'user':
                    conversation_context += f"User: {msg.get('message', '')}\n"
                elif msg.get('type') == 'assistant':
                    conversation_context += f"Assistant: {msg.get('message', '')}\n"
        
        # Add preferences context
        preferences_context = ""
        user_preferences = session_data.get('user_preferences', {})
        if user_preferences:
            preferences_context = "\n\nUSER PREFERENCES:\n"
            preferences_context += json.dumps(user_preferences, indent=2)
        
        # Create system message for chat assistant
        language_context = "Respond in Hindi and English mix" if request.language == "hi" else "Respond in English"
        
        system_message = f"""You are a helpful chat assistant for Telekom ecommerce. {language_context}.

Available products:
DEVICES: {devices}

PLANS: {plans}

{preferences_context}

{conversation_context}

You help users find devices and plans through natural conversation. Handle user queries for:
1. Product search and recommendations
2. Plan comparisons  
3. General assistance about devices and plans
4. Questions about features, pricing, etc.

Always respond in JSON format:
{{
    "response": "Your conversational response to the user",
    "recommendations": {{
        "devices": [recommended device objects if relevant],
        "plans": [recommended plan objects if relevant]
    }},
    "explanations": {{
        "device_explanations": {{"device_id": ["reason1", "reason2"]}},
        "plan_explanations": {{"plan_id": ["reason1", "reason2"]}}
    }},
    "follow_up_questions": ["1-3 relevant follow-up questions"],
    "preference_summary": ["list of understood user preferences"]
}}

Be conversational, helpful, and provide specific product recommendations when relevant."""
        
        # Send message to OpenAI
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": request.message}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        # Parse LLM response
        response_content = response.choices[0].message.content
        try:
            result = json.loads(response_content)
            
            # If LLM doesn't return structured data, create a simple response
            if "response" not in result:
                result = {
                    "response": response_content,
                    "recommendations": {"devices": [], "plans": []},
                    "explanations": {"device_explanations": {}, "plan_explanations": {}},
                    "follow_up_questions": [],
                    "preference_summary": []
                }
            
            # If no specific recommendations but there's a search intent, use recommendation engine
            if (not result.get("recommendations", {}).get("devices") and 
                not result.get("recommendations", {}).get("plans") and
                any(keyword in request.message.lower() for keyword in ['find', 'search', 'recommend', 'suggest', 'want', 'need', 'looking', 'show'])):
                
                # Use weighted recommendation algorithm
                recommendations = recommendation_engine.generate_weighted_recommendations(
                    session_data,
                    devices,
                    plans,
                    request.message
                )
                
                # Add recommendations to result
                result["recommendations"]["devices"] = recommendations.get('devices', [])
                result["recommendations"]["plans"] = recommendations.get('plans', [])
                result["explanations"]["device_explanations"] = recommendations.get('device_explanations', {})
                result["explanations"]["plan_explanations"] = recommendations.get('plan_explanations', {})
            
            # Add assistant response to conversation history
            session_manager.add_to_conversation_history(
                session_id,
                'assistant',
                result.get('response', ''),
                result.get('recommendations', {})
            )
            
            # Update viewed items if search results returned
            if result.get("recommendations", {}).get("devices"):
                for device in result["recommendations"]["devices"]:
                    if isinstance(device, dict) and "id" in device:
                        session_manager.update_viewed_item(session_id, 'devices', device["id"], device)
            
            if result.get("recommendations", {}).get("plans"):
                for plan in result["recommendations"]["plans"]:
                    if isinstance(plan, dict) and "id" in plan:
                        session_manager.update_viewed_item(session_id, 'plans', plan["id"], plan)
            
            # Extract preferences from conversation periodically
            if len(session_data['conversation_history']) % 3 == 0:  # Every 3 interactions
                if not session_data.get('user_preferences') or len(session_data['user_preferences']) == 0:
                    new_preferences = await preference_extractor.extract_user_preferences(
                        session_data['conversation_history']
                    )
                else:
                    new_preferences = await preference_extractor.refine_preferences(
                        session_data['user_preferences'],
                        session_data['conversation_history'][-5:]  # Use just recent messages for refinement
                    )
                
                if new_preferences:
                    session_manager.update_user_preferences(session_id, new_preferences)
                    result["preference_summary"] = await preference_extractor.generate_preference_explanation(new_preferences)
            
            # Add session_id to result
            result["session_id"] = session_id
            result["session"] = {
                "session_id": session_id,
                "user_preferences": session_data.get('user_preferences', {}),
                "conversation_count": len(session_data.get('conversation_history', []))
            }
            
            return result
        
        except json.JSONDecodeError:
            # If JSON parsing fails, return a simple response
            session_manager.add_to_conversation_history(
                session_id,
                'assistant',
                "I'm having trouble understanding your request. Could you try again?"
            )
            
            return {
                "response": "I'm having trouble understanding your request. Could you try again?",
                "session_id": session_id,
                "recommendations": {"devices": [], "plans": []},
                "explanations": {"device_explanations": {}, "plan_explanations": {}},
                "follow_up_questions": ["What kind of device are you looking for?", "Are you interested in any specific features?"],
                "preference_summary": []
            }
    
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/api/session/{session_id}")
async def get_session_data(session_id: str):
    """Get session data for the frontend"""
    session_data = session_manager.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    # Return a sanitized version of the session data
    # (omitting internal implementation details)
    return {
        "session_id": session_id,
        "created_at": session_data.get("created_at"),
        "last_access": session_data.get("last_access"),
        "conversation_count": len(session_data.get("conversation_history", [])),
        "user_preferences": session_data.get("user_preferences", {}),
        "recently_viewed": {
            "devices": [
                {
                    "id": device_id,
                    "name": device_data.get("data", {}).get("name", ""),
                    "view_count": device_data.get("view_count", 0),
                    "last_viewed": device_data.get("last_viewed")
                }
                for device_id, device_data in session_data.get("viewed_items", {}).get("devices", {}).items()
                if "data" in device_data
            ][:5],
            "plans": [
                {
                    "id": plan_id,
                    "name": plan_data.get("data", {}).get("name", ""),
                    "view_count": plan_data.get("view_count", 0),
                    "last_viewed": plan_data.get("last_viewed")
                }
                for plan_id, plan_data in session_data.get("viewed_items", {}).get("plans", {}).items()
                if "data" in plan_data
            ][:5]
        },
        "preferences_summary": await preference_extractor.generate_preference_explanation(
            session_data.get("user_preferences", {})
        )
    }

@app.post("/api/session/{session_id}/preferences")
async def update_session_preferences(session_id: str, request: PreferenceUpdateRequest):
    """Update user preferences in session"""
    session_data = session_manager.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    # Update preferences
    success = session_manager.update_user_preferences(session_id, request.preferences)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update preferences")
    
    # Return updated preferences summary
    updated_session = session_manager.get_session(session_id)
    return {
        "success": True,
        "preferences": updated_session.get("user_preferences", {}),
        "preferences_summary": await preference_extractor.generate_preference_explanation(
            updated_session.get("user_preferences", {})
        )
    }

@app.get("/api/featured-devices")
async def get_featured_devices(session_id: Optional[str] = None):
    """Get featured devices for homepage"""
    # If session provided, use preferences for personalized recommendations
    if session_id:
        session_data = session_manager.get_session(session_id)
        if session_data and session_data.get('user_preferences'):
            # Use recommendation engine for personalized featured devices
            recommendations = recommendation_engine.generate_weighted_recommendations(
                session_data,
                devices_store,
                [],  # No plans needed for featured devices
                None  # No specific query
            )
            
            if recommendations and recommendations.get('devices'):
                # Return personalized recommendations
                return recommendations['devices'][:3]
    
    # Default behavior - return first 3 devices
    return devices_store[:3]

@app.get("/api/popular-plans")
async def get_popular_plans(session_id: Optional[str] = None):
    """Get popular plans, potentially personalized by user preferences"""
    # If session provided, use preferences for personalized recommendations
    if session_id:
        session_data = session_manager.get_session(session_id)
        if session_data and session_data.get('user_preferences'):
            # Use recommendation engine for personalized popular plans
            recommendations = recommendation_engine.generate_weighted_recommendations(
                session_data,
                [],  # No devices needed for popular plans
                plans_store,
                None  # No specific query
            )
            
            if recommendations and recommendations.get('plans'):
                # Return personalized recommendations
                return recommendations['plans'][:3]
    
    # Default behavior - return popular plans or first few if none marked as popular
    popular = [p for p in plans_store if p.get("popular", False)]
    if not popular:
        popular = plans_store[:2]
    return popular

@app.get("/")
async def root():
    return {"message": "Telekom Ecommerce API is running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify all services"""
    health_status = {
        "api": "healthy",
        "storage": "healthy",
        "openai": "unknown",
        "sessions": {
            "active_count": len(session_manager.session_store),
            "status": "healthy"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check in-memory storage
    try:
        health_status["data"] = {
            "devices_count": len(devices_store),
            "plans_count": len(plans_store)
        }
    except Exception as e:
        health_status["storage"] = f"error: {str(e)}"
    
    # Check OpenAI configuration
    if OPENAI_API_KEY:
        health_status["openai"] = "configured"
    else:
        health_status["openai"] = "not_configured"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)