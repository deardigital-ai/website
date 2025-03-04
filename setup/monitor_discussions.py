import json
import os
import time
import requests
import subprocess
import logging
import traceback
import sys
from datetime import datetime, timedelta
import argparse

# Setup logging
log_file = "discussion_bot.log"
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("discussion-monitor")

def get_recent_discussions(repo, token, since_minutes=5):
    """Get discussions created or updated in the last few minutes"""
    logger.debug(f"Checking for discussions updated in the last {since_minutes} minutes")
    owner, repo_name = repo.split('/')
    
    # Calculate the time threshold
    since_time = datetime.utcnow() - timedelta(minutes=since_minutes)
    since_iso = since_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    logger.debug(f"Looking for discussions updated since {since_iso}")
    
    # GraphQL query to get recent discussions
    query = """
    query($owner: String!, $name: String!, $since: DateTime!) {
      repository(owner: $owner, name: $name) {
        discussions(first: 10, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            id
            title
            body
            createdAt
            updatedAt
            number
            comments(last: 5) {
              nodes {
                id
                body
                createdAt
                updatedAt
              }
            }
          }
        }
      }
    }
    """
    
    variables = {
        "owner": owner,
        "name": repo_name,
        "since": since_iso
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        logger.debug(f"Sending GraphQL request to GitHub API for {owner}/{repo_name}")
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": variables}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch discussions: {response.text}")
            return []
        
        data = response.json()
        
        # Log the raw response for debugging
        logger.debug(f"GitHub API Response: {json.dumps(data, indent=2)}")
        
        discussions = data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
        logger.debug(f"Found {len(discussions)} discussions")
        
        # Filter discussions updated since the threshold time
        recent_discussions = []
        for discussion in discussions:
            updated_at = datetime.strptime(discussion["updatedAt"], '%Y-%m-%dT%H:%M:%SZ')
            if updated_at >= since_time:
                logger.debug(f"Adding discussion #{discussion['number']} to process list (updated at {discussion['updatedAt']})")
                recent_discussions.append(discussion)
                
                # Check for recent comments
                comments = discussion.get("comments", {}).get("nodes", [])
                logger.debug(f"Discussion #{discussion['number']} has {len(comments)} recent comments")
                
                for comment in comments:
                    comment_updated_at = datetime.strptime(comment["updatedAt"], '%Y-%m-%dT%H:%M:%SZ')
                    if comment_updated_at >= since_time:
                        logger.debug(f"Adding comment {comment['id']} from discussion #{discussion['number']} to process list")
                        recent_discussions.append({
                            "type": "comment",
                            "discussion_id": discussion["id"],
                            "comment_id": comment["id"],
                            "body": comment["body"],
                            "discussion_number": discussion["number"]
                        })
        
        logger.info(f"Found {len(recent_discussions)} discussions/comments to process")
        return recent_discussions
    except Exception as e:
        logger.error(f"Error fetching discussions: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def process_discussion(discussion, repo, token):
    """Process a single discussion or comment"""
    try:
        if discussion.get("type") == "comment":
            logger.info(f"Processing comment in discussion #{discussion['discussion_number']}")
            logger.debug(f"Comment body: {discussion['body'][:100]}...")
            # Create event payload similar to GitHub's webhook payload
            event_payload = {
                "action": "created",
                "discussion": {
                    "node_id": discussion["discussion_id"],
                    "number": discussion["discussion_number"]
                },
                "comment": {
                    "node_id": discussion["comment_id"],
                    "body": discussion["body"]
                },
                "repository": {
                    "full_name": repo,
                    "owner": {
                        "login": repo.split('/')[0]
                    },
                    "name": repo.split('/')[1]
                }
            }
            event_type = "discussion_comment"
        else:
            logger.info(f"Processing discussion #{discussion['number']}: {discussion['title']}")
            logger.debug(f"Discussion body: {discussion['body'][:100]}...")
            # Create event payload similar to GitHub's webhook payload
            event_payload = {
                "action": "created",
                "discussion": {
                    "node_id": discussion["id"],
                    "title": discussion["title"],
                    "body": discussion["body"],
                    "number": discussion["number"]
                },
                "repository": {
                    "full_name": repo,
                    "owner": {
                        "login": repo.split('/')[0]
                    },
                    "name": repo.split('/')[1]
                }
            }
            event_type = "discussion"
        
        # Write event payload to file
        event_payload_file = "event_payload.json"
        with open(event_payload_file, "w") as f:
            json.dump(event_payload, f, indent=2)
        logger.debug(f"Wrote event payload to {event_payload_file}")
        
        # Create placeholder comment and get its ID
        placeholder_id = create_placeholder(event_type, event_payload, token)
        logger.info(f"Created placeholder comment with ID: {placeholder_id}")
        
        # Run the discussion bot
        cmd = [
            "python3", "python/main.py",
            "--github-event", event_type,
            "--event-payload-file", event_payload_file,
            "--placeholder-id", placeholder_id
        ]
        
        logger.debug(f"Running command: {' '.join(cmd)}")
        try:
            # Capture output for logging
            process = subprocess.run(
                cmd, 
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.debug(f"Command stdout: {process.stdout}")
            logger.debug(f"Command stderr: {process.stderr}")
            logger.info(f"Successfully processed {event_type}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error processing {event_type}: {str(e)}")
            logger.error(f"Command stdout: {e.stdout}")
            logger.error(f"Command stderr: {e.stderr}")
    except Exception as e:
        logger.error(f"Error in process_discussion: {str(e)}")
        logger.error(traceback.format_exc())

def create_placeholder(event_type, event_payload, token):
    """Create a placeholder comment and return its ID"""
    try:
        placeholder_text = '![Loading animation](https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif)\n\ndeardigital AI generating response...'
        
        if event_type == "discussion":
            # Create placeholder for discussion
            discussion_id = event_payload["discussion"]["node_id"]
            logger.debug(f"Creating placeholder for discussion with ID: {discussion_id}")
            
            query = """
            mutation($discussionId: ID!, $body: String!) {
              addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
                comment { id }
              }
            }
            """
            
            variables = {
                "discussionId": discussion_id,
                "body": placeholder_text
            }
        else:
            # Create placeholder for comment
            discussion_id = event_payload["discussion"]["node_id"]
            comment_id = event_payload["comment"]["node_id"]
            logger.debug(f"Creating placeholder reply to comment {comment_id} in discussion {discussion_id}")
            
            query = """
            mutation($discussionId: ID!, $replyToId: ID!, $body: String!) {
              addDiscussionComment(input: {discussionId: $discussionId, replyToId: $replyToId, body: $body}) {
                comment { id }
              }
            }
            """
            
            variables = {
                "discussionId": discussion_id,
                "replyToId": comment_id,
                "body": placeholder_text
            }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.debug(f"Sending GraphQL mutation to create placeholder")
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": variables}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to create placeholder: {response.text}")
            return "null"
        
        data = response.json()
        logger.debug(f"Placeholder creation response: {json.dumps(data, indent=2)}")
        
        comment_id = data.get("data", {}).get("addDiscussionComment", {}).get("comment", {}).get("id", "null")
        logger.info(f"Created placeholder comment with ID: {comment_id}")
        return comment_id
    except Exception as e:
        logger.error(f"Error creating placeholder: {str(e)}")
        logger.error(traceback.format_exc())
        return "null"

def main():
    """Main monitoring loop"""
    parser = argparse.ArgumentParser(description='GitHub Discussion Monitor')
    parser.add_argument('--token', help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--repo', help='Repository in format owner/name (or set REPOSITORY env var)')
    parser.add_argument('--interval', type=int, default=10, help='Polling interval in seconds (default: 10)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Log environment information
    logger.info("Starting discussion bot with environment:")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    token = args.token or os.environ.get("GITHUB_TOKEN")
    repo = args.repo or os.environ.get("REPOSITORY")
    interval = args.interval
    
    logger.info(f"Repository: {repo or 'Not set'}")
    logger.info(f"GITHUB_TOKEN set: {'Yes' if token else 'No'}")
    logger.info(f"TOGETHER_API_KEY set: {'Yes' if os.environ.get('TOGETHER_API_KEY') else 'No'}")
    
    if not token or not repo:
        logger.error("GitHub token and repository must be provided via arguments or environment variables")
        return
    
    logger.info(f"Starting discussion monitor for {repo}")
    logger.info(f"Polling interval: {interval} seconds")
    logger.info(f"Log file: {os.path.abspath(log_file)}")
    
    # Keep track of processed discussions to avoid duplicates
    processed_ids = set()
    
    try:
        while True:
            try:
                # Get recent discussions
                logger.debug("Checking for recent discussions...")
                discussions = get_recent_discussions(repo, token)
                
                for discussion in discussions:
                    # Generate a unique ID for this discussion or comment
                    if discussion.get("type") == "comment":
                        unique_id = f"comment-{discussion['comment_id']}"
                    else:
                        unique_id = f"discussion-{discussion['id']}"
                    
                    # Skip if already processed
                    if unique_id in processed_ids:
                        logger.debug(f"Skipping already processed item: {unique_id}")
                        continue
                    
                    # Process the discussion
                    logger.info(f"Processing new item: {unique_id}")
                    process_discussion(discussion, repo, token)
                    processed_ids.add(unique_id)
                    logger.debug(f"Added {unique_id} to processed items")
                
                # Limit the size of processed_ids to avoid memory issues
                if len(processed_ids) > 1000:
                    logger.debug("Trimming processed_ids list to avoid memory issues")
                    processed_ids = set(list(processed_ids)[-500:])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                logger.error(traceback.format_exc())
            
            # Sleep for the specified interval before checking again
            logger.debug(f"Sleeping for {interval} seconds before next check")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")

if __name__ == "__main__":
    main() 