import logging
import time
import requests
from typing import List, Dict, Optional
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

    def _update_comment_with_image(self, comment_id: str, image_prompt: str, response_text: str) -> None:
        """
        Update a comment with the generated image.
        
        Args:
            comment_id: The ID of the comment to update
            image_prompt: The prompt used to generate the image
            response_text: The original response text
            
        Returns:
            None
        """
        try:
            logger.info(f"Generating image for comment {comment_id}")
            
            # Generate the image using the Together API
            image_data = self.together_client.generate_image(image_prompt)
            
            if not image_data:
                logger.error("Failed to generate image, keeping placeholder")
                return
                
            logger.info("Successfully generated image, updating comment")
            
            # For GitHub, we need to upload the image to GitHub's asset storage
            # This would typically be done using GitHub's API
            # For now, we'll use a placeholder approach
            
            # In a real implementation, you would:
            # 1. Convert the base64 data to a binary file
            # 2. Upload it to GitHub using their API
            # 3. Get the URL of the uploaded image
            # 4. Use that URL in the markdown
            
            # For demonstration purposes, we'll use a data URL
            # Note: GitHub may not support data URLs for security reasons
            # A proper implementation would use GitHub's asset upload API
            
            # Format the updated response with the image
            updated_response = response_text.replace(
                '<img src="https://github.com/user-attachments/assets/6c765944-a101-4848-b907-ba19f974e55a"', 
                f'<img src="data:image/png;base64,{image_data}"'
            )
            
            # Update the comment with the generated image
            self._update_discussion_comment(comment_id, updated_response)
            
            logger.info(f"Successfully updated comment {comment_id} with generated image")
            
        except Exception as e:
            logger.error(f"Error updating comment with image: {str(e)}")
            # Don't raise the exception to prevent the workflow from failing

    def _format_response(self, response_text: str, discussion_url: str, conversation_history=None, current_message=None) -> str:
        """
        Format the response text with an image at the top.
        
        Args:
            response_text: The text response from the AI
            discussion_url: URL of the discussion
            conversation_history: Optional conversation history for image prompt generation
            current_message: Optional current message for image prompt generation
            
        Returns:
            Formatted response with image placeholder
        """
        try:
            # Generate tarot card prompt if conversation history is provided
            image_prompt = None
            if conversation_history is not None and current_message is not None:
                image_prompt = self.together_client.generate_tarot_prompt(
                    conversation_history=conversation_history,
                    current_message=current_message
                )
                
                # Log the generated prompt
                logger.info(f"Generated image prompt: {image_prompt}")
                
                # Add placeholder image with the prompt as alt text
                placeholder_image = f'\n\n<img src="https://github.com/user-attachments/assets/6c765944-a101-4848-b907-ba19f974e55a" alt="{image_prompt}" width="600">\n\n'
                
                # Return the formatted response with placeholder image
                return f"{placeholder_image}{response_text}"
            
            # If no conversation history, just return the response text
            return response_text
            
        except Exception as e:
            logger.error(f"Error formatting response with image: {str(e)}")
            # Return the original response if image formatting fails
            return response_text

    def handle_discussion(self, event_payload: dict, placeholder_id: Optional[str] = None):
        """Handle a discussion creation or edit event."""
        try:
            # Log event payload structure
            logger.debug(f"Event payload keys: {event_payload.keys()}")
            logger.debug(f"Repository full name: {event_payload.get('repository', {}).get('full_name')}")
            logger.debug(f"Discussion number: {event_payload.get('discussion', {}).get('number')}")
            
            repo_full_name = event_payload['repository']['full_name']
            discussion_number = event_payload['discussion']['number']
            
            try:
                # Get discussion details
                discussion = self._get_discussion(repo_full_name, discussion_number)
                
                # Check if we should respond
                if not self._should_respond(discussion):
                    logger.info(f"Skipping discussion #{discussion_number} - does not meet response criteria")
                    return
                
                # Check if placeholder ID was provided
                placeholder = None
                if placeholder_id and placeholder_id.lower() != "null":
                    try:
                        logger.info(f"Placeholder ID provided: {placeholder_id}")
                        placeholder = self._get_discussion_comment(placeholder_id)
                    except Exception as e:
                        logger.error(f"Failed to get placeholder comment: {str(e)}")
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
                    
                    # Generate tarot card prompt
                    image_prompt = self.together_client.generate_tarot_prompt(
                        conversation_history=history,
                        current_message=discussion['body']
                    )
                    
                    # Format response with image
                    formatted_response = self._format_response(
                        response_text=response, 
                        discussion_url=discussion['url'],
                        conversation_history=history,
                        current_message=discussion['body']
                    )
                    logger.info("Successfully generated response")
                    
                    # Update placeholder or create new comment
                    comment_id = None
                    if placeholder and placeholder.get('id') and placeholder['id'].lower() != "null":
                        try:
                            logger.info(f"Updating placeholder comment {placeholder['id']} with actual response")
                            self._update_discussion_comment(placeholder['id'], formatted_response)
                            logger.info(f"Successfully updated placeholder with actual response")
                            comment_id = placeholder['id']
                        except Exception as e:
                            logger.error(f"Failed to update placeholder: {str(e)}")
                            # If updating fails, try to create a new comment
                            logger.info("Falling back to creating a new comment")
                            new_comment = self._create_discussion_comment(repo_full_name, discussion['id'], formatted_response)
                            comment_id = new_comment['id'] if new_comment else None
                    else:
                        # If no placeholder was created, create a regular comment
                        logger.info("No valid placeholder exists, creating regular comment")
                        new_comment = self._create_discussion_comment(repo_full_name, discussion['id'], formatted_response)
                        comment_id = new_comment['id'] if new_comment else None
                        
                    logger.info(f"Successfully responded to discussion #{discussion_number}")
                    
                    # Generate and update with the actual image if we have a comment ID
                    if comment_id and image_prompt:
                        self._update_comment_with_image(comment_id, image_prompt, response)
                    
                except Exception as e:
                    logger.error(f"Failed to generate response: {str(e)}")
                    
                    # Update placeholder with error message if it exists
                    error_message = (
                        "⚠️ **Error generating response**\n\n"
                        f"I encountered an error while generating a response: {str(e)}\n\n"
                        "Please try again later or contact the repository maintainers if the issue persists."
                    )
                    
                    if placeholder and placeholder.get('id') and placeholder['id'].lower() != "null":
                        try:
                            logger.info(f"Updating placeholder with error message")
                            self._update_discussion_comment(placeholder['id'], error_message)
                        except Exception as update_error:
                            logger.error(f"Failed to update placeholder with error message: {str(update_error)}")
                    else:
                        logger.info("No valid placeholder to update with error message")
                    
                    # Re-raise the exception to be caught by the outer try-except
                    raise
                    
            except Exception as e:
                logger.error(f"Error handling discussion: {str(e)}")
                # Log the error but don't re-raise to prevent the workflow from failing
                
        except Exception as e:
            logger.error(f"Unexpected error in handle_discussion: {str(e)}")
            # Log the error but don't re-raise to prevent the workflow from failing

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

    def handle_discussion_comment(self, event_payload: dict, placeholder_id: Optional[str] = None):
        """Handle a discussion comment creation or edit event."""
        try:
            # Log event payload structure
            logger.debug(f"Event payload keys: {event_payload.keys()}")
            logger.debug(f"Repository full name: {event_payload.get('repository', {}).get('full_name')}")
            logger.debug(f"Discussion number: {event_payload.get('discussion', {}).get('number')}")
            logger.debug(f"Comment ID: {event_payload.get('comment', {}).get('id')}")
            
            repo_full_name = event_payload['repository']['full_name']
            discussion_number = event_payload['discussion']['number']
            comment_id = event_payload['comment']['id']
            
            try:
                # Get discussion and comment details
                discussion = self._get_discussion(repo_full_name, discussion_number)
                comment = self._get_comment(repo_full_name, comment_id)
                
                # Check if we should respond
                if not self._should_respond_to_comment(comment):
                    logger.info(f"Skipping comment {comment_id} - does not meet response criteria")
                    return
                
                # Check if placeholder ID was provided
                placeholder = None
                if placeholder_id and placeholder_id.lower() != "null":
                    try:
                        logger.info(f"Placeholder ID provided: {placeholder_id}")
                        placeholder = self._get_discussion_comment(placeholder_id)
                    except Exception as e:
                        logger.error(f"Failed to get placeholder comment: {str(e)}")
                        # Continue without placeholder if it fails
                        placeholder = None
                
                # Respect cooldown before generating the actual response
                self._respect_cooldown()
                
                # Get conversation history
                history = self._get_conversation_history(discussion, comment)
                
                # Generate response
                logger.info("Generating AI response")
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
                    
                    # Generate tarot card prompt
                    image_prompt = self.together_client.generate_tarot_prompt(
                        conversation_history=history,
                        current_message=comment['body']
                    )
                    
                    # Format response with image
                    formatted_response = self._format_response(
                        response_text=response, 
                        discussion_url=discussion['url'],
                        conversation_history=history,
                        current_message=comment['body']
                    )
                    logger.info("Successfully generated response")
                    
                    # Update placeholder or create new comment
                    reply_id = None
                    if placeholder and placeholder.get('id') and placeholder['id'].lower() != "null":
                        try:
                            logger.info(f"Updating placeholder comment {placeholder['id']} with actual response")
                            self._update_discussion_comment(placeholder['id'], formatted_response)
                            logger.info(f"Successfully updated placeholder with actual response")
                            reply_id = placeholder['id']
                        except Exception as e:
                            logger.error(f"Failed to update placeholder: {str(e)}")
                            # If updating fails, try to create a new reply
                            logger.info("Falling back to creating a new reply")
                            new_reply = self._create_comment_reply(repo_full_name, discussion['id'], comment['id'], formatted_response)
                            reply_id = new_reply['id'] if new_reply else None
                    else:
                        # If no placeholder was created, create a regular reply
                        logger.info("No valid placeholder exists, creating regular reply")
                        new_reply = self._create_comment_reply(repo_full_name, discussion['id'], comment['id'], formatted_response)
                        reply_id = new_reply['id'] if new_reply else None
                        
                    logger.info(f"Successfully responded to comment {comment_id}")
                    
                    # Generate and update with the actual image if we have a reply ID
                    if reply_id and image_prompt:
                        self._update_comment_with_image(reply_id, image_prompt, response)
                    
                except Exception as e:
                    logger.error(f"Failed to generate response: {str(e)}")
                    
                    # Update placeholder with error message if it exists
                    error_message = (
                        "⚠️ **Error generating response**\n\n"
                        f"I encountered an error while generating a response: {str(e)}\n\n"
                        "Please try again later or contact the repository maintainers if the issue persists."
                    )
                    
                    if placeholder and placeholder.get('id') and placeholder['id'].lower() != "null":
                        try:
                            logger.info(f"Updating placeholder with error message")
                            self._update_discussion_comment(placeholder['id'], error_message)
                        except Exception as update_error:
                            logger.error(f"Failed to update placeholder with error message: {str(update_error)}")
                    else:
                        logger.info("No valid placeholder to update with error message")
                    
                    # Re-raise the exception to be caught by the outer try-except
                    raise
                    
            except Exception as e:
                logger.error(f"Error handling comment: {str(e)}")
                # Log the error but don't re-raise to prevent the workflow from failing
                
        except Exception as e:
            logger.error(f"Unexpected error in handle_discussion_comment: {str(e)}")
            # Log the error but don't re-raise to prevent the workflow from failing 