import logging
import time
from typing import List, Dict
from github import Github
from github.GithubObject import GithubObject
from github.GraphQLException import GraphQLException

from python.config import API_CONFIG, BOT_CONFIG
from python.bot.together_client import TogetherClient

logger = logging.getLogger(__name__)

class GitHubHandler:
    """Handler for GitHub discussions and comments."""
    
    def __init__(self):
        self.github = Github(API_CONFIG['github_token'])
        self.together_client = TogetherClient()
        self.last_response_time = 0
        
        # System prompt for the model
        self.system_prompt = (
            "You are a helpful AI assistant that provides clear, accurate, and polite responses. "
            "When discussing complex topics, use real-world examples to make them more relatable. "
            "Always base your responses on factual information."
        )

    def _respect_cooldown(self):
        """Ensure we respect the cooldown period between responses."""
        current_time = time.time()
        time_since_last = current_time - self.last_response_time
        
        if time_since_last < BOT_CONFIG['cooldown_seconds']:
            sleep_time = BOT_CONFIG['cooldown_seconds'] - time_since_last
            logger.info(f"Respecting cooldown, sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_response_time = time.time()

    def _get_conversation_history(self, discussion: GithubObject) -> List[Dict]:
        """Reconstruct conversation history from a discussion."""
        history = []
        
        # Add the initial discussion post
        history.append({
            'user': discussion.author.login,
            'content': discussion.body,
            'response': None
        })
        
        # Add all comments in chronological order
        for comment in discussion.get_all_comments():
            history.append({
                'user': comment.author.login,
                'content': comment.body,
                'response': None
            })
        
        return history

    def _format_response(self, response_text: str, discussion_url: str) -> str:
        """Format the response with signature and discussion link."""
        return f"{response_text}{BOT_CONFIG['signature']}\n[View conversation]({discussion_url})"

    def handle_discussion(self, event_payload: dict):
        """Handle a discussion creation or edit event."""
        try:
            # Get the discussion using GraphQL
            repo = self.github.get_repo(event_payload['repository']['full_name'])
            discussion_number = event_payload['discussion']['number']
            
            try:
                # First try using the new GraphQL API
                discussion = repo.get_discussion(discussion_number)
            except (AttributeError, GraphQLException):
                # Fallback to REST API if GraphQL fails
                discussions = repo.get_discussions()
                discussion = next((d for d in discussions if d.number == discussion_number), None)
                if not discussion:
                    raise ValueError(f"Discussion #{discussion_number} not found")
            
            # Respect cooldown
            self._respect_cooldown()
            
            # Get conversation history
            history = self._get_conversation_history(discussion)
            
            # Generate response
            prompt = self.together_client.format_conversation_prompt(
                conversation_history=history,
                current_message=discussion.body,
                system_prompt=self.system_prompt
            )
            
            response = self.together_client.generate_response(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            # Format and post response
            formatted_response = self._format_response(response, discussion.html_url)
            discussion.create_reply(formatted_response)
            
            logger.info(f"Successfully responded to discussion #{discussion.number}")
            
        except Exception as e:
            logger.error(f"Error handling discussion: {str(e)}", exc_info=True)
            raise

    def handle_discussion_comment(self, event_payload: dict):
        """Handle a discussion comment creation or edit event."""
        try:
            # Get the discussion and comment using GraphQL
            repo = self.github.get_repo(event_payload['repository']['full_name'])
            discussion_number = event_payload['discussion']['number']
            
            try:
                # First try using the new GraphQL API
                discussion = repo.get_discussion(discussion_number)
            except (AttributeError, GraphQLException):
                # Fallback to REST API if GraphQL fails
                discussions = repo.get_discussions()
                discussion = next((d for d in discussions if d.number == discussion_number), None)
                if not discussion:
                    raise ValueError(f"Discussion #{discussion_number} not found")
            
            # Get the specific comment
            comment = None
            for c in discussion.get_all_comments():
                if str(c.id) == str(event_payload['comment']['id']):
                    comment = c
                    break
                    
            if not comment:
                raise ValueError(f"Comment {event_payload['comment']['id']} not found")
            
            # Respect cooldown
            self._respect_cooldown()
            
            # Get conversation history
            history = self._get_conversation_history(discussion)
            
            # Generate response
            prompt = self.together_client.format_conversation_prompt(
                conversation_history=history,
                current_message=comment.body,
                system_prompt=self.system_prompt
            )
            
            response = self.together_client.generate_response(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            # Format and post response
            formatted_response = self._format_response(response, comment.html_url)
            discussion.create_reply(formatted_response)
            
            logger.info(f"Successfully responded to comment on discussion #{discussion.number}")
            
        except Exception as e:
            logger.error(f"Error handling discussion comment: {str(e)}", exc_info=True)
            raise 