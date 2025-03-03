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
        """Get a discussion using GitHub GraphQL API."""
        headers = {
            'Authorization': f'Bearer {self.github_token}',
            'Content-Type': 'application/json',
        }
        
        # Use GraphQL to get all the discussion details we need
        query = """
        query GetDiscussion($owner: String!, $name: String!, $number: Int!) {
          repository(owner: $owner, name: $name) {
            discussion(number: $number) {
              id
              databaseId
              url
              body
              author {
                login
              }
              comments(first: 100) {
                nodes {
                  id
                  databaseId
                  body
                  author {
                    login
                  }
                  url
                  replies(first: 100) {
                    nodes {
                      id
                      databaseId
                      body
                      author {
                        login
                      }
                      url
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            'owner': repo_full_name.split('/')[0],
            'name': repo_full_name.split('/')[1],
            'number': discussion_number
        }
        
        response = requests.post(
            'https://api.github.com/graphql',
            headers=headers,
            json={'query': query, 'variables': variables}
        )
        
        if response.status_code != 200:
            logger.error(f"GraphQL Error Response: {response.text}")
            response.raise_for_status()
            
        data = response.json()
        if 'errors' in data:
            logger.error(f"GraphQL Errors: {data['errors']}")
            raise Exception(f"GraphQL Error: {data['errors'][0]['message']}")
            
        discussion_data = data['data']['repository']['discussion']
        if not discussion_data:
            raise ValueError(f"Discussion #{discussion_number} not found")
            
        return discussion_data

    def _create_discussion_comment(self, repo_full_name: str, discussion_id: str, body: str, reply_to_id: str = None) -> Dict:
        """Create a comment on a discussion using GitHub GraphQL API.
        
        If reply_to_id is provided, the comment will be created as a reply to the specified comment.
        """
        headers = {
            'Authorization': f'Bearer {self.github_token}',
            'Content-Type': 'application/json',
        }
        
        # Add reply_to_id to variables if provided
        variables = {
            'discussionId': discussion_id,
            'body': body
        }
        
        if reply_to_id:
            variables['replyToId'] = reply_to_id
            logger.info(f"Creating reply to comment {reply_to_id}")
            mutation = """
            mutation CreateDiscussionCommentReply($discussionId: ID!, $body: String!, $replyToId: ID!) {
              addDiscussionComment(input: {discussionId: $discussionId, body: $body, replyToId: $replyToId}) {
                comment {
                  id
                  url
                }
              }
            }
            """
        else:
            logger.info("Creating top-level comment")
            mutation = """
            mutation CreateDiscussionComment($discussionId: ID!, $body: String!) {
              addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
                comment {
                  id
                  url
                }
              }
            }
            """
        
        response = requests.post(
            'https://api.github.com/graphql',
            headers=headers,
            json={'query': mutation, 'variables': variables}
        )
        
        if response.status_code != 200:
            logger.error(f"GraphQL Error Response: {response.text}")
            response.raise_for_status()
            
        data = response.json()
        if 'errors' in data:
            logger.error(f"GraphQL Errors: {data['errors']}")
            raise Exception(f"GraphQL Error: {data['errors'][0]['message']}")
            
        return data['data']['addDiscussionComment']['comment']

    def _create_placeholder_comment(self, repo_full_name: str, discussion_id: str, reply_to_id: str = None) -> Dict:
        """Create a placeholder comment while the actual response is being generated."""
        logger.info("Creating placeholder comment")
        
        placeholder_content = (
            '<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="900">\n\n'
            'deardigital AI generating response...'
        )
        
        try:
            comment = self._create_discussion_comment(
                repo_full_name, 
                discussion_id, 
                placeholder_content, 
                reply_to_id
            )
            logger.info(f"Successfully created placeholder comment with ID: {comment['id']}")
            return comment
        except Exception as e:
            logger.error(f"Failed to create placeholder comment: {str(e)}")
            raise

    def _update_discussion_comment(self, comment_id: str, body: str) -> Dict:
        """Update an existing discussion comment using GitHub GraphQL API."""
        logger.info(f"Updating comment {comment_id}")
        
        headers = {
            'Authorization': f'Bearer {self.github_token}',
            'Content-Type': 'application/json',
        }
        
        mutation = """
        mutation UpdateDiscussionComment($commentId: ID!, $body: String!) {
          updateDiscussionComment(input: {commentId: $commentId, body: $body}) {
            comment {
              id
              url
            }
          }
        }
        """
        
        variables = {
            'commentId': comment_id,
            'body': body
        }
        
        response = requests.post(
            'https://api.github.com/graphql',
            headers=headers,
            json={'query': mutation, 'variables': variables}
        )
        
        if response.status_code != 200:
            logger.error(f"GraphQL Error Response: {response.text}")
            response.raise_for_status()
            
        data = response.json()
        if 'errors' in data:
            logger.error(f"GraphQL Errors: {data['errors']}")
            raise Exception(f"GraphQL Error: {data['errors'][0]['message']}")
            
        logger.info(f"Successfully updated comment {comment_id}")
        return data['data']['updateDiscussionComment']['comment']

    def _get_conversation_history(self, discussion: Dict) -> List[Dict]:
        """Reconstruct conversation history from a discussion."""
        history = []
        
        # Add the initial discussion post
        history.append({
            'user_input': discussion['body'],
            'response': None,
            'user': discussion['author']['login']  # Keep user info for reference
        })
        
        # Add all comments in chronological order
        for comment in discussion['comments']['nodes']:
            history.append({
                'user_input': comment['body'],
                'response': None,
                'user': comment['author']['login']  # Keep user info for reference
            })
        
        return history

    def _format_response(self, response_text: str, discussion_url: str) -> str:
        """Return the response text without any additional formatting."""
        return response_text

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
                # Get the discussion using GraphQL API
                logger.info(f"Fetching discussion #{discussion_number}")
                discussion = self._get_discussion(repo_full_name, discussion_number)
            except Exception as e:
                logger.error(f"Failed to get discussion: {str(e)}")
                raise
            
            # Create placeholder comment immediately (no cooldown)
            try:
                logger.info("Creating placeholder comment for discussion")
                placeholder = self._create_placeholder_comment(repo_full_name, discussion['id'])
                logger.info(f"Placeholder comment created with ID: {placeholder['id']}")
            except Exception as e:
                logger.error(f"Failed to create placeholder: {str(e)}")
                # Continue without placeholder if it fails
                placeholder = None
            
            # Respect cooldown before generating the actual response
            self._respect_cooldown()
            
            # Get conversation history
            history = self._get_conversation_history(discussion)
            
            # Generate response
            logger.info("Generating AI response")
            try:
                prompt = self.together_client.format_conversation_history(
                    conversation_history=history,
                    current_message=discussion['body'],
                    system_prompt=self.system_prompt
                )
                
                response = self.together_client.generate_response(
                    prompt=prompt,
                    system_prompt=self.system_prompt
                )
                
                # Format response
                formatted_response = self._format_response(response, discussion['url'])
                logger.info("Successfully generated response")
                
                # Update placeholder or create new comment
                if placeholder:
                    try:
                        logger.info(f"Updating placeholder comment {placeholder['id']} with actual response")
                        self._update_discussion_comment(placeholder['id'], formatted_response)
                        logger.info(f"Successfully updated placeholder with actual response")
                    except Exception as e:
                        logger.error(f"Failed to update placeholder: {str(e)}")
                        # If updating fails, try to create a new comment
                        logger.info("Falling back to creating a new comment")
                        self._create_discussion_comment(repo_full_name, discussion['id'], formatted_response)
                else:
                    # If no placeholder was created, create a regular comment
                    logger.info("No placeholder exists, creating regular comment")
                    self._create_discussion_comment(repo_full_name, discussion['id'], formatted_response)
                    
                logger.info(f"Successfully responded to discussion #{discussion_number}")
                
            except Exception as e:
                logger.error(f"Failed to generate response: {str(e)}")
                
                # Update placeholder with error message if it exists
                if placeholder:
                    error_message = (
                        "⚠️ **Error generating response**\n\n"
                        "I encountered an issue while generating a response. "
                        "Please try again later or contact support if the problem persists."
                    )
                    try:
                        logger.info(f"Updating placeholder with error message")
                        self._update_discussion_comment(placeholder['id'], error_message)
                    except Exception as update_error:
                        logger.error(f"Failed to update placeholder with error message: {str(update_error)}")
                
                raise
            
        except Exception as e:
            logger.error(f"Error handling discussion: {str(e)}", exc_info=True)
            raise

    def _find_comment_in_discussion(self, discussion: Dict, target_id: str, target_db_id: str) -> Dict:
        """Find a comment or reply in a discussion by its ID or database ID."""
        logger.info(f"Searching for comment/reply with ID: {target_id} or DB ID: {target_db_id}")
        
        # First check main comments
        for comment in discussion['comments']['nodes']:
            logger.debug(f"Checking comment - ID: {comment['id']}, DB ID: {comment.get('databaseId')}")
            
            if comment['id'] == target_id or str(comment.get('databaseId')) == target_db_id:
                logger.info(f"Found matching comment: {comment}")
                return comment
                
            # Check replies if this comment has any
            if 'replies' in comment and 'nodes' in comment['replies']:
                for reply in comment['replies']['nodes']:
                    logger.debug(f"Checking reply - ID: {reply['id']}, DB ID: {reply.get('databaseId')}")
                    
                    if reply['id'] == target_id or str(reply.get('databaseId')) == target_db_id:
                        logger.info(f"Found matching reply: {reply}")
                        return reply
        
        return None

    def handle_discussion_comment(self, event_payload: dict):
        """Handle a discussion comment creation or edit event."""
        try:
            repo_full_name = event_payload['repository']['full_name']
            discussion_number = event_payload['discussion']['number']
            
            # Log the event payload for debugging
            logger.debug(f"Event payload: {event_payload}")
            logger.info(f"Processing comment event for discussion #{discussion_number}")
            
            try:
                # Get the discussion using GraphQL API
                logger.info(f"Fetching discussion #{discussion_number}")
                discussion = self._get_discussion(repo_full_name, discussion_number)
                logger.debug(f"Discussion data retrieved")
            except Exception as e:
                logger.error(f"Failed to get discussion: {str(e)}")
                raise
            
            # Get the specific comment
            comment_id = event_payload['comment']['node_id']
            db_id = str(event_payload['comment']['id'])
            logger.info(f"Looking for comment with ID: {comment_id}, DB ID: {db_id}")
            
            # Try to find the comment or reply
            comment = self._find_comment_in_discussion(discussion, comment_id, db_id)
            
            if not comment:
                error_msg = f"Comment/reply not found. ID: {comment_id}, DB ID: {db_id}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"Found comment: {comment['id']}")
            
            # Create placeholder comment immediately (no cooldown)
            try:
                logger.info("Creating placeholder reply to comment")
                placeholder = self._create_placeholder_comment(
                    repo_full_name, 
                    discussion['id'], 
                    reply_to_id=comment['id']
                )
                logger.info(f"Placeholder reply created with ID: {placeholder['id']}")
            except Exception as e:
                logger.error(f"Failed to create placeholder reply: {str(e)}")
                # Continue without placeholder if it fails
                placeholder = None
            
            # Respect cooldown before generating the actual response
            self._respect_cooldown()
            
            # Get conversation history
            history = self._get_conversation_history(discussion)
            
            # Generate response
            logger.info("Generating AI response for comment")
            try:
                prompt = self.together_client.format_conversation_history(
                    conversation_history=history,
                    current_message=comment['body'],
                    system_prompt=self.system_prompt
                )
                
                response = self.together_client.generate_response(
                    prompt=prompt,
                    system_prompt=self.system_prompt
                )
                
                # Format response
                formatted_response = self._format_response(response, comment['url'])
                logger.info("Successfully generated response for comment")
                
                # Update placeholder or create new reply
                if placeholder:
                    try:
                        logger.info(f"Updating placeholder reply {placeholder['id']} with actual response")
                        self._update_discussion_comment(placeholder['id'], formatted_response)
                        logger.info(f"Successfully updated placeholder with actual response")
                    except Exception as e:
                        logger.error(f"Failed to update placeholder reply: {str(e)}")
                        # If updating fails, try to create a new reply
                        logger.info("Falling back to creating a new reply")
                        self._create_discussion_comment(
                            repo_full_name, 
                            discussion['id'], 
                            formatted_response,
                            reply_to_id=comment['id']
                        )
                else:
                    # If no placeholder was created, create a regular reply
                    logger.info("No placeholder exists, creating regular reply")
                    self._create_discussion_comment(
                        repo_full_name, 
                        discussion['id'], 
                        formatted_response,
                        reply_to_id=comment['id']
                    )
                    
                logger.info(f"Successfully responded to comment in discussion #{discussion_number}")
                
            except Exception as e:
                logger.error(f"Failed to generate response for comment: {str(e)}")
                
                # Update placeholder with error message if it exists
                if placeholder:
                    error_message = (
                        "⚠️ **Error generating response**\n\n"
                        "I encountered an issue while generating a response. "
                        "Please try again later or contact support if the problem persists."
                    )
                    try:
                        logger.info(f"Updating placeholder with error message")
                        self._update_discussion_comment(placeholder['id'], error_message)
                    except Exception as update_error:
                        logger.error(f"Failed to update placeholder with error message: {str(update_error)}")
                
                # Try fallback to regular comment if reply fails
                if not placeholder:
                    try:
                        logger.info("Attempting to create error message as regular comment")
                        error_message = (
                            "⚠️ **Error generating response**\n\n"
                            "I encountered an issue while generating a response. "
                            "Please try again later or contact support if the problem persists."
                        )
                        self._create_discussion_comment(repo_full_name, discussion['id'], error_message)
                    except Exception as fallback_error:
                        logger.error(f"Fallback error message also failed: {str(fallback_error)}")
                
                raise
            
        except Exception as e:
            logger.error(f"Error handling discussion comment: {str(e)}", exc_info=True)
            raise 