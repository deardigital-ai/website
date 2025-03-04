import json
import os
import time
import requests
import subprocess
import logging
from datetime import datetime, timedelta
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("discussion-monitor")

def get_recent_discussions(repo, token, since_minutes=5):
    """Get discussions created or updated in the last few minutes"""
    owner, repo_name = repo.split('/')
    
    # Calculate the time threshold
    since_time = datetime.utcnow() - timedelta(minutes=since_minutes)
    since_iso = since_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
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
    
    response = requests.post(
        "https://api.github.com/graphql",
        headers=headers,
        json={"query": query, "variables": variables}
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch discussions: {response.text}")
        return []
    
    data = response.json()
    discussions = data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
    
    # Filter discussions updated since the threshold time
    recent_discussions = []
    for discussion in discussions:
        updated_at = datetime.strptime(discussion["updatedAt"], '%Y-%m-%dT%H:%M:%SZ')
        if updated_at >= since_time:
            recent_discussions.append(discussion)
            
            # Check for recent comments
            for comment in discussion.get("comments", {}).get("nodes", []):
                comment_updated_at = datetime.strptime(comment["updatedAt"], '%Y-%m-%dT%H:%M:%SZ')
                if comment_updated_at >= since_time:
                    # Add this as a comment event
                    recent_discussions.append({
                        "type": "comment",
                        "discussion_id": discussion["id"],
                        "comment_id": comment["id"],
                        "body": comment["body"],
                        "discussion_number": discussion["number"]
                    })
    
    return recent_discussions

def process_discussion(discussion, repo, token):
    """Process a single discussion or comment"""
    if discussion.get("type") == "comment":
        logger.info(f"Processing comment in discussion #{discussion['discussion_number']}")
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
    with open("event_payload.json", "w") as f:
        json.dump(event_payload, f)
    
    # Create placeholder comment and get its ID
    placeholder_id = create_placeholder(event_type, event_payload, token)
    
    # Run the discussion bot
    cmd = [
        "python3", "python/main.py",
        "--github-event", event_type,
        "--event-payload-file", "event_payload.json",
        "--placeholder-id", placeholder_id
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logger.info(f"Successfully processed {event_type}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing {event_type}: {str(e)}")

def create_placeholder(event_type, event_payload, token):
    """Create a placeholder comment and return its ID"""
    placeholder_text = '![Loading animation](https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif)\n\ndeardigital AI generating response...'
    
    if event_type == "discussion":
        # Create placeholder for discussion
        discussion_id = event_payload["discussion"]["node_id"]
        
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
    
    response = requests.post(
        "https://api.github.com/graphql",
        headers=headers,
        json={"query": query, "variables": variables}
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to create placeholder: {response.text}")
        return "null"
    
    data = response.json()
    comment_id = data.get("data", {}).get("addDiscussionComment", {}).get("comment", {}).get("id", "null")
    logger.info(f"Created placeholder comment with ID: {comment_id}")
    return comment_id

def main():
    """Main monitoring loop"""
    parser = argparse.ArgumentParser(description='GitHub Discussion Monitor')
    parser.add_argument('--token', help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--repo', help='Repository in format owner/name (or set REPOSITORY env var)')
    parser.add_argument('--interval', type=int, default=10, help='Polling interval in seconds (default: 10)')
    args = parser.parse_args()
    
    token = args.token or os.environ.get("GITHUB_TOKEN")
    repo = args.repo or os.environ.get("REPOSITORY")
    interval = args.interval
    
    if not token or not repo:
        logger.error("GitHub token and repository must be provided via arguments or environment variables")
        return
    
    logger.info(f"Starting discussion monitor for {repo}")
    logger.info(f"Polling interval: {interval} seconds")
    
    # Keep track of processed discussions to avoid duplicates
    processed_ids = set()
    
    try:
        while True:
            try:
                # Get recent discussions
                discussions = get_recent_discussions(repo, token)
                
                for discussion in discussions:
                    # Generate a unique ID for this discussion or comment
                    if discussion.get("type") == "comment":
                        unique_id = f"comment-{discussion['comment_id']}"
                    else:
                        unique_id = f"discussion-{discussion['id']}"
                    
                    # Skip if already processed
                    if unique_id in processed_ids:
                        continue
                    
                    # Process the discussion
                    process_discussion(discussion, repo, token)
                    processed_ids.add(unique_id)
                
                # Limit the size of processed_ids to avoid memory issues
                if len(processed_ids) > 1000:
                    processed_ids = set(list(processed_ids)[-500:])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}", exc_info=True)
            
            # Sleep for the specified interval before checking again
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")

if __name__ == "__main__":
    main() 