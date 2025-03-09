# Auto Discussion Generator

This GitHub Action automatically creates new discussions in your repository using a local AI model. It generates discussion topics related to AI automation or GitHub, with engaging content to spark community conversations.

## Features

- Automatically creates new GitHub discussions on a schedule
- Uses a local AI model (`qwq:latest`) to generate content
- Topics focus on AI automation and GitHub
- Runs on self-hosted runners for privacy and control
- Can be triggered manually via workflow_dispatch

## Setup Instructions

### 1. Configure the Category ID

Before using this action, you need to set the correct category ID for your repository's discussions. To find your category ID:

1. Go to your repository's Discussions tab
2. Open browser developer tools (F12)
3. Navigate to a specific category
4. Look for a URL parameter or element with an ID like `DIC_kwDOLYQwhs4CZvYA`
5. Update the `categoryId` value in the workflow file with your actual category ID

```yaml
# In auto-discussion.yml
const categoryId = 'YOUR_CATEGORY_ID_HERE';  # Replace with your actual category ID
```

### 2. Ensure Self-Hosted Runner Setup

This action requires a self-hosted runner with:

- Access to the local Ollama API at `http://localhost:11434`
- The `qwq:latest` model installed and available
- Required tools: `curl`, `jq`, and `md5sum`

### 3. Adjust Schedule (Optional)

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
5. Verify the category ID is correct

## Customization

You can customize the AI prompts in the workflow file to change:

- Topic focus areas
- Discussion length and style
- Content structure

## Manual Triggering

You can manually trigger the workflow from the Actions tab in your repository by selecting "Auto Discussion Generator" and clicking "Run workflow". 