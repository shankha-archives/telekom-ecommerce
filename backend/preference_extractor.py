import json
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI

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

async def extract_user_preferences(conversation_history):
    """
    Extract user preferences from conversation history using LLM.
    Returns a structured object with user preferences for devices and plans.
    """
    # Ensure we have a client
    client = get_openai_client()
    if not client:
        print("OpenAI client not available - cannot extract preferences")
        return {}
    
    # Create a system message for preference extraction
    system_message = """
    Analyze the conversation history between user and assistant.
    Extract user preferences, needs, and constraints for mobile devices and plans.
    Return ONLY a JSON object with the following structure:
    {
        "device_preferences": {
            "brand": ["Apple", "Samsung", etc], 
            "price_range": {"min": 100, "max": 1000},
            "features": ["good camera", "battery life", etc],
            "storage": ["64GB", "128GB", etc],
            "color": ["black", "blue", etc]
        },
        "plan_preferences": {
            "data_needs": "high|medium|low",
            "price_sensitivity": "high|medium|low",
            "international": true|false,
            "family_plan": true|false,
            "contract_length": "monthly|1-year|2-year"
        },
        "demographics": {
            "age_group": "student|professional|senior",
            "tech_savvy": "high|medium|low",
            "usage_type": "streaming|gaming|business|casual"
        },
        "explicit_constraints": ["budget under 50 euros monthly", "need iPhone", etc]
    }
    Focus on information explicitly shared by the user or clearly implied.
    Include ONLY preferences that can be confidently inferred from the conversation.
    If a category has no clear preferences, omit it entirely or return an empty object/array.
    
    DO NOT include any text outside the JSON object in your response.
    """
    
    # Format conversation history for the LLM
    formatted_history = []
    for message in conversation_history:
        role = "user" if message.get("type") == "user" else "assistant"
        formatted_history.append({
            "role": role,
            "content": message.get("message", "")
        })
    
    try:
        # Call LLM to extract preferences
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                *formatted_history
            ],
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        preferences_text = response.choices[0].message.content.strip()
        preferences = json.loads(preferences_text)
        
        return preferences
    except Exception as e:
        print(f"Error extracting preferences: {str(e)}")
        return {}

async def refine_preferences(current_preferences, conversation_history):
    """
    Refine existing preferences based on new conversation history.
    This is less resource-intensive than extracting from scratch each time.
    """
    # Ensure we have a client
    client = get_openai_client()
    if not client:
        print("OpenAI client not available - cannot refine preferences")
        return current_preferences
    
    # Create a system message for preference refinement
    system_message = f"""
    You are analyzing a conversation to refine user preferences for mobile devices and plans.
    
    CURRENT PREFERENCES:
    {json.dumps(current_preferences, indent=2)}
    
    Review the recent conversation and update these preferences.
    ADD new preferences that are mentioned.
    MODIFY existing preferences if contradicted.
    RETAIN existing preferences that aren't contradicted.
    
    Return ONLY a JSON object with the updated preferences using the same structure as above.
    DO NOT include any text outside the JSON object in your response.
    """
    
    # Format recent conversation history
    recent_history = conversation_history[-5:]  # Only use the most recent messages
    formatted_history = []
    for message in recent_history:
        role = "user" if message.get("type") == "user" else "assistant"
        formatted_history.append({
            "role": role,
            "content": message.get("message", "")
        })
    
    try:
        # Call LLM to refine preferences
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                *formatted_history
            ],
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        preferences_text = response.choices[0].message.content.strip()
        updated_preferences = json.loads(preferences_text)
        
        return updated_preferences
    except Exception as e:
        print(f"Error refining preferences: {str(e)}")
        return current_preferences

async def generate_preference_explanation(preferences):
    """
    Generate a natural language explanation of the user's preferences.
    This is useful for confirming understanding with the user.
    """
    # Ensure we have a client
    client = get_openai_client()
    if not client:
        print("OpenAI client not available - cannot generate preference explanation")
        return []
    
    # If preferences are empty, return empty explanation
    if not preferences or (
        not preferences.get('device_preferences') and 
        not preferences.get('plan_preferences') and
        not preferences.get('demographics') and
        not preferences.get('explicit_constraints')
    ):
        return []
    
    # Create a system message for generating explanation
    system_message = f"""
    Generate a concise list of bullet points that summarize the user's preferences for mobile devices and plans.
    Make each point conversational and easy to understand.
    Focus on the most important preferences that will impact recommendations.
    
    User preferences:
    {json.dumps(preferences, indent=2)}
    
    Return ONLY a JSON array of strings, each representing a single preference statement.
    For example:
    [
      "You're looking for an iPhone with at least 128GB of storage",
      "Your budget is around €700-900",
      "You need a plan with at least 20GB of data"
    ]
    
    Include 3-6 points maximum, focusing on the most important preferences.
    DO NOT include any text outside the JSON array in your response.
    """
    
    try:
        # Call LLM to generate explanation
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_message}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        explanation_text = response.choices[0].message.content.strip()
        explanation = json.loads(explanation_text)
        
        return explanation
    except Exception as e:
        print(f"Error generating preference explanation: {str(e)}")
        return []