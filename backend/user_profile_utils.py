import csv
import os
import json

def load_user_profiles(csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), 'sample_users.csv')
    users = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Parse JSON fields if present
            try:
                row['purchase_history'] = json.loads(row['purchase_history']) if 'purchase_history' in row and row['purchase_history'] else []
            except Exception:
                row['purchase_history'] = []
            try:
                row['preferences'] = json.loads(row['preferences']) if 'preferences' in row and row['preferences'] else {}
            except Exception:
                row['preferences'] = {}
            try:
                row['devices'] = json.loads(row['devices']) if 'devices' in row and row['devices'] else []
            except Exception:
                row['devices'] = []
            users.append(row)
    return users

def get_user_profile(user_id, csv_path=None):
    users = load_user_profiles(csv_path)
    for user in users:
        if user.get('user_id') == user_id:
            return user
    return None
