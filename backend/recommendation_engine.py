import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import re
import math
from datetime import datetime, timedelta
from semantic_search import semantic_search_products, initialize_semantic_search
from knowledge_base import knowledge_base

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Initialize OpenAI client
openai_client = None

def get_openai_client():
    """Get or initialize the OpenAI client"""
    global openai_client
    if OPENAI_API_KEY and openai_client is None:
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return openai_client

def initialize_rag_system(all_devices, all_plans):
    """
    Initialize the enhanced RAG system with product data and tariff data for semantic search
    
    Args:
        all_devices: List of all devices
        all_plans: List of all plans
    """
    try:
        # Get tariff data from knowledge base
        tariff_data = knowledge_base.tariff_data if knowledge_base.initialized else None
        
        success = initialize_semantic_search(all_devices, all_plans, tariff_data)
        if success:
            print("DEBUG: Enhanced RAG system initialized successfully with tariff data")
        else:
            print("DEBUG: RAG system initialization failed or not available")
        return success
    except Exception as e:
        print(f"DEBUG: Error initializing enhanced RAG system: {str(e)}")
        return False

def generate_weighted_recommendations(session_data, all_devices, all_plans, query=None):
    """
    Generate recommendations based on session context and weighted scores.
    Returns the top recommended devices and plans with explanations.
    """
    print(f"DEBUG: Starting recommendation generation")
    print(f"DEBUG: Session data keys: {session_data.keys() if session_data else 'None'}")
    print(f"DEBUG: Devices count: {len(all_devices) if all_devices else 0}")
    print(f"DEBUG: Plans count: {len(all_plans) if all_plans else 0}")
    print(f"DEBUG: Query: {query}")
    
    # Get user preferences from session
    preferences = session_data.get('user_preferences', {})
    viewed_items = session_data.get('viewed_items', {'devices': {}, 'plans': {}})
    search_queries = session_data.get('search_queries', [])
    
    # Set default weights for scoring factors
    weights = {
        'explicit_query': 0.4,      # Current search query match
        'preferences_match': 0.3,   # Match with user preferences
        'viewing_history': 0.15,    # Previously viewed items
        'recency': 0.05,            # Recently viewed items get a boost
        'popularity': 0.1           # General popularity of the item
    }
    
    # Score all devices
    device_scores = {}
    device_explanations = {}
    
    for device in all_devices:
        device_id = device['id']
        score = 0
        explanations = []
        
        # Base popularity score (based on rating)
        rating = device.get('rating', 3.0)
        if rating is None:
            rating = 3.0
        elif isinstance(rating, str):
            try:
                rating = float(rating)
            except:
                rating = 3.0
                
        popularity_score = weights['popularity'] * (rating / 5)
        score += popularity_score
        
        if rating >= 4.0:
            explanations.append(f"Highly rated device ({rating}/5)")
        
        # Viewing history score
        if device_id in viewed_items.get('devices', {}):
            view_data = viewed_items['devices'][device_id]
            view_count = view_data.get('view_count', 0)
            
            # Basic view count score - caps at 5 views
            view_score = weights['viewing_history'] * min(view_count / 5, 1.0)
            score += view_score
            
            if view_count > 1:
                explanations.append(f"You've viewed this {view_count} times")
            
            # Recency boost - viewed in last hour
            if 'last_viewed' in view_data:
                try:
                    last_viewed = datetime.fromisoformat(view_data['last_viewed'])
                    now = datetime.utcnow()
                    if now - last_viewed < timedelta(hours=1):
                        recency_score = weights['recency']
                        score += recency_score
                        explanations.append("Recently viewed")
                except:
                    pass
        
        # Preferences match score
        device_prefs = preferences.get('device_preferences', {})
        pref_score = 0
        pref_matches = []
        
        # Brand preference match
        if 'brand' in device_prefs and device_prefs['brand']:
            brand = device.get('brand', '')
            if any(b.lower() == brand.lower() for b in device_prefs['brand']):
                brand_score = 0.3
                pref_score += brand_score
                pref_matches.append(f"Preferred brand: {brand}")
        
        # Price range match
        if 'price_range' in device_prefs:
            price = device.get('price', 0)
            if isinstance(price, str):
                try:
                    price = float(price)
                except:
                    price = 0
                    
            min_price = device_prefs['price_range'].get('min', 0)
            max_price = device_prefs['price_range'].get('max', float('inf'))
            
            if min_price <= price <= max_price:
                price_score = 0.25
                pref_score += price_score
                pref_matches.append(f"Within your budget (€{min_price}-€{max_price})")
        
        # Storage preference match
        if 'storage' in device_prefs and device_prefs['storage']:
            device_storage = device.get('storage', '')
            if any(storage.lower() in device_storage.lower() for storage in device_prefs['storage']):
                storage_score = 0.15
                pref_score += storage_score
                pref_matches.append(f"Preferred storage: {device_storage}")
        
        # Color preference match
        if 'color' in device_prefs and device_prefs['color']:
            device_color = device.get('color', '')
            if any(color.lower() in device_color.lower() for color in device_prefs['color']):
                color_score = 0.1
                pref_score += color_score
                pref_matches.append(f"Preferred color: {device_color}")
        
        # Features preference match
        if 'features' in device_prefs and device_prefs['features']:
            device_features = device.get('features', [])
            if isinstance(device_features, str):
                # Convert string to list if needed
                device_features = device_features.split(';')
                
            # Check for matches with preferred features
            matched_features = []
            for feature in device_prefs['features']:
                for device_feature in device_features:
                    if feature.lower() in device_feature.lower():
                        matched_features.append(feature)
                        break
            
            if matched_features:
                feature_score = 0.2 * (len(matched_features) / len(device_prefs['features']))
                pref_score += feature_score
                pref_matches.append(f"Has {len(matched_features)} of your preferred features")
        
        # Add weighted preference score to total score
        score += weights['preferences_match'] * pref_score
        if pref_matches:
            explanations.extend(pref_matches)
        
        # Query match score
        if query:
            query_lower = query.lower()
            query_score = 0
            query_matches = []
            
            # Name match (highest weight)
            device_name = device.get('name', '')
            if query_lower in device_name.lower():
                name_score = 0.6
                query_score += name_score
                query_matches.append(f"Matches your search for '{query}'")
            
            # Brand match (medium weight)
            device_brand = device.get('brand', '')
            if query_lower in device_brand.lower():
                brand_score = 0.3
                query_score += brand_score
                query_matches.append(f"Matches {device_brand} brand")
            
            # Description match (lower weight)
            device_desc = device.get('description', '')
            if query_lower in device_desc.lower():
                desc_score = 0.1
                query_score += desc_score
            
            # Add weighted query score to total score
            score += weights['explicit_query'] * query_score
            if query_matches:
                explanations.extend(query_matches)
        
        # Store the final score and explanations
        device_scores[device_id] = score
        device_explanations[device_id] = explanations
    
    # Score all plans
    plan_scores = {}
    plan_explanations = {}
    
    for plan in all_plans:
        plan_id = plan['id']
        score = 0
        explanations = []
        
        # Base popularity score
        if plan.get('popular', False):
            popularity_score = weights['popularity'] * 1.0
            score += popularity_score
            explanations.append("Popular plan")
        
        # Viewing history score
        if plan_id in viewed_items.get('plans', {}):
            view_data = viewed_items['plans'][plan_id]
            view_count = view_data.get('view_count', 0)
            
            # Basic view count score - caps at 5 views
            view_score = weights['viewing_history'] * min(view_count / 5, 1.0)
            score += view_score
            
            if view_count > 1:
                explanations.append(f"You've viewed this {view_count} times")
            
            # Recency boost - viewed in last hour
            if 'last_viewed' in view_data:
                try:
                    last_viewed = datetime.fromisoformat(view_data['last_viewed'])
                    now = datetime.utcnow()
                    if now - last_viewed < timedelta(hours=1):
                        recency_score = weights['recency']
                        score += recency_score
                        explanations.append("Recently viewed")
                except:
                    pass
        
        # Preferences match score
        plan_prefs = preferences.get('plan_preferences', {})
        pref_score = 0
        pref_matches = []
        
        # Data needs match
        if 'data_needs' in plan_prefs:
            data_need = plan_prefs['data_needs']
            plan_data = plan.get('data', '').lower()
            
            # Check for unlimited data
            if 'unlimited' in plan_data and data_need == 'high':
                data_score = 0.4
                pref_score += data_score
                pref_matches.append("Unlimited data matches your high data needs")
            elif data_need == 'medium' and ('10gb' in plan_data or '15gb' in plan_data or '20gb' in plan_data):
                data_score = 0.3
                pref_score += data_score
                pref_matches.append("Data allowance matches your medium data needs")
            elif data_need == 'low' and any(limit in plan_data for limit in ['2gb', '3gb', '5gb', '6gb']):
                data_score = 0.3
                pref_score += data_score
                pref_matches.append("Data allowance matches your low data needs")
        
        # Price sensitivity match
        if 'price_sensitivity' in plan_prefs:
            price_sensitivity = plan_prefs['price_sensitivity']
            plan_price = plan.get('price', 0)
            if plan_price is None:
                plan_price = 0
            elif isinstance(plan_price, str):
                try:
                    plan_price = float(plan_price)
                except:
                    plan_price = 0
            
            # Match price sensitivity to plan price ranges
            if price_sensitivity == 'high' and plan_price <= 30:
                price_score = 0.3
                pref_score += price_score
                pref_matches.append("Budget-friendly plan")
            elif price_sensitivity == 'medium' and 30 <= plan_price <= 50:
                price_score = 0.3
                pref_score += price_score
                pref_matches.append("Mid-range price plan")
            elif price_sensitivity == 'low' and plan_price >= 50:
                price_score = 0.3
                pref_score += price_score
                pref_matches.append("Premium plan")
        
        # International usage match
        if 'international' in plan_prefs and plan_prefs['international']:
            plan_features = plan.get('features', [])
            if isinstance(plan_features, str):
                plan_features = plan_features.split(';')
                
            if any('roaming' in feature.lower() or 'international' in feature.lower() for feature in plan_features):
                international_score = 0.2
                pref_score += international_score
                pref_matches.append("Includes international features")
        
        # Contract length preference
        if 'contract_length' in plan_prefs:
            preferred_length = plan_prefs['contract_length']
            plan_duration = plan.get('duration', '').lower()
            
            if (preferred_length == 'monthly' and 'month' in plan_duration) or \
               (preferred_length == '1-year' and '1' in plan_duration and 'year' in plan_duration) or \
               (preferred_length == '2-year' and '2' in plan_duration and 'year' in plan_duration):
                contract_score = 0.2
                pref_score += contract_score
                pref_matches.append(f"Matches preferred {preferred_length} contract")
        
        # Add weighted preference score to total score
        score += weights['preferences_match'] * pref_score
        if pref_matches:
            explanations.extend(pref_matches)
        
        # Query match score
        if query:
            query_lower = query.lower()
            query_score = 0
            query_matches = []
            
            # Name match (highest weight)
            plan_name = plan.get('name', '')
            if query_lower in plan_name.lower():
                name_score = 0.6
                query_score += name_score
                query_matches.append(f"Matches your search for '{query}'")
            
            # Data match (look for GB amounts in the query)
            plan_data = plan.get('data', '').lower()
            data_pattern = r'(\d+)\s*(gb|g|gig)'
            data_matches = re.findall(data_pattern, query_lower)
            
            if data_matches:
                for amount, _ in data_matches:
                    if amount in plan_data or (amount + 'gb') in plan_data:
                        data_score = 0.4
                        query_score += data_score
                        query_matches.append(f"Has {amount}GB data")
            
            # Features match
            plan_features = plan.get('features', [])
            if isinstance(plan_features, str):
                plan_features = plan_features.split(';')
                
            feature_words = ['unlimited', 'roaming', '5g', 'streaming', 'family', 'business']
            for word in feature_words:
                if word in query_lower:
                    for feature in plan_features:
                        if word in feature.lower():
                            feature_score = 0.3
                            query_score += feature_score
                            query_matches.append(f"Includes {word}")
                            break
            
            # Add weighted query score to total score
            score += weights['explicit_query'] * query_score
            if query_matches:
                explanations.extend(query_matches)
        
        # Store the final score and explanations
        plan_scores[plan_id] = score
        plan_explanations[plan_id] = explanations
    
    # Sort by scores and return top recommendations
    top_device_ids = sorted(device_scores.items(), key=lambda x: x[1], reverse=True)[:5]
    top_plan_ids = sorted(plan_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Map IDs to full objects
    recommended_devices = []
    for device_id, score in top_device_ids:
        device = next((d for d in all_devices if d['id'] == device_id), None)
        if device:
            recommended_devices.append(device)
    
    recommended_plans = []
    for plan_id, score in top_plan_ids:
        plan = next((p for p in all_plans if p['id'] == plan_id), None)
        if plan:
            recommended_plans.append(plan)
    
    # Return recommendations with explanations
    device_explanation_dict = {}
    for d_id, _ in top_device_ids:
        if d_id in device_explanations:
            device_explanation_dict[d_id] = device_explanations[d_id]
    
    plan_explanation_dict = {}
    for p_id, _ in top_plan_ids:
        if p_id in plan_explanations:
            plan_explanation_dict[p_id] = plan_explanations[p_id]
            
    return {
        'devices': recommended_devices,
        'plans': recommended_plans,
        'device_explanations': device_explanation_dict,
        'plan_explanations': plan_explanation_dict
    }

def generate_rag_enhanced_recommendations(session_data, all_devices, all_plans, query=None):
    """
    Generate recommendations with RAG enhancement for better semantic understanding.
    Falls back to original recommendations if RAG is not available.
    
    Args:
        session_data: User session data
        all_devices: List of all devices
        all_plans: List of all plans
        query: Search query string
        
    Returns:
        Enhanced recommendations with semantic matching
    """
    print(f"DEBUG: Starting RAG-enhanced recommendation generation")
    print(f"DEBUG: Query: {query}")
    
    # Get base recommendations using existing weighted scoring
    base_recommendations = generate_weighted_recommendations(session_data, all_devices, all_plans, query)
    
    # If no query or query is too short, return base recommendations
    if not query or len(query.strip()) < 10:
        print("DEBUG: Query too short for semantic search, using base recommendations")
        return base_recommendations
    
    try:
        # Perform semantic search for complex queries
        semantic_results = semantic_search_products(query, "both")
        
        if not semantic_results or (not semantic_results.get("devices") and not semantic_results.get("plans")):
            print("DEBUG: No semantic results found, using base recommendations")
            return base_recommendations
        
        print(f"DEBUG: Found {len(semantic_results.get('devices', []))} semantic device matches")
        print(f"DEBUG: Found {len(semantic_results.get('plans', []))} semantic plan matches")
        
        # Apply semantic boost to existing device scores
        enhanced_device_scores = {}
        device_explanations = base_recommendations.get('device_explanations', {})
        
        for device in all_devices:
            device_id = device['id']
            base_score = 0
            
            # Find base score from existing recommendations
            for base_device in base_recommendations.get('devices', []):
                if base_device.get('id') == device_id:
                    base_score = 0.5  # Give base recommendations initial boost
                    break
            
            # Apply semantic similarity boost
            semantic_score = 0
            for sem_device_id, sim_score in semantic_results.get("devices", []):
                if sem_device_id == device_id:
                    semantic_score = sim_score * 0.3  # 30% weight for semantic similarity
                    break
            
            # Combine scores
            final_score = base_score + semantic_score
            if final_score > 0:
                enhanced_device_scores[device_id] = final_score
                
                # Add semantic explanation
                if device_id not in device_explanations:
                    device_explanations[device_id] = []
                if semantic_score > 0.2:  # Only add if significant semantic match
                    device_explanations[device_id].append(f"Semantically matches your search query")
        
        # Apply semantic boost to existing plan scores
        enhanced_plan_scores = {}
        plan_explanations = base_recommendations.get('plan_explanations', {})
        
        for plan in all_plans:
            plan_id = plan['id']
            base_score = 0
            
            # Find base score from existing recommendations
            for base_plan in base_recommendations.get('plans', []):
                if base_plan.get('id') == plan_id:
                    base_score = 0.5  # Give base recommendations initial boost
                    break
            
            # Apply semantic similarity boost
            semantic_score = 0
            for sem_plan_id, sim_score in semantic_results.get("plans", []):
                if sem_plan_id == plan_id:
                    semantic_score = sim_score * 0.3  # 30% weight for semantic similarity
                    break
            
            # Combine scores
            final_score = base_score + semantic_score
            if final_score > 0:
                enhanced_plan_scores[plan_id] = final_score
                
                # Add semantic explanation
                if plan_id not in plan_explanations:
                    plan_explanations[plan_id] = []
                if semantic_score > 0.2:  # Only add if significant semantic match
                    plan_explanations[plan_id].append(f"Semantically matches your search query")
        
        # Sort by enhanced scores and return top recommendations
        top_device_ids = sorted(enhanced_device_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        top_plan_ids = sorted(enhanced_plan_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Map IDs to full objects
        enhanced_devices = []
        for device_id, score in top_device_ids:
            device = next((d for d in all_devices if d['id'] == device_id), None)
            if device:
                enhanced_devices.append(device)
        
        enhanced_plans = []
        for plan_id, score in top_plan_ids:
            plan = next((p for p in all_plans if p['id'] == plan_id), None)
            if plan:
                enhanced_plans.append(plan)
        
        # If we have enhanced results, return them
        if enhanced_devices or enhanced_plans:
            print(f"DEBUG: Returning {len(enhanced_devices)} enhanced devices and {len(enhanced_plans)} enhanced plans")
            return {
                'devices': enhanced_devices if enhanced_devices else base_recommendations.get('devices', []),
                'plans': enhanced_plans if enhanced_plans else base_recommendations.get('plans', []),
                'device_explanations': device_explanations,
                'plan_explanations': plan_explanations
            }
        
    except Exception as e:
        print(f"DEBUG: Error in RAG enhancement: {str(e)}")
    
    # Fallback to base recommendations
    print("DEBUG: Falling back to base recommendations")
    return base_recommendations

async def generate_recommendation_summary(recommendations, preferences, query=None):
    """
    Generate a natural language summary of the recommendations.
    This enhances the user experience by explaining why items were recommended.
    """
    print(f"DEBUG: Generating recommendation summary")
    print(f"DEBUG: Recommendations: {recommendations.keys() if recommendations else 'None'}")
    print(f"DEBUG: Preferences: {preferences.keys() if preferences else 'None'}")
    
    client = get_openai_client()
    if not client:
        print("DEBUG: OpenAI client not available")
        return "Here are some recommendations based on your preferences."
    
    # Safely get data from recommendations
    devices = recommendations.get('devices', [])
    plans = recommendations.get('plans', [])
    device_explanations = recommendations.get('device_explanations', {})
    plan_explanations = recommendations.get('plan_explanations', {})
    
    # If we have no recommendations, return a simple message
    if not devices and not plans:
        print("DEBUG: No recommendations available")
        return "I couldn't find any specific recommendations based on your query."
    
    # Create a detailed context for the LLM
    context = {
        'query': query,
        'preferences': preferences,
        'device_recommendations': [{
            'name': d.get('name', ''),
            'brand': d.get('brand', ''),
            'price': d.get('price', ''),
            'explanations': device_explanations.get(d.get('id', ''), [])
        } for d in devices],
        'plan_recommendations': [{
            'name': p.get('name', ''),
            'price': p.get('price', ''),
            'data': p.get('data', ''),
            'explanations': plan_explanations.get(p.get('id', ''), [])
        } for p in plans]
    }
    
    # System prompt for summary generation
    system_prompt = f"""
    Create a friendly, conversational summary explaining these product recommendations to the user.
    
    USER QUERY: {query if query else "No specific query"}
    
    USER PREFERENCES:
    {json.dumps(preferences, indent=2)}
    
    RECOMMENDATIONS:
    Device recommendations: {json.dumps(context['device_recommendations'], indent=2)}
    Plan recommendations: {json.dumps(context['plan_recommendations'], indent=2)}
    
    Guidelines:
    1. Be concise but conversational (max 2-3 sentences)
    2. Explain why these items match their needs/preferences
    3. Mention 1-2 specific devices or plans by name if available
    4. If the user had a specific query, acknowledge it
    5. DO NOT list all recommendations - just summarize the overall selection
    
    Example good responses:
    "Based on your preference for Apple devices with good cameras, I've found several iPhone options within your €600-900 budget. The iPhone 15 looks perfect for your photography needs."
    "Since you need a plan with plenty of data for streaming, I've selected plans with at least 20GB. The MagentaMobil M plan offers a great balance of data and price."
    """
    
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"Error generating recommendation summary: {str(e)}")
        if devices and plans:
            return "Here are some devices and plans that match your preferences."
        elif devices:
            return "Here are some devices that match your preferences."
        elif plans:
            return "Here are some plans that match your preferences."
        else:
            return "Here are some recommendations for you."