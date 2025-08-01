#!/usr/bin/env python
"""
Analytics tracking for the recommendation engine

This module provides functionality to track and analyze recommendation quality,
user interactions, and recommendation conversions.
"""

import os
import json
import time
import uuid
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Any, Optional, Union
import csv
from collections import defaultdict, Counter
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("recommendation_analytics")

# Constants
ANALYTICS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "analytics")
RECOMMENDATION_LOG = os.path.join(ANALYTICS_DIR, "recommendation_log.csv")
CONVERSION_LOG = os.path.join(ANALYTICS_DIR, "conversion_log.csv")
ANALYTICS_LOCK = threading.Lock()

# Ensure analytics directory exists
os.makedirs(ANALYTICS_DIR, exist_ok=True)

# Initialize CSV files with headers if they don't exist
def init_analytics_files():
    """Initialize analytics files with headers if they don't exist"""
    
    # Recommendation log
    if not os.path.exists(RECOMMENDATION_LOG):
        with open(RECOMMENDATION_LOG, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'event_id', 'session_id', 'user_id',
                'query_type', 'query', 'device_count', 'plan_count',
                'preference_match_score', 'top_device_id', 'top_plan_id'
            ])
    
    # Conversion log
    if not os.path.exists(CONVERSION_LOG):
        with open(CONVERSION_LOG, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'event_id', 'session_id', 'user_id',
                'item_id', 'item_type', 'item_name', 'price',
                'recommendation_id', 'time_to_conversion', 
                'preference_count', 'conversion_step'
            ])

# Initialize files
init_analytics_files()

class RecommendationEvent:
    """Represents a single recommendation event for tracking"""
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.session_id = session_id
        self.user_id = user_id
        self.query_type = None  # 'search', 'chat', 'browse'
        self.query = None
        self.recommendations = {
            'devices': [],
            'plans': []
        }
        self.preferences = {}
        self.preference_match_scores = {
            'devices': {},  # device_id -> score
            'plans': {}     # plan_id -> score
        }
        self.metadata = {}
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'user_id': self.user_id,
            'query_type': self.query_type,
            'query': self.query,
            'recommendations': self.recommendations,
            'preferences': self.preferences,
            'preference_match_scores': self.preference_match_scores,
            'metadata': self.metadata
        }
    
    def log(self):
        """Log the recommendation event to analytics"""
        with ANALYTICS_LOCK:
            with open(RECOMMENDATION_LOG, 'a', newline='') as f:
                writer = csv.writer(f)
                
                # Calculate summary metrics
                device_count = len(self.recommendations.get('devices', []))
                plan_count = len(self.recommendations.get('plans', []))
                
                # Calculate average preference match score
                device_scores = list(self.preference_match_scores.get('devices', {}).values())
                plan_scores = list(self.preference_match_scores.get('plans', {}).values())
                
                all_scores = device_scores + plan_scores
                avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
                
                # Get top recommendation IDs
                top_device_id = self.recommendations.get('devices', [{}])[0].get('id', '') if device_count > 0 else ''
                top_plan_id = self.recommendations.get('plans', [{}])[0].get('id', '') if plan_count > 0 else ''
                
                writer.writerow([
                    self.timestamp.isoformat(),
                    self.event_id,
                    self.session_id,
                    self.user_id or '',
                    self.query_type or '',
                    self.query or '',
                    device_count,
                    plan_count,
                    f"{avg_score:.2f}",
                    top_device_id,
                    top_plan_id
                ])

