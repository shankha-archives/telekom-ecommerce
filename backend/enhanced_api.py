#!/usr/bin/env python
"""
Enhanced API endpoints for the context-aware chat system

This module provides new API endpoints that integrate all the 
components of the enhanced context-aware recommendation system:
- Session management
- User preference extraction
- Weighted recommendations
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from fastapi import FastAPI, HTTPException, Body, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from uuid import uuid4
import os

# Import custom modules
import session_manager
import preference_extractor
import recommendation_engine
import recommendation_analytics

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_api")

# Models for request/response data
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: str = "en"
    chat_history: Optional[List[Dict]] = None

class PreferencesRequest(BaseModel):
    preferences: Dict[str, Any]
    session_id: str

class SearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

async def setup_enhanced_routes(app: FastAPI, devices: List[Dict], plans: List[Dict]):
    """
    Configure routes for the enhanced API endpoints
    """
    # Analytical tracking events
    recommendation_id = None
    
    # Set up templates for the dashboard
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    templates = Jinja2Templates(directory=templates_dir)
    
    # Set up static files (for dashboard CSS, JS, etc.)
    try:
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(static_dir, exist_ok=True)
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")
    
    @app.get("/dashboard", response_class=HTMLResponse)
    async def get_dashboard(request: Request):
        """
        Debugging dashboard for the context-aware recommendation system
        """
        return templates.TemplateResponse("dashboard.html", {"request": request})
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    
    @app.post("/api/chat")
    async def chat(request: ChatRequest):
        """
        Enhanced chat endpoint that processes user messages and returns
        context-aware responses with recommendations
        """
        try:
            # Get or create session
            session_id, session_data = session_manager.get_or_create_session(request.session_id)
            
            # Add message to conversation history
            session_manager.add_to_conversation_history(
                session_id, 
                "user", 
                request.message
            )
            
            # Get conversation history
            conversation = session_data["conversation_history"]
            
            # Extract user preferences from conversation
            preferences = await preference_extractor.extract_user_preferences(conversation)
            
            # Update session with extracted preferences
            if preferences:
                session_manager.update_user_preferences(session_id, preferences)
                session_data = session_manager.get_session(session_id)  # Refresh session data
                
            # Generate recommendations
            recommendations = recommendation_engine.generate_weighted_recommendations(
                session_data,
                devices,
                plans,
                query=request.message
            )
            
            # Generate explanations for the recommendations
            explanations = {}
            if recommendations and (recommendations.get("devices") or recommendations.get("plans")):
                explanations = recommendation_engine.generate_explanations(
                    recommendations,
                    session_data["user_preferences"]
                )
                
            # Track recommendation for analytics
            recommendation_id = recommendation_analytics.track_recommendation(
                session_id=session_id,
                query=request.message,
                query_type="chat",
                recommendations=recommendations,
                user_preferences=session_data.get("user_preferences", {}),
                metadata={
                    "conversation_count": len(conversation),
                    "language": request.language
                }
            )
            
            # Generate follow-up questions based on context
            follow_up_questions = generate_follow_up_questions(
                request.message,
                recommendations,
                session_data["user_preferences"]
            )
            
            # Prepare preference summary if significant preferences were detected
            preference_summary = []
            user_prefs = session_data.get("user_preferences", {})
            
            if user_prefs:
                device_prefs = user_prefs.get("device_preferences", {})
                if device_prefs:
                    if device_prefs.get("brand"):
                        preference_summary.append(f"Looking for {', '.join(device_prefs['brand'])} devices")
                    
                    if device_prefs.get("price_range"):
                        p_range = device_prefs["price_range"]
                        preference_summary.append(f"Budget between €{p_range['min']}-€{p_range['max']}")
                    
                    if device_prefs.get("features"):
                        preference_summary.append(f"Important features: {', '.join(device_prefs['features'])}")
                
                plan_prefs = user_prefs.get("plan_preferences", {})
                if plan_prefs:
                    if plan_prefs.get("data_needs"):
                        data_map = {
                            "low": "Basic data usage",
                            "medium": "Moderate data usage",
                            "high": "Heavy data usage"
                        }
                        preference_summary.append(data_map.get(plan_prefs["data_needs"], 
                                               f"Data usage: {plan_prefs['data_needs']}"))
            
            # Track conversions if the user mentioned adding to cart
            if "cart" in request.message.lower() and "add" in request.message.lower():
                # Check for recently viewed items in session that might be added to cart
                recently_viewed_devices = session_data.get('viewed_items', {}).get('devices', {})
                if recently_viewed_devices:
                    # Get most recently viewed device
                    recent_device_id = next(iter(recently_viewed_devices))
                    recent_device = recently_viewed_devices[recent_device_id].get('data', {})
                    
                    if recent_device:
                        recommendation_analytics.track_conversion(
                            session_id=session_id,
                            item_id=recent_device_id,
                            item_type='device',
                            item_data=recent_device,
                            conversion_step='add_to_cart',
                            recommendation_id=recommendation_id
                        )
            
            # Prepare response
            response = "I understand what you're looking for. Here are some recommendations based on your preferences."
            
            if not recommendations.get("devices") and not recommendations.get("plans"):
                response = "I couldn't find any recommendations matching your criteria. Could you tell me more about what you're looking for?"
            
            # For speech synthesis - optimize for voice
            speech_text = response
            if recommendations:
                if recommendations.get("devices"):
                    device_count = len(recommendations["devices"])
                    if device_count == 1:
                        device = recommendations["devices"][0]
                        speech_text = f"I found the perfect device for you: the {device['name']} for {device['price']} euros."
                    elif device_count > 1:
                        speech_text = f"I found {device_count} devices that match your needs, including the {recommendations['devices'][0]['name']}."
                
                if recommendations.get("plans"):
                    plan_count = len(recommendations["plans"])
                    if plan_count == 1:
                        plan = recommendations["plans"][0]
                        speech_text += f" For a plan, I recommend the {plan['name']} at {plan['price']} euros per month."
                    elif plan_count > 1:
                        speech_text += f" I also found {plan_count} plans that might work for you."
            
            # Add assistant message to conversation history
            session_manager.add_to_conversation_history(
                session_id, 
                "assistant", 
                response
            )
            
            return {
                "session_id": session_id,
                "response": response,
                "speech_text": speech_text,
                "recommendations": recommendations,
                "explanations": explanations,
                "preference_summary": preference_summary if preference_summary else None,
                "follow_up_questions": follow_up_questions,
                "session": session_data
            }
            
        except Exception as e:
            logger.exception("Error in chat endpoint")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/session/{session_id}/preferences")
    async def update_preferences(session_id: str, request: PreferencesRequest):
        """
        Update user preferences for a specific session
        """
        try:
            success = session_manager.update_user_preferences(
                session_id, 
                request.preferences
            )
            
            if not success:
                raise HTTPException(status_code=404, detail="Session not found")
                
            session_data = session_manager.get_session(session_id)
            
            return {
                "status": "success",
                "message": "Preferences updated successfully",
                "session_data": session_data
            }
            
        except Exception as e:
            logger.exception("Error updating preferences")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/session/{session_id}")
    async def get_session(session_id: str):
        """
        Get session data
        """
        try:
            session_data = session_manager.get_session(session_id)
            
            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")
                
            return session_data
            
        except Exception as e:
            logger.exception("Error getting session")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/search")
    async def search(request: SearchRequest):
        """
        Enhanced search endpoint that leverages user context
        """
        try:
            # Get or create session
            session_id, session_data = session_manager.get_or_create_session(request.session_id)
            
            # Add search query to session
            session_manager.add_search_query(session_id, request.query)
            
            # Generate recommendations
            recommendations = recommendation_engine.generate_weighted_recommendations(
                session_data,
                devices,
                plans,
                query=request.query,
                filters=request.filters
            )
            
            # Generate explanations
            explanations = {}
            if recommendations and (recommendations.get("devices") or recommendations.get("plans")):
                explanations = recommendation_engine.generate_explanations(
                    recommendations,
                    session_data["user_preferences"]
                )
            
            # Track recommendation for analytics
            recommendation_id = recommendation_analytics.track_recommendation(
                session_id=session_id,
                query=request.query,
                query_type="search",
                recommendations=recommendations,
                user_preferences=session_data.get("user_preferences", {})
            )
            
            # Prepare response
            response = "Here are the recommendations based on your search."
            
            if not recommendations.get("devices") and not recommendations.get("plans"):
                response = "No results found for your search criteria."
            
            return {
                "session_id": session_id,
                "response": response,
                "recommendations": recommendations,
                "explanations": explanations,
                "recommendation_id": recommendation_id
            }
            
        except Exception as e:
            logger.exception("Error in search endpoint")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/analytics/recommendations")
    async def get_recommendation_analytics(days: int = 7):
        """
        Get recommendation analytics data
        """
        try:
            stats = recommendation_analytics.get_recommendation_stats(days)
            return stats
        except Exception as e:
            logger.exception("Error getting recommendation analytics")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/analytics/recent-events")
    async def get_recent_events(days: int = 1, limit: int = 50):
        """
        Get recent recommendation and conversion events
        """
        try:
            events = recommendation_analytics.get_recent_events(days, limit)
            return events
        except Exception as e:
            logger.exception("Error getting recent events")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/analytics/conversion")
    async def track_conversion_event(request: Request):
        """
        Track a conversion event (e.g., adding to cart from frontend)
        """
        try:
            data = await request.json()
            result = recommendation_analytics.track_conversion(
                session_id=data.get("session_id"),
                item_id=data.get("item_id"),
                item_type=data.get("item_type"),
                item_data=data.get("item_data", {}),
                conversion_step=data.get("conversion_step", "add_to_cart"),
                user_id=data.get("user_id"),
                recommendation_id=data.get("recommendation_id")
            )
            
            return {"success": bool(result), "event_id": result}
        except Exception as e:
            logger.exception("Error tracking conversion event")
            raise HTTPException(status_code=500, detail=str(e))

def generate_follow_up_questions(message: str, recommendations: Dict, preferences: Dict) -> List[str]:
    """
    Generate follow-up questions based on user message, recommendations and preferences
    """
    follow_ups = []
    
    # Device-related follow-ups
    if recommendations.get("devices"):
        if len(recommendations["devices"]) > 1:
            follow_ups.append("Which features are most important to you in a phone?")
            
        # Check if user has specified preferences
        device_prefs = preferences.get("device_preferences", {})
        if not device_prefs.get("brand"):
            follow_ups.append("Do you have a preferred brand?")
        if not device_prefs.get("price_range"):
            follow_ups.append("What's your budget for a new device?")
    
    # Plan-related follow-ups  
    if recommendations.get("plans"):
        if len(recommendations["plans"]) > 1:
            follow_ups.append("How much data do you typically use each month?")
            
        # Check plan preferences
        plan_prefs = preferences.get("plan_preferences", {})
        if not plan_prefs.get("data_needs"):
            follow_ups.append("Do you need a plan with a lot of data?")
        if not plan_prefs.get("international") and not "international" in message.lower():
            follow_ups.append("Do you need international calling or roaming features?")
    
    # General follow-ups if no specific preferences found
    if not recommendations.get("devices") and not recommendations.get("plans"):
        follow_ups = [
            "What kind of phone are you looking for?",
            "What's your budget for a device and plan?",
            "Do you need a lot of data in your plan?"
        ]
    
    # Limit to max 3 follow-up questions
    return follow_ups[:3]