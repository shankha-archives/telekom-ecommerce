from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import uuid
import asyncio
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI

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

class VoiceRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    language: str = "en"  # en or hi
    last_search_results: Optional[Dict] = None
    chat_history: Optional[List[Dict]] = None

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
async def get_device(device_id: str):
    """Get specific device"""
    device = find_by_id(devices_store, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@app.get("/api/plans")
async def get_plans():
    """Get all plans (always up-to-date from CSV)"""
    csv_path = os.path.join(os.path.dirname(__file__), 'sample_plans.csv')
    plans = load_plans_from_csv(csv_path)
    return plans

@app.get("/api/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get specific plan"""
    plan = find_by_id(plans_store, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@app.post("/api/search")
async def smart_search(request: SearchRequest):
    """Smart LLM-powered search for devices and plans"""
    try:
        if not OPENAI_API_KEY:
            # Fallback to simple text search if no API key
            query_lower = request.query.lower()
            filtered_devices = [
                d for d in devices_store 
                if query_lower in d["name"].lower() or 
                   query_lower in d["brand"].lower() or 
                   query_lower in d["description"].lower()
            ]
            
            filtered_plans = [
                p for p in plans_store 
                if query_lower in p["name"].lower() or 
                   any(query_lower in feature.lower() for feature in p["features"])
            ]
            
            return {
                "devices": filtered_devices,
                "plans": filtered_plans,
                "recommendation": f"Found {len(filtered_devices)} devices and {len(filtered_plans)} plans matching '{request.query}'"
            }
        
        # Get all devices and plans from in-memory storage
        devices = devices_store
        plans = plans_store
        
        # Create LLM chat instance
        session_id = request.session_id or str(uuid.uuid4())
        
        if not OPENAI_API_KEY:
            # Fallback search without AI
            filtered_devices = [d for d in devices if request.query.lower() in d["name"].lower() or 
                              request.query.lower() in d["brand"].lower()]
            filtered_plans = [p for p in plans if request.query.lower() in p["name"].lower()]
            
            return {
                "devices": filtered_devices[:3],
                "plans": filtered_plans[:2],
                "recommendation": f"Here are search results for '{request.query}'",
                "session_id": session_id
            }
        
        # Create system message for OpenAI
        system_message = """You are a smart assistant for Telekom ecommerce. Help users find the best devices and plans based on their needs. 

Available devices and plans:
{devices_and_plans}

When users ask about devices or plans, analyze their query and recommend the most suitable options. 
Always respond in JSON format with:
{{
    "recommended_devices": [list of device IDs that match the query],
    "recommended_plans": [list of plan IDs that match the query],
    "explanation": "Brief explanation of why these recommendations fit the user's needs",
    "follow_up_questions": [list of helpful follow-up questions]
}}

Focus on understanding user intent (budget, usage patterns, preferences) and matching them with appropriate products.""".format(
            devices_and_plans=f"DEVICES: {devices}\n\nPLANS: {plans}"
        )
        
        # Send user query to OpenAI
        client = get_openai_client()
        if not client:
            # Fallback search without AI
            filtered_devices = [d for d in devices if request.query.lower() in d["name"].lower() or 
                              request.query.lower() in d["brand"].lower()]
            filtered_plans = [p for p in plans if request.query.lower() in p["name"].lower()]
            
            return {
                "devices": filtered_devices[:3],
                "plans": filtered_plans[:2],
                "recommendation": f"Here are search results for '{request.query}'",
                "session_id": session_id
            }
            
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": request.query}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Parse LLM response (assuming it returns JSON)
        import json
        try:
            response_content = response.choices[0].message.content
            llm_result = json.loads(response_content)
            
            # Get recommended devices and plans
            recommended_devices = []
            for device_id in llm_result.get("recommended_devices", []):
                device = find_by_id(devices, device_id)
                if device:
                    recommended_devices.append(device)
            
            recommended_plans = []
            for plan_id in llm_result.get("recommended_plans", []):
                plan = find_by_id(plans, plan_id)
                if plan:
                    recommended_plans.append(plan)
            
            return {
                "devices": recommended_devices,
                "plans": recommended_plans,
                "recommendation": llm_result.get("explanation", "Here are my recommendations based on your query."),
                "follow_up_questions": llm_result.get("follow_up_questions", []),
                "session_id": session_id
            }
        except json.JSONDecodeError:
            # If LLM doesn't return valid JSON, fall back to text response
            return {
                "devices": devices[:3],  # Return first 3 devices as fallback
                "plans": plans[:2],      # Return first 2 plans as fallback
                "recommendation": response_content,
                "session_id": session_id
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.post("/api/voice-search")
async def voice_search(request: VoiceRequest):
    """Voice assistant for search and conversation with context"""
    try:
        if not OPENAI_API_KEY:
            return {
                "response": f"I heard: '{request.text}'. Voice assistant requires API key configuration.",
                "action": "none",
                "data": {}
            }
        
        # Get context data
        devices = devices_store
        plans = plans_store
        
        session_id = request.session_id or str(uuid.uuid4())
        
        # Create voice assistant LLM chat with enhanced context
        language_context = "Respond in Hindi and English mix" if request.language == "hi" else "Respond in English"
        
        # Build context string including last search results and chat history
        context_data = f"DEVICES: {devices}\n\nPLANS: {plans}"
        
        # Process chat history for better context
        conversation_context = ""
        if hasattr(request, 'chat_history') and request.chat_history:
            recent_messages = request.chat_history[-6:]  # Last 6 messages
            conversation_context = "\n\nRECENT CONVERSATION:\n"
            for msg in recent_messages:
                if msg.get('type') == 'user':
                    conversation_context += f"User: {msg.get('message', '')}\n"
                elif msg.get('type') == 'assistant':
                    conversation_context += f"Assistant: {msg.get('message', '')}\n"
        
        # Add last search results to context if available
        search_results_context = ""
        if hasattr(request, 'last_search_results') and request.last_search_results:
            search_results_context = f"\n\nLAST SEARCH RESULTS SHOWN TO USER:\n"
            if request.last_search_results.get('devices'):
                search_results_context += f"Devices shown: {[d.get('name') for d in request.last_search_results.get('devices', [])]}\n"
            if request.last_search_results.get('plans'):
                search_results_context += f"Plans shown: {[p.get('name') for p in request.last_search_results.get('plans', [])]}\n"
        
        # Create system message for voice assistant
        system_message = f"""You are a helpful voice assistant for Telekom ecommerce. {language_context}.

Available products:
{context_data}{conversation_context}{search_results_context}

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
- When users ask follow-up questions like "add to cart" after showing search results, you should know what items were previously shown
- ALWAYS look at the LAST SEARCH RESULTS SHOWN TO USER section to understand what items were recently displayed
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
    "language": "{request.language}"
}}

Be conversational, helpful, and contextually aware. When you correct speech recognition errors, briefly mention what you understood (e.g., "I understood you're looking for the S plan...")."""
        
        # Send request to OpenAI
        client = get_openai_client()
        if not client:
            return {
                "response": f"I heard: '{request.text}'. Voice assistant requires API key configuration.",
                "action": "none",
                "data": {},
                "language": request.language
            }
            
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": request.text}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        import json
        try:
            response_content = response.choices[0].message.content
            result = json.loads(response_content)
            
            # Process search results if action is search
            if result.get("action") == "search" and result.get("data"):
                # Find matching devices and plans
                recommended_devices = []
                recommended_plans = []
                
                # Simple keyword matching for now - can be enhanced with LLM
                query_lower = request.text.lower()
                
                # Search devices
                for device in devices:
                    if (any(keyword in device.get('name', '').lower() for keyword in query_lower.split()) or
                        any(keyword in device.get('brand', '').lower() for keyword in query_lower.split()) or
                        any(keyword in device.get('description', '').lower() for keyword in query_lower.split())):
                        recommended_devices.append(device)
                
                # Search plans  
                for plan in plans:
                    if (any(keyword in plan.get('name', '').lower() for keyword in query_lower.split()) or
                        any(keyword in str(plan.get('features', [])).lower() for keyword in query_lower.split())):
                        recommended_plans.append(plan)
                
                # Limit results
                recommended_devices = recommended_devices[:3]
                recommended_plans = recommended_plans[:2]
                
                result["data"]["recommended_devices"] = recommended_devices
                result["data"]["recommended_plans"] = recommended_plans
            
            return result
        except json.JSONDecodeError:
            return {
                "response": response_content,
                "action": "none", 
                "data": {},
                "language": request.language
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice search error: {str(e)}")

@app.get("/api/featured-devices")
async def get_featured_devices():
    """Get featured devices for homepage"""
    return devices_store[:3]

@app.get("/api/popular-plans") 
async def get_popular_plans():
    """Get popular plans"""
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
        "timestamp": asyncio.get_event_loop().time()
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