class ConversionEvent:
    """Represents a conversion event (adding to cart, purchase, etc.)"""
    
    def __init__(self, session_id: str, item_id: str, item_type: str, 
                 recommendation_id: Optional[str] = None,
                 user_id: Optional[str] = None):
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.session_id = session_id
        self.user_id = user_id
        self.item_id = item_id
        self.item_type = item_type  # 'device' or 'plan'
        self.item_name = None
        self.price = None
        self.recommendation_id = recommendation_id  # ID of recommendation event that led to this
        self.time_to_conversion = None  # seconds from recommendation to conversion
        self.preference_count = 0  # number of user preferences at time of conversion
        self.conversion_step = None  # 'add_to_cart', 'purchase', 'wishlist', etc.
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'item_type': self.item_type,
            'item_name': self.item_name,
            'price': self.price,
            'recommendation_id': self.recommendation_id,
            'time_to_conversion': self.time_to_conversion,
            'preference_count': self.preference_count,
            'conversion_step': self.conversion_step
        }
    
    def log(self):
        """Log the conversion event to analytics"""
        with ANALYTICS_LOCK:
            with open(CONVERSION_LOG, 'a', newline='') as f:
                writer = csv.writer(f)
                
                writer.writerow([
                    self.timestamp.isoformat(),
                    self.event_id,
                    self.session_id,
                    self.user_id or '',
                    self.item_id,
                    self.item_type,
                    self.item_name or '',
                    self.price or '',
                    self.recommendation_id or '',
                    f"{self.time_to_conversion:.1f}" if self.time_to_conversion else '',
                    self.preference_count,
                    self.conversion_step or ''
                ])

# Global dictionary to store recent recommendations for tracking conversions
# Structure: {session_id -> {recommendation_id -> RecommendationEvent}}
recent_recommendations = {}

