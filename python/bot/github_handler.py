import logging
import time
import requests
from typing import List, Dict
from github import Github
from github.GithubObject import GithubObject
from github.GithubException import GithubException
import pkg_resources

from python.config import API_CONFIG, BOT_CONFIG
from python.bot.together_client import TogetherClient

logger = logging.getLogger(__name__)

class GitHubHandler:
    """Handler for GitHub discussions and comments."""
    
    def __init__(self):
        self.github = Github(API_CONFIG['github_token'])
        self.together_client = TogetherClient()
        self.last_response_time = 0
        self.github_token = API_CONFIG['github_token']
        
        # Log version information
        pygithub_version = pkg_resources.get_distribution('PyGithub').version
        logger.info(f"Using PyGithub version: {pygithub_version}")
        
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

    def _get_discussion(self, repo_full_name: str, discussion_number: int) -> Dict:
        """Get a discussion using GitHub REST API."""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {self.github_token}'
        }
        
        # First get the discussion ID using GraphQL (required for REST API)
        graphql_url = 'https://api.github.com/graphql'
        query = f"""
        {{
          repository(owner: "{repo_full_name.split('/')[0]}", name: "{repo_full_name.split('/')[1]}") {{
            discussion(number: {discussion_number}) {{
              id
            }}
          }}
        }}
        """
        
        response = requests.post(
            graphql_url,
            headers={'Authorization': f'Bearer {self.github_token}'},
            json={'query': query}
        )
        response.raise_for_status()
        
        discussion_id = response.json()['data']['repository']['discussion']['id']
        
        # Now get the full discussion details using REST API
        url = f'https://api.github.com/repos/{repo_full_name}/discussions/{discussion_id}'
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()

    def _create_discussion_comment(self, repo_full_name: str, discussion_number: int, body: str) -> Dict:
        """Create a comment on a discussion using GitHub REST API."""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {self.github_token}'
        }
        
        url = f'https://api.github.com/repos/{repo_full_name}/discussions/{discussion_number}/comments'
        data = {'body': body}
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()

    def _get_conversation_history(self, discussion: Dict) -> List[Dict]:
        """Reconstruct conversation history from a discussion."""
        history = []
        
        # Add the initial discussion post
        history.append({
            'user': discussion['author']['login'],
            'content': discussion['body'],
            'response': None
        })
        
        # Add all comments in chronological order
        for comment in discussion.get('comments', []):
            history.append({
                'user': comment['author']['login'],
                'content': comment['body'],
                'response': None
            })
        
        return history

    def _format_response(self, response_text: str, discussion_url: str) -> str:
        """Format the response with signature and discussion link."""
        return f"{response_text}{BOT_CONFIG['signature']}\n[View conversation]({discussion_url})"

    def handle_discussion(self, event_payload: dict):
        """Handle a discussion creation or edit event."""
        try:
            # Log event payload structure
            logger.debug(f"Event payload keys: {event_payload.keys()}")
            logger.debug(f"Repository full name: {event_payload.get('repository', {}).get('full_name')}")
            logger.debug(f"Discussion number: {event_payload.get('discussion', {}).get('number')}")
            
            repo_full_name = event_payload['repository']['full_name']
            discussion_number = event_payload['discussion']['number']
            
            try:
                # Get the discussion using REST API
                discussion = self._get_discussion(repo_full_name, discussion_number)
            except Exception as e:
                logger.error(f"Failed to get discussion: {str(e)}")
                raise
            
            # Respect cooldown
            self._respect_cooldown()
            
            # Get conversation history
            history = self._get_conversation_history(discussion)
            
            # Generate response
            prompt = self.together_client.format_conversation_prompt(
                conversation_history=history,
                current_message=discussion['body'],
                system_prompt=self.system_prompt
            )
            
            response = self.together_client.generate_response(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            # Format and post response
            formatted_response = self._format_response(response, discussion['html_url'])
            
            try:
                # Create comment using REST API
                self._create_discussion_comment(repo_full_name, discussion_number, formatted_response)
                logger.info(f"Successfully responded to discussion #{discussion_number}")
            except Exception as e:
                logger.error(f"Failed to create comment: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error handling discussion: {str(e)}", exc_info=True)
            raise

    def handle_discussion_comment(self, event_payload: dict):
        """Handle a discussion comment creation or edit event."""
        try:
            repo_full_name = event_payload['repository']['full_name']
            discussion_number = event_payload['discussion']['number']
            
            try:
                # Get the discussion using REST API
                discussion = self._get_discussion(repo_full_name, discussion_number)
            except Exception as e:
                logger.error(f"Failed to get discussion: {str(e)}")
                raise
            
            # Get the specific comment
            comment = None
            comment_id = event_payload['comment']['id']
            for c in discussion.get('comments', []):
                if str(c['id']) == str(comment_id):
                    comment = c
                    break
                    
            if not comment:
                raise ValueError(f"Comment {comment_id} not found")
            
            # Respect cooldown
            self._respect_cooldown()
            
            # Get conversation history
            history = self._get_conversation_history(discussion)
            
            # Generate response
            prompt = self.together_client.format_conversation_prompt(
                conversation_history=history,
                current_message=comment['body'],
                system_prompt=self.system_prompt
            )
            
            response = self.together_client.generate_response(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            # Format and post response
            formatted_response = self._format_response(response, comment['html_url'])
            
            try:
                # Create comment using REST API
                self._create_discussion_comment(repo_full_name, discussion_number, formatted_response)
                logger.info(f"Successfully responded to comment on discussion #{discussion_number}")
            except Exception as e:
                logger.error(f"Failed to create comment: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error handling discussion comment: {str(e)}", exc_info=True)
            raise 