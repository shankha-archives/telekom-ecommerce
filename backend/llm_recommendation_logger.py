import csv
import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), 'llm_recommendation_log.csv')

CSV_FIELDS = [
    'timestamp',
    'user_id',
    'user_profile',
    'llm_input',
    'llm_response',
    'context',
]

def log_llm_recommendation(user_id, user_profile, llm_input, llm_response, context):
    """
    Log a context-aware LLM recommendation to a CSV file.
    user_profile/context should be dicts/objects (will be stringified as JSON).
    """
    import json
    row = {
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'user_profile': json.dumps(user_profile, ensure_ascii=False),
        'llm_input': json.dumps(llm_input, ensure_ascii=False) if isinstance(llm_input, (dict, list)) else str(llm_input),
        'llm_response': json.dumps(llm_response, ensure_ascii=False) if isinstance(llm_response, (dict, list)) else str(llm_response),
        'context': json.dumps(context, ensure_ascii=False) if isinstance(context, (dict, list)) else str(context),
    }
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