def track_recommendation(
    session_id: str, 
    query: str,
    query_type: str,
    recommendations: Dict[str, List[Dict]],
    user_preferences: Dict,
    user_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str:
    """
    Track a recommendation event
    
    Args:
        session_id: The session ID
        query: The search query or chat message
        query_type: Type of query ('search', 'chat', 'browse')
        recommendations: Dict with 'devices' and 'plans' lists
        user_preferences: User preferences from session
        user_id: Optional user ID
        metadata: Additional metadata
    
    Returns:
        The recommendation event ID
    """
    try:
        # Create recommendation event
        event = RecommendationEvent(session_id, user_id)
        event.query = query
        event.query_type = query_type
        event.recommendations = recommendations
        event.preferences = user_preferences
        event.metadata = metadata or {}
        
        # Calculate preference match scores
        if user_preferences:
            # For devices
            device_prefs = user_preferences.get('device_preferences', {})
            for i, device in enumerate(recommendations.get('devices', [])):
                score = calculate_preference_match(device, device_prefs)
                event.preference_match_scores['devices'][device.get('id')] = score
            
            # For plans
            plan_prefs = user_preferences.get('plan_preferences', {})
            for i, plan in enumerate(recommendations.get('plans', [])):
                score = calculate_preference_match(plan, plan_prefs)
                event.preference_match_scores['plans'][plan.get('id')] = score
        
        # Store in recent recommendations
        if session_id not in recent_recommendations:
            recent_recommendations[session_id] = {}
        
        recent_recommendations[session_id][event.event_id] = event
        
        # Clean old recommendations (keep only last 24 hours)
        clean_old_recommendations()
        
        # Log the event
        event.log()
        
        logger.info(f"Tracked recommendation event: {event.event_id} for session {session_id}")
        return event.event_id
    
    except Exception as e:
        logger.error(f"Error tracking recommendation: {str(e)}")
        return ""

def track_conversion(
    session_id: str,
    item_id: str,
    item_type: str,
    item_data: Dict,
    conversion_step: str = 'add_to_cart',
    user_id: Optional[str] = None,
    recommendation_id: Optional[str] = None
) -> str:
    """
    Track a conversion event
    
    Args:
        session_id: The session ID
        item_id: ID of the item converted
        item_type: Type of item ('device' or 'plan')
        item_data: Full item data
        conversion_step: Type of conversion ('add_to_cart', 'purchase', etc.)
        user_id: Optional user ID
        recommendation_id: ID of recommendation that led to this conversion
    
    Returns:
        The conversion event ID
    """
    try:
        # Create conversion event
        event = ConversionEvent(session_id, item_id, item_type, recommendation_id, user_id)
        event.item_name = item_data.get('name', '')
        event.price = item_data.get('price', 0)
        event.conversion_step = conversion_step
        
        # Get preference count from session
        try:
            from session_manager import get_session
            session_data = get_session(session_id)
            if session_data and 'user_preferences' in session_data:
                device_pref_count = len(session_data['user_preferences'].get('device_preferences', {}))
                plan_pref_count = len(session_data['user_preferences'].get('plan_preferences', {}))
                event.preference_count = device_pref_count + plan_pref_count
        except ImportError:
            pass
        
        # Calculate time to conversion if we have the recommendation event
        if recommendation_id and session_id in recent_recommendations and recommendation_id in recent_recommendations[session_id]:
            rec_event = recent_recommendations[session_id][recommendation_id]
            time_diff = event.timestamp - rec_event.timestamp
            event.time_to_conversion = time_diff.total_seconds()
        
        # Log the event
        event.log()
        
        logger.info(f"Tracked conversion event: {event.event_id} for session {session_id}")
        return event.event_id
    
    except Exception as e:
        logger.error(f"Error tracking conversion: {str(e)}")
        return ""

def calculate_preference_match(item: Dict, preferences: Dict) -> float:
    """
    Calculate how well an item matches user preferences
    
    Returns a score from 0 to 1
    """
    if not preferences:
        return 0.0
    
    matches = 0
    total_prefs = 0
    
    # Check for brand match (for devices)
    if 'brand' in preferences and 'brand' in item:
        total_prefs += 1
        if item['brand'] in preferences['brand']:
            matches += 1
    
    # Check for price range match
    if 'price_range' in preferences and 'price' in item:
        total_prefs += 1
        price = item.get('price', 0)
        price_range = preferences['price_range']
        min_price = price_range.get('min', 0)
        max_price = price_range.get('max', float('inf'))
        
        if min_price <= price <= max_price:
            matches += 1
    
    # Check for storage match (for devices)
    if 'storage' in preferences and 'storage' in item:
        total_prefs += 1
        if any(s in item['storage'] for s in preferences['storage']):
            matches += 1
    
    # Check for color match (for devices)
    if 'color' in preferences and 'color' in item:
        total_prefs += 1
        if any(c.lower() in item['color'].lower() for c in preferences['color']):
            matches += 1
    
    # Check for features match (for devices)
    if 'features' in preferences and 'features' in item:
        total_prefs += 1
        if any(feature in item.get('features', []) for feature in preferences['features']):
            matches += 1
    
    # For plans, check data needs
    if 'data_needs' in preferences and 'data' in item:
        total_prefs += 1
        data_needs = preferences['data_needs']
        plan_data = item['data'].lower()
        
        if data_needs == 'low' and any(x in plan_data for x in ['2gb', '3gb', '5gb', 'basic']):
            matches += 1
        elif data_needs == 'medium' and any(x in plan_data for x in ['10gb', '15gb', '20gb']):
            matches += 1
        elif data_needs == 'high' and any(x in plan_data for x in ['unlimited', 'infinity', '50gb', '100gb']):
            matches += 1
    
    # Calculate final score
    if total_prefs == 0:
        return 0.0
    
    return matches / total_prefs

def clean_old_recommendations():
    """Clean recommendations older than 24 hours"""
    now = datetime.now()
    cutoff = now - timedelta(hours=24)
    
    sessions_to_remove = []
    for session_id, recommendations in recent_recommendations.items():
        recs_to_remove = []
        for rec_id, event in recommendations.items():
            if event.timestamp < cutoff:
                recs_to_remove.append(rec_id)
        
        # Remove old recommendations
        for rec_id in recs_to_remove:
            del recommendations[rec_id]
        
        # Mark empty sessions for removal
        if not recommendations:
            sessions_to_remove.append(session_id)
    
    # Remove empty sessions
    for session_id in sessions_to_remove:
        del recent_recommendations[session_id]

def get_recommendation_stats(days: int = 7) -> Dict:
    """Get recommendation statistics for the last N days"""
    stats = {
        'total_recommendations': 0,
        'total_conversions': 0,
        'conversion_rate': 0,
        'avg_preference_match': 0,
        'avg_time_to_conversion': 0,
        'recommendations_by_day': {},
        'conversions_by_day': {},
        'top_device_conversions': [],
        'top_plan_conversions': [],
        'avg_preferences_count': 0
    }
    
    try:
        # Calculate cutoff date
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        # Process recommendation log
        recommendation_counts = defaultdict(int)
        preference_scores = []
        rec_dates = defaultdict(int)
        
        with open(RECOMMENDATION_LOG, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = row['timestamp']
                if timestamp < cutoff_str:
                    continue
                
                stats['total_recommendations'] += 1
                recommendation_counts[row['session_id']] += 1
                
                try:
                    score = float(row['preference_match_score'])
                    preference_scores.append(score)
                except (ValueError, TypeError):
                    pass
                
                # Track by day
                date = timestamp.split('T')[0]
                rec_dates[date] = rec_dates.get(date, 0) + 1
        
        # Process conversion log
        conversion_counts = defaultdict(int)
        conversion_times = []
        preference_counts = []
        device_conversions = Counter()
        plan_conversions = Counter()
        conv_dates = defaultdict(int)
        
        with open(CONVERSION_LOG, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = row['timestamp']
                if timestamp < cutoff_str:
                    continue
                
                stats['total_conversions'] += 1
                conversion_counts[row['session_id']] += 1
                
                try:
                    # Track time to conversion
                    if row['time_to_conversion']:
                        time_to_conv = float(row['time_to_conversion'])
                        conversion_times.append(time_to_conv)
                    
                    # Track preference counts
                    if row['preference_count']:
                        pref_count = int(row['preference_count'])
                        preference_counts.append(pref_count)
                    
                    # Track top conversions
                    if row['item_type'] == 'device':
                        device_conversions[row['item_name']] += 1
                    elif row['item_type'] == 'plan':
                        plan_conversions[row['item_name']] += 1
                except (ValueError, TypeError):
                    pass
                
                # Track by day
                date = timestamp.split('T')[0]
                conv_dates[date] = conv_dates.get(date, 0) + 1
        
        # Calculate statistics
        if stats['total_recommendations'] > 0:
            stats['avg_preference_match'] = sum(preference_scores) / len(preference_scores) if preference_scores else 0
        
        if stats['total_conversions'] > 0:
            stats['conversion_rate'] = (stats['total_conversions'] / stats['total_recommendations']) * 100 if stats['total_recommendations'] > 0 else 0
            stats['avg_time_to_conversion'] = sum(conversion_times) / len(conversion_times) if conversion_times else 0
            stats['avg_preferences_count'] = sum(preference_counts) / len(preference_counts) if preference_counts else 0
        
        # Add daily stats
        stats['recommendations_by_day'] = dict(rec_dates)
        stats['conversions_by_day'] = dict(conv_dates)
        
        # Add top conversions
        stats['top_device_conversions'] = device_conversions.most_common(5)
        stats['top_plan_conversions'] = plan_conversions.most_common(5)
        
        return stats
    
    except Exception as e:
        logger.error(f"Error getting recommendation stats: {str(e)}")
        return stats

def get_recent_events(days: int = 1, limit: int = 50) -> Dict:
    """Get recent recommendation and conversion events"""
    events = {
        'recommendations': [],
        'conversions': []
    }
    
    try:
        # Calculate cutoff date
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        # Get recommendations
        recommendations = []
        with open(RECOMMENDATION_LOG, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['timestamp'] < cutoff_str:
                    continue
                recommendations.append(dict(row))
        
        # Sort by timestamp (newest first)
        recommendations.sort(key=lambda x: x['timestamp'], reverse=True)
        events['recommendations'] = recommendations[:limit]
        
        # Get conversions
        conversions = []
        with open(CONVERSION_LOG, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['timestamp'] < cutoff_str:
                    continue
                conversions.append(dict(row))
        
        # Sort by timestamp (newest first)
        conversions.sort(key=lambda x: x['timestamp'], reverse=True)
        events['conversions'] = conversions[:limit]
        
        return events
    
    except Exception as e:
        logger.error(f"Error getting recent events: {str(e)}")
        return events