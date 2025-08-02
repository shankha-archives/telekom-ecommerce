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
from knowledge_base import initialize_knowledge_base

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
        
        # Initialize Enhanced RAG system with tariff data
        try:
            # Initialize enhanced knowledge base with both listing.json and tariff 1.json
            kb_success = initialize_knowledge_base("listing.json", "tariff 1.json")
            if kb_success:
                print("✅ Enhanced knowledge base initialized successfully (listing + tariff data)")
            else:
                print("⚠️  Enhanced knowledge base initialization failed")
            
            # Initialize semantic search with loaded data
            rag_success = recommendation_engine.initialize_rag_system(devices_store, plans_store)
            if rag_success:
                print("✅ Enhanced RAG system initialized successfully with tariff integration")
            else:
                print("⚠️  RAG system initialization failed - falling back to basic recommendations")
        except Exception as e:
            print(f"⚠️  Enhanced RAG initialization error: {e}")
            print("⚠️  Continuing with basic recommendations")
        
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
            recommendations = recommendation_engine.generate_rag_enhanced_recommendations(
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
                recommendations = recommendation_engine.generate_rag_enhanced_recommendations(
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
        
        # Check for cart-related voice commands - expanded intent detection
        cart_keywords = [
            'add to cart', 'add this to cart', 'i want this', 'buy this', 'purchase this', 'get this',
            'i choose this', 'i choose that', 'choose this', 'choose that', 'i select this', 'select this',
            'i take this', 'take this', 'i pick this', 'pick this', 'i go with this', 'go with this',
            'i want that', 'want this', 'want that', 'take that', 'pick that', 'select that',
            'yes add', 'add it', 'get it', 'buy it', 'purchase it', 'i\'ll take it', 'i will take it',
            'sounds good', 'looks good', 'perfect', 'that works', 'that\'s good', 'that\'s perfect',
            'ok i choose', 'okay i choose', 'alright i choose', 'sure i choose', 'yes i choose'
        ]
        message_lower = request.message.lower()
        
        if any(keyword in message_lower for keyword in cart_keywords):
            # Extract item information from recent conversation context
            recent_recommendations = session_data.get('conversation_history', [])
            last_assistant_message = None
            
            # Find the last assistant message with recommendations
            for msg in reversed(recent_recommendations):
                if msg.get('type') == 'assistant' and msg.get('recommendations'):
                    last_assistant_message = msg
                    break
            
            if last_assistant_message and last_assistant_message.get('recommendations'):
                # Try to identify which item the user wants to add
                recommendations = last_assistant_message.get('recommendations', {})
                devices = recommendations.get('devices', [])
                plans = recommendations.get('plans', [])
                
                # Enhanced item selection logic
                item_to_add = None
                item_type = None
                
                # Check if user is referring to a specific item type
                if 'plan' in message_lower and plans:
                    item_to_add = plans[0]  # Take first plan if multiple
                    item_type = 'plan'
                elif 'device' in message_lower and devices:
                    item_to_add = devices[0]  # Take first device if multiple
                    item_type = 'device'
                elif 'phone' in message_lower and devices:
                    item_to_add = devices[0]
                    item_type = 'device'
                elif plans and len(plans) == 1:
                    # If only one plan was recommended, assume they mean that one
                    item_to_add = plans[0]
                    item_type = 'plan'
                elif devices and len(devices) == 1:
                    # If only one device was recommended, assume they mean that one
                    item_to_add = devices[0]
                    item_type = 'device'
                elif plans:
                    # Default to plan if available (since plans are more commonly chosen via voice)
                    item_to_add = plans[0]
                    item_type = 'plan'
                elif devices:
                    # Fall back to device
                    item_to_add = devices[0]
                    item_type = 'device'
                
                if item_to_add and item_type:
                    try:
                        # Add item to cart
                        add_request = AddToCartRequest(
                            session_id=session_id,
                            item_id=item_to_add.get('id'),
                            item_type=item_type,
                            quantity=1,
                            voice_command=request.message
                        )
                        cart_result = await add_to_cart(add_request)
                        
                        # Return cart confirmation with navigation action
                        return {
                            "response": f"Perfect! I've added the {item_to_add.get('name')} to your cart. Let me show you your cart now.",
                            "session_id": session_id,
                            "cart_action": True,
                            "navigate_to_cart": True,  # Signal frontend to navigate to cart
                            "cart_summary": cart_result['cart_summary'],
                            "cart_items": [{
                                "id": item_to_add.get('id'),
                                "name": item_to_add.get('name'),
                                "price": item_to_add.get('price'),
                                "type": item_type
                            }],
                            "voice_confirmation": cart_result['voice_confirmation'],
                            "recommendations": {"devices": [], "plans": []},
                            "explanations": {"device_explanations": {}, "plan_explanations": {}},
                            "follow_up_questions": ["Would you like to proceed to checkout?", "Continue shopping?"],
                            "preference_summary": []
                        }
                    except Exception as e:
                        print(f"Voice cart add error: {str(e)}")
                        # Continue with normal chat flow if cart add fails
        
        # Check for cart navigation commands
        cart_navigation_keywords = [
            'show my cart', 'show cart', 'view cart', 'what\'s in my cart', 'go to cart',
            'take me to cart', 'open cart', 'see my cart', 'check my cart', 'cart contents',
            'my shopping cart', 'shopping cart', 'what did i add', 'what have i added',
            'proceed to checkout', 'checkout', 'buy now', 'complete purchase'
        ]
        
        if any(keyword in message_lower for keyword in cart_navigation_keywords):
            # Get current cart state
            cart_data = await get_cart(session_id)
            
            if cart_data.get('total_items', 0) > 0:
                return {
                    "response": f"Here's your cart! You have {cart_data['total_items']} item(s) totaling €{cart_data['total_price']:.2f}. Let me show you the details.",
                    "session_id": session_id,
                    "navigate_to_cart": True,
                    "cart_summary": cart_data,
                    "voice_confirmation": f"Your cart has {cart_data['total_items']} items",
                    "recommendations": {"devices": [], "plans": []},
                    "explanations": {"device_explanations": {}, "plan_explanations": {}},
                    "follow_up_questions": ["Would you like to proceed to checkout?", "Continue shopping?", "Remove any items?"],
                    "preference_summary": []
                }
            else:
                return {
                    "response": "Your cart is currently empty. Would you like me to help you find some devices or plans?",
                    "session_id": session_id,
                    "navigate_to_cart": False,
                    "voice_confirmation": "Your cart is empty",
                    "recommendations": {"devices": [], "plans": []},
                    "explanations": {"device_explanations": {}, "plan_explanations": {}},
                    "follow_up_questions": ["Show me devices under €500", "Recommend plans under €50", "What's popular today?"],
                    "preference_summary": []
                }
        
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
                recommendations = recommendation_engine.generate_rag_enhanced_recommendations(
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
    # Try to get existing session, or create one if it doesn't exist
    session_id, session_data = session_manager.get_or_create_session(session_id)
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

# Cart Management Models
class CartItem(BaseModel):
    id: str
    type: str  # 'device', 'plan', 'bundle'
    name: str
    price: float
    original_price: Optional[float] = None
    quantity: int = 1
    bundle_components: Optional[List[Dict]] = None
    compatibility_checks: Optional[Dict] = None

class AddToCartRequest(BaseModel):
    session_id: str
    item_id: str
    item_type: str  # 'device', 'plan', 'bundle'
    quantity: int = 1
    voice_command: Optional[str] = None

class UpdateCartRequest(BaseModel):
    session_id: str
    item_id: str
    quantity: int

@app.post("/api/cart/add")
async def add_to_cart(request: AddToCartRequest):
    """Add item to cart with voice command support"""
    try:
        # Get session data
        session_id, session_data = session_manager.get_or_create_session(request.session_id)
        
        # Find the item based on type
        item = None
        if request.item_type == 'device':
            item = next((d for d in devices_store if d.get('id') == request.item_id), None)
        elif request.item_type == 'plan':
            item = next((p for p in plans_store if p.get('id') == request.item_id), None)
        elif request.item_type == 'bundle':
            # Handle bundle logic (device + plan combination)
            # For now, treat as device with plan attached
            item = next((d for d in devices_store if d.get('id') == request.item_id), None)
        
        if not item:
            raise HTTPException(status_code=404, detail=f"{request.item_type.capitalize()} not found")
        
        # Initialize cart if not exists
        if 'cart' not in session_data:
            session_data['cart'] = []
        
        # Check if item already in cart
        existing_item = next((cart_item for cart_item in session_data['cart'] 
                            if cart_item.get('id') == request.item_id and cart_item.get('type') == request.item_type), None)
        
        if existing_item:
            # Update quantity
            existing_item['quantity'] += request.quantity
        else:
            # Add new item to cart
            cart_item = {
                'id': request.item_id,
                'type': request.item_type,
                'name': item.get('name', ''),
                'price': float(item.get('price', 0)),
                'original_price': float(item.get('original_price', item.get('price', 0))),
                'quantity': request.quantity,
                'bundle_components': [],
                'compatibility_checks': {}
            }
            
            # Add bundle logic if needed
            if request.item_type == 'bundle':
                cart_item['bundle_components'] = [
                    {'type': 'device', 'name': item.get('name', ''), 'price': float(item.get('price', 0))}
                ]
            
            session_data['cart'].append(cart_item)
        
        # Update session
        session_manager.update_session(session_id, session_data)
        
        # Calculate cart totals
        cart_total = sum(item.get('price', 0) * item.get('quantity', 1) for item in session_data['cart'])
        cart_count = sum(item.get('quantity', 1) for item in session_data['cart'])
        
        # Prepare response
        response = {
            'success': True,
            'message': f"{item.get('name', 'Item')} added to cart",
            'cart_item': cart_item if not existing_item else existing_item,
            'cart_summary': {
                'total_items': cart_count,
                'total_price': cart_total,
                'items': session_data['cart']
            },
            'voice_confirmation': f"{item.get('name', 'Item')} added to your cart"
        }
        
        # Add voice command context if provided
        if request.voice_command:
            response['voice_command_processed'] = request.voice_command
        
        return response
    
    except Exception as e:
        print(f"Add to cart error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add item to cart: {str(e)}")

@app.get("/api/cart/{session_id}")
async def get_cart(session_id: str):
    """Get cart contents for session"""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return {'cart': [], 'total_items': 0, 'total_price': 0}
        
        cart = session_data.get('cart', [])
        cart_total = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart)
        cart_count = sum(item.get('quantity', 1) for item in cart)
        
        return {
            'cart': cart,
            'total_items': cart_count,
            'total_price': cart_total,
            'session_id': session_id
        }
    
    except Exception as e:
        print(f"Get cart error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cart: {str(e)}")

@app.put("/api/cart/update")
async def update_cart_item(request: UpdateCartRequest):
    """Update cart item quantity"""
    try:
        session_data = session_manager.get_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        cart = session_data.get('cart', [])
        item = next((cart_item for cart_item in cart if cart_item.get('id') == request.item_id), None)
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found in cart")
        
        if request.quantity <= 0:
            # Remove item from cart
            cart.remove(item)
            message = f"{item.get('name', 'Item')} removed from cart"
        else:
            # Update quantity
            item['quantity'] = request.quantity
            message = f"{item.get('name', 'Item')} quantity updated"
        
        # Update session
        session_manager.update_session(request.session_id, session_data)
        
        # Calculate new totals
        cart_total = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart)
        cart_count = sum(item.get('quantity', 1) for item in cart)
        
        return {
            'success': True,
            'message': message,
            'cart_summary': {
                'total_items': cart_count,
                'total_price': cart_total,
                'items': cart
            }
        }
    
    except Exception as e:
        print(f"Update cart error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update cart: {str(e)}")

@app.delete("/api/cart/{session_id}/clear")
async def clear_cart(session_id: str):
    """Clear all items from cart"""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data['cart'] = []
        session_manager.update_session(session_id, session_data)
        
        return {
            'success': True,
            'message': 'Cart cleared',
            'cart_summary': {
                'total_items': 0,
                'total_price': 0,
                'items': []
            }
        }
    
    except Exception as e:
        print(f"Clear cart error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cart: {str(e)}")

@app.post("/api/cart/compatibility-check")
async def check_compatibility(request: dict):
    """Check compatibility between devices and plans"""
    try:
        device_id = request.get('device_id')
        plan_id = request.get('plan_id')
        
        device = next((d for d in devices_store if d.get('id') == device_id), None)
        plan = next((p for p in plans_store if p.get('id') == plan_id), None)
        
        if not device or not plan:
            raise HTTPException(status_code=404, detail="Device or plan not found")
        
        # Basic compatibility checks
        compatibility = {
            'compatible': True,
            'warnings': [],
            'recommendations': []
        }
        
        # Check network compatibility
        device_features = device.get('features', '').split(';')
        plan_features = plan.get('features', '').split(';')
        
        has_5g_device = any('5G' in feature for feature in device_features)
        has_5g_plan = any('5G' in feature for feature in plan_features)
        
        if has_5g_plan and not has_5g_device:
            compatibility['warnings'].append("This plan includes 5G, but your device doesn't support 5G")
        
        if not has_5g_plan and has_5g_device:
            compatibility['recommendations'].append("Consider upgrading to a 5G plan to use your device's full potential")
        
        # Check eSIM compatibility
        has_esim_device = any('eSIM' in feature for feature in device_features)
        if has_esim_device:
            compatibility['recommendations'].append("This device supports eSIM for easy activation")
        
        return compatibility
    
    except Exception as e:
        print(f"Compatibility check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Compatibility check failed: {str(e)}")

@app.get("/api/featured-devices")
async def get_featured_devices(session_id: Optional[str] = None):
    """Get featured devices for homepage"""
    # If session provided, use preferences for personalized recommendations
    if session_id:
        session_data = session_manager.get_session(session_id)
        if session_data and session_data.get('user_preferences'):
            # Use recommendation engine for personalized featured devices
            recommendations = recommendation_engine.generate_rag_enhanced_recommendations(
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
            recommendations = recommendation_engine.generate_rag_enhanced_recommendations(
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