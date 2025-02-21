import logging
import time
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

    def _get_conversation_history(self, discussion: GithubObject) -> List[Dict]:
        """Reconstruct conversation history from a discussion."""
        history = []
        
        # Add the initial discussion post
        history.append({
            'user': discussion.author.login if hasattr(discussion, 'author') else discussion.user.login,
            'content': discussion.body,
            'response': None
        })
        
        # Add all comments in chronological order
        comments_method = getattr(discussion, 'get_all_comments', None) or getattr(discussion, 'get_comments', None)
        if comments_method:
            for comment in comments_method():
                history.append({
                    'user': comment.author.login if hasattr(comment, 'author') else comment.user.login,
                    'content': comment.body,
                    'response': None
                })
        
        return history

    def _format_response(self, response_text: str, discussion_url: str) -> str:
        """Format the response with signature and discussion link."""
        return f"{response_text}{BOT_CONFIG['signature']}\n[View conversation]({discussion_url})"

    def _get_discussion_schema(self, owner: str, name: str, number: int) -> str:
        """Get the GraphQL schema with variables replaced."""
        # Simple query without nested fields first
        return """
        {
            repository(owner: "%s", name: "%s") {
                discussion(number: %d) {
                    id
                    title
                    body
                    url
                    author {
                        login
                    }
                }
            }
        }
        """ % (owner, name, number)

    def _get_discussions_schema(self, owner: str, name: str) -> str:
        """Get the GraphQL schema for listing discussions."""
        return """
        {
            repository(owner: "%s", name: "%s") {
                discussions(first: 100) {
                    nodes {
                        id
                        number
                        title
                        body
                        url
                        author {
                            login
                        }
                    }
                }
            }
        }
        """ % (owner, name)

    def handle_discussion(self, event_payload: dict):
        """Handle a discussion creation or edit event."""
        try:
            # Log event payload structure
            logger.debug(f"Event payload keys: {event_payload.keys()}")
            logger.debug(f"Repository full name: {event_payload.get('repository', {}).get('full_name')}")
            logger.debug(f"Discussion number: {event_payload.get('discussion', {}).get('number')}")
            
            # Get the discussion
            repo = self.github.get_repo(event_payload['repository']['full_name'])
            discussion_number = event_payload['discussion']['number']
            owner, name = event_payload['repository']['full_name'].split('/')
            
            # Log repository information
            logger.debug(f"Repository permissions: {repo.permissions}")
            
            # Get GraphQL schema with variables replaced
            discussion_schema = self._get_discussion_schema(owner, name, discussion_number)
            
            # Log GraphQL query details
            logger.debug(f"GraphQL Schema to be used: {discussion_schema}")
            
            try:
                # Try using GraphQL API
                logger.debug(f"Attempting GraphQL query for owner: {owner}, name: {name}, number: {discussion_number}")
                discussion = repo.get_discussion(discussion_number, discussion_schema)
            except (AttributeError, GithubException) as e:
                logger.warning(f"GraphQL API failed with error type {type(e)}: {str(e)}")
                logger.warning(f"Full exception details: {repr(e)}")
                # Log the actual response if available
                if hasattr(e, 'data'):
                    logger.warning(f"Error response data: {e.data}")
                
                logger.info("Attempting fallback to REST API...")
                # Fallback to REST API
                try:
                    # Use a different schema for listing discussions
                    discussions_schema = self._get_discussions_schema(owner, name)
                    discussions = repo.get_discussions(discussions_schema)
                    discussion = next((d for d in discussions if d.number == discussion_number), None)
                    if not discussion:
                        raise ValueError(f"Discussion #{discussion_number} not found")
                except Exception as rest_e:
                    logger.error(f"REST API fallback failed: {str(rest_e)}")
                    raise
            
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
            # Try both methods for creating replies
            try:
                if hasattr(discussion, 'create_reply'):
                    discussion.create_reply(formatted_response)
                else:
                    discussion.create_comment(formatted_response)
            except Exception as e:
                logger.error(f"Failed to create reply: {str(e)}")
                # Final fallback - try to create a regular comment
                discussion.create_comment(formatted_response)
            
            logger.info(f"Successfully responded to discussion #{discussion.number}")
            
        except Exception as e:
            logger.error(f"Error handling discussion: {str(e)}", exc_info=True)
            raise

    def handle_discussion_comment(self, event_payload: dict):
        """Handle a discussion comment creation or edit event."""
        try:
            # Get the discussion
            repo = self.github.get_repo(event_payload['repository']['full_name'])
            discussion_number = event_payload['discussion']['number']
            
            # GraphQL schema for discussions
            discussion_schema = """
            query($owner: String!, $name: String!, $number: Int!) {
                repository(owner: $owner, name: $name) {
                    discussion(number: $number) {
                        id
                        title
                        body
                        url
                        author {
                            login
                        }
                        comments(first: 100) {
                            nodes {
                                id
                                body
                                author {
                                    login
                                }
                            }
                        }
                    }
                }
            }
            """
            
            try:
                # Try using GraphQL API
                owner, name = event_payload['repository']['full_name'].split('/')
                discussion = repo.get_discussion(discussion_number, discussion_schema)
            except (AttributeError, GithubException) as e:
                logger.warning(f"GraphQL API failed, falling back to REST: {str(e)}")
                # Fallback to REST API
                discussions = repo.get_discussions()
                discussion = next((d for d in discussions if d.number == discussion_number), None)
                if not discussion:
                    raise ValueError(f"Discussion #{discussion_number} not found")
            
            # Get the specific comment
            comment = None
            comments_method = getattr(discussion, 'get_all_comments', None) or getattr(discussion, 'get_comments', None)
            if comments_method:
                for c in comments_method():
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
            # Try both methods for creating replies
            try:
                if hasattr(discussion, 'create_reply'):
                    discussion.create_reply(formatted_response)
                else:
                    discussion.create_comment(formatted_response)
            except Exception as e:
                logger.error(f"Failed to create reply: {str(e)}")
                # Final fallback - try to create a regular comment
                discussion.create_comment(formatted_response)
            
            logger.info(f"Successfully responded to comment on discussion #{discussion.number}")
            
        except Exception as e:
            logger.error(f"Error handling discussion comment: {str(e)}", exc_info=True)
            raise 