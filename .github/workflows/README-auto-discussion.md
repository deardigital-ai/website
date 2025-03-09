# Auto Discussion Generator

This GitHub Action automatically creates new discussions in your repository using a local AI model. It generates discussion topics related to AI automation or GitHub, with engaging content to spark community conversations.

## Features

- Automatically creates new GitHub discussions on a schedule
- Uses a local AI model (`qwq:latest`) to generate content
- Topics focus on AI automation and GitHub
- Runs on self-hosted runners for privacy and control
- Can be triggered manually via workflow_dispatch
- Automatically detects repository and discussion category IDs

## Setup Instructions

### 1. Discussion Categories

The action will automatically use the first available discussion category in your repository. If you want to use a specific category:

1. Go to your repository's Discussions tab and ensure discussions are enabled
2. Create categories if you don't have any
3. If you want to use a specific category, modify the `categoryId` fallback value in the workflow file

```yaml
# In auto-discussion.yml
let categoryId = 'YOUR_CATEGORY_ID_HERE'; // Default fallback
```

### 2. Ensure Self-Hosted Runner Setup

This action requires a self-hosted runner with:

- Access to the local Ollama API at `http://localhost:11434`
- The `qwq:latest` model installed and available
- Required tools: `curl`, `jq`, `perl`, and `md5sum`

### 3. Test Ollama API

Before running the action, you can test if the Ollama API is working correctly using the provided test script:

```bash
# Make the script executable if needed
chmod +x .github/scripts/test-ollama-api.sh

# Run the test script
.github/scripts/test-ollama-api.sh
```

The script will check if:
- The Ollama API is accessible
- The qwq model is available
- Content generation works correctly

### 4. Adjust Schedule (Optional)

By default, the action runs every minute. You can adjust the schedule by modifying the cron expression:

```yaml
schedule:
  - cron: '*/5 * * * *'  # Run every 5 minutes
```

## Troubleshooting

If discussions aren't being created:

1. Check that your self-hosted runner is active
2. Verify the Ollama API is accessible at http://localhost:11434
3. Ensure the qwq:latest model is installed
4. Confirm your GitHub token has permission to create discussions
5. Check the workflow logs to see if the repository ID and category ID are being correctly detected
6. Ensure discussions are enabled for your repository

### Common Errors

#### "Could not resolve to a node with the global id"
This error occurs when the repository ID is incorrect. The action now automatically detects the correct repository ID using GraphQL.

#### "Discussion category not found"
This error occurs when the category ID is incorrect. The action will try to use the first available category, but if none are found, it will use the fallback value.

#### AI Model Output Contains `<think>` Tags
If you see `<think>` tags in the generated content, the action now uses improved filtering with Perl to remove these tags and their content.

## Customization

You can customize the AI prompts in the workflow file to change:

- Topic focus areas
- Discussion length and style
- Content structure

## Manual Triggering

You can manually trigger the workflow from the Actions tab in your repository by selecting "Auto Discussion Generator" and clicking "Run workflow".

## Helper Script

A helper script is available to find discussion category IDs if you need to specify a particular category:

```bash
# Install dependencies
npm install @octokit/graphql

# Set your GitHub token
export GITHUB_TOKEN=your_token_here

# Run the script
node .github/scripts/find-discussion-category-id.js owner repo
``` 