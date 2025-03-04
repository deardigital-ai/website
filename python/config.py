import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import socket
import re
from typing import Dict, Any

# Load environment variables from .env file if it exists
load_dotenv()

# Model configuration
MODEL_CONFIG: Dict[str, Any] = {
    'model': 'deepseek-ai/deepseek-v2',
    'temperature': 0.7,
    'top_p': 0.95,
    'top_k': 50,
    'repetition_penalty': 1.02,
    'max_tokens': 4096,
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
BOT_CONFIG: Dict[str, Any] = {
    'cooldown_seconds': 5,  # Minimum time between responses
    'max_history_messages': 10,  # Maximum number of messages to include in history
    'max_retries': 3,  # Maximum number of retries for API calls
    'retry_delay': 2,  # Delay between retries in seconds
}

# API configuration
API_CONFIG: Dict[str, Any] = {
    'github_token': os.environ.get('GITHUB_TOKEN', ''),
    'together_api_key': os.environ.get('TOGETHER_API_KEY', ''),
}

def setup_logging():
    """Set up logging configuration."""
    # Create a filter to redact sensitive information
    class SensitiveInfoFilter(logging.Filter):
        def __init__(self):
            super().__init__()
            # Get the hostname but don't expose it in logs
            self.hostname = socket.gethostname()
            # Create patterns for sensitive information
            self.patterns = [
                (re.compile(re.escape(self.hostname), re.IGNORECASE), '[HOSTNAME]'),
                # Add more patterns as needed
                (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), '[IP-ADDRESS]'),  # IP addresses
                (re.compile(r'token=\w+'), 'token=[REDACTED]'),  # API tokens
                (re.compile(r'key=\w+'), 'key=[REDACTED]'),  # API keys
                (re.compile(r'password=\w+'), 'password=[REDACTED]'),  # Passwords
            ]
        
        def filter(self, record):
            if isinstance(record.msg, str):
                for pattern, replacement in self.patterns:
                    record.msg = pattern.sub(replacement, record.msg)
            return True

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add sensitive info filter to the handler
    sensitive_filter = SensitiveInfoFilter()
    console_handler.addFilter(sensitive_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure file handler if needed
    log_file = os.environ.get('LOG_FILE')
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('github').setLevel(logging.WARNING)
    logging.getLogger('markdown_it').setLevel(logging.WARNING)  # Added to suppress markdown debug logs 