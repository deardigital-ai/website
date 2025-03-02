import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Model configuration
MODEL_CONFIG = {
    'model': 'deepseek-ai/DeepSeek-R1',
    'temperature': 0.6,
    'top_p': 0.95,
    'max_tokens': None,
    'safety_model': "meta-llama/Meta-Llama-Guard-3-8B",
}

# System prompt to guide the model's behavior
SYSTEM_PROMPT = """You are a helpful AI assistant that provides clear, accurate, and polite responses. 
When discussing complex topics, use real-world examples to make them more relatable. 
Always base your responses on factual information.

Important guidelines:
1. Provide direct responses in the requested language or format
2. Always maintain a helpful and friendly tone
3. If you can't do something, explain why politely

Remember to respond in the same language as the user's request when specifically asked."""

# Bot configuration
BOT_CONFIG = {
    'signature': '\n\n---\n*Response by DeepSeek-R1 Bot*',
    'cooldown_seconds': 30,
    'max_retries': 3,
    'retry_base_delay': 2,  # Base delay for exponential backoff
}

# API configuration
API_CONFIG = {
    'together_api_key': os.getenv('TOGETHER_API_KEY'),
    'github_token': os.getenv('GITHUB_TOKEN'),
}

def setup_logging():
    """Configure logging settings."""
    logging.basicConfig(
        level=logging.INFO,  # Changed to INFO level
        format='%(asctime)s - %(levelname)s - %(message)s',  # Simplified format
        handlers=[
            logging.StreamHandler(),  # Console handler
            logging.FileHandler(  # File handler
                Path(__file__).parent.parent / 'bot.log',
                encoding='utf-8'
            )
        ]
    )

    # Set logging levels for modules
    logging.getLogger('python.bot').setLevel(logging.INFO)
    
    # Reduce noise from other libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('github').setLevel(logging.WARNING)
    logging.getLogger('markdown_it').setLevel(logging.WARNING)  # Added to suppress markdown debug logs 