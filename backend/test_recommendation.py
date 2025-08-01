#!/usr/bin/env python
"""
Simple test script for the recommendation engine
"""
import json
import os
from datetime import datetime
import recommendation_engine
import csv

def load_devices_from_csv(csv_path):
    devices = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            features = row['features'].split(';') if row['features'] else []
            device = {
                'id': row['id'] or "test_id",
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

def load_plans_from_csv(csv_path):
    plans = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            features = row['features'].split(';') if row['features'] else []
            plan = {
                'id': row['id'] or "test_id",
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

def main():
    print("Running simple recommendation engine test...")
    
    # Load test data
    devices_path = os.path.join(os.path.dirname(__file__), 'sample_devices.csv')
    plans_path = os.path.join(os.path.dirname(__file__), 'sample_plans.csv')
    
    devices = load_devices_from_csv(devices_path)
    plans = load_plans_from_csv(plans_path)
    
    print(f"Loaded {len(devices)} devices and {len(plans)} plans")
    
    # Create simple session data
    session_data = {
        'created_at': datetime.utcnow(),
        'last_access': datetime.utcnow(),
        'conversation_history': [],
        'user_preferences': {
            'device_preferences': {
                'brand': ['Apple'],
                'price_range': {'min': 800, 'max': 1200},
            }
        },
        'viewed_items': {'devices': {}, 'plans': {}},
        'search_queries': ['iPhone with good camera']
    }
    
    # Test the recommendation engine
    try:
        print("\nTesting recommendation engine...")
        recommendations = recommendation_engine.generate_weighted_recommendations(
            session_data,
            devices,
            plans,
            "iPhone with good camera"
        )
        
        print(f"Success! Got recommendations with keys: {recommendations.keys()}")
        
        # Show device recommendations
        if 'devices' in recommendations:
            print(f"\nDevice recommendations ({len(recommendations['devices'])} items):")
            for device in recommendations['devices']:
                device_id = device.get('id')
                explanations = recommendations.get('device_explanations', {}).get(device_id, [])
                print(f"- {device.get('name')} ({device.get('brand')})")
                for explanation in explanations:
                    print(f"  * {explanation}")
        
        # Show plan recommendations
        if 'plans' in recommendations:
            print(f"\nPlan recommendations ({len(recommendations['plans'])} items):")
            for plan in recommendations['plans']:
                plan_id = plan.get('id')
                explanations = recommendations.get('plan_explanations', {}).get(plan_id, [])
                print(f"- {plan.get('name')} (€{plan.get('price')})")
                for explanation in explanations:
                    print(f"  * {explanation}")
        
        print("\nTest completed successfully!")
    except Exception as e:
        print(f"Error in recommendation engine: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()