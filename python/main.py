import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from python.bot.github_handler import GitHubHandler
from python.bot.terminal_interface import TerminalInterface
from python.config import setup_logging

def parse_args():
    parser = argparse.ArgumentParser(description='DeepSeek-R1 Discussion Bot')
    parser.add_argument('--github-event', type=str, help='GitHub event type')
    parser.add_argument('--event-payload', type=str, help='GitHub event payload as JSON')
    return parser.parse_args()

def handle_github_event(event_type: str, event_payload: dict):
    """Handle GitHub discussion events."""
    github_handler = GitHubHandler()
    
    if event_type == 'discussion':
        if event_payload['action'] in ['created', 'edited']:
            github_handler.handle_discussion(event_payload)
    
    elif event_type == 'discussion_comment':
        if event_payload['action'] in ['created', 'edited']:
            github_handler.handle_discussion_comment(event_payload)

def main():
    setup_logging()
    args = parse_args()

    try:
        if args.github_event and args.event_payload:
            # GitHub Action mode
            event_payload = json.loads(args.event_payload)
            handle_github_event(args.github_event, event_payload)
        else:
            # Terminal mode
            terminal = TerminalInterface()
            terminal.run()

    except Exception as e:
        logging.error(f"Error in main: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 