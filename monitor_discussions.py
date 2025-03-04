import json
import os
import time
import requests
import subprocess
import logging
import traceback
import sys
import socket
import re
from datetime import datetime, timedelta

# Setup logging with sensitive information filter
log_file = "discussion_bot.log"

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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("discussion-monitor")

# Add sensitive info filter to all handlers
sensitive_filter = SensitiveInfoFilter()
for handler in logger.handlers:
    handler.addFilter(sensitive_filter)

# Log environment information
logger.info("Starting discussion bot with environment:")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Repository: {os.environ.get('REPOSITORY', 'Not set')}")
logger.info(f"GITHUB_TOKEN set: {'Yes' if os.environ.get('GITHUB_TOKEN') else 'No'}")
logger.info(f"TOGETHER_API_KEY set: {'Yes' if os.environ.get('TOGETHER_API_KEY') else 'No'}")

def get_recent_discussions(repo, token, since_minutes=5):
    """Get discussions created or updated in the last few minutes"""
    logger.debug(f"Checking for discussions updated in the last {since_minutes} minutes")
    owner, repo_name = repo.split('/')
    
    # Calculate the time threshold
    since_time = datetime.utcnow() - timedelta(minutes=since_minutes)
    since_iso = since_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    logger.debug(f"Looking for discussions updated since {since_iso}")
    
    # GraphQL query to get recent discussions
    # Fixed query to actually use the $since variable in the filter
    query = """
    query($owner: String!, $name: String!, $since: DateTime!) {
      repository(owner: $owner, name: $name) {
        discussions(first: 10, orderBy: {field: UPDATED_AT, direction: DESC}, filterBy: {updatedSince: $since}) {
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