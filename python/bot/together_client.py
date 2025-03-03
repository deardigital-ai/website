import logging
import backoff
import requests
from typing import Dict, Optional
import re
import base64
import json
from together import Together

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
        # Initialize Together SDK client
        self.together_client = Together(api_key=self.api_key)

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
            
            # Prepare the request payload, using MODEL_CONFIG for all parameters
            payload = {
                "model": MODEL_CONFIG["model"],
                "prompt": formatted_prompt,
                "temperature": kwargs.get("temperature", MODEL_CONFIG["temperature"]),
                "top_p": kwargs.get("top_p", MODEL_CONFIG["top_p"]),
                "max_tokens": kwargs.get("max_tokens", MODEL_CONFIG["max_tokens"]),
                "top_k": kwargs.get("top_k", MODEL_CONFIG["top_k"]),
                "repetition_penalty": kwargs.get("repetition_penalty", MODEL_CONFIG["repetition_penalty"]),
                "stop": ["Human:", "Assistant:"],
                "safety_model": MODEL_CONFIG["safety_model"]
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
                response_text = result["output"]["choices"][0]["text"].strip()
                
                # Remove thinking parts enclosed in <think> tags
                response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
                
                # Handle case where opening <think> tag is missing but closing </think> is present
                response_text = re.sub(r'^(.*?)</think>', '', response_text, flags=re.DOTALL)
                
                # Clean up the text by removing excessive newlines that might be left after removing <think> blocks
                response_text = re.sub(r'\n{3,}', '\n\n', response_text)
                
                # Final cleanup
                return response_text.strip()
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

    def generate_tarot_prompt(self, conversation_history: list, current_message: str) -> str:
        """
        Generate a tarot card image prompt based on the conversation context.
        
        Args:
            conversation_history: List of previous messages
            current_message: The current message being responded to
            
        Returns:
            A string containing the tarot card image prompt
        """
        try:
            # Format the conversation for analysis
            formatted_conversation = self._format_conversation_for_analysis(conversation_history, current_message)
            
            # Create a system prompt for generating the tarot card
            tarot_system_prompt = """
            Analyze the following conversation and create a prompt for a tarot card image.
            The prompt should reflect the themes, interests, and context of the conversation.
            
            Follow these rules:
            1. Always start with "Tarot Card: " to trigger image generation
            2. Create a detailed description of a tarot card that symbolically represents the conversation
            3. Include visual elements like colors, symbols, and composition
            4. Make the description detailed and vivid, around 100-150 words
            5. Do not include any explanations or notes - only the image description
            
            Examples of good tarot card prompts:
            - Tarot Card: A detailed illustration of a large, radiant star, with seven smaller stars surrounding it. The words "THE STAR" appear below. The background is a mix of twilight purples and deep blues. A figure kneels at the edge of a stream, pouring water into it, while holding another jug in the other hand. There's a small tree on the horizon. The Roman numeral "XVII" is above the star.
            - Tarot Card: An illustration of a woman with fair skin and natural, wavy hair cascading in soft curls around her face. She has striking, light-colored eyes and defined brows that convey depth and wisdom. Dressed in a red and navy plaid shirt, partially unbuttoned to reveal a white undershirt, her sleeves are rolled up casually to her forearms. She leans thoughtfully against a weathered, blue door frame with peeling paint, adding a rustic, vintage charm. Below her, the words "THE DREAMER" are inscribed. In the top corner, a small crescent moon symbol signifies introspection, while the Roman numeral "VII" is above, representing inner vision and contemplation.
            """
            
            # Generate the tarot card prompt
            payload = {
                "model": MODEL_CONFIG["model"],
                "prompt": f"{tarot_system_prompt}\n\nConversation to analyze:\n{formatted_conversation}\n\nTarot Card Prompt:",
                "temperature": 0.7,
                "max_tokens": 300,
                "stop": ["\n\n"],
            }
            
            # Make the API request
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            response.raise_for_status()
            
            # Extract and return the generated prompt
            result = response.json()
            if "output" in result and "choices" in result["output"]:
                prompt_text = result["output"]["choices"][0]["text"].strip()
                
                # Ensure it starts with "Tarot Card:"
                if not prompt_text.startswith("Tarot Card:"):
                    prompt_text = "Tarot Card: " + prompt_text
                
                logger.info(f"Generated tarot card prompt: {prompt_text}")
                return prompt_text
            else:
                logger.error(f"Unexpected response format from Together API: {result}")
                return "Tarot Card: A mystical tarot card with symbols representing digital communication and AI assistance."
                
        except Exception as e:
            logger.error(f"Error generating tarot card prompt: {str(e)}")
            # Return a default prompt in case of error
            return "Tarot Card: A mystical tarot card with symbols representing digital communication and AI assistance."
    
    def generate_image(self, prompt: str) -> Optional[str]:
        """
        Generate an image using the Together API based on the provided prompt.
        
        Args:
            prompt: The prompt to generate an image from
            
        Returns:
            Base64 encoded image data or None if generation fails
        """
        try:
            logger.info("Generating image from prompt")
            
            response = self.together_client.images.generate(
                prompt=prompt,
                model="black-forest-labs/FLUX.1-dev-lora",
                width=608,
                height=960,
                steps=40,
                n=1,
                response_format="b64_json",
                image_loras=[
                    {
                        "path": "https://huggingface.co/prithivMLmods/Retro-Pixel-Flux-LoRA/resolve/main/Retro-Pixel.safetensors?download=true",
                        "scale": 0.6
                    },
                    {
                        "path": "https://huggingface.co/prithivMLmods/Ton618-Tarot-Cards-Flux-LoRA/resolve/main/Tarot-card.safetensors?download=true",
                        "scale": 1
                    }
                ]
            )
            
            logger.info("Successfully generated image")
            return response.data[0].b64_json
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None
    
    def _format_conversation_for_analysis(self, conversation_history: list, current_message: str) -> str:
        """Format the conversation history for analysis to generate a tarot card prompt."""
        formatted_messages = []
        
        # Add previous messages from history
        for msg in conversation_history:
            formatted_messages.append(f"User: {msg['user_input']}")
            if msg.get('response'):
                formatted_messages.append(f"Assistant: {msg['response']}")
        
        # Add the current message
        formatted_messages.append(f"User: {current_message}")
        
        return "\n\n".join(formatted_messages) 