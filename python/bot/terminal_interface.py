import logging
import sys
from typing import List, Dict, Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status

from python.config import MODEL_CONFIG, BOT_CONFIG, SYSTEM_PROMPT
from python.bot.together_client import TogetherClient

logger = logging.getLogger(__name__)

class TerminalInterface:
    """Terminal interface for chatting with DeepSeek-R1."""
    
    def __init__(self):
        self.together_client = TogetherClient()
        self.console = Console()
        self.conversation_history: List[Dict] = []
        self.system_prompt = SYSTEM_PROMPT

    def _print_markdown(self, text: str):
        """Print text with markdown formatting."""
        markdown = Markdown(text)
        self.console.print(markdown)

    def _print_help(self):
        """Print available commands."""
        help_text = """
Available commands:
- /help   - Show this help message
- /clear  - Clear conversation history
- /exit   - Exit the chat
- /config - Show current configuration
        """
        self.console.print(Panel(help_text, title="Help"))

    def _print_config(self):
        """Print current configuration."""
        config_text = f"""
Model Configuration:
- Model: {MODEL_CONFIG['model']}
- Temperature: {MODEL_CONFIG['temperature']}
- Top P: {MODEL_CONFIG['top_p']}
- Max Tokens: {MODEL_CONFIG['max_tokens']}

Bot Configuration:
- Cooldown: {BOT_CONFIG['cooldown_seconds']} seconds
- Max Retries: {BOT_CONFIG['max_retries']}
        """
        self.console.print(Panel(config_text, title="Configuration"))

    def _handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if should continue chat."""
        if command == "/help":
            self._print_help()
        elif command == "/clear":
            self.conversation_history.clear()
            self.console.print("Conversation history cleared.")
        elif command == "/exit":
            self.console.print("Goodbye!")
            return False
        elif command == "/config":
            self._print_config()
        else:
            self.console.print(f"Unknown command: {command}")
        return True

    def chat(self):
        """Start the chat interface."""
        self.console.print(Panel("Welcome to DeepSeek-R1 Chat! Type /help for available commands.", title="DeepSeek-R1 Chat"))

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\nYou")

                # Handle commands
                if user_input.startswith("/"):
                    if not self._handle_command(user_input):
                        break
                    continue

                # Show thinking indicator
                with Status("[bold blue]Thinking...", spinner="dots"):
                    # Generate response
                    prompt = self.together_client.format_conversation_history(
                        conversation_history=self.conversation_history,
                        current_message=user_input,
                        system_prompt=self.system_prompt
                    )

                    response = self.together_client.generate_response(
                        prompt=prompt,
                        system_prompt=self.system_prompt
                    )

                    # Store in history
                    self.conversation_history.append({
                        'user_input': user_input,
                        'response': response
                    })

                # Print response
                self.console.print("\n[bold blue]Assistant:[/bold blue]")
                self._print_markdown(response)

            except KeyboardInterrupt:
                self.console.print("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error in chat: {str(e)}", exc_info=True)
                self.console.print(f"\n[red]Error:[/red] {str(e)}")

    def run(self):
        """Run the terminal interface."""
        try:
            self.chat()
        except Exception as e:
            logger.error(f"Fatal error in terminal interface: {str(e)}", exc_info=True)
            self.console.print(f"\n[red]Fatal error:[/red] {str(e)}")
            sys.exit(1) 