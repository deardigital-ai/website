import logging
import backoff
import requests
from typing import Dict, Optional

from python.config import API_CONFIG, MODEL_CONFIG

logger = logging.getLogger(__name__)

class TogetherClient:
    """Client for interacting with Together API."""
    
    def __init__(self):
        self.api_key = API_CONFIG['together_api_key']
        if not self.api_key:
            raise ValueError("Together API key not found in environment")
        
        self.base_url = "https://api.together.xyz/inference"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, requests.exceptions.HTTPError),
        max_tries=3,
        base=2
    )
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response using the DeepSeek-R1 model."""
        try:
            # Format the prompt with system prompt if provided
            formatted_prompt = f"{system_prompt}\n\n" if system_prompt else ""
            formatted_prompt += f"Human: {prompt}\n\nAssistant:"
            
            # Prepare the request payload
            payload = {
                "model": MODEL_CONFIG["model"],
                "prompt": formatted_prompt,
                "temperature": kwargs.get("temperature", MODEL_CONFIG["temperature"]),
                "top_p": kwargs.get("top_p", MODEL_CONFIG["top_p"]),
                "max_tokens": kwargs.get("max_tokens", MODEL_CONFIG["max_tokens"]),
                "stop": ["Human:", "Assistant:"]
            }

            # Make the API request
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )

            # Only log errors
            if not response.ok:
                logger.error(f"API request failed with status {response.status_code}")
                logger.error(f"Response content: {response.text}")

            response.raise_for_status()

            # Extract and return the generated text
            result = response.json()
            if "output" in result and "choices" in result["output"]:
                return result["output"]["choices"][0]["text"].strip()
            else:
                raise ValueError(f"Unexpected response format from Together API: {result}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Together API: {str(e)}")
            logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error in generate_response: {str(e)}")
            raise

    def format_conversation_history(
        self,
        conversation_history: list,
        current_message: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Format the conversation history and current message into a prompt."""
        # Format conversation history in Human/Assistant format
        formatted_messages = []
        
        # Add previous messages from history
        for msg in conversation_history:
            formatted_messages.append(f"Human: {msg['user_input']}")
            if msg.get('response'):
                formatted_messages.append(f"Assistant: {msg['response']}")
        
        # Add the current message
        formatted_messages.append(current_message)
        
        return "\n\n".join(formatted_messages) 