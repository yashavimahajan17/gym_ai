import requests
import uuid
import json
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
BASE_API_URL = "https://aws-us-east-2.langflow.datastax.com"
LANGFLOW_ID = "17c6a20f-5697-4e9e-9763-3278ae51eb55"
DATASTAX_ORG = "868193b5-f3c3-4f2e-a431-293f6000b00d"
APPLICATION_TOKEN = os.getenv("LANGFLOW_TOKEN")


def dict_to_string(obj, level=0):
    """Convert a dictionary to a readable string format."""
    strings = []
    indent = "  " * level

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                nested_string = dict_to_string(value, level + 1)
                strings.append(f"{indent}{key}: {nested_string}")
            else:
                strings.append(f"{indent}{key}: {value}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            nested_string = dict_to_string(item, level + 1)
            strings.append(f"{indent}Item {idx + 1}: {nested_string}")
    else:
        strings.append(f"{indent}{obj}")

    return ", ".join(strings)


def _get_headers():
    """Get the required headers for API requests."""
    return {
        "X-DataStax-Current-Org": DATASTAX_ORG,
        "Authorization": f"Bearer {APPLICATION_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _run_flow(question: str, profile_str: str) -> str:
    """
    Run the Langflow ask-ai-v2 flow with the given question and profile.
    
    Args:
        question: The question or prompt to send to the AI
        profile_str: The user profile as a string
        
    Returns:
        The AI response text
    """
    api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/ask-ai-v2"
    
    payload = {
        "output_type": "text",
        "input_type": "text",
        "session_id": str(uuid.uuid4()),
        "tweaks": {
            "TextInput-KG2ew": {
                "input_value": question
            },
            "TextInput-qDXMR": {
                "input_value": profile_str
            }
        }
    }
    
    # Check if token is set
    if not APPLICATION_TOKEN:
        raise Exception("LANGFLOW_TOKEN is not set in .env file")
    
    try:
        response = requests.post(api_url, json=payload, headers=_get_headers())
        response.raise_for_status()
        
        # Parse the response to extract the text
        result = response.json()
        
        # Check for error in response
        if "error" in result:
            raise Exception(f"API Error: {result['error']}")
        
        # Try different response formats
        outputs = result.get("outputs", [])
        if not outputs:
            raise Exception(f"Empty outputs in response. Full response: {json.dumps(result)[:500]}")
        
        inner_outputs = outputs[0].get("outputs", [])
        if not inner_outputs:
            raise Exception(f"Empty inner outputs. First output: {json.dumps(outputs[0])[:500]}")
        
        results = inner_outputs[0].get("results", {})
        
        # Try "text" key first
        if "text" in results:
            return results["text"]["data"]["text"]
        # Try "message" key (for chat output)
        elif "message" in results:
            return results["message"]["data"]["text"]
        else:
            raise Exception(f"No 'text' or 'message' in results. Results keys: {list(results.keys())}")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error making API request: {e}")


def ask_ai(profile, question):
    """
    Ask the AI a question based on the user's profile.
    
    Args:
        profile: The user's profile dictionary
        question: The question to ask
        
    Returns:
        The AI's response as a string
    """
    profile_str = dict_to_string(profile)
    return _run_flow(question, profile_str)


def get_macros(profile, goals):
    """
    Get AI-generated macro recommendations based on profile and goals.
    
    Args:
        profile: The user's general profile information
        goals: List of fitness goals
        
    Returns:
        Dictionary with calories, protein, fat, and carbs values
    """
    api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/macros"
    
    profile_str = dict_to_string(profile)
    goals_str = ", ".join(goals) if goals else "general fitness"
    
    # Construct the input message for macro calculation
    input_message = f"Profile: {profile_str}\nGoals: {goals_str}"
    
    payload = {
        "output_type": "chat",
        "input_type": "chat",
        "input_value": input_message,
        "session_id": str(uuid.uuid4())
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=_get_headers())
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        response_text = result["outputs"][0]["outputs"][0]["results"]["message"]["data"]["text"]
        
        # Try to parse the response as JSON
        import re
        json_match = re.search(r'\{[^{}]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(response_text)
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error making API request: {e}")
    except json.JSONDecodeError:
        # Return default values if parsing fails
        return {
            "calories": 2000,
            "protein": 140,
            "fat": 60,
            "carbs": 200
        }
    except (KeyError, IndexError) as e:
        raise Exception(f"Error parsing response: {e}")